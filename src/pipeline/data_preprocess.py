# data_preprocess.py
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np
from zenml import step, log_metadata
from typing import Tuple, Annotated


@step(name="preprocess_data")
def preprocess_data() -> Tuple[
    Annotated[pd.DataFrame, "X_train"],
    Annotated[pd.DataFrame, "X_test"],
    Annotated[pd.Series, "y_train"],
    Annotated[pd.Series, "y_test"],
]:
    """
    Preprocess the Iris dataset and split into train/test sets.
    
    Returns ZenML artifacts that are automatically tracked and versioned:
        - X_train: Training features
        - X_test: Test features  
        - y_train: Training labels
        - y_test: Test labels
    """
    # Load the Iris dataset
    iris = load_iris()
    df = pd.DataFrame(
        data=iris.data,
        columns=iris.feature_names
    )
    target = pd.Series(iris.target, name="target")
    
    # Split data into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(
        df, target, test_size=0.2, random_state=42
    )
    
    print(f"[preprocess_data] Dataset loaded: {len(df)} samples")
    print(f"[preprocess_data] Train set: {len(X_train)} samples")
    print(f"[preprocess_data] Test set: {len(X_test)} samples")
    
    # Log metadata for this step
    log_metadata(
        metadata={
            "dataset_info": {
                "name": "Iris",
                "total_samples": len(df),
                "num_features": len(iris.feature_names),
                "num_classes": len(iris.target_names),
                "feature_names": list(iris.feature_names),
                "class_names": list(iris.target_names),
            },
            "split_info": {
                "train_samples": len(X_train),
                "test_samples": len(X_test),
                "test_size": 0.2,
                "random_state": 42,
            },
        },
    )
    
    return X_train, X_test, y_train, y_test


def main():
    """
    Main function for running the preprocessing step directly.
    """
    X_train, X_test, y_train, y_test = preprocess_data()
    print(f"X_train shape: {X_train.shape}")

if __name__ == "__main__":
    main()