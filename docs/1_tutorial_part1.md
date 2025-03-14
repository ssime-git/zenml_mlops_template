# zenml_mlops_template
MLOPS with zenml

Setting Up a Local ZenML Environment with a Dockerized ZenML Server

This tutorial walks through setting up ZenML locally, using a Dockerized ZenML server for metadata, and deploying an ML pipeline that serves a model via a FastAPI API. We’ll cover creating an isolated Python environment, installing ZenML, launching the ZenML server in Docker, configuring a local stack (orchestrator, artifact store, etc.), and running the pipeline containers. We also demonstrate how to call the FastAPI inference endpoint and monitor the pipeline’s logs, metrics, and experiment tracking dashboards.

## Virtual Environment Setup

It’s best practice to use a Python virtual environment for this project to isolate dependencies and avoid conflicts ￼ ￼. Follow these steps to create and activate a virtual environment:
* Create a new virtual environment: In your project directory, run python3 -m venv .venv (use py -m venv .venv on Windows) ￼. This command creates a folder (here named .venv) containing a fresh Python installation just for this project.
* Activate the virtual environment: Before installing any packages, activate the environment. On macOS/Linux, use: `source .venv/bin/activate`. On Windows, run: `.venv\Scripts\activate` . After activation, your shell prompt may prefix with the environment name, indicating that you’re now using the isolated Python. All pip install operations will install packages into this environment.

Once activated, you’re ready to install ZenML and its tools without affecting your system Python.

## ZenML Installation and Connection

With the virtual environment active, install ZenML and set up the ZenML server and client:
1. Install ZenML (and necessary integrations): Use pip to install ZenML in your environment:

```bash	
pip install zenml
```

This installs the ZenML CLI and Python SDK ￼. If you plan to use specific libraries (for example, Scikit-learn for model training or MLflow for tracking), install ZenML integrations for them. For instance:

```bash
zenml integration install sklearn mlflow
# when prompted, enter `y` to validate and install
```

This ensures ZenML has all the required packages for those integrations ￼. (The zenml CLI acts as a package manager for optional integrations.)

* Prepare a Dockerized ZenML Server: ZenML uses a central server to store metadata (pipelines, artifacts, stack configs, etc.) when in production mode. We will run this server locally using Docker. Create a docker-compose.yml file with the following services:
* MySQL Database: Required by the ZenML server as a metadata store. Use the official MySQL image, exposing the default port:

```yaml
services:
  mysql:
    image: mysql:8.0
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: password
    volumes:
      - ./data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  zenml:
    image: zenmldocker/zenml-server
    platform: linux/amd64
    ports:
      - "8888:8080"
    environment:
      ZENML_STORE_URL: mysql://root:password@mysql/zenml
      ZENML_DEFAULT_USER_NAME: admin
      ZENML_DEFAULT_USER_PASSWORD: zenml
      ZENML_DEFAULT_USER_EMAIL: admin@zenml.io
      ZENML_AUTH_TYPE: default
      ZENML_STORE_TYPE: sql
    depends_on:
      mysql:
        condition: service_healthy
```

In this configuration, ZENML_STORE_URL points the server to the MySQL database (using credentials defined above). We also set a default admin username and password for the ZenML server UI ￼. The port mapping 8888:8080 means the ZenML server’s API (and web UI) will be available on http://localhost:8888.

2. Launch the ZenML server: Run the Docker Compose setup to start the services. In your terminal (in the same directory as the docker-compose.yml), execute:

```bash
docker-compose up -d
```

This builds (if needed) and starts the MySQL and ZenML server containers in detached mode ￼. After a few seconds, both containers should be running. You can verify the status with docker ps (or docker-compose ps), which should list the zenml and mysql services as Up ￼.

3. Verify the ZenML server is running: Open a browser to `http://localhost:8888`. 

You should see the ZenML dashboard login page. Log in with the default credentials (admin / zenml and change the password to `P@ssword123$`) you set in the compose file. 

After logging in, the ZenML web dashboard will show an initially empty list of pipelines, stack components, etc., since we haven’t run anything yet. (If you encounter issues, check the container logs with docker logs zenml for any errors.)

4. Connect the ZenML client to the server: Now that the server is up, link your local ZenML CLI/SDK to this remote ZenML server. Run the following command in your terminal:

```bash
zenml connect --url http://localhost:8888 --username admin --password P@ssword123$
```

This will display the following message:

