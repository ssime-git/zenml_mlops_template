#!/usr/bin/env python3
"""
This script runs the ML pipeline for training a model on the Iris dataset.
It handles ZenML stack setup and pipeline execution.
"""

import os
import sys
import logging
import time
import requests
import subprocess

# Add the src directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline.pipeline import create_pipeline
from src.pipeline.data_preprocess import preprocess_data
from src.pipeline.train_model import train_model

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pipeline-runner")

def wait_for_service(url: str, max_retries: int = 30, retry_interval: int = 5):
    """
    Wait for a service to be available.
    
    Args:
        url: URL to check
        max_retries: Maximum number of retries
        retry_interval: Interval between retries in seconds
    
    Returns:
        bool: True if service is available, False otherwise
    """
    for i in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                logger.info(f"{url} is available!")
                return True
        except requests.RequestException:
            logger.info(f"{url} not available yet. Retrying in {retry_interval}s... ({i+1}/{max_retries})")
            time.sleep(retry_interval)
    
    logger.error(f"Could not connect to {url} after {max_retries} retries")
    return False

def login_to_zenml():
    """
    Configure ZenML client with API key authentication.
    """
    try:
        # Log environment variables for debugging
        logger.info("ZenML Environment variables:")
        for key, value in sorted(os.environ.items()):
            if key.startswith("ZENML_"):
                # Mask the actual API key value for security
                if key in ["ZENML_API_KEY"]:
                    logger.info(f"{key}=****")
                else:
                    logger.info(f"{key}={value}")
        
        # Get server URL and API key from environment
        server_url = os.environ.get("ZENML_SERVER_URL")
        api_key = os.environ.get("ZENML_API_KEY")
        
        if not server_url or not api_key:
            logger.error("Missing required environment variables for ZenML authentication")
            return False
        
        # Set environment variables for ZenML client
        os.environ["ZENML_STORE_TYPE"] = "rest"
        os.environ["ZENML_STORE_URL"] = server_url
        os.environ["ZENML_STORE_API_KEY"] = api_key
        
        # Import ZenML client to test connection
        from zenml.client import Client
        
        # Initialize ZenML client to test connection
        logger.info(f"Connecting to ZenML server at {server_url} with API key authentication")
        client = Client()
        
        # Test connection by getting active stack
        active_stack = client.active_stack.name
        logger.info(f"Successfully connected to ZenML server. Active stack: {active_stack}")
        return True
    
    except Exception as e:
        logger.error(f"Error connecting to ZenML server: {e}")
        return False

def setup_zenml_stack():
    """
    Set up the ZenML stack with MLflow integration.
    """
    try:
        # Initialize repository
        try:
            subprocess.run(["zenml", "init"], check=True)
            logger.info("ZenML repository initialized successfully!")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Error initializing repository: {e}")
            logger.warning("Repository may already be initialized")
        
        # Import ZenML modules
        from zenml.client import Client
        
        # Initialize ZenML client
        logger.info("Initializing ZenML client...")
        client = Client()
        logger.info("ZenML client initialized successfully!")
        
        # Register MLflow tracker if it doesn't exist
        try:
            client.get_stack_component("mlflow_tracker")
            logger.info("MLflow tracker already exists")
        except Exception:
            # Register MLflow tracker
            from zenml.integrations.mlflow import MLFlowExperimentTracker
            
            mlflow_tracker = MLFlowExperimentTracker(
                name="mlflow_tracker",
                tracking_uri=os.environ.get("MLFLOW_TRACKING_URI")
            )
            client.register_stack_component(mlflow_tracker)
            logger.info("MLflow tracker registered")
        
        # Register artifact store if it doesn't exist
        try:
            client.get_stack_component("local_store")
            logger.info("Artifact store already exists")
        except Exception:
            # Register artifact store
            from zenml.artifact_stores import LocalArtifactStore
            
            artifact_store = LocalArtifactStore(
                name="local_store",
                path="/app/data-file"
            )
            client.register_stack_component(artifact_store)
            logger.info("Artifact store registered")
        
        # Register orchestrator if it doesn't exist
        try:
            client.get_stack_component("local_orchestrator")
            logger.info("Orchestrator already exists")
        except Exception:
            # Register orchestrator
            from zenml.orchestrators import LocalOrchestrator
            
            orchestrator = LocalOrchestrator(
                name="local_orchestrator"
            )
            client.register_stack_component(orchestrator)
            logger.info("Orchestrator registered")
        
        # Register stack if it doesn't exist
        try:
            client.get_stack("local_stack")
            logger.info("Stack already exists")
        except Exception:
            # Register stack
            from zenml.stack import Stack
            
            stack = Stack(
                name="local_stack",
                orchestrator="local_orchestrator",
                artifact_store="local_store",
                experiment_tracker="mlflow_tracker"
            )
            client.register_stack(stack)
            logger.info("Stack registered")
        
        # Set active stack
        client.activate_stack("local_stack")
        logger.info("local_stack is now active")
        
        return True
    except Exception as e:
        logger.error(f"Error setting up ZenML stack: {e}")
        return False

def main():
    """
    Main function to run the pipeline.
    """
    # Wait for MLflow server to be available
    mlflow_url = os.environ.get("MLFLOW_TRACKING_URI")
    logger.info(f"Waiting for MLflow server at {mlflow_url}...")
    if not wait_for_service(mlflow_url):
        logger.error("MLflow server not available. Exiting.")
        sys.exit(1)
    
    # Wait for ZenML server to be available
    zenml_url = os.environ.get("ZENML_SERVER_URL")
    logger.info(f"Waiting for ZenML server at {zenml_url}...")
    if not wait_for_service(zenml_url):
        logger.error("ZenML server not available. Exiting.")
        sys.exit(1)
    
    logger.info(f"Using ZenML server at {zenml_url}")
    
    try:
        # Login to ZenML server
        if not login_to_zenml():
            logger.error("Failed to login to ZenML server. Exiting.")
            sys.exit(1)
        
        # Set up ZenML stack
        if not setup_zenml_stack():
            logger.error("Failed to set up ZenML stack. Exiting.")
            sys.exit(1)
        
        # Create and run the pipeline
        logger.info("Creating and running the pipeline...")
        pipeline = create_pipeline(preprocess_data, train_model)
        pipeline.run()
        logger.info("Pipeline completed successfully!")
        
    except Exception as e:
        logger.error(f"Error running pipeline: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
