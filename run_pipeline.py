# run_pipeline.py
from zenml import pipeline, get_pipeline_context, log_metadata
from datetime import datetime

# Import steps from src/pipeline modules
from src.pipeline.data_preprocess import preprocess_data
from src.pipeline.train_model import train_model


@pipeline(name="iris_classification_pipeline") # set enable_cache=False to disable caching (default: True)
def iris_pipeline():
    """
    ZenML pipeline for Iris flower classification.
    
    Steps:
        1. preprocess_data: Load and preprocess the Iris dataset, split into train/test
        2. train_model: Train a RandomForest classifier and log to MLflow
    
    Artifact Lineage:
        preprocess_data outputs (X_train, X_test, y_train, y_test) are automatically
        tracked by ZenML and passed as versioned artifacts to train_model.
    """
    # Connect the steps: outputs of preprocess are inputs to train
    # ZenML automatically tracks these as versioned artifacts with full lineage
    X_train, X_test, y_train, y_test = preprocess_data()
    train_model(X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test)


if __name__ == "__main__":
    from zenml.client import Client
    
    # Run the pipeline
    run = iris_pipeline()
    
    # Log pipeline-level metadata after successful run
    log_metadata(
        metadata={
            "pipeline_info": {
                "description": "Iris flower classification pipeline",
                "model_type": "RandomForestClassifier",
                "mlflow_experiment": "iris_classification",
                "mlflow_model_name": "iris-classifier",
            },
            "execution_info": {
                "timestamp": datetime.now().isoformat(),
                "python_version": "3.12",
            },
        },
        run_id_name_or_prefix=str(run.id),
    )