```sh
The `zenml connect` command is deprecated and will be removed in a future release. Please use the `zenml login` command instead. 
Connecting to a ZenML server using a username and password is insecure because the password is locally stored on your filesystem and is no longer supported. The web 
login workflow will be used instead. An alternative for non-interactive environments is to create and use a service account API key (see 
https://docs.zenml.io/how-to/connecting-to-zenml/connect-with-a-service-account for more information).
Calling `zenml login`...
Migrating the ZenML global configuration from version 0.73.0 to version 0.75.0...
Authenticating to ZenML server 'http://localhost:8888' using the web login...
If your browser did not open automatically, please open the following URL into your browser to proceed with the authentication:

http://localhost:8888/devices/verify?device_id=d953e41e-f2e3-418c-9aab-7656bfa17368&user_code=1769b2cd4b2c3905166962b90963971b

Successfully logged in to http://localhost:8888.
The current global active stack is no longer available. Resetting the active stack to default.
Updated the global store configuration.
```

This authenticates your ZenML client with the server at the given URL using the provided credentials ￼. Once connected, any ZenML commands you run (like registering stack components or running pipelines) will be recorded on this ZenML server (instead of a local SQLite store). If the connection is successful, you can test it by running zenml whoami or zenml stack list – it should show the active user as admin and the default stack from the server.

5. Initialize a ZenML project: In your project directory, initialize ZenML:

```bash
zenml init
```

You will see :

```sh
⠙ Initializing ZenML repository at /Users/seb/Documents/zenml_mlops_template.
Setting the repo active workspace to 'default'.
ZenML repository initialized at /Users/seb/Documents/zenml_mlops_template.
The local active stack was initialized to 'default'. This local configuration will only take effect when you're running ZenML from the initialized repository root, or
from a subdirectory. For more information on repositories and configurations, please visit https://docs.zenml.io/user-guide/production-guide/understand-stacks.
```

This will set up a `.zen/` directory to track ZenML configurations for your project ￼. (If you had a previous ZenML setup in this folder, you might need to remove any existing `.zen` directory before init to avoid conflicts ￼.) After `zenml init`, your current directory is registered as a ZenML repository, and you’re ready to configure your stack and pipelines.

## 	Configuring a Local ZenML Stack

A ZenML stack defines the infrastructure and tools on which your pipeline will run ￼. By default, ZenML has a default stack (often using a local filesystem artifact store and local orchestrator), but here we’ll create a custom stack that suits our setup. Specifically, we’ll use a Local Docker Orchestrator to run pipeline steps in isolated Docker containers, a local artifact store to save artifacts, and MLflow for experiment tracking. We’ll register each component and then assemble them into a stack:

1. Register a local artifact store: The artifact store is where ZenML will persist pipeline outputs (datasets, models, etc.). Register a local artifact store pointing to a directory on disk. For example:

```bash
zenml artifact-store register local_store --flavor=local --path=./zenml_artifacts
```

You will see:

```sh
You are configuring a stack component that is using local resources while connected to a remote ZenML server. The stack component may not be usable from other hosts or by other users. You should consider using a non-local stack component alternative instead.
Successfully registered artifact_store `local_store`.
Dashboard URL: http://localhost:8888/stacks
```

This creates an artifact store named "local_store" using the local filesystem flavor ￼. The `	--path=./zenml_artifacts` tells it to use the `zenml_artifacts` folder in the current directory (you can choose any writable path). ZenML will automatically manage artifact sub-folders within this location.

2. Register a local Docker orchestrator: The orchestrator is responsible for running pipeline steps. We use the built-in local Docker orchestrator so that each step runs in a container (emulating a production environment while still running on our machine) ￼ ￼. Register it with:

```bash
zenml orchestrator register local_docker_orchestrator --flavor=local_docker
```

You will see:

```sh
You are configuring a stack component that is using local resources while connected to a remote ZenML server. The stack component may not be usable from other hosts or by other users. You should consider using a non-local stack component alternative instead.
Successfully registered orchestrator `local_docker_orchestrator`.
Dashboard URL: http://localhost:8888/stacks
```

This creates an orchestrator named "local_docker_orchestrator" that will execute pipeline steps in Docker containers . Make sure Docker is running, as the orchestrator will use it to spin up containers for each step.

3. Register an experiment tracker (MLflow): To log metrics and parameters, we integrate MLflow as an experiment tracker. If you installed the MLflow integration earlier, register the MLflow tracker:

```bash
zenml experiment-tracker register mlflow_tracker --flavor=mlflow
```

This adds an experiment tracker component named "mlflow_tracker" using MLflow’s tracking service ￼. By default, without additional arguments, this will log to a local MLflow setup (it will use a local mlruns directory for storing runs). We will manually start the MLflow UI later to visualize these runs.

4. Create and activate the stack: Now combine the above components into a new stack, and set it as the active stack for your project:

