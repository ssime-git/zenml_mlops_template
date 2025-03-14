# Custom Notes: ZenML API Key Generation

To set up a Docker Compose environment where an init container generates a ZenML service account API key for use by a training service, follow these steps:
	1.	Create a Shell Script to Generate the API Key: This script will run inside the init container to create a service account and store the API key in a shared volume.

```bash
#!/bin/bash
set -e

# Wait for the ZenML server to be ready
until curl -sSf http://zenml_server:8080; do
    echo "Waiting for ZenML server..."
    sleep 5
done

# Create a service account and extract the API key
API_KEY=$(zenml service-account create training_service_account --role=admin | grep 'API Key:' | awk '{print $NF}')

# Save the API key to a file in the shared volume
echo $API_KEY > /shared/api_key.txt
```

Ensure this script is executable (chmod +x generate_api_key.sh) and placed in your project directory.

	2.	Define the Docker Compose File: This file will set up the ZenML server, the init container to generate the API key, and the training service that uses the API key.

```yaml
version: '3.8'

services:
  zenml_server:
    image: zenml/server:latest
    ports:
      - "8080:8080"
    environment:
      - ZENML_AUTHENTICATION_REQUIRED=true
    volumes:
      - zenml_data:/var/lib/zenml

  api_key_init:
    image: zenml/zenml:latest
    entrypoint: ["/bin/bash", "-c", "/scripts/generate_api_key.sh"]
    volumes:
      - ./generate_api_key.sh:/scripts/generate_api_key.sh
      - shared_data:/shared
    depends_on:
      zenml_server:
        condition: service_healthy

  training_service:
    image: your_training_image:latest
    environment:
      - ZENML_STORE_URL=http://zenml_server:8080
      - ZENML_STORE_API_KEY_FILE=/shared/api_key.txt
    volumes:
      - shared_data:/shared
    depends_on:
      api_key_init:
        condition: service_completed_successfully

volumes:
  zenml_data:
  shared_data:
```

In this configuration:
	•	zenml_server: Runs the ZenML server with authentication enabled.
	•	api_key_init: An init container that waits for the ZenML server to be ready, creates a service account, and writes the API key to a shared volume.
	•	training_service: Your training service container that reads the API key from the shared volume and connects to the ZenML server. ￼
	•	Volumes:
	•	zenml_data: Persists ZenML server data.
	•	shared_data: Shared volume for passing the API key between containers.

	3.	Build and Run the Docker Compose Setup:

```bash
docker-compose up --build
```

This command will build and start all services as defined. The api_key_init service will run the script to generate the API key before the training_service starts.

Security Considerations:
	•	Ensure that the shared volume (shared_data) is secured and accessible only to authorized services to prevent unauthorized access to the API key.
	•	Regularly rotate the API key and update the training_service accordingly to maintain security.

By following this setup, you can automate the generation and usage of a ZenML service account API key within a Docker Compose environment, facilitating seamless authentication for your training services.

## Alternative approach

After reviewing the ZenML documentation, the approach of using a service account with an API key is indeed recommended for authenticating ZenML clients in non-interactive environments, such as Docker containers.

To streamline the process and avoid the complexity of generating the API key at runtime within the Docker environment, you can pre-generate the service account and API key on your local machine and then pass the necessary credentials to your Docker containers. Here’s how:

1. Pre-Generate the Service Account and API Key:
On your local machine, run the following command to create a service account and generate an API key:

```bash
zenml service-account create training_service_account
```

This command will output the API key. Ensure you store this API key securely, as it won’t be retrievable later.

2. Store the API Key Securely:
Save the API key in a secure location, such as a secrets management system or an environment variable, ensuring it’s protected from unauthorized access.

3. Modify Your Docker Compose Configuration:
Update your docker-compose.yml file to pass the pre-generated API key to your training service container:

```yaml
version: '3.8'

services:
  zenml_server:
    image: zenml/server:latest
    ports:
      - "8080:8080"
    environment:
      - ZENML_AUTHENTICATION_REQUIRED=true
    volumes:
      - zenml_data:/var/lib/zenml

  training_service:
    image: your_training_image:latest
    environment:
      - ZENML_STORE_URL=http://zenml_server:8080
      - ZENML_STORE_API_KEY=${ZENML_API_KEY}
    depends_on:
      - zenml_server

volumes:
  zenml_data:
```

