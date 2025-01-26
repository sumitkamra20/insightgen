#!/bin/bash

# Define project root directory (assuming you are already inside insightgen)
PROJECT_ROOT="."

# Create virtual environment directory (you may exclude this from Git)
mkdir -p $PROJECT_ROOT/venv

# Create folders for input and output data
mkdir -p $PROJECT_ROOT/data/input
mkdir -p $PROJECT_ROOT/data/output
mkdir -p $PROJECT_ROOT/data/temp

# Create source code structure with 'insightgen' as src directory
mkdir -p $PROJECT_ROOT/insightgen/api
mkdir -p $PROJECT_ROOT/insightgen/processing
mkdir -p $PROJECT_ROOT/insightgen/utils

# Create models directory for future fine-tuning
mkdir -p $PROJECT_ROOT/models/fine_tuned_model
mkdir -p $PROJECT_ROOT/models/training_scripts

# Create tests folder for unit and integration tests
mkdir -p $PROJECT_ROOT/tests

# Create configuration and logs folders
mkdir -p $PROJECT_ROOT/config
mkdir -p $PROJECT_ROOT/logs

# Create necessary files
touch $PROJECT_ROOT/.env
touch $PROJECT_ROOT/requirements.txt
touch $PROJECT_ROOT/README.md
touch $PROJECT_ROOT/setup.py
touch $PROJECT_ROOT/Dockerfile
touch $PROJECT_ROOT/.gitignore
touch $PROJECT_ROOT/config/settings.py
touch $PROJECT_ROOT/logs/process.log

# Provide necessary Python script files
touch $PROJECT_ROOT/insightgen/api/openai_client.py
touch $PROJECT_ROOT/insightgen/processing/process_slides.py
touch $PROJECT_ROOT/insightgen/utils/helpers.py
touch $PROJECT_ROOT/insightgen/main.py

# Add __init__.py files for package recognition
touch $PROJECT_ROOT/insightgen/__init__.py
touch $PROJECT_ROOT/insightgen/api/__init__.py
touch $PROJECT_ROOT/insightgen/processing/__init__.py
touch $PROJECT_ROOT/insightgen/utils/__init__.py

# Add common Git ignore patterns
echo "venv/" >> $PROJECT_ROOT/.gitignore
echo "data/temp/" >> $PROJECT_ROOT/.gitignore
echo "*.log" >> $PROJECT_ROOT/.gitignore
echo "__pycache__/" >> $PROJECT_ROOT/.gitignore
echo "*.pyc" >> $PROJECT_ROOT/.gitignore
echo ".DS_Store" >> $PROJECT_ROOT/.gitignore

echo "Project structure created successfully in '$PROJECT_ROOT'!"