```bash
zenml stack register local_stack \
    -o local_docker_orchestrator \
    -a local_store \
    -e mlflow_tracker \
    --set
```

You will see:

```sh
Stack 'local_stack' successfully registered!
               Stack Configuration                
┏━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ COMPONENT_TYPE     │ COMPONENT_NAME            ┃
┠────────────────────┼───────────────────────────┨
┃ EXPERIMENT_TRACKER │ mlflow_tracker            ┃
┠────────────────────┼───────────────────────────┨
┃ ARTIFACT_STORE     │ local_store               ┃
┠────────────────────┼───────────────────────────┨
┃ ORCHESTRATOR       │ local_docker_orchestrator ┃
┗━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
               'local_stack' stack                
No labels are set for this stack.
Stack 'local_stack' with id '1ebab81d-3d52-45e9-8f98-8e614bde74d2' is owned by user admin.
Active repository stack set to:'local_stack'
To delete the objects created by this command run, please run in a sequence:

zenml stack delete -y local_stack                                                                                                                                                                                                                                 
Dashboard URL: http://localhost:8888/stacks
```

Here, `-o` specifies the orchestrator, `-a` the artifact store, and `-e` the experiment tracker for the stack ￼. We name the stack "local_stack" and include the `--set` flag to mark it as the active stack to use for pipeline runs. After this, running `zenml stack describe local_stack` should show a table with the components (orchestrator, artifact store, experiment tracker) listed under "local_stack" as configured ￼.

With the stack configured, your ZenML client knows to use Docker for orchestration, store artifacts in the local directory, and log experiments to MLflow. All these configurations are stored in the ZenML server’s database (under your admin account) as well, which means they are centralized and can be shared if others connect to the same server.

## Architecture Overview

At this point, it’s helpful to understand the overall architecture of our setup before executing the pipeline. In this ZenML deployment, we have a client-server architecture ￼ with the following key components:

* **ZenML Client (your environment)**: The ZenML Python library and CLI running on your local machine (inside the virtual environment). This is where you define pipelines and steps in code, and where you issue commands to run pipelines. The client is connected to the ZenML server and uses the stack we set up to run the pipeline.

* **ZenML Server (Dockerized)**: A FastAPI-based service running in a Docker container that acts as the central metadata store and coordination hub ￼ ￼. It stores information about pipeline runs, stack configurations, artifacts, and more in its connected database (MySQL in our case). We access its web Dashboard via http://localhost:8888 to view pipeline runs, artifacts, and configurations .

* **Orchestrator (Local Docker)**: Part of our stack, the orchestrator is responsible for executing pipeline steps. The Local Docker Orchestrator runs each step in its own Docker container on the local machine ￼. This provides isolation and reproducibility—each step runs with a controlled environment defined by ZenML (it can package the code and dependencies into images).

* **Artifact Store (Local Filesystem)**: Another stack component, the artifact store is simply a folder (./zenml_artifacts) on the host where ZenML will save outputs from each pipeline step (like trained model files, evaluation results, etc.). The orchestrator’s containers will write to this shared volume so that artifacts persist after containers finish.

* **Experiment Tracker (MLflow)**: An optional stack component we included for experiment tracking. With MLflow integrated, the pipeline steps can log metrics, parameters, and models to MLflow. In our setup, MLflow will log to a local directory (or a local MLflow server if one is running). We will use the MLflow UI to view these experiment runs.

* **Model Deployment (FastAPI)**: After the training pipeline, we will deploy the trained model using a FastAPI application (packaged in a Docker container). This is not managed by ZenML’s stack per se (unless using ZenML’s model deployer), but rather an application we run to serve predictions. It will load the model artifact from the artifact store and provide an HTTP endpoint for inference.

### Flow of Execution: 

Once everything is set up, the process will be as follows: you trigger a ZenML pipeline run from the client, the ZenML orchestrator builds Docker images for each step and runs them as containers (logging metadata back to the ZenML server). The training step, for example, might load data, train a model, save the model artifact to the artifact store, and log metrics to MLflow. When the pipeline completes, you can view the run in the ZenML dashboard (to see if it succeeded and inspect artifact URIs) and in the MLflow UI (to see detailed metrics and parameters logged). Then, using the model artifact, you launch the FastAPI container (either as part of a deployment pipeline or manually) to serve predictions. The architecture diagram (shown in the documentation) illustrates these components and interactions — the ZenML server and database sit at the center tracking everything, while pipeline workloads and MLflow run in your local infrastructure ￼. All data and compute remain on your machine (or network) since ZenML simply orchestrates existing tools rather than hosting the compute itself.

