"""
Pipeline definition for the ML training pipeline.
"""
import os
import logging
from zenml.pipelines import pipeline
from src.pipeline.data_preprocess import preprocess_data
from src.pipeline.train_model import train_model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_pipeline(preprocess_data_fn, train_model_fn):
    """
    Create a ZenML pipeline for Iris flower classification.
    
    Args:
        preprocess_data_fn: Function for data preprocessing
        train_model_fn: Function for model training
        
    Returns:
        A pipeline instance that can be executed.
    """
    @pipeline(name="iris_classification_pipeline")
    def train_pipeline():
        """
        ZenML pipeline for Iris flower classification.
        
        Returns:
            A pipeline instance that can be executed.
        """
        # Connect the steps: output of preprocess is input to train
        logger.info("Starting iris classification pipeline")
        data_path = preprocess_data_fn()
        logger.info(f"Preprocessing completed, data path: {data_path}")
        model_path = train_model_fn(data_path=data_path)
        logger.info(f"Training completed, model path: {model_path}")
        logger.info("Pipeline execution completed successfully")
        return model_path
    
    return train_pipeline

# Usage
train_pipeline = create_pipeline(preprocess_data, train_model)
