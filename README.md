# ZenML MLOps Template

A complete MLOps pipeline using ZenML, MLflow, FastAPI, and Docker.

## Quick Start

```bash
# 1. Start all services
make up

# 2. Run the training pipeline (auto-creates service account)
make train

# 3. Make a prediction
make predict

# 4. Trigger retraining via API
make retrain
```

> **Note:** The pipeline-runner automatically creates a ZenML service account and API key on first run using the REST API. No manual setup required.

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| ZenML Dashboard | http://localhost:8888 | admin / zenml |
| MLflow UI | http://localhost:5001 | - |
| Inference API | http://localhost:8000 | - |
| Prometheus | http://localhost:9092 | - |
| Grafana | http://localhost:3002 | admin / admin |

## Architecture

```mermaid
graph TD
    subgraph "Infrastructure"
        MySQL[(MySQL)] --> ZenML[ZenML Server]
        MLflow[MLflow Tracking]
    end
    
    subgraph "Pipeline Execution"
        Runner[Pipeline Runner] -->|Register & Track| ZenML
        Runner -->|Step 1| Preprocess[Data Preprocessing]
        Preprocess -->|Step 2| Train[Model Training]
        Train -->|Log Model| MLflow
    end
    
    subgraph "Inference Service"
        API[FastAPI] --> Predict["/predict"]
        API --> Retrain["/retrain"]
        API --> Health["/health"]
        API -->|Load Model| MLflow
    end
    
    subgraph "Monitoring"
        Prometheus --> Grafana
    end
    
    Retrain -.->|Trigger| Runner
    API -->|Metrics| Prometheus
    
    User([User]) -->|make train| Runner
    User -->|API Calls| API
    User -->|View Pipelines| ZenML
    User -->|View Experiments| MLflow
    User -->|View Metrics| Grafana
```

## Project Structure

```
zenml_mlops_template/
├── config/                         # Configuration files
│   └── prometheus.yml
├── docs/
│   └── tutorial.ipynb              # Interactive tutorial notebook
├── dockerfiles/                    # Docker build files
│   ├── Dockerfile.inference
│   ├── Dockerfile.pipeline-runner
│   ├── requirements-*.txt          # Pinned dependencies
├── scripts/
│   └── run_zenml_pipeline.sh       # Pipeline runner script
├── src/
│   ├── pipeline/
│   │   ├── data_preprocess.py      # Data preprocessing step
│   │   └── train_model.py          # Model training step
│   └── services/
│       └── inference/
│           └── inference_service.py # FastAPI service
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── run_pipeline.py                 # ZenML pipeline definition
```

## Tutorial

For an interactive walkthrough, open the Jupyter notebook:

```bash
jupyter notebook docs/tutorial.ipynb
```

The notebook demonstrates all make commands with example outputs.

## Commands

### Makefile Commands

```bash
make help      # Show all available commands
make up        # Start all services
make down      # Stop all services
make build     # Build Docker images
make logs      # View service logs
make train     # Run training pipeline
make retrain   # Trigger retraining via API
make predict   # Make example prediction
make health    # Check API health
make clean     # Remove containers and data
```

### Docker Compose Commands

```bash
# Start infrastructure only
docker compose up -d

# Run training pipeline (on-demand)
docker compose --profile pipeline run --rm pipeline-runner

# View logs
docker compose logs -f <service-name>

# Stop everything
docker compose down -v
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Prediction
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4, "petal_width": 0.2}'
```

Response:
```json
{"prediction": 0}
```

### Model Info
```bash
curl http://localhost:8000/model/info
```

Response:
```json
{
  "model_name": "iris-classifier",
  "production_version": "1",
  "run_id": "a93d65c7b1f845559ac9e34c4fc1fd33",
  "metrics": {"accuracy": 1.0},
  "parameters": {"n_estimators": "50"},
  "total_versions": 2,
  "aliases": {"production": "1", "challenger": "2"}
}
```

### Trigger Retraining
```bash
curl -X POST http://localhost:8000/retrain
```

