# train_model.py
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from zenml import step, log_metadata
from typing import Annotated

# Model Registry configuration
MODEL_NAME = "iris-classifier"
EXPERIMENT_NAME = "iris_classification"


def get_production_model_accuracy(client: MlflowClient) -> float:
    """
    Get the accuracy of the current production model from the registry.
    
    Returns:
        float: Accuracy of the production model, or 0.0 if no production model exists
    """
    try:
        # Get the latest version with "Production" alias
        model_version = client.get_model_version_by_alias(MODEL_NAME, "production")
        run_id = model_version.run_id
        run = client.get_run(run_id)
        accuracy = run.data.metrics.get("accuracy", 0.0)
        print(f"[train_model] Current production model (v{model_version.version}) accuracy: {accuracy:.4f}")
        return accuracy
    except mlflow.exceptions.MlflowException:
        print(f"[train_model] No production model found in registry")
        return 0.0


def register_and_promote_model(client: MlflowClient, run_id: str, new_accuracy: float, production_accuracy: float) -> bool:
    """
    Register the model and promote to production if it's better than the current one.
    
    Returns:
        bool: True if model was promoted to production, False otherwise
    """
    model_uri = f"runs:/{run_id}/model"
    
    # Register the model
    result = mlflow.register_model(model_uri, MODEL_NAME)
    version = result.version
    print(f"[train_model] Registered model version: {version}")
    
    # Add description to the version
    client.update_model_version(
        name=MODEL_NAME,
        version=version,
        description=f"Accuracy: {new_accuracy:.4f}"
    )
    
    # Compare and promote if better
    if new_accuracy > production_accuracy:
        # Set the new model as production
        client.set_registered_model_alias(MODEL_NAME, "production", version)
        print(f"[train_model] ✅ New model (v{version}) promoted to production! Accuracy: {new_accuracy:.4f} > {production_accuracy:.4f}")
        return True
    else:
        # Keep as candidate/challenger
        client.set_registered_model_alias(MODEL_NAME, "challenger", version)
        print(f"[train_model] ❌ New model (v{version}) NOT promoted. Accuracy: {new_accuracy:.4f} <= {production_accuracy:.4f}")
        return False


@step(name="train_model")
def train_model(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
) -> Annotated[str, "model_uri"]:
    """
    ZenML step that trains a RandomForest model and logs to MLflow.
    Uses Model Registry to track versions and only promotes to production if accuracy improves.
    
    Args:
        X_train: Training features (ZenML artifact)
        X_test: Test features (ZenML artifact)
        y_train: Training labels (ZenML artifact)
        y_test: Test labels (ZenML artifact)
        
    Returns:
        model_uri: MLflow model URI (ZenML artifact)
    """
    # Set MLflow tracking URI 
    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    client = MlflowClient()
    
    # Get current production model accuracy for comparison
    production_accuracy = get_production_model_accuracy(client)

    with mlflow.start_run() as run:
        n_estimators = 50
        model = RandomForestClassifier(n_estimators=n_estimators, random_state=42)
        mlflow.log_param("n_estimators", n_estimators)
        mlflow.log_param("train_samples", len(X_train))
        mlflow.log_param("test_samples", len(X_test))

        model.fit(X_train, y_train)
        accuracy = model.score(X_test, y_test)
        mlflow.log_metric("accuracy", accuracy)

        # Log model artifact to MLflow
        mlflow.sklearn.log_model(
            model, 
            artifact_path="model",
            registered_model_name=None  # We'll register manually for more control
        )
        
        print(f"[train_model] Model accuracy: {accuracy:.4f}")
        print(f"[train_model] Model saved to MLflow with run_id: {run.info.run_id}")
        
        # Register and potentially promote the model
        promoted = register_and_promote_model(client, run.info.run_id, accuracy, production_accuracy)
        
        # Log metadata to ZenML for lineage tracking
        # Organized metadata (shows as cards in dashboard)
        log_metadata(
            metadata={
                "model_metrics": {
                    "accuracy": accuracy,
                    "n_estimators": n_estimators,
                },
                "mlflow_info": {
                    "run_id": run.info.run_id,
                    "model_name": MODEL_NAME,
                    "promoted_to_production": promoted,
                },
            },
        )
        
        # Return the MLflow model URI
        model_uri = f"runs:/{run.info.run_id}/model"
        return model_uri

def main():
    """
    Main function for running the training step directly.
    Used when this script is executed as a standalone program.
    """
    train_model("./data-file/iris_preprocessed.csv")

if __name__ == "__main__":
    main()