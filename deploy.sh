#!/bin/bash

# Exit on error
set -e

# Check if required environment variables are set
if [ -z "$GCP_PROJECT_ID" ]; then
  echo "Error: GCP_PROJECT_ID environment variable is not set"
  echo "Usage: GCP_PROJECT_ID=your-project-id GCS_BUCKET=your-bucket OPENAI_API=your-api-key ./deploy.sh"
  exit 1
fi

if [ -z "$GCS_BUCKET" ]; then
  echo "Error: GCS_BUCKET environment variable is not set"
  echo "Usage: GCP_PROJECT_ID=your-project-id GCS_BUCKET=your-bucket OPENAI_API=your-api-key ./deploy.sh"
  exit 1
fi

if [ -z "$OPENAI_API" ]; then
  echo "Error: OPENAI_API environment variable is not set"
  echo "Usage: GCP_PROJECT_ID=your-project-id GCS_BUCKET=your-bucket OPENAI_API=your-api-key ./deploy.sh"
  exit 1
fi

# Set variables
IMAGE_NAME="gcr.io/$GCP_PROJECT_ID/insightgen-api"
TAG=$(date +%Y%m%d-%H%M%S)

echo "Building Docker image: $IMAGE_NAME:$TAG"
docker build -t "$IMAGE_NAME:$TAG" .

echo "Pushing Docker image to Container Registry"
docker push "$IMAGE_NAME:$TAG"

echo "Deploying to Cloud Run"
gcloud run deploy insightgen-api \
  --image="$IMAGE_NAME:$TAG" \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=1 \
  --set-env-vars="STORAGE_MODE=gcs,GCS_BUCKET=$GCS_BUCKET,OPENAI_API=$OPENAI_API,OPENAI_OBSERVATIONS_MODEL=${OPENAI_OBSERVATIONS_MODEL:-gpt-4o},OPENAI_HEADLINES_MODEL=${OPENAI_HEADLINES_MODEL:-gpt-4o}" \
  --timeout=3600s \
  --project="$GCP_PROJECT_ID"

echo "Deployment completed successfully!"
echo "Your API is now available at: $(gcloud run services describe insightgen-api --platform=managed --region=us-central1 --format='value(status.url)' --project="$GCP_PROJECT_ID")"
