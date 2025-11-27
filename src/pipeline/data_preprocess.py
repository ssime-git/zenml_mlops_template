# data_preprocess.py
from sklearn.datasets import load_iris
import pandas as pd
import os
import numpy as np
from zenml import step


@step(name="preprocess_data")
def preprocess_data() -> str:
    """
    Preprocess the Iris dataset.
    
    Returns:
        str: Path to the preprocessed data file
    """
    # Load the Iris dataset
    iris = load_iris()
    df = pd.DataFrame(
        data=np.c_[iris.data, iris.target],
        columns=iris.feature_names + ['target']
    )
    
    # Create output directory if it doesn't exist
    output_dir = 'data-file'
    os.makedirs(output_dir, exist_ok=True)
    
    # Save preprocessed data
    output_path = os.path.join(output_dir, 'iris_preprocessed.csv')
    df.to_csv(output_path, index=False)
    
    return output_path

def main():
    """
    Main function for running the preprocessing step directly.
    Used when this script is executed as a standalone program.
    """
    preprocess_data()

if __name__ == "__main__":
    main()