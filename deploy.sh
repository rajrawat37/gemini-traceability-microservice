#!/bin/bash

# Deploy to Google Cloud Run
# Make sure you're authenticated with gcloud and have the correct project set

set -e

# Configuration
PROJECT_ID="poc-genai-hacks"
SERVICE_NAME="vertex-agent-api"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying Vertex Agent API to Google Cloud Run..."
echo "Project: ${PROJECT_ID}"
echo "Service: ${SERVICE_NAME}"
echo "Region: ${REGION}"

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t ${IMAGE_NAME} .

# Push to Google Container Registry
echo "📤 Pushing image to GCR..."
docker push ${IMAGE_NAME}

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 900 \
    --max-instances 10 \
    --set-env-vars "PROJECT_ID=${PROJECT_ID},LOCATION=us,PROCESSOR_ID=e7f52140009fdda2,DLP_LOCATION=us,RAG_CORPUS_NAME=projects/poc-genai-hacks/locations/europe-west3/ragCorpora/6917529027641081856,RAG_LOCATION=europe-west3,GEMINI_LOCATION=us-central1,GEMINI_MODEL=gemini-2.0-flash-001"

echo "✅ Deployment complete!"
echo "🌐 Service URL: https://${SERVICE_NAME}-${REGION}-${PROJECT_ID}.a.run.app"
