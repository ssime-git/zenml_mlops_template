#!/bin/bash
# Helper script to run ZenML CLI commands with proper authentication
# Uses the same service account approach as run_zenml_pipeline.sh

ZENML_URL="${ZENML_STORE_URL:-http://zenml:8080}"
ADMIN_USER="${ZENML_DEFAULT_USER_NAME:-admin}"
ADMIN_PASS="${ZENML_DEFAULT_USER_PASSWORD:-zenml}"
SERVICE_ACCOUNT_NAME="pipeline-runner"

# Wait for ZenML server
until curl -s "$ZENML_URL/health" > /dev/null 2>&1; do
    echo "Waiting for ZenML server..."
    sleep 2
done

# Authenticate as admin to get access token
AUTH_RESPONSE=$(curl -s -X POST "$ZENML_URL/api/v1/login" \
    -d "username=$ADMIN_USER&password=$ADMIN_PASS" \
    -H "Content-Type: application/x-www-form-urlencoded")

ACCESS_TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "ERROR: Failed to authenticate as admin"
    exit 1
fi

# Get service account ID
SA_LIST=$(curl -s -X GET "$ZENML_URL/api/v1/service_accounts?name=$SERVICE_ACCOUNT_NAME" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

SA_ID=$(echo "$SA_LIST" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$SA_ID" ]; then
    echo "ERROR: Service account '$SERVICE_ACCOUNT_NAME' not found. Run 'make train' first."
    exit 1
fi

# Create a temporary API key for this CLI session
API_KEY_RESPONSE=$(curl -s -X POST "$ZENML_URL/api/v1/service_accounts/$SA_ID/api_keys" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"cli-session-$(date +%s)\"}")

ZENML_STORE_API_KEY=$(echo "$API_KEY_RESPONSE" | grep -o '"key":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ZENML_STORE_API_KEY" ]; then
    echo "ERROR: Failed to create API key"
    exit 1
fi

# Set environment for ZenML CLI
export ZENML_STORE_URL="$ZENML_URL"
export ZENML_STORE_API_KEY

# Run the ZenML command
exec zenml "$@"
