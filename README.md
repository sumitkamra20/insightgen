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
