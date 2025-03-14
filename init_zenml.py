#!/usr/bin/env python3
"""
Script to initialize ZenML repository and stack using the Python API.
This should be run before the pipeline to ensure proper configuration.
"""

import os
import sys
import logging
import time
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("zenml-init")

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

def setup_zenml():
    """
    Initialize ZenML repository and set up the stack using the Python API.
    """
    # Wait for ZenML server to be available
    zenml_url = os.environ.get("ZENML_SERVER_URL", "http://zenml:8080")
    logger.info(f"Waiting for ZenML server at {zenml_url}...")
    if not wait_for_service(zenml_url):
        logger.error("ZenML server not available. Exiting.")
        sys.exit(1)
    
    # Wait for MLflow server to be available
    mlflow_url = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    logger.info(f"Waiting for MLflow server at {mlflow_url}...")
    if not wait_for_service(mlflow_url):
        logger.error("MLflow server not available. Exiting.")
        sys.exit(1)
    
    # Set up ZenML client with API key authentication
    api_key = os.environ.get("ZENML_API_KEY")
    if not api_key:
        logger.error("ZENML_API_KEY environment variable not set. Exiting.")
        sys.exit(1)
    
    # Set environment variables for ZenML client
    os.environ["ZENML_STORE_TYPE"] = "rest"
    os.environ["ZENML_STORE_URL"] = zenml_url
    os.environ["ZENML_STORE_API_KEY"] = api_key
    
    try:
        # Import ZenML modules
        from zenml.client import Client
        
        # Initialize ZenML client
        logger.info("Initializing ZenML client...")
        client = Client()
        logger.info("ZenML client initialized successfully!")
        
        # Now we can proceed with running the pipeline
        logger.info("ZenML initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Unexpected error during ZenML initialization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_zenml()