(In summary, ZenML acts as the glue: the client and server manage coordination and metadata, and they leverage Docker, storage, and MLflow as the infrastructure for actual ML tasks. This modular design means you could swap out components — e.g., use a cloud artifact store or a Kubernetes orchestrator — without changing your pipeline code.)

## Running the Pipeline with Docker Compose

Now it’s time to execute the ML pipeline and the related services using Docker and Docker Compose. We will run the pipeline (training) and then the model serving container, verifying each component as we go. Make sure Docker is running and that you’ve saved any necessary code (pipeline code, FastAPI app code, etc.) from previous steps.

1. Build the Docker images for pipeline steps (if applicable): When using the local Docker orchestrator, ZenML will handle building Docker images for your pipeline steps automatically when you run the pipeline. It uses the base Python environment and integration requirements to containerize the steps. You generally do not need to manually call docker build for pipeline steps – ZenML does it under the hood. However, ensure that your pipeline code is accessible (typically in the current directory or installed as a package) so that ZenML can package it into the images. If you want to force a rebuild of images (for example, after changing code), you can run zenml pipeline run ... --build (or simply rerun the pipeline, as ZenML will detect changes). For transparency, ZenML will output logs during this process, indicating building of Docker images for each step and any package installation happening inside those images.

2. Run the training pipeline: Execute your ZenML pipeline (e.g., via a Python script or notebook). For instance, if you have a pipeline defined in run_pipeline.py, run:

python run_pipeline.py

This will trigger ZenML to: use the active stack (local_stack), build the step containers, and run each step in sequence. You’ll see logs in the console for each step starting and finishing, for example: “Using stack: local_stack (orchestrator: local_docker_orchestrator, artifact_store: local_store, experiment_tracker: mlflow_tracker)”, followed by messages like “Step trainer has started.” and “Step trainer has finished in X seconds.” ￼. ZenML streams these logs to the console for convenience. If the pipeline completes successfully, the trained model artifact will be saved in zenml_artifacts (for example, as a .pkl file or other format your step used) and any metrics will be logged to MLflow.

Verification: After the run, you can double-check:
	•	The ZenML dashboard (refresh the web UI) should list a new Pipeline Run with status Completed (or Failed if something went wrong).
	•	In the zenml_artifacts folder, you should find outputs from each step (structured by pipeline and step name).
	•	The console logs provide quick feedback for each step’s execution ￼. If any step errored, ZenML would report it and mark the pipeline as failed.

3. Build and run the FastAPI inference service: With the model artifact available, the next part is deploying the FastAPI app that uses this model for predictions. We assume you have a FastAPI application (e.g., in app.py or similar) that loads the model from the artifact store and exposes an endpoint (for example, /predict). To containerize and run this API:
	•	Build the FastAPI Docker image: If you have a Dockerfile for the FastAPI app, you can integrate it into your docker-compose.yml or build it manually. For example, if your compose file has a service named model_api for this, run:

docker-compose build model_api

This command builds the Docker image for the model_api service according to the Dockerfile ￼. Ensure the Dockerfile copies or has access to the model artifact (you might volume mount the zenml_artifacts directory or copy the artifact during build). If not using compose for build, you can do docker build -t model_api:latest . in the FastAPI app directory.

	•	Start the FastAPI container: Once built, launch the container. If using compose, run:

docker-compose up -d model_api

This will start the FastAPI API container in detached mode ￼. The FastAPI server (Uvicorn) should start inside the container. You can verify it’s running by checking the container status: docker ps should show a container for model_api Up, and you can also inspect logs with docker logs <container_name> to see if Uvicorn reported “Started server at 0.0.0.0:”.

	•	Confirm the API is reachable: If your FastAPI app is listening on a port (say 8000) and you mapped it in docker-compose (e.g., "8000:8000" in the service definition), you can test the endpoint in a browser or via curl. For instance, visiting http://localhost:8000/docs would show the interactive Swagger UI of the FastAPI app if configured, indicating the API is live.

At this stage, all components of the MLOps pipeline are up and running as containers:
	•	The ZenML server (with MySQL) is running and tracking metadata.
	•	The MLflow tracking server (if configured to run separately) or at least the MLflow backend is ready for viewing results.
	•	The pipeline’s training steps have executed in Docker (and those ephemeral containers have exited after completing tasks).
	•	The FastAPI inference service is running in a container, ready to accept requests.

We used Docker Compose for a coordinated setup. A quick way to see every container is docker-compose ps (which will list zenml server, mysql, model_api, etc., with their state and ports). You should see each expected service marked as “Up” (for persistent ones) or “Exit 0” (for one-off run containers that have completed).

