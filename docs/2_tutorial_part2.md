## 2_tutorial_part2.md

End-to-End MLOps Tutorial with ZenML and Docker

This tutorial shows you how to build a local MLOps architecture using ZenML and Docker. You will:
	•	Set up a Python virtual environment and install ZenML.
	•	Launch a Dockerized ZenML server (with MySQL as the metadata store).
	•	Configure a local ZenML stack (using a local Docker orchestrator, local artifact store, and MLflow experiment tracker).
	•	Run pipeline steps (data preprocessing and model training) as Python scripts.
	•	Deploy a FastAPI inference service that serves predictions.
	•	Use Docker Compose to coordinate the services.
	•	Monitor experiment runs and API metrics using MLflow and Prometheus/Grafana.

All components run locally without any cloud dependencies.

⸻

1. Setting Up Your Python Virtual Environment

Create and activate a virtual environment to isolate your dependencies:

# Create the virtual environment in your project folder
python -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

Now install ZenML (and any desired integrations):

pip install zenml
# Optional: Install integrations for scikit-learn and MLflow
zenml integration install sklearn mlflow



⸻

2. Running a Dockerized ZenML Server

Docker Compose Configuration

Create a file called docker-compose.yml with the following content. This will define the ZenML server (backed by MySQL), MLflow, and later services for your pipeline:

version: "3.9"
services:
  # MySQL: Metadata store for ZenML
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: zenml
    ports:
      - "3306:3306"
    volumes:
      - ./data/mysql:/var/lib/mysql

  # ZenML Server: Exposes a dashboard and API
  zenml:
    image: zenmldocker/zenml-server:latest
    environment:
      # Using host.docker.internal for local connection (on macOS/Windows)
      - ZENML_STORE_URL=mysql+pymysql://root:password@host.docker.internal:3306/zenml
      - ZENML_DEFAULT_USER_NAME=admin
      - ZENML_DEFAULT_USER_PASSWORD=zenml
    ports:
      - "8888:8080"
    depends_on:
      - mysql

  # MLflow Tracking Server: For experiment tracking
  mlflow:
    image: python:3.9-slim
    ports:
      - "5000:5000"
    volumes:
      - ./mlflow_data:/mlflow
    command: >
      sh -c "pip install mlflow && 
             mlflow server 
             --backend-store-uri sqlite:///mlflow/mlflow.db 
             --default-artifact-root /mlflow/artifacts 
             --host 0.0.0.0 --port 5000"

  # Data Preprocessing Service (see script below)
  data-preprocess:
    build:
      context: .
      dockerfile: Dockerfile.preprocess
    volumes:
      - iris_data:/data
    depends_on:
      - zenml

  # Model Training Service (see script below)
  train-model:
    build:
      context: .
      dockerfile: Dockerfile.train
    volumes:
      - iris_data:/data
      - iris_model:/model
    environment:
      MLFLOW_TRACKING_URI: http://mlflow:5000
    depends_on:
      - data-preprocess
      - mlflow

  # Inference Service (FastAPI REST API)
  inference-api:
    build:
      context: .
      dockerfile: Dockerfile.inference
    volumes:
      - iris_model:/model
    ports:
      - "8000:8000"
    depends_on:
      - train-model
    restart: unless-stopped

  # Prometheus for monitoring
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    depends_on:
      - inference-api

  # Grafana for dashboards
  grafana:
    image: grafana/grafana-oss:latest
    ports:
      - "3000:3000"
    depends_on:
      - prometheus

volumes:
  iris_data:
  iris_model:

Prometheus Configuration

Create a prometheus.yml file in the same directory:

global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "inference_api"
    static_configs:
      - targets: ["inference-api:8000"]

Launch the ZenML Server

Now start the Docker services:

docker-compose up -d

Verify that the ZenML server is running by navigating to http://localhost:8888 and log in using:
	•	Username: admin
	•	Password: zenml

⸻

3. Configuring the ZenML Stack

With your virtual environment active, connect your ZenML CLI to the running ZenML server:

