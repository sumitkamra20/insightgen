#!/bin/bash

# Activate the virtual environment
source insightgen_venv/bin/activate

# Set the Google application credentials explicitly
export GOOGLE_APPLICATION_CREDENTIALS="/Users/sumitkamra/code/sumitkamra20/keys/insightgen-453212-500436e1010d.json"

# Set the API port to avoid conflicts with Airflow (which is using 8080)
export API_PORT=8082

# Start the API server
python run_api.py
