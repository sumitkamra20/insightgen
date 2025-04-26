# Apache Airflow Workflow Setup: Summary of Process, Issues, and Solutions

## Setup Process Overview

1. **Initial Configuration**
   - Set up Airflow using Docker Compose with three services: PostgreSQL, webserver, and scheduler
   - Configured environment variables for authentication and Google Cloud credentials
   - Mounted volumes for DAGs, logs, plugins, and Google service account key

2. **DAG Implementation**
   - Created a `weekly_summary.py` DAG that generates analytics tables in BigQuery
   - Implemented five tasks to create summary tables for user registrations, job counts, batch sizes, durations, and per-user jobs
   - Initially set to run on a daily schedule
   - Later modified to run every 5 minutes for demo purposes

3. **BigQuery Integration**
   - Connected Airflow to BigQuery using service account credentials
   - Created SQL queries to build analytics tables from user activity and registration data
   - Set up proper error handling and result processing

## Issues Encountered and Solutions

1. **Plugin Loading Errors**
   ```
   ERROR - Failed to import plugin /opt/airflow/plugins/__init__.py
   ImportError: attempted relative import with no known parent package
   ```
   **Solution**: Modified the plugin structure to define utilities directly in the file instead of using relative imports:
   ```python
   # Define utilities module directly in this file
   class InsightGenUtils:
       """Utility functions for InsightGen workflow orchestration"""
       @staticmethod
       def validate_data(data):
           """Example validation function"""
           return data is not None
   ```

2. **Authentication Problems**
   - Login failed with credentials "airflow/airflow"

   **Solution**:
   - Added environment variables to set username and password:
     ```yaml
     - AIRFLOW__WEBSERVER__AUTHENTICATE=True
     - AIRFLOW__WEBSERVER__AUTH_BACKEND=airflow.api.auth.backend.basic_auth
     - _AIRFLOW_WWW_USER_USERNAME=airflow
     - _AIRFLOW_WWW_USER_PASSWORD=airflow
     ```
   - Created a script to add the admin user:
     ```bash
     docker-compose exec webserver airflow users create \
         --username airflow \
         --firstname Admin \
         --lastname User \
         --role Admin \
         --email admin@example.com \
         --password airflow
     ```

3. **DAG Not Appearing in UI**
   - After deleting a DAG, it disappeared from the UI

   **Solution**:
   - Verified DAG file still existed in the correct location
   - Restarted scheduler and webserver to reprocess DAG files:
     ```bash
     docker-compose restart scheduler webserver
     ```

4. **Tasks Stuck in "Scheduled" State**
   - Tasks would not progress from "scheduled" state to "running"

   **Solutions**:
   1. Added concurrency settings to docker-compose.yml:
      ```yaml
      - AIRFLOW__CORE__PARALLELISM=4
      - AIRFLOW__CORE__DAG_CONCURRENCY=2
      - AIRFLOW__SCHEDULER__MAX_THREADS=2
      - AIRFLOW__SCHEDULER__PARSING_PROCESSES=2
      ```
   2. Created default pool:
      ```bash
      docker-compose exec webserver airflow pools set default_pool 4 "Default pool"
      ```
   3. Fixed database schema issues:
      ```bash
      docker-compose exec webserver airflow db init
      docker-compose exec webserver airflow db upgrade
      docker-compose exec webserver airflow connections create-default-connections
      ```

5. **BigQuery Permission/Configuration Issues**
   - Tables were being created but not visible in console

   **Solution**:
   - Created test scripts to verify BigQuery connectivity
   - Confirmed tables were being created by directly querying the dataset
   - Verified credential mounting and permissions were correct

## Technical Improvements

1. **Worker Concurrency Optimization**
   - Added settings to control task processing:
     ```yaml
     AIRFLOW__CORE__PARALLELISM=4
     AIRFLOW__CORE__DAG_CONCURRENCY=2
     AIRFLOW__SCHEDULER__MAX_THREADS=2
     ```

2. **Schedule Interval Adjustment**
   - Modified from daily to 5-minute intervals for demo purposes:
     ```python
     schedule_interval="*/5 * * * *"  # Run every 5 minutes
     ```

3. **Error Handling Improvements**
   - Added proper BigQuery client error handling
   - Implemented appropriate task retries and timeout configuration

## Validation and Testing

1. **Created test_bq.py script** to verify BigQuery connectivity and permissions:
   - Tested simple queries
   - Checked dataset existence
   - Created test tables

2. **Created check_tables.py script** to verify DAG operation:
   - Listed all tables in the analytics dataset
   - Confirmed row counts and creation timestamps
   - Validated that all expected tables were present

## Final Outcome

Successfully configured Airflow to run a DAG that creates the following analytical tables:
- daily_registrations (registrations per day)
- daily_job_counts (job counts per day)
- daily_avg_batch_size (average batch size per day)
- daily_avg_duration (average job duration per day)
- total_jobs_by_user (job counts per user)

These tables can now be used for visualization in Looker Studio or similar tools.

## Important Commands Reference

### Container Management
```bash
# Start all containers
docker-compose up -d

# Stop all containers
docker-compose down

# Restart specific services
docker-compose restart webserver scheduler

# Check container status
docker-compose ps
```

### Airflow User Management
```bash
# Create admin user
docker-compose exec webserver airflow users create \
    --username airflow \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password airflow

# List users
docker-compose exec webserver airflow users list
```

### DAG Management
```bash
# List all DAGs
docker-compose exec webserver airflow dags list

# Trigger a DAG
docker-compose exec webserver airflow dags trigger weekly_summary

# Check DAG status
docker-compose exec webserver airflow dags list-runs -d weekly_summary
```

### Task Management
```bash
# List tasks in a DAG
docker-compose exec webserver airflow tasks list weekly_summary --tree

# Check task states for a DAG run
docker-compose exec webserver airflow tasks states-for-dag-run weekly_summary [RUN_ID]

# Create pool
docker-compose exec webserver airflow pools set default_pool 4 "Default pool"
```

### Database Management
```bash
# Initialize database
docker-compose exec webserver airflow db init

# Upgrade database
docker-compose exec webserver airflow db upgrade

# Create default connections
docker-compose exec webserver airflow connections create-default-connections
```
