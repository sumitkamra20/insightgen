import jwt
import datetime
import os
import uuid
import bcrypt
from dotenv import load_dotenv, find_dotenv
from google.cloud import bigquery
from typing import Dict, Optional, Tuple

# Load environment variables
dotenv_path = find_dotenv()
load_dotenv(dotenv_path, override=True)

# Get environment variables
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "insightgen-453212")
USERS_TABLE = os.getenv("BQ_USER_TABLE", f"{PROJECT_ID}.insightgen_users.users")

# JWT settings
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-should-be-in-env-file")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 168  # 7 days (effectively non-expiring for dev)

# Initialize BigQuery client
bq = bigquery.Client(project=PROJECT_ID)

def generate_token(user_id: str, login_id: str, access_level: str, full_name: str = None, email: str = None) -> str:
    """
    Generate a JWT token for a user.

    Args:
        user_id: User ID from database
        login_id: User's login ID
        access_level: User's access level (admin, standard, etc.)
        full_name: User's full name (optional)
        email: User's email (optional)

    Returns:
        JWT token as string
    """
    payload = {
        "sub": user_id,  # subject (user id)
        "login_id": login_id,
        "access_level": access_level,
        "iat": datetime.datetime.utcnow(),  # issued at
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS),  # expiration
        "jti": str(uuid.uuid4())  # JWT ID (unique)
    }

    # Add optional user information to reduce database lookups
    if full_name:
        payload["full_name"] = full_name
    if email:
        payload["email"] = email

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def verify_token(token: str) -> Tuple[bool, Dict]:
    """
    Verify a JWT token and return the payload if valid.

    Args:
        token: JWT token to verify

    Returns:
        Tuple of (is_valid, payload)
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, {"error": "Token has expired"}
    except jwt.InvalidTokenError:
        return False, {"error": "Invalid token"}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def authenticate_user(login_id: str, password: str) -> Tuple[bool, Optional[Dict]]:
    """
    Authenticate a user with login_id and password.

    Args:
        login_id: User's login ID
        password: User's password

    Returns:
        Tuple of (is_authenticated, user_data)
    """
    # Query to find the user
    query = f"""
    SELECT user_id, login_id, hashed_password, full_name, email, access_level, access_granted
    FROM `{USERS_TABLE}`
    WHERE login_id = @login_id
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("login_id", "STRING", login_id)
        ]
    )

    # Execute query
    query_job = bq.query(query, job_config=job_config)
    results = list(query_job.result())

    # Check if user exists
    if not results:
        return False, {"error": "User not found"}

    user = dict(results[0])

    # Check if user has access
    if not user.get("access_granted", False):
        return False, {"error": "Access denied"}

    # Verify password
    if verify_password(password, user["hashed_password"]):
        # Remove sensitive data before returning
        user.pop("hashed_password", None)

        # Generate token
        token = generate_token(
            user_id=user["user_id"],
            login_id=user["login_id"],
            access_level=user["access_level"],
            full_name=user.get("full_name"),
            email=user.get("email")
        )

        user["token"] = token
        return True, user

    return False, {"error": "Invalid password"}

def get_user_from_token(token: str) -> Tuple[bool, Optional[Dict]]:
    """
    Get user information from a token.

    Args:
        token: JWT token

    Returns:
        Tuple of (is_valid, user_data)
    """
    is_valid, payload = verify_token(token)

    if not is_valid:
        return False, payload  # Contains error

    # Get user information directly from the token instead of querying BigQuery
    # This significantly improves performance for authenticated endpoints
    user = {
        "user_id": payload["sub"],
        "login_id": payload["login_id"],
        "full_name": payload.get("full_name", payload["login_id"]),  # Fallback to login_id if full_name not in token
        "email": payload.get("email", ""),  # Optional field
        "access_level": payload["access_level"],
        "access_granted": True,  # We assume this is true since we verified the token
        "token_expires": datetime.datetime.fromtimestamp(payload["exp"]).isoformat()
    }

    return True, user
