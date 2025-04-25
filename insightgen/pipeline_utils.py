from google.cloud import bigquery
from datetime import datetime, timezone
import os
import json
from dotenv import load_dotenv, find_dotenv

# Force reload environment variables to ensure correct credentials
dotenv_path = find_dotenv()
load_dotenv(dotenv_path, override=True)

# Project settings
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "insightgen-453212")

# Table references
USERS_TABLE = os.getenv("BQ_USER_TABLE", f"{PROJECT_ID}.insightgen_users.users")
PERM_TABLE = os.getenv("BQ_PERM_TABLE", f"{PROJECT_ID}.insightgen_users.user_service_permissions")
ACTIVITY_TABLE = os.getenv("BQ_ACTIVITY_TABLE", f"{PROJECT_ID}.insightgen_users.user_activity_logs")
USERS_TEST_TABLE = os.getenv("BQ_USER_TEST_TABLE", f"{PROJECT_ID}.insightgen_users.users_test")

# Print the table paths for debugging
print(f"DEBUG - Users test table path: {USERS_TEST_TABLE}")
print(f"DEBUG - Using project ID: {PROJECT_ID}")

# Initialize BQ with explicit project
bq = bigquery.Client(project=PROJECT_ID)

def insert_user(user: dict, table_id=None):
    """
    Add a new row to the users table.

    Args:
        user: Dictionary containing user data
        table_id: Optional table ID to override the default USERS_TEST_TABLE

    Returns:
        Dictionary containing the inserted user data including registration timestamp
    """
    # Use the specified table or default to USERS_TEST_TABLE
    target_table = table_id or USERS_TEST_TABLE

    # Make a copy to avoid modifying the original
    user_data = user.copy()

    # Add registration timestamp
    user_data["registered_at"] = datetime.now(timezone.utc).isoformat()

    # Convert JSON fields to strings
    if "extra_info" in user_data and isinstance(user_data["extra_info"], (dict, list)):
        user_data["extra_info"] = json.dumps(user_data["extra_info"])

    # Insert the row
    errors = bq.insert_rows_json(target_table, [user_data])

    if errors:
        raise Exception(f"Error inserting user: {errors}")

    return user_data

def log_user_activity(job_data):
    """
    Log completed user activity to BigQuery.

    Args:
        job_data: Dictionary containing all job data to be logged

    Returns:
        Boolean indicating success or failure
    """
    try:
        # Ensure the job_data has all required fields set (even if empty)
        required_fields = [
            "user_id", "job_id", "service", "status", "error_message",
            "ts", "pptx_filename", "pdf_filename", "pptx_file_path",
            "pdf_file_path", "output_path", "output_type", "download_url",
            "batch_size", "duration_seconds", "slide_metadata"
        ]

        # Set defaults for missing fields
        for field in required_fields:
            if field not in job_data:
                if field in ["batch_size", "duration_seconds"]:
                    job_data[field] = None  # Numeric fields can be null
                elif field == "ts":
                    job_data[field] = datetime.now(timezone.utc).isoformat()
                elif field == "slide_metadata":
                    job_data[field] = json.dumps({})
                else:
                    job_data[field] = ""  # String fields default to empty string

        # Convert slide_metadata to JSON string if it's not already
        if isinstance(job_data["slide_metadata"], (dict, list)):
            job_data["slide_metadata"] = json.dumps(job_data["slide_metadata"])

        # Insert the row into the activity log table
        errors = bq.insert_rows_json(ACTIVITY_TABLE, [job_data])

        if errors:
            print(f"Error logging user activity: {errors}")
            return False

        print(f"Successfully logged activity for job {job_data['job_id']}")
        return True

    except Exception as e:
        print(f"Exception in log_user_activity: {str(e)}")
        return False
