# run_pipeline.py
from zenml.pipelines import pipeline

# Import steps from src/pipeline modules
from src.pipeline.data_preprocess import preprocess_data
from src.pipeline.train_model import train_model

@pipeline
def iris_pipeline(preprocess, train):
    """
    ZenML pipeline for Iris flower classification.
    
    Args:
        preprocess: Data preprocessing step
        train: Model training step
    """
    # Connect the steps: output of preprocess is input to train
    data_path = preprocess()
    train(data_path)

if __name__ == "__main__":
    # Run the pipeline with the steps from src/pipeline
    iris_pipeline(
        preprocess=preprocess_data(),
        train=train_model()
    )
