#!/usr/bin/env python3
"""
Script to set up a ZenML API key for non-interactive authentication.
This is designed for use with ZenML 0.75.0 in containerized environments.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("zenml-api-key-setup")

def save_api_key_to_env_file(api_key: str, env_file: str = ".env"):
    """
    Save the API key to a .env file for use with docker-compose.
    
    Args:
        api_key: The API key to save
        env_file: Path to the .env file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        env_path = Path(env_file)
        
        # Read existing content if file exists
        env_content = {}
        if env_path.exists():
            with open(env_path, "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        env_content[key] = value
        
        # Update or add the API key
        env_content["ZENML_API_KEY"] = api_key
        
        # Write back to file
        with open(env_path, "w") as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
                
        logger.info(f"API key saved to {env_file}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save API key to {env_file}: {e}")
        return False

def main():
    """
    Main function to set up ZenML API key.
    """
    parser = argparse.ArgumentParser(description="Set up ZenML API key for docker-compose")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument("--api-key", help="ZenML API key to use (if not provided, will prompt for input)")
    args = parser.parse_args()
    
    # Get API key from command line or prompt
    api_key = args.api_key
    if not api_key:
        print("\nPlease enter the ZenML API key (starts with 'ZENKEY_'):")
        api_key = input("> ").strip()
    
    if not api_key or not api_key.startswith("ZENKEY_"):
        logger.error("Invalid API key format. API key should start with 'ZENKEY_'")
        sys.exit(1)
    
    # Save API key to .env file
    if not save_api_key_to_env_file(api_key, args.env_file):
        logger.error("Failed to save API key to .env file")
        sys.exit(1)
    
    logger.info(f"ZenML API key setup completed successfully!")
    logger.info(f"API key saved to {args.env_file} file with variable name ZENML_API_KEY")
    logger.info(f"To use this key with docker-compose, run: docker-compose up -d")

if __name__ == "__main__":
    main()
