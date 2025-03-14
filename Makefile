install:
	zenml integration install sklearn mlflow

connect:
	zenml connect --url http://localhost:8888 --username admin --password P@ssword123$

init:
	zenml init

register-local-store:
	zenml artifact-store register local_store --flavor=local --path=./zenml_artifacts

register-local-docker-orchestrator:
	zenml orchestrator register local_docker_orchestrator --flavor=local_docker

register-mlflow-experiment-tracker:
	zenml experiment-tracker register mlflow_tracker --flavor=mlflow

register-local-stack:
	zenml stack register local_stack \
    -o local_docker_orchestrator \
    -a local_store \
    -e mlflow_tracker \
    --set

describe-local-stack:
	zenml stack describe local_stack