zenml connect --url http://localhost:8888 --username admin --password zenml

Initialize your ZenML repository:

zenml init

Register and set up your stack components:
	1.	Artifact Store:

zenml artifact-store register local_store --flavor=local --path=./zenml_artifacts


	2.	Local Docker Orchestrator:

zenml orchestrator register local_docker_orchestrator --flavor=local_docker


	3.	MLflow Experiment Tracker:

zenml experiment-tracker register mlflow_tracker --flavor=mlflow


	4.	Register the Stack:

zenml stack register local_stack \
    -o local_docker_orchestrator \
    -a local_store \
    -e mlflow_tracker \
    --set



You can now verify the active stack with:

zenml stack describe local_stack



⸻

4. Python Scripts for Pipeline Steps

A. Data Preprocessing Script (data_preprocess.py)

Create a file named data_preprocess.py:

# data_preprocess.py
from sklearn.datasets import load_iris
import pandas as pd

def main():
    # Load the Iris dataset
    iris = load_iris()
    df = pd.DataFrame(data=iris.data, columns=iris.feature_names)
    df['target'] = iris.target

    # Save preprocessed data to CSV (in /data, a shared volume)
    output_path = "/data/iris_preprocessed.csv"
    df.to_csv(output_path, index=False)
    print(f"Preprocessing complete. Data saved to {output_path}")

if __name__ == "__main__":
    main()

B. Model Training Script (train_model.py)

Create a file named train_model.py:

# train_model.py
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import joblib
import mlflow

def main():
    # Load preprocessed data from shared volume
    data_path = "/data/iris_preprocessed.csv"
    df = pd.read_csv(data_path)
    X = df.drop("target", axis=1)
    y = df["target"]

    # Split data into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Set MLflow tracking URI (ensure it matches our mlflow service)
    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment("iris_classification")

    with mlflow.start_run():
        n_estimators = 50
        model = RandomForestClassifier(n_estimators=n_estimators, random_state=42)
        mlflow.log_param("n_estimators", n_estimators)

        model.fit(X_train, y_train)
        accuracy = model.score(X_test, y_test)
        mlflow.log_metric("accuracy", accuracy)

        # Log model artifact to MLflow and save locally for inference
        mlflow.sklearn.log_model(model, artifact_path="model")
        joblib.dump(model, "/model/random_forest_model.joblib")

        print(f"Training complete. Accuracy: {accuracy:.4f}")

if __name__ == "__main__":
    main()

C. Inference Service Script (inference_service.py)

Create a file named inference_service.py:

# inference_service.py
from fastapi import FastAPI
from pydantic import BaseModel
import joblib
from prometheus_client import Counter, make_asgi_app

# Load the trained model from the shared volume
model = joblib.load("/model/random_forest_model.joblib")

app = FastAPI(title="Iris Prediction API")

class IrisFeatures(BaseModel):
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float

# Prometheus counter for number of prediction requests
prediction_count = Counter("prediction_requests_total", "Total prediction requests")

@app.post("/predict")
def predict(features: IrisFeatures):
    prediction_count.inc()
    data = [[
        features.sepal_length,
        features.sepal_width,
        features.petal_length,
        features.petal_width
    ]]
    pred_class = int(model.predict(data)[0])
    return {"prediction": pred_class}

# Mount Prometheus metrics endpoint at /metrics
app.mount("/metrics", make_asgi_app())

D. (Optional) ZenML Pipeline Script (run_pipeline.py)

If you want to run these steps as a ZenML pipeline rather than as independent Docker containers, you could define a pipeline like this:

# run_pipeline.py
from zenml.pipelines import pipeline
from zenml.steps import step

@step
def preprocess_data() -> str:
    import pandas as pd
    from sklearn.datasets import load_iris

    iris = load_iris()
    df = pd.DataFrame(data=iris.data, columns=iris.feature_names)
    df['target'] = iris.target

    output_path = "iris_preprocessed.csv"
    df.to_csv(output_path, index=False)
    print(f"Preprocessed data saved to {output_path}")
    return output_path

