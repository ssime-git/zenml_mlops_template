.PHONY: help up down build logs train retrain clean public private zenml

help:
	@echo "ZenML MLOps Template - Available commands:"
	@echo ""
	@echo "  make up        - Start all services (ZenML, MLflow, Inference API, Prometheus, Grafana)"
	@echo "  make down      - Stop all services"
	@echo "  make build     - Build all Docker images"
	@echo "  make logs      - View logs from all services"
	@echo "  make train     - Run the ML training pipeline"
	@echo "  make retrain   - Trigger model retraining via API"
	@echo "  make predict   - Make example prediction"
	@echo "  make health    - Check API health"
	@echo "  make clean     - Remove all containers, volumes, and data"
	@echo "  make zenml CMD=\"...\" - Run ZenML CLI commands"
	@echo ""
	@echo "Quick start:"
	@echo "  make up && make train"
	@echo ""
	@echo "Service URLs:"
	@echo "  - ZenML Dashboard: http://localhost:8888 (admin / zenml)"
	@echo "  - MLflow UI:       http://localhost:5001"
	@echo "  - Inference API:   http://localhost:8000"
	@echo "  - Prometheus:      http://localhost:9092"
	@echo "  - Grafana:         http://localhost:3002"

# Docker Compose commands
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

# Training commands
train:
	docker compose --profile pipeline run --rm pipeline-runner

retrain:
	curl -X POST http://localhost:8000/retrain

# Inference commands
predict:
	@echo "Example prediction request:"
	curl -X POST http://localhost:8000/predict \
		-H "Content-Type: application/json" \
		-d '{"sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4, "petal_width": 0.2}'

health:
	curl http://localhost:8000/health

# Cleanup
# you might need to sudo remove data/ folder
clean:
	docker compose down -v
	docker run --rm -v $(PWD)/data:/data alpine rm -rf /data/* 2>/dev/null || true
	rm -rf ./data-file/*.csv .env

# Local development (without Docker)
install-local:
	uv sync

run-local:
	python run_pipeline.py

# ZenML CLI - run any zenml command
# Usage: make zenml CMD="pipeline list"
#        make zenml CMD="artifact list"  
#        make zenml CMD="stack describe"
zenml:
	docker compose --profile pipeline run --rm --entrypoint /app/zenml_cli.sh pipeline-runner $(CMD)

# GitHub repository visibility
make-public:
	gh repo edit --visibility public --accept-visibility-change-consequences

make-private:
	gh repo edit --visibility private --accept-visibility-change-consequences