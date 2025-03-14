#!/usr/bin/env python3
"""
Script to set up a ZenML service account and API key for non-interactive authentication.
This is designed for use with ZenML 0.75.0 in containerized environments.
"""

import os
import sys
import logging
import subprocess
import argparse
import re
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("zenml-api-key-setup")

def connect_to_zenml_server(server_url: str):
    """
    Connect to the ZenML server.
    
    Args:
        server_url: URL of the ZenML server
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Connecting to ZenML server at {server_url}")
        result = subprocess.run(
            ["zenml", "connect", server_url],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Successfully connected to ZenML server at {server_url}")
            return True
        else:
            logger.error(f"Failed to connect to ZenML server: {result.stderr}")
            return False
    
    except Exception as e:
        logger.error(f"Error connecting to ZenML server: {e}")
        return False

def login_to_zenml(username: str, password: str):
    """
    Login to ZenML server using CLI.
    
    Args:
        username: Username for login
        password: Password for login
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Logging in to ZenML server with username {username}")
        
        # For ZenML 0.75.0, we need to use an interactive approach
        # Create a temporary file with username and password
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(f"{username}\n{password}\n")
            temp_file = f.name
        
        try:
            # Use the expect-like approach to provide username and password
            login_cmd = f"cat {temp_file} | zenml login"
            login_result = subprocess.run(login_cmd, shell=True, capture_output=True, text=True)
            
            if "Successfully logged in" in login_result.stdout or login_result.returncode == 0:
                logger.info("Successfully logged in to ZenML server")
                return True
            else:
                logger.error(f"Failed to login to ZenML server: {login_result.stderr}")
                logger.error(f"Login output: {login_result.stdout}")
                return False
        finally:
            # Clean up the temporary file
            os.unlink(temp_file)
    
    except Exception as e:
        logger.error(f"Error logging in to ZenML server: {e}")
        return False

def create_service_account(name: str):
    """
    Create a ZenML service account and generate an API key.
    
    Args:
        name: Name of the service account
        
    Returns:
        str: The generated API key or None if failed
    """
    try:
        logger.info(f"Creating service account '{name}'...")
        result = subprocess.run(
            ["zenml", "service-account", "create", name, "--create-api-key", "true"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # The API key is printed in the output
        output = result.stdout
        logger.info(f"Service account creation output: {output}")
        
        # Extract the API key from the output
        # The format is typically: "API key: <key>"
        api_key_match = re.search(r"API key: ([a-zA-Z0-9_\-\.]+)", output)
        
        if not api_key_match:
            logger.error("Failed to extract API key from command output")
            logger.error(f"Command output: {output}")
            return None
            
        api_key = api_key_match.group(1)
        logger.info(f"Service account '{name}' created successfully")
        return api_key
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create service account: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating service account: {e}")
        return None

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
    parser = argparse.ArgumentParser(description="Set up ZenML service account and API key")
    parser.add_argument("--name", default="training-service", help="Name of the service account")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument("--server", default="http://localhost:8080", help="ZenML server URL")
    parser.add_argument("--username", default="admin", help="ZenML admin username")
    parser.add_argument("--password", default="P@ssword123$", help="ZenML admin password")
    args = parser.parse_args()
    
    # Connect to ZenML server
    if not connect_to_zenml_server(args.server):
        logger.error("Failed to connect to ZenML server. Exiting.")
        sys.exit(1)
    
    # Login to ZenML server
    if not login_to_zenml(args.username, args.password):
        logger.error("Failed to login to ZenML server. Exiting.")
        sys.exit(1)
    
    # Create service account and get API key
    api_key = create_service_account(args.name)
    if not api_key:
        logger.error("Failed to create service account and get API key")
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
