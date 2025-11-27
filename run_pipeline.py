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
        1. preprocess_data: Load and preprocess the Iris dataset
        2. train_model: Train a RandomForest classifier and log to MLflow
    """
    # Connect the steps: output of preprocess is input to train
    data_path = preprocess_data()
    train_model(data_path=data_path)


if __name__ == "__main__":
    # Run the pipeline
    iris_pipeline()
