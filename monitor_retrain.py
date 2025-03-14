#!/usr/bin/env python3
"""
Monitor script to watch for retraining signal file and trigger model retraining.
This script should be run as a separate process or container.
"""

import os
import time
import subprocess
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("retrain-monitor")

SIGNAL_FILE = "data-file/retrain_requested"  # Relative path
CHECK_INTERVAL = 5  # seconds

def main():
    """Main monitoring loop."""
    logger.info("Starting retraining monitor...")
    logger.info(f"Watching for signal file: {os.path.abspath(SIGNAL_FILE)}")
    
    while True:
        if os.path.exists(SIGNAL_FILE):
            logger.info(f"Retraining signal file detected: {SIGNAL_FILE}")
            
            # Read the signal file content
            with open(SIGNAL_FILE, 'r') as f:
                content = f.read()
                logger.info(f"Signal file content: {content}")
            
            # Remove the signal file
            os.remove(SIGNAL_FILE)
            logger.info("Signal file removed")
            
            # Trigger retraining by restarting the train-model service
            try:
                logger.info("Restarting train-model service...")
                result = subprocess.run(
                    ["docker-compose", "restart", "train-model"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.info(f"Restart command output: {result.stdout}")
                logger.info("Model retraining triggered successfully")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to restart train-model service: {e.stderr}")
            except Exception as e:
                logger.error(f"Error during retraining: {str(e)}")
        else:
            logger.debug(f"No signal file found at {os.path.abspath(SIGNAL_FILE)}")
        
        # Wait before checking again
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
