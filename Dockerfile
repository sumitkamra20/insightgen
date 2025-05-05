FROM python:3.10-slim

WORKDIR /app

# Copy only the necessary files
COPY requirements.txt .
COPY insightgen/ ./insightgen/
COPY run_api.py .

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV STORAGE_MODE=gcs
ENV PORT=8090

# Expose the port
EXPOSE 8090

# Run the API server using the run_api.py script
CMD ["python", "run_api.py"]
