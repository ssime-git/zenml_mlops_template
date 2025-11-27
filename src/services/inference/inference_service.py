# inference_service.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
import os
import subprocess
from prometheus_client import Counter, make_asgi_app
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set MLflow tracking URI
mlflow_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
mlflow.set_tracking_uri(mlflow_uri)
logger.info(f"Using MLflow tracking URI: {mlflow_uri}")

# Initialize FastAPI app
app = FastAPI(title="Iris Prediction API")

# Define input data model
class IrisFeatures(BaseModel):
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float

# Prometheus counter for number of prediction requests
prediction_count = Counter("prediction_requests_total", "Total prediction requests")
retrain_count = Counter("model_retrain_total", "Total model retrain requests")

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Model Registry configuration
MODEL_NAME = "iris-classifier"

# Global variable for model
model = None
current_model_version = None

def load_model_from_mlflow():
    """
    Load the production model from MLflow Model Registry.
    Falls back to latest run if no production model is registered.
    """
    global model, current_model_version
    client = mlflow.tracking.MlflowClient()
    
    try:
        # Try to load from Model Registry (production alias)
        model_version = client.get_model_version_by_alias(MODEL_NAME, "production")
        model_uri = f"models:/{MODEL_NAME}@production"
        model = mlflow.sklearn.load_model(model_uri)
        current_model_version = model_version.version
        logger.info(f"Loaded production model from registry: {MODEL_NAME} v{model_version.version}")
        return True
    except mlflow.exceptions.MlflowException as e:
        logger.warning(f"No production model in registry, trying latest run: {e}")
    
    # Fallback: Load from latest experiment run (for backward compatibility)
    try:
        experiment_name = "iris_classification"
        mlflow.set_experiment(experiment_name)
        experiment = client.get_experiment_by_name(experiment_name)
        
        if experiment:
            runs = client.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=["attributes.start_time DESC"],
                max_results=1
            )
            
            if runs:
                run_id = runs[0].info.run_id
                model = mlflow.sklearn.load_model(f"runs:/{run_id}/model")
                current_model_version = f"run:{run_id[:8]}"
                logger.info(f"Loaded model from MLflow run: {run_id}")
                return True
        
        logger.warning("No model found in MLflow")
        return False
    except Exception as e:
        logger.error(f"Error loading model from MLflow: {str(e)}")
        return False

@app.post("/predict")
def predict(features: IrisFeatures):
    """
    Make a prediction with the trained model.
    
    Args:
        features: Input features for prediction
        
    Returns:
        dict: Prediction result
    """
    global model
    
    # Try to load the model if it's not already loaded
    if model is None:
        success = load_model_from_mlflow()
        if not success:
            raise HTTPException(
                status_code=503, 
                detail="Model not available. Please train the model first."
            )
    
    # Increment the prediction counter
    prediction_count.inc()
    
    # Prepare the data for prediction with feature names matching training data
    data = pd.DataFrame([{
        "sepal length (cm)": features.sepal_length,
        "sepal width (cm)": features.sepal_width,
        "petal length (cm)": features.petal_length,
        "petal width (cm)": features.petal_width
    }])
    
    # Make the prediction
    pred_class = int(model.predict(data)[0])
    return {"prediction": pred_class}

@app.get("/health")
def health():
    """
    Health check endpoint.
    
    Returns:
        dict: Status message including model version
    """
    # Check if model is loaded or can be loaded
    global model, current_model_version
    if model is None:
        model_available = load_model_from_mlflow()
    else:
        model_available = True
    
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_available": model_available,
        "model_version": current_model_version,
        "model_name": MODEL_NAME
    }

@app.get("/model/info")
def model_info():
    """
    Get detailed information about the current production model.
    
    Returns:
        dict: Model metadata from MLflow Model Registry
    """
    client = mlflow.tracking.MlflowClient()
    
    try:
        # Get production model version from registry
        model_version = client.get_model_version_by_alias(MODEL_NAME, "production")
        run = client.get_run(model_version.run_id)
        
        # Get all versions for this model
        all_versions = client.search_model_versions(f"name='{MODEL_NAME}'")
        
        return {
            "model_name": MODEL_NAME,
            "production_version": model_version.version,
            "run_id": model_version.run_id,
            "created_at": model_version.creation_timestamp,
            "description": model_version.description,
            "metrics": {
                "accuracy": run.data.metrics.get("accuracy"),
            },
            "parameters": {
                "n_estimators": run.data.params.get("n_estimators"),
            },
            "total_versions": len(all_versions),
            "aliases": {
                "production": model_version.version,
                "challenger": next(
                    (v.version for v in all_versions 
                     if "challenger" in (v.aliases or [])), 
                    None
                )
            }
        }
    except mlflow.exceptions.MlflowException as e:
        return {
            "model_name": MODEL_NAME,
            "production_version": None,
            "error": f"No production model registered: {str(e)}",
            "total_versions": 0
        }

@app.post("/retrain")
def retrain_model(background_tasks: BackgroundTasks):
    """
    Trigger model retraining in the background.
    
    Returns:
        dict: Status message
    """
    # Increment the retrain counter
    retrain_count.inc()
    
    # Add the retraining task to background tasks
    background_tasks.add_task(_retrain_model_task)
    
    return {
        "status": "retraining_started",
        "message": "Model retraining has been started in the background. The new model will be used for predictions once training is complete."
    }

def _retrain_model_task():
    """
    Background task to retrain the model by triggering the pipeline-runner container.
    """
    try:
        logger.info("Starting model retraining via pipeline-runner...")
        
        # Trigger the pipeline-runner container via docker compose
        # Use -p to specify project name matching the existing containers
        # Use --no-deps to avoid recreating dependent services
        result = subprocess.run(
            [
                "docker", "compose",
                "-p", "zenml_mlops_template",
                "--profile", "pipeline",
                "run", "--rm", "--no-deps", "pipeline-runner"
            ],
            capture_output=True,
            text=True,
            cwd="/app/workspace",  # Mount point for the project
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode == 0:
            logger.info("Pipeline completed successfully")
            logger.info(f"Output: {result.stdout[-500:] if len(result.stdout) > 500 else result.stdout}")
        else:
            logger.error(f"Pipeline failed with code {result.returncode}")
            logger.error(f"Error: {result.stderr[-500:] if len(result.stderr) > 500 else result.stderr}")
        
        # Reload the model after training
        load_model_from_mlflow()
        logger.info("Model reloaded after retraining")
        
    except subprocess.TimeoutExpired:
        logger.error("Pipeline timed out after 10 minutes")
    except Exception as e:
        logger.error(f"Error during model retraining: {str(e)}")

# Try to load the model at startup, but don't fail if it's not available
@app.on_event("startup")
def startup_event():
    """
    Load the model when the application starts.
    """
    logger.info("Starting inference service...")
    load_model_from_mlflow()
