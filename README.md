# InsightGen

InsightGen is an AI-powered tool that automatically generates insightful headlines for market research presentations, with a current focus on BGS (Business Growth Strategy) studies. The application processes PPTX and PDF files to extract meaningful insights and create compelling headlines.

## Features

- Upload and process PPTX and PDF files
- AI-powered headline generation
- Streamlit-based user interface
- FastAPI backend service
- Google Cloud Storage integration
- Docker support for containerization
- Cloud deployment ready
- Auto deployment is working

## Google Cloud Deployment Steps

### Option 1: Using the deploy.sh Script

1. Ensure you have Google Cloud SDK installed and configured
2. Set the required environment variables:
```bash
export GCP_PROJECT_ID=your-project-id
export GCS_BUCKET=your-storage-bucket
export OPENAI_API=your-openai-api-key
```
3. Run the deployment script:
```bash
./deploy.sh
```

### Option 2: Using Cloud Build

1. Set up a Cloud Build trigger in the Google Cloud Console:
   - Go to Cloud Build > Triggers
   - Create a new trigger pointing to your GitHub repository
   - Set the build configuration to use the cloudbuild.yaml file

2. Configure substitution variables in your trigger:
   - `_GCS_BUCKET`: Name of your Google Cloud Storage bucket (default: insightgen-generators)
   - `_OPENAI_API`: Your OpenAI API key

3. Make sure your project has the necessary IAM permissions:
   - Service account: cloud-build-service-account@$PROJECT_ID.iam.gserviceaccount.com
   - Roles needed: Cloud Run Admin, Storage Admin

4. Push changes to your repository to trigger the build automatically, or manually trigger the build

5. The Cloud Build process will:
   - Build the Docker container
   - Push it to Container Registry
   - Deploy to Cloud Run with the following configuration:
     - Region: us-central1
     - Memory: 2Gi
     - CPU: 1
     - Timeout: 3600s (1 hour)
     - Unauthenticated access enabled
     - Environment variables set for STORAGE_MODE, GCS_BUCKET, and OPENAI_API

6. After deployment, your API will be available at the Cloud Run service URL

## Prerequisites

- Python 3.8 or higher
- Docker (optional, for containerized deployment)
- Google Cloud Platform account (for cloud deployment)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/insightgen.git
cd insightgen
```

2. Create and activate a virtual environment:
```bash
python -m venv insightgen_venv
source insightgen_venv/bin/activate  # On Windows: insightgen_venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with the following variables:
```
OPENAI_API_KEY=your_openai_api_key
GOOGLE_CLOUD_PROJECT=your_project_id
```

## Usage

### Local Development

1. Start the API server:
```bash
./start_api.sh
```

2. Start the UI server:
```bash
./start_ui.sh
```

3. Open your browser and navigate to `http://localhost:8501`

### Docker Deployment

Build and run using Docker:
```bash
docker build -t insightgen .
docker run -p 8501:8501 insightgen
```

## Project Structure

- `run_ui.py`: Streamlit-based user interface
- `run_api.py`: FastAPI backend service
- `insightgen/`: Core application package
- `generators/`: AI model generators
- `tests/`: Test suite
- `config/`: Configuration files
- `models/`: Model definitions
- `data/`: Data storage
- `notebooks/`: Jupyter notebooks for development

## Development

For development, install additional dependencies:
```bash
pip install -r requirements-dev.txt
```

## Deployment

The project includes configuration files for various deployment platforms:
- `cloudbuild.yaml`: Google Cloud Build configuration
- `render.yaml`: Render deployment configuration
- `Dockerfile`: Container configuration

## Contributing

SUMIT KAMRA