Using the FastAPI Inference API and Monitoring Results

With the model deployed in the FastAPI container, you can now send data to the API and get predictions, and also inspect the various dashboards and logs:

1. Calling the FastAPI endpoint for inference: To get a prediction from your model, send an HTTP request to the FastAPI app. Typically, you’ll use a POST request with JSON data. For example, if the API is expecting feature inputs in JSON format, you can use a tool like curl from the command line. Suppose our FastAPI has a /predict endpoint that accepts a JSON payload of features (the exact format depends on your model). A sample request might look like:

curl -X 'POST' http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"feature1": 5.1, "feature2": 3.5, "feature3": 1.4, "feature4": 0.2}'

In this example, we send a JSON with four features (imagine a model expecting Iris flower measurements). The -H 'Content-Type: application/json' header tells the API we’re sending JSON data. (In practice, replace the URL path and JSON body with what your API expects.) For instance, a generic example from a FastAPI tutorial shows adding a new record with JSON data using curl ￼ – the format above is analogous.

If the request is successful, the FastAPI server will return a JSON response containing the prediction result(s). For example, it might respond with a JSON like: {"prediction": "[Iris-setosa]"} or {"result": 12.34} depending on how your endpoint is implemented. You should see this response printed in the terminal from the curl command.

(Tip: You can also use tools like Postman or the auto-generated Swagger UI (/docs) to test the API by manually inputting values and observing the output.)

2. Checking the inference service logs: To ensure the request was processed correctly, you can look at the logs of the FastAPI container. Run:

docker logs <container_name_or_id>

Replace <container_name_or_id> with the name/ID of the model API container (e.g., docker logs project_model_api_1 if Compose named it that). In the logs, you should see an entry corresponding to your POST request (Uvicorn logs will show the request path and a 200 status if all went well). Any errors in the prediction (stack traces, etc.) would also appear here, which is useful for debugging if the API didn’t return as expected.

3. Viewing metrics and experiment tracking: The training pipeline logged metadata to the ZenML server and metrics to MLflow:
	•	ZenML Dashboard: Navigate to the ZenML dashboard in your browser (the one at localhost:8888). You should see your pipeline listed under “Pipeline Runs”. Clicking into it will show details like the step artifacts. You can trace which artifact (e.g., model file) was produced by which step, and see run metadata such as timings. This dashboard is useful for an overview of your pipeline executions and for sharing with team members (if the server is remote) ￼.
	•	MLflow UI: To inspect the detailed experiment tracking, start the MLflow UI if it’s not already running. Since we didn’t explicitly start an MLflow tracking server as a persistent service in earlier steps, we can use the MLflow UI in local mode. Run the command:

mlflow ui

(from within the virtual environment, in the directory where mlruns is located – likely your project root). This will launch a web UI at http://127.0.0.1:5000 by default ￼. Open that in a browser; you should see the MLflow interface. Under the “Experiments” section, find the experiment corresponding to your ZenML pipeline (by default, ZenML may log under an experiment named after the pipeline or “Default”). You will see one run entry for each pipeline run. Clicking on the run shows parameters (if logged) and metrics like accuracy, loss, etc., plotted over time or listed as values ￼ ￼. This rich UI lets you compare runs, visualize metrics, and even view artifacts or models if logged. (Since we logged metrics manually or via integration in our ZenML steps, those should appear here. If you used ZenML’s MLflow integration properly, it handles logging to MLflow under the hood.)

	•	Other dashboards: If you integrated any other tools (for example, if you had a model deployment tool or a monitoring system), now is the time to check those as well. In our setup, ZenML and MLflow are the main ones. ZenML doesn’t log training metrics itself; it delegates to MLflow for that ￼ ￼, so the MLflow UI is the primary place to evaluate model performance metrics in this pipeline.

4. Reviewing pipeline output and artifacts: You can also directly inspect the artifact store folder (zenml_artifacts). For example, open the directory to find the saved model file from training. This can be useful to manually verify the artifact (or even load it outside the pipeline to test). Because ZenML tracked this artifact, the ZenML UI or CLI (zenml artifact list) might show it with a UID, but the actual content is in the file in this folder.

5. (Optional) Iterate and re-run: With everything wired up, you can experiment by adjusting your pipeline (e.g., change a model hyperparameter or use a different dataset) and running it again. Each run will produce a new entry in ZenML/MLflow, which you can compare. The FastAPI service can be left running and pointed to a specific model artifact (you might need to update it if a new model should be served). In a production scenario, you might automate the deployment of a new model version to the FastAPI service when a new model is trained, but that’s beyond this tutorial’s scope.