Response:
```json
{
  "status": "retraining_started",
  "message": "Model retraining has been started in the background..."
}
```

### Prometheus Metrics
```bash
curl http://localhost:8000/metrics
```

## Training Pipeline

The pipeline consists of two ZenML steps:

1. **preprocess_data**: Loads the Iris dataset and saves preprocessed CSV
2. **train_model**: Trains RandomForest classifier, registers in MLflow Model Registry

### Model Registry

The pipeline uses **MLflow Model Registry** for model versioning and promotion:

- **Model Name**: `iris-classifier`
- **Aliases**: 
  - `production` - Current best model serving predictions
  - `challenger` - New models that didn't beat production

**Promotion Logic**: New models are only promoted to production if their accuracy **exceeds** the current production model's accuracy.

```sh
# Example output from training:
[train_model] Current production model (v1) accuracy: 1.0000
[train_model] Model accuracy: 0.9800
[train_model] ❌ New model (v2) NOT promoted. Accuracy: 0.9800 <= 1.0000
```

### Run Training

```bash
# Via Docker (recommended)
make train

# Or directly
docker compose --profile pipeline run --rm pipeline-runner
```

### Retraining Flow

```mermaid
sequenceDiagram
    participant User
    participant API as Inference API
    participant Runner as Pipeline Runner
    participant Registry as MLflow Registry
    
    User->>API: POST /retrain
    API-->>User: {"status": "retraining_started"}
    API->>Runner: docker compose run pipeline-runner
    Runner->>Runner: Preprocess data
    Runner->>Runner: Train model
    Runner->>Registry: Get production model accuracy
    Runner->>Registry: Register new model version
    alt New accuracy > Production accuracy
        Runner->>Registry: Promote to production
        API->>Registry: Load new production model
    else New accuracy <= Production accuracy
        Runner->>Registry: Mark as challenger
        Note over API: Keep using current model
    end
```

## Monitoring

### MLflow
- View experiments: http://localhost:5001
- **Model Registry**: http://localhost:5001/#/models
- Track metrics, parameters, and model artifacts
- View registered models and their versions (production vs challenger)

### Prometheus
- View metrics: http://localhost:9092
- Query `prediction_requests_total` for prediction count
- Query `model_retrain_total` for retrain count

### Grafana
![alt text](./assets/grafana_dashboard.png)
- Dashboard: http://localhost:3002/d/mlops-inference
- Login: admin / admin
- **Pre-configured**: Prometheus datasource and MLOps dashboard are auto-provisioned

The MLOps Inference Dashboard includes:
- Total Predictions counter
- Total Model Retrains counter
- API Status indicator
- Prediction Request Rate graph
- Model Retrain Events timeline
- Cumulative Metrics Over Time

## Local Development

```bash
# Install dependencies
uv sync

# Run pipeline locally
python run_pipeline.py
```

## Troubleshooting

```bash
# Check service status
docker compose ps

# View logs
docker compose logs zenml
docker compose logs mlflow
docker compose logs inference-api

# Restart a service
docker compose restart <service-name>

# Full reset
make clean
make up
make train
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| ZENML_PASSWORD | zenml | ZenML admin password |
| MLFLOW_TRACKING_URI | http://mlflow:5000 | MLflow server URL |
| ZENML_STORE_URL | http://zenml:8080 | ZenML server URL |

### Custom Password

To use a custom ZenML admin password, create a `.env` file:

```bash
ZENML_PASSWORD=your_secure_password
```

### Automatic Setup

On first run, `make train` automatically:

1. **Activates ZenML server** - Creates admin user via `PUT /api/v1/activate`
2. **Creates service account** - `pipeline-runner` for non-interactive auth
3. **Generates API key** - For secure pipeline execution
4. **Runs the pipeline** - Executes preprocessing and training steps

No manual configuration required.

### Pinned Versions

All dependencies are pinned in `dockerfiles/requirements-*.txt` and `pyproject.toml` for reproducibility.
