import pytest
import uuid
from insightgen.pipeline_utils import insert_user, bq, USERS_TEST_TABLE
import time
from dotenv import load_dotenv, find_dotenv

# Force reload environment variables to ensure correct credentials
dotenv_path = find_dotenv()
load_dotenv(dotenv_path, override=True)

def test_insert_user(monkeypatch):
    # Create a tracking list to record calls
    calls = []

    # Define a mock function to replace insert_rows_json
    def mock_insert_rows_json(table_name, rows):
        calls.append((table_name, rows))
        return []

    # Patch the bq.insert_rows_json method
    monkeypatch.setattr(bq, 'insert_rows_json', mock_insert_rows_json)

    # Sample user data based on schema
    test_user = {
        "user_id": str(uuid.uuid4()),
        "login_id": "testuser123",
        "hashed_password": "hashed_password_value",
        "full_name": "Test User",
        "email": "test@example.com",
        "company": "Test Company",
        "designation": "Developer",
        "access_granted": True,
        "access_level": "standard",
        "extra_info": {"test_field": "test_value"}
    }

    # Call the function
    insert_user(test_user)

    # Verify the insert_rows_json was called
    assert len(calls) == 1

    # Get the arguments passed to insert_rows_json
    table_name, rows = calls[0]

    # Validate table name and data
    assert table_name == USERS_TEST_TABLE
    assert len(rows) == 1

    # Check that all user fields are present in the inserted data
    inserted_row = rows[0]
    for key, value in test_user.items():
        if key == "extra_info":
            # Skip exact comparison for extra_info as it gets converted to a string
            assert "extra_info" in inserted_row
        else:
            assert inserted_row[key] == value

    # Verify registered_at field was added
    assert "registered_at" in inserted_row


def test_actual_insert_to_bigquery():
    """Test that actually writes to the BigQuery test table and verifies the insertion."""
    # Generate a unique identifier for this test run
    test_id = str(uuid.uuid4())
    timestamp = int(time.time())
    test_email = f"test_{test_id[:8]}_{timestamp}@myemail.com"

    # Create test user with unique identifiers
    test_user = {
        "user_id": test_id,
        "login_id": f"testuser_{test_id[:8]}_{timestamp}",
        "hashed_password": "thisismine",
        "full_name": "Sam Pitroda",
        "email": test_email,
        "company": "Test Company",
        "designation": "Tester",
        "access_granted": True,
        "access_level": "admin",
        "extra_info": {"test_run": timestamp}
    }

    # Insert the user
    insert_user(test_user)
    print(f"User inserted with ID: {test_id}")

    # Allow some time for BigQuery to process the insertion
    time.sleep(2)

    # Query to verify the record was inserted
    query = f"""
    SELECT *
    FROM `{USERS_TEST_TABLE}`
    WHERE user_id = '{test_id}'
    """

    print(f"Executing query: {query}")
    query_job = bq.query(query)
    results = list(query_job.result())

    # Verify the user was inserted
    assert len(results) == 1, "User record was not found in BigQuery"

    # Verify specific fields
    row = dict(results[0])
    assert row["email"] == test_email
    assert row["user_id"] == test_id
    assert "registered_at" in row

    print(f"Test successful - record verified in BigQuery")
