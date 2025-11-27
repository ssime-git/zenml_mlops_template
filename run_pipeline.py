# run_pipeline.py
from zenml import pipeline

# Import steps from src/pipeline modules
from src.pipeline.data_preprocess import preprocess_data
from src.pipeline.train_model import train_model


@pipeline(name="iris_classification_pipeline")
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
    # Run the pipeline
    iris_pipeline()
