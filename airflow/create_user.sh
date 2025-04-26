#!/bin/bash
# Script to create an admin user in Airflow

echo "Creating admin user in Airflow..."
docker-compose exec webserver airflow users create \
    --username airflow \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password airflow

echo "User creation completed."
