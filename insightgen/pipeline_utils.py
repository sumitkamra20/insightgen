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

def insert_user(user: dict):
    """Add a new row to users."""
    # Make a copy to avoid modifying the original
    user_data = user.copy()

    # Add registration timestamp
    user_data["registered_at"] = datetime.now(timezone.utc).isoformat()

    # Convert JSON fields to strings
    if "extra_info" in user_data and isinstance(user_data["extra_info"], (dict, list)):
        user_data["extra_info"] = json.dumps(user_data["extra_info"])

    # Insert the row
    errors = bq.insert_rows_json(USERS_TEST_TABLE, [user_data])

    if errors:
        raise Exception(f"Error inserting user: {errors}")

    return user_data