In this configuration:
* ZENML_STORE_URL: Specifies the URL of the ZenML server.
* ZENML_STORE_API_KEY: References the API key stored in an environment variable.

4. Set the Environment Variable:
Before deploying your Docker Compose setup, export the ZENML_API_KEY environment variable with the pre-generated API key:

```bash
export ZENML_API_KEY=<YOUR_PRE_GENERATED_API_KEY>
```

Replace <YOUR_PRE_GENERATED_API_KEY> with the actual API key obtained in step 1.

5. Deploy Your Docker Compose Setup:
With the environment variable set, deploy your Docker Compose services:

```bash
docker-compose up
```

The training_service container will now have access to the ZENML_STORE_API_KEY environment variable, allowing it to authenticate with the ZenML server without requiring an init container to generate the API key at runtime.

Security Considerations:
* Environment Variable Management: Ensure that the ZENML_API_KEY environment variable is managed securely, especially in shared or production environments.
* API Key Rotation: Regularly rotate the API key and update the environment variable accordingly to maintain security.

By pre-generating the service account and API key, and securely passing the credentials to your Docker containers, you simplify the setup process and align with ZenML’s recommended practices for authenticating in non-interactive environments.

## zenml 0.75.0
Yes, as of ZenML version 0.75.0, the recommended approach for authenticating ZenML clients in non-interactive environments, such as Docker containers, is to use a service account with an API key. This method allows for secure and automated interactions with the ZenML server without manual intervention.

Setting Up a Service Account and API Key:
	1.	Create a Service Account and Generate an API Key:
Run the following command to create a service account and obtain an API key:

zenml service-account create <SERVICE_ACCOUNT_NAME>

This command will output an API key associated with the service account. Ensure you store this API key securely, as it won’t be retrievable later.

	2.	Configure Environment Variables in Your Docker Container:
Set the following environment variables in your Docker container to enable the ZenML client to authenticate with the server:

export ZENML_STORE_URL=https://your-zenml-server-url
export ZENML_STORE_API_KEY=<YOUR_API_KEY>

Replace https://your-zenml-server-url with your actual ZenML server URL and <YOUR_API_KEY> with the API key obtained in the previous step.

Integrating with Docker Compose:

To incorporate this setup into a Docker Compose environment, you can define the necessary environment variables within your docker-compose.yml file:

version: '3.8'

services:
  zenml_server:
    image: zenml/server:latest
    ports:
      - "8080:8080"
    environment:
      - ZENML_AUTHENTICATION_REQUIRED=true
    volumes:
      - zenml_data:/var/lib/zenml

  training_service:
    image: your_training_image:latest
    environment:
      - ZENML_STORE_URL=http://zenml_server:8080
      - ZENML_STORE_API_KEY=${ZENML_API_KEY}
    depends_on:
      - zenml_server

volumes:
  zenml_data:

In this configuration:
	•	ZENML_STORE_URL: Specifies the URL of the ZenML server.
	•	ZENML_STORE_API_KEY: References the API key stored in an environment variable.

Setting the Environment Variable:

Before deploying your Docker Compose setup, export the ZENML_API_KEY environment variable with the pre-generated API key:

export ZENML_API_KEY=<YOUR_PRE_GENERATED_API_KEY>

Replace <YOUR_PRE_GENERATED_API_KEY> with the actual API key obtained earlier.

Deploying Your Docker Compose Setup:

With the environment variable set, deploy your Docker Compose services:

docker-compose up

The training_service container will now have access to the ZENML_STORE_API_KEY environment variable, allowing it to authenticate with the ZenML server without manual intervention.

Security Considerations:
	•	Environment Variable Management: Ensure that the ZENML_API_KEY environment variable is managed securely, especially in shared or production environments.
	•	API Key Rotation: Regularly rotate the API key and update the environment variable accordingly to maintain security.

By following this approach, you can securely and efficiently authenticate ZenML clients within Docker containers in version 0.75.0, aligning with ZenML’s recommended practices for non-interactive environments.