FROM python:3.10-slim

WORKDIR /app

# Copy only the necessary files
COPY requirements.txt .
COPY insightgen/ ./insightgen/

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV STORAGE_MODE=gcs
ENV PORT=8080

# Expose the port
EXPOSE 8080

# Run the API server
CMD ["uvicorn", "insightgen.api.app:app", "--host", "0.0.0.0", "--port", "8080"]
