#!/bin/bash
set -e

ZENML_URL="${ZENML_STORE_URL:-http://zenml:8080}"
ADMIN_USER="${ZENML_DEFAULT_USER_NAME:-admin}"
ADMIN_PASS="${ZENML_DEFAULT_USER_PASSWORD:-zenml}"
SERVICE_ACCOUNT_NAME="pipeline-runner"

echo "=============================================="
echo "ZenML Pipeline Runner"
echo "=============================================="

echo "Waiting for ZenML server to be ready..."
until curl -s "$ZENML_URL/health" > /dev/null 2>&1; do
    echo "ZenML server not ready, waiting..."
    sleep 3
done
echo "ZenML server is ready!"

echo "Waiting for MLflow to be ready..."
until curl -s http://mlflow:5000/ > /dev/null 2>&1; do
    echo "MLflow not ready, waiting..."
    sleep 3
done
echo "MLflow is ready!"

# Check if server needs activation (first run)
SERVER_INFO=$(curl -s "$ZENML_URL/api/v1/info")
SERVER_ACTIVE=$(echo "$SERVER_INFO" | grep -o '"active":[^,]*' | cut -d':' -f2)

if [ "$SERVER_ACTIVE" = "false" ]; then
    echo ""
    echo "Server not activated. Activating with admin account..."
    ACTIVATE_RESPONSE=$(curl -s -X PUT "$ZENML_URL/api/v1/activate" \
        -H "Content-Type: application/json" \
        -d "{\"admin_username\": \"$ADMIN_USER\", \"admin_password\": \"$ADMIN_PASS\"}")
    
    if echo "$ACTIVATE_RESPONSE" | grep -q '"name":"admin"'; then
        echo "Server activated successfully!"
    else
        echo "WARNING: Server activation may have failed: $ACTIVATE_RESPONSE"
    fi
fi

# Auto-create API key if not provided
if [ -z "$ZENML_STORE_API_KEY" ]; then
    echo ""
    echo "No API key provided. Auto-creating service account..."
    
    # Authenticate as admin
    AUTH_RESPONSE=$(curl -s -X POST "$ZENML_URL/api/v1/login" \
        -d "username=$ADMIN_USER&password=$ADMIN_PASS" \
        -H "Content-Type: application/x-www-form-urlencoded")
    
    ACCESS_TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$ACCESS_TOKEN" ]; then
        echo "ERROR: Failed to authenticate as admin."
        echo "Response: $AUTH_RESPONSE"
        exit 1
    fi
    
    # Check if service account exists
    SA_LIST=$(curl -s -X GET "$ZENML_URL/api/v1/service_accounts?name=$SERVICE_ACCOUNT_NAME" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    SA_ID=$(echo "$SA_LIST" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    
    if [ -z "$SA_ID" ]; then
        # Create service account
        echo "Creating service account '$SERVICE_ACCOUNT_NAME'..."
        SA_RESPONSE=$(curl -s -X POST "$ZENML_URL/api/v1/service_accounts" \
            -H "Authorization: Bearer $ACCESS_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"name\": \"$SERVICE_ACCOUNT_NAME\", \"active\": true}")
        
        SA_ID=$(echo "$SA_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
        
        if [ -z "$SA_ID" ]; then
            echo "ERROR: Failed to create service account."
            exit 1
        fi
        echo "Service account created: $SA_ID"
    else
        echo "Service account exists: $SA_ID"
    fi
    
    # Create API key
    echo "Creating API key..."
    API_KEY_RESPONSE=$(curl -s -X POST "$ZENML_URL/api/v1/service_accounts/$SA_ID/api_keys" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"pipeline-run-$(date +%s)\"}")
    
    ZENML_STORE_API_KEY=$(echo "$API_KEY_RESPONSE" | grep -o '"key":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$ZENML_STORE_API_KEY" ]; then
        echo "ERROR: Failed to create API key."
        exit 1
    fi
    
    export ZENML_STORE_API_KEY
    echo "API key created successfully."
fi

echo ""
echo "Connecting to ZenML server..."
export ZENML_STORE_URL="$ZENML_URL"

# Setup S3/MinIO artifact store if not already configured
echo ""
echo "Setting up S3 artifact store (MinIO)..."

# Check if s3-artifacts store exists
S3_STORE_EXISTS=$(zenml artifact-store list 2>/dev/null | grep -c "s3-artifacts" || true)

if [ "$S3_STORE_EXISTS" = "0" ]; then
    echo "Registering S3 artifact store..."
    zenml artifact-store register s3-artifacts \
        --flavor=s3 \
        --path=s3://zenml-artifacts \
        --client_kwargs='{"endpoint_url": "http://minio:9000"}' \
        2>/dev/null || echo "Artifact store may already exist"
fi

# Check if s3-stack exists
S3_STACK_EXISTS=$(zenml stack list 2>/dev/null | grep -c "s3-stack" || true)

if [ "$S3_STACK_EXISTS" = "0" ]; then
    echo "Registering S3 stack..."
    zenml stack register s3-stack \
        -a s3-artifacts \
        -o default \
        2>/dev/null || echo "Stack may already exist"
fi

# Set the S3 stack as active
echo "Setting s3-stack as active..."
zenml stack set s3-stack 2>/dev/null || true

# Run the ZenML pipeline
echo ""
echo "Running ZenML pipeline..."
cd /app
python run_pipeline.py

echo ""
echo "=============================================="
echo "Pipeline completed successfully!"
echo "=============================================="