@step
def train_model(data_path: str) -> str:
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestClassifier
    import joblib

    df = pd.read_csv(data_path)
    X = df.drop("target", axis=1)
    y = df["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X_train, y_train)
    accuracy = model.score(X_test, y_test)
    print(f"Model accuracy: {accuracy:.4f}")

    model_path = "random_forest_model.joblib"
    joblib.dump(model, model_path)
    return model_path

@pipeline
def iris_pipeline(preprocess, train):
    data_path = preprocess()
    train(data_path)

if __name__ == "__main__":
    iris_pipeline(
        preprocess=preprocess_data(),
        train=train_model()
    )

(Note: The ZenML pipeline above uses local file paths. When run with the local Docker orchestrator, ZenML packages the code and mounts volumes accordingly.)

⸻

5. Dockerfiles for Each Service

Dockerfile for Data Preprocessing Service (Dockerfile.preprocess)

# Dockerfile.preprocess
FROM python:3.9-slim
RUN pip install pandas scikit-learn
COPY data_preprocess.py /app/data_preprocess.py
WORKDIR /app
ENTRYPOINT ["python", "data_preprocess.py"]

Dockerfile for Model Training Service (Dockerfile.train)

# Dockerfile.train
FROM python:3.9-slim
RUN pip install pandas scikit-learn mlflow joblib
COPY train_model.py /app/train_model.py
WORKDIR /app
ENTRYPOINT ["python", "train_model.py"]

Dockerfile for Inference Service (Dockerfile.inference)

# Dockerfile.inference
FROM python:3.9-slim
RUN pip install fastapi uvicorn[standard] joblib scikit-learn prometheus-client
COPY inference_service.py /app/inference_service.py
WORKDIR /app
EXPOSE 8000
ENTRYPOINT ["uvicorn", "inference_service:app", "--host", "0.0.0.0", "--port", "8000"]



⸻

6. Running and Verifying the Entire System
	1.	Start Docker Compose:

docker-compose up --build

This builds all custom images (for data preprocessing, training, inference) and starts all containers.

	2.	Verify ZenML Server:
Open http://localhost:8888 and log in with admin/zenml.
	3.	Run the Pipeline:
The data-preprocess and train-model containers run their scripts and exit after completion. Check logs via:

docker-compose logs data-preprocess
docker-compose logs train-model

They will show status messages (e.g., “Preprocessing complete”, “Training complete. Accuracy: 0.9333”).

	4.	Test the Inference API:
With the FastAPI service running on port 8000, send a sample prediction request:

curl -X POST -H "Content-Type: application/json" \
     -d '{"sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4, "petal_width": 0.2}' \
     http://localhost:8000/predict

You should receive a JSON response with the prediction result.

	5.	View Metrics and Experiment Tracking:
	•	MLflow UI: Run mlflow ui (from your virtual environment) and visit http://127.0.0.1:5000 to see the logged experiment (accuracy, parameters, model).
	•	Prometheus: Visit http://localhost:9090 to query metrics (like prediction_requests_total).
	•	Grafana: Visit http://localhost:3000 to create dashboards (configure Prometheus as the data source).
	6.	(Optional) Running the ZenML Pipeline Script:
If you defined run_pipeline.py, you can run it with:

python run_pipeline.py

ZenML will use your active stack to orchestrate the steps (with logs visible in your terminal).

⸻

Conclusion

This tutorial provides a complete, self-contained guide to creating an end-to-end MLOps pipeline using ZenML, Docker Compose, and Python. You learned how to:
	•	Create a virtual environment and install ZenML.
	•	Run a ZenML server in Docker with MySQL as a metadata store.
	•	Configure and register a ZenML stack locally.
	•	Write Python scripts for data preprocessing, model training, and inference.
	•	Build Docker images for each service and run them via Docker Compose.
	•	Test the inference API and monitor experiments/metrics via MLflow, Prometheus, and Grafana.

You now have a solid local MLOps setup that you can iterate on and eventually extend for more complex use cases. Enjoy experimenting with your ZenML-powered pipeline!