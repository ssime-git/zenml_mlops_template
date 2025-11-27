# train_model.py
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import mlflow
import os
from zenml import step


@step(name="train_model")
def train_model(data_path: str) -> str:
    """
    ZenML step that trains a RandomForest model on the preprocessed data and logs metrics to MLflow.
    
    Args:
        data_path: Path to the preprocessed data CSV file
        
    Returns:
        str: Path to the saved model in MLflow
    """
    # Load preprocessed data from shared volume
    df = pd.read_csv(data_path)
    X = df.drop("target", axis=1)
    y = df["target"]

    # Split data into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Set MLflow tracking URI 
    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment("iris_classification")

    with mlflow.start_run() as run:
        n_estimators = 50
        model = RandomForestClassifier(n_estimators=n_estimators, random_state=42)
        mlflow.log_param("n_estimators", n_estimators)

        model.fit(X_train, y_train)
        accuracy = model.score(X_test, y_test)
        mlflow.log_metric("accuracy", accuracy)

        # Log model artifact to MLflow
        mlflow.sklearn.log_model(model, artifact_path="model")
        
        print(f"Model accuracy: {accuracy:.4f}")
        print(f"Model saved to MLflow with run_id: {run.info.run_id}")
        
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