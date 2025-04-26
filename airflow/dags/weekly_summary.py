"""
Weekly Summary DAG

This DAG builds summary tables in BigQuery for analytics purposes.
It runs on a daily schedule to keep analytics tables up-to-date.
"""

from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow import DAG
from google.cloud import bigquery

# Define default arguments
default_args = {
    "owner": "insightgen",
    "depends_on_past": False,
    "email": ["sumitkamra@gmail.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Define your DAG with @dag or via DAG() context
with DAG(
    dag_id="weekly_summary",
    default_args=default_args,
    description="Build daily summary tables",
    schedule_interval="@daily",           # run once a day
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["analytics"],
) as dag:

    @task()
    def build_daily_registrations():
        """
        1) Create or replace insightgen_analytics.daily_registrations
        """
        client = bigquery.Client()
        sql = """
        CREATE OR REPLACE TABLE `insightgen-453212.insightgen_analytics.daily_registrations` AS
        SELECT
          DATE(registered_at) AS day,
          COUNT(*) AS registrations
        FROM `insightgen-453212.insightgen_users.users`
        GROUP BY day
        """
        client.query(sql).result()  # .result() waits for completion

    @task()
    def build_daily_job_counts():
        """
        2) Create or replace insightgen_analytics.daily_job_counts
        """
        client = bigquery.Client()
        sql = """
        CREATE OR REPLACE TABLE `insightgen-453212.insightgen_analytics.daily_job_counts` AS
        SELECT
          DATE(ts) AS day,
          COUNT(*) AS total_jobs
        FROM `insightgen-453212.insightgen_users.user_activity_logs`
        GROUP BY day
        """
        client.query(sql).result()

    @task()
    def build_daily_batch_size():
        """
        3) Create or replace insightgen_analytics.daily_avg_batch_size
        """
        client = bigquery.Client()
        sql = """
        CREATE OR REPLACE TABLE `insightgen-453212.insightgen_analytics.daily_avg_batch_size` AS
        SELECT
          DATE(ts) AS day,
          AVG(batch_size) AS avg_batch_size
        FROM `insightgen-453212.insightgen_users.user_activity_logs`
        GROUP BY day
        """
        client.query(sql).result()

    @task()
    def build_daily_avg_duration():
        """
        4) Create or replace insightgen_analytics.daily_avg_duration
        """
        client = bigquery.Client()
        sql = """
        CREATE OR REPLACE TABLE `insightgen-453212.insightgen_analytics.daily_avg_duration` AS
        SELECT
          DATE(ts) AS day,
          AVG(duration_seconds) AS avg_duration
        FROM `insightgen-453212.insightgen_users.user_activity_logs`
        GROUP BY day
        """
        client.query(sql).result()

    @task()
    def build_total_jobs_by_user():
        """
        5) Create or replace insightgen_analytics.total_jobs_by_user
        """
        client = bigquery.Client()
        sql = """
        CREATE OR REPLACE TABLE `insightgen-453212.insightgen_analytics.total_jobs_by_user` AS
        SELECT
          u.full_name,
          COUNT(l.job_id) AS jobs_count
        FROM `insightgen-453212.insightgen_users.users` AS u
        JOIN `insightgen-453212.insightgen_users.user_activity_logs` AS l
          ON u.user_id = l.user_id
        GROUP BY u.full_name
        """
        client.query(sql).result()

    # they're all independent so they will run in parallel
    reg = build_daily_registrations()
    jobs = build_daily_job_counts()
    batch = build_daily_batch_size()
    duration = build_daily_avg_duration()
    by_user = build_total_jobs_by_user()
