import uuid
import os
import bcrypt
from dotenv import load_dotenv, find_dotenv
from insightgen.pipeline_utils import insert_user

# Force reload environment variables to ensure correct credentials
dotenv_path = find_dotenv()
load_dotenv(dotenv_path, override=True)

# Get table reference from environment variable
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "insightgen-453212")
USERS_TABLE = os.getenv("BQ_USER_TABLE", f"{PROJECT_ID}.insightgen_users.users")

def create_test_user(login_id, password, full_name, email, access_level="standard"):
    """
    Create a test user in the BigQuery users table with proper password hashing.
    """
    # Generate a unique user ID
    user_id = str(uuid.uuid4())

    # Hash the password
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    # Create user data
    user_data = {
        "user_id": user_id,
        "login_id": login_id,
        "hashed_password": hashed_password,
        "full_name": full_name,
        "email": email,
        "company": "Test Company",
        "designation": "Tester",
        "access_granted": True,
        "access_level": access_level,
        "extra_info": {"created_via": "create_test_user_script"}
    }

    # Insert user into BigQuery using the pipeline_utils function
    print(f"Creating test user: {login_id}")
    try:
        # Use the insert_user function, specifying the USERS_TABLE
        inserted_user = insert_user(user_data, table_id=USERS_TABLE)

        print(f"User created successfully with ID: {user_id}")
        print(f"Login credentials: {login_id} / {password}")
        print(f"Registration timestamp: {inserted_user['registered_at']}")

        return user_id

    except Exception as e:
        print(f"Exception creating user: {e}")
        return None

if __name__ == "__main__":
    # Create a test admin user
    admin_id = create_test_user(
        login_id="admin",
        password="Admin@123",
        full_name="Admin User",
        email="admin@example.com",
        access_level="admin"
    )

    # Create a regular test user
    test_user_id = create_test_user(
        login_id="testuser",
        password="Test@123",
        full_name="Test User",
        email="test@example.com",
        access_level="standard"
    )
