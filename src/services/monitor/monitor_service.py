#!/usr/bin/env python3
"""
Monitor service to watch for retraining signal file and trigger model retraining.
This module provides the core functionality for the retraining monitor service.
"""

import os
import time
import logging
import docker
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("retrain-monitor")

class RetrainingMonitor:
    """
    Service that monitors for retraining signal files and triggers model retraining.
    """
    
    def __init__(
        self, 
        signal_file_path=None, 
        check_interval=None,
        service_name="train-model"
    ):
        """
        Initialize the retraining monitor service.
        
        Args:
            signal_file_path (str, optional): Path to the signal file to monitor.
                Defaults to environment variable SIGNAL_FILE_PATH or "/app/data-file/retrain_requested".
            check_interval (int, optional): Interval in seconds between checks.
                Defaults to environment variable CHECK_INTERVAL or 5.
            service_name (str, optional): Name of the service to restart.
                Defaults to "train-model".
        """
        self.signal_file = signal_file_path or os.environ.get(
            "SIGNAL_FILE_PATH", "/app/data-file/retrain_requested"
        )
        self.check_interval = int(check_interval or os.environ.get("CHECK_INTERVAL", "5"))
        self.service_name = service_name
        
        # Initialize Docker client
        self.docker_client = docker.from_env()
        
        logger.info(f"Initialized retraining monitor with signal file: {self.signal_file}")
        logger.info(f"Check interval: {self.check_interval} seconds")
        logger.info(f"Service to restart: {self.service_name}")
    
    def _trigger_retraining(self):
        """
        Trigger the model retraining process by restarting the train-model service.
        
        Returns:
            bool: True if retraining was triggered successfully, False otherwise.
        """
        try:
            logger.info(f"Restarting {self.service_name} service...")
            
            # Find the container for the train-model service
            # In Docker Compose, container names are prefixed with the project name
            # and may include a sequence number, so we use a partial match
            containers = self.docker_client.containers.list(
                all=True,
                filters={"name": self.service_name}
            )
            
            if not containers:
                logger.error(f"No container found for service {self.service_name}")
                
                # Try a more generic search
                logger.info("Trying a more generic search for the container...")
                all_containers = self.docker_client.containers.list(all=True)
                containers = [c for c in all_containers if self.service_name in c.name]
                
                if not containers:
                    logger.error("Still no container found. Available containers:")
                    for c in all_containers:
                        logger.error(f"  - {c.name}")
                    return False
            
            # Restart the container
            for container in containers:
                logger.info(f"Found container: {container.name}, restarting...")
                container.restart()
                logger.info(f"Container {container.name} restarted successfully")
            
            logger.info("Model retraining triggered successfully")
            return True
        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error during retraining: {str(e)}")
            return False
    
    def run(self):
        """
        Run the monitoring loop to check for signal files and trigger retraining.
        This method runs indefinitely until interrupted.
        """
        logger.info("Starting retraining monitor service...")
        logger.info(f"Watching for signal file: {self.signal_file}")
        
        while True:
            if os.path.exists(self.signal_file):
                logger.info(f"Retraining signal file detected: {self.signal_file}")
                
                # Read the signal file content
                try:
                    with open(self.signal_file, 'r') as f:
                        content = f.read()
                        logger.info(f"Signal file content: {content}")
                except Exception as e:
                    logger.error(f"Error reading signal file: {str(e)}")
                    content = "Unknown"
                
                # Remove the signal file
                try:
                    os.remove(self.signal_file)
                    logger.info("Signal file removed")
                except Exception as e:
                    logger.error(f"Error removing signal file: {str(e)}")
                
                # Trigger retraining
                self._trigger_retraining()
            else:
                logger.debug(f"No signal file found at {self.signal_file}")
            
            # Wait before checking again
            time.sleep(self.check_interval)


def main():
    """
    Main entry point for the retraining monitor service.
    """
    monitor = RetrainingMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
