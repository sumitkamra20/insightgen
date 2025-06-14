from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Cookie, Header
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
import logging
import json
from datetime import datetime
from pydantic import BaseModel
import bcrypt
from google.cloud import bigquery

from insightgen.main import process_presentation
from insightgen.process_slides import validate_files, extract_slide_metadata
from insightgen.auth import authenticate_user, get_user_from_token, verify_token, generate_token

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up BigQuery client and table references
bq = bigquery.Client()
USERS_TABLE = os.getenv("USERS_TABLE", "insightgen_users.users")

app = FastAPI(
    title="InsightGen API",
    description="API for generating insights and headlines for presentations",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Store job status
jobs = {}

# OAuth2 password bearer token scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Auth-related models
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class LoginRequest(BaseModel):
    username: str
    password: str

class RegistrationRequest(BaseModel):
    username: str
    password: str
    full_name: str
    email: str
    company: str = ""
    designation: str = ""
    access_level: str = "standard"  # Default to standard user

class UserResponse(BaseModel):
    user_id: str
    login_id: str
    full_name: str
    email: str
    access_level: str
    token_expires: Optional[str] = None

# Helper function to get current user
async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    cookie_token: Optional[str] = Cookie(None, alias="auth_token"),
    authorization: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """
    Get the current authenticated user from token.
    Tries to get token from:
    1. OAuth2 bearer token
    2. Cookie
    3. Authorization header
    """
    # Try different token sources
    final_token = token

    if not final_token and cookie_token:
        final_token = cookie_token

    if not final_token and authorization:
        scheme, _, param = authorization.partition(" ")
        if scheme.lower() == "bearer":
            final_token = param

    if not final_token:
        return None

    # Verify token and get user
    is_valid, user_data = get_user_from_token(final_token)

    if not is_valid:
        return None

    return user_data

# ---- Auth Routes ----

@app.post("/api/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate a user and return a JWT token.
    """
    is_authenticated, user_data = authenticate_user(form_data.username, form_data.password)

    if not is_authenticated:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": user_data["token"],
        "token_type": "bearer",
        "user": user_data
    }

@app.post("/api/auth/login", response_model=TokenResponse)
async def login_json(login_data: LoginRequest):
    """
    Authenticate a user with JSON payload and return a JWT token.
    """
    is_authenticated, user_data = authenticate_user(login_data.username, login_data.password)

    if not is_authenticated:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create response with cookie
    response = JSONResponse(content={
        "access_token": user_data["token"],
        "token_type": "bearer",
        "user": user_data
    })

    # Set cookie
    response.set_cookie(
        key="auth_token",
        value=user_data["token"],
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 3600  # 7 days
    )

    return response

@app.get("/api/auth/me", response_model=UserResponse)
async def get_my_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get information about the current authenticated user.
    """
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return current_user

@app.post("/api/auth/logout")
async def logout():
    """
    Logout the current user by clearing the auth cookie.
    """
    response = JSONResponse(content={"message": "Logged out successfully"})

    # Clear the auth cookie
    response.delete_cookie(key="auth_token")

    return response

@app.get("/api/auth/verify")
async def verify_auth(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """
    Verify if the current authentication is valid.
    """
    if not current_user:
        return JSONResponse(content={"authenticated": False})

    return JSONResponse(content={
        "authenticated": True,
        "user": {
            "user_id": current_user["user_id"],
            "login_id": current_user["login_id"],
            "full_name": current_user["full_name"],
            "access_level": current_user["access_level"]
        }
    })

@app.get("/")
async def root():
    return {"message": "Welcome to InsightGen API", "version": "0.1.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/upload-and-process/")
async def upload_and_process(
    background_tasks: BackgroundTasks,
    pptx_file: UploadFile = File(...),
    pdf_file: UploadFile = File(...),
    user_prompt: str = Form(...),
    generator_id: Optional[str] = Form(None),
    context_window_size: Optional[int] = Form(None),
    few_shot_examples: Optional[str] = Form(None),
    batch_size: Optional[int] = Form(10),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Upload PPTX and PDF files and process them to generate insights and headlines.
    Requires authentication.
    """
    # Check authentication
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Create unique job ID
    job_id = str(uuid.uuid4())

    try:
        # Read file contents
        try:
            pptx_content = await pptx_file.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid or corrupt PPTX file: {str(e)}")

        try:
            pdf_content = await pdf_file.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid or corrupt PDF file: {str(e)}")

        # Validate files using the function from process_slides.py
        warnings, is_valid, error_message = validate_files(
            pptx_content=pptx_content,
            pdf_content=pdf_content,
            pptx_filename=pptx_file.filename,
            pdf_filename=pdf_file.filename
        )

        # If validation failed, raise an exception
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)

        # Reset file pointers
        await pptx_file.seek(0)
        await pdf_file.seek(0)

        # Initialize job status
        jobs[job_id] = {
            "status": "processing",
            "message": "Files uploaded, processing started",
            "warnings": warnings,
            "output_file": None,
            "metrics": None,
            "created_at": datetime.now().isoformat(),
            "pptx_filename": pptx_file.filename,
            "pdf_filename": pdf_file.filename,
            "user_id": current_user["user_id"],  # Associate job with user
            "created_by": current_user["full_name"]
        }

        # Process in background
        background_tasks.add_task(
            process_job,
            job_id,
            pptx_content,
            pdf_content,
            pptx_file.filename,
            user_prompt,
            generator_id,
            context_window_size,
            few_shot_examples,
            batch_size
        )

        response_data = {
            "job_id": job_id,
            "status": "processing",
            "message": "Files uploaded, processing started"
        }

        if warnings:
            response_data["warnings"] = warnings

        return response_data

    except Exception as e:
        logging.error(f"Error in upload_and_process: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def process_job(
    job_id: str,
    pptx_content: bytes,
    pdf_content: bytes,
    pptx_filename: str,
    user_prompt: str,
    generator_id: Optional[str],
    context_window_size: Optional[int],
    few_shot_examples: Optional[str],
    batch_size: int = 10
):
    """
    Process the job in the background.

    Args:
        job_id: The unique job ID
        pptx_content: The PPTX file content
        pdf_content: The PDF file content
        pptx_filename: The name of the PPTX file
        user_prompt: User prompt with market and brand information
        generator_id: ID of the generator to use (optional)
        context_window_size: Number of previous headlines to maintain in context (optional)
        few_shot_examples: Optional examples of observation-headline pairs for few-shot learning
        batch_size: Number of slides to process in one batch (default: 10)
    """
    import time
    start_time = time.time()
    pdf_filename = jobs[job_id].get("pdf_filename", "")
    user_id = jobs[job_id].get("user_id", "")

    try:
        # Get existing warnings if any
        warnings = jobs[job_id].get("warnings", [])

        # Process presentation
        result, metrics = process_presentation(
            pptx_file_content=pptx_content,
            pdf_file_content=pdf_content,
            pptx_filename=pptx_filename,
            user_prompt=user_prompt,
            generator_id=generator_id,
            context_window_size=context_window_size,
            few_shot_examples=few_shot_examples,
            batch_size=batch_size
        )

        # Extract filename and content from result
        output_filename, output_content = result

        # Calculate processing duration
        duration_seconds = time.time() - start_time

        # Update job status
        jobs[job_id] = {
            "status": "completed",
            "message": "Processing completed successfully",
            "warnings": warnings,  # Preserve warnings
            "output_filename": output_filename,
            "output_content": output_content,  # Store binary content
            "metrics": metrics,
            "completed_at": datetime.now().isoformat(),
            "user_id": user_id  # Ensure user_id is preserved
        }

        logging.info(f"Job {job_id} completed successfully")

        # Prepare and log activity data
        from insightgen.pipeline_utils import log_user_activity

        # Extract number of slides processed from metrics
        batch_size_processed = metrics.get("content_slides_processed", batch_size)

        # Log successful job completion
        activity_data = {
            "user_id": user_id,
            "job_id": job_id,
            "service": "HeadlineAI",
            "status": "success",
            "error_message": "",
            "ts": datetime.now().isoformat(),
            "pptx_filename": pptx_filename,
            "pdf_filename": pdf_filename,
            "pptx_file_path": "",  # To be implemented in next build
            "pdf_file_path": "",   # To be implemented in next build
            "output_path": "",     # To be implemented in next build
            "output_type": "pptx",
            "download_url": "",    # Keeping blank until storage bucket is implemented
            "batch_size": batch_size_processed,
            "duration_seconds": duration_seconds,
            "slide_metadata": {
                "user_prompt": user_prompt,
                "generator_id": generator_id if generator_id else "default",
                "context_window_size": context_window_size,
                "few_shot_examples": "custom" if few_shot_examples else "default",
                "headline_count": metrics.get("headlines_generated", 0),
                "observation_count": metrics.get("observations_generated", 0),
                "total_slides": metrics.get("total_slides", 0)
            }
        }

        # Log to BigQuery
        log_result = log_user_activity(activity_data)
        if not log_result:
            logging.warning(f"Failed to log activity for job {job_id}")

    except Exception as e:
        # Calculate duration even for failed jobs
        duration_seconds = time.time() - start_time

        logging.error(f"Error processing job {job_id}: {str(e)}")
        # Get existing warnings if any
        warnings = jobs[job_id].get("warnings", [])

        jobs[job_id] = {
            "status": "failed",
            "message": f"Processing failed: {str(e)}",
            "warnings": warnings,  # Preserve warnings
            "output_filename": None,
            "output_content": None,
            "metrics": None,
            "completed_at": datetime.now().isoformat(),
            "user_id": user_id  # Ensure user_id is preserved
        }

        # Log failed job
        from insightgen.pipeline_utils import log_user_activity

        # Log error completion
        error_data = {
            "user_id": user_id,
            "job_id": job_id,
            "service": "HeadlineAI",
            "status": "error",
            "error_message": str(e),
            "ts": datetime.now().isoformat(),
            "pptx_filename": pptx_filename,
            "pdf_filename": pdf_filename,
            "pptx_file_path": "",
            "pdf_file_path": "",
            "output_path": "",
            "output_type": "",
            "download_url": "",
            "batch_size": batch_size,
            "duration_seconds": duration_seconds,
            "slide_metadata": {
                "user_prompt": user_prompt,
                "generator_id": generator_id if generator_id else "default"
            }
        }

        # Log to BigQuery
        log_result = log_user_activity(error_data)
        if not log_result:
            logging.warning(f"Failed to log error activity for job {job_id}")

@app.get("/job-status/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Get the status of a job.
    If user is authenticated, checks that the job belongs to the user.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id].copy()

    # If user is authenticated, check job ownership
    if current_user and "user_id" in job:
        if job["user_id"] != current_user["user_id"] and current_user["access_level"] != "admin":
            raise HTTPException(status_code=403, detail="You don't have permission to access this job")

    # Remove binary content from response
    if "output_content" in job:
        del job["output_content"]

    return job

@app.get("/download/{job_id}")
async def download_result(
    job_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Download the processed PPTX file.
    If user is authenticated, checks that the job belongs to the user.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    # If user is authenticated, check job ownership
    if current_user and "user_id" in job:
        if job["user_id"] != current_user["user_id"] and current_user["access_level"] != "admin":
            raise HTTPException(status_code=403, detail="You don't have permission to access this job")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    if not job.get("output_content"):
        raise HTTPException(status_code=404, detail="Output file not found")

    # Note: We're removing the download activity logging to ensure only one record per job
    # is created in the activity_log table (at job completion)

    return Response(
        content=job["output_content"],
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename={job['output_filename']}"}
    )

@app.delete("/job/{job_id}")
async def delete_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a job.
    Requires authentication and job ownership.
    """
    # Check authentication
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    # Check job ownership
    if "user_id" in job and job["user_id"] != current_user["user_id"] and current_user["access_level"] != "admin":
        raise HTTPException(status_code=403, detail="You don't have permission to delete this job")

    del jobs[job_id]
    return {"message": "Job deleted"}

@app.get("/jobs")
async def list_jobs(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all jobs.
    If user is authenticated, only returns jobs belonging to the user or all jobs for admin.
    """
    # Check authentication
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    result = []

    for job_id, job in jobs.items():
        # Filter by user_id if not admin
        if current_user["access_level"] != "admin" and job.get("user_id") != current_user["user_id"]:
            continue

        job_copy = job.copy()

        # Remove binary content
        if "output_content" in job_copy:
            del job_copy["output_content"]

        job_copy["job_id"] = job_id
        result.append(job_copy)

    return result

@app.post("/inspect-files/")
async def inspect_files(
    pptx_file: UploadFile = File(...),
    pdf_file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Inspect PPTX and PDF files before processing to provide detailed information about the files.
    Requires authentication.
    """
    # Check authentication
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        # Read file contents
        try:
            pptx_content = await pptx_file.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid or corrupt PPTX file: {str(e)}")

        try:
            pdf_content = await pdf_file.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid or corrupt PDF file: {str(e)}")

        # Validate files
        warnings, is_valid, error_message = validate_files(
            pptx_content=pptx_content,
            pdf_content=pdf_content,
            pptx_filename=pptx_file.filename,
            pdf_filename=pdf_file.filename
        )

        # Extract slide metadata
        slide_data = {}
        if is_valid:
            try:
                slide_data = extract_slide_metadata(
                    pptx_file_content=pptx_content,
                    pptx_filename=pptx_file.filename
                )
            except Exception as e:
                logging.error(f"Error extracting slide metadata: {str(e)}")
                warnings.append(f"Error analyzing slide structure: {str(e)}")

        # Analyze slide data
        inspection_results = {
            "is_valid": is_valid,
            "error_message": error_message,
            "warnings": warnings,
            "slide_stats": {}
        }

        if slide_data:
            # Count header slides
            header_slides = [slide_num for slide_num, data in slide_data.items()
                            if not data.get("content_slide", True)]
            header_slide_count = len(header_slides)

            # Count content slides
            content_slides = [slide_num for slide_num, data in slide_data.items()
                             if data.get("content_slide", True)]
            content_slide_count = len(content_slides)

            # Count slides missing title placeholders
            missing_placeholders = [slide_num for slide_num, data in slide_data.items()
                                   if data.get("content_slide", True) and not data.get("has_placeholder", False)]
            missing_placeholder_count = len(missing_placeholders)

            inspection_results["slide_stats"] = {
                "total_slides": len(slide_data),
                "header_slides": {
                    "count": header_slide_count,
                    "slide_numbers": header_slides
                },
                "content_slides": {
                    "count": content_slide_count,
                    "slide_numbers": content_slides
                },
                "missing_placeholders": {
                    "count": missing_placeholder_count,
                    "slide_numbers": missing_placeholders
                }
            }

            # Add warning if no header slides found
            if header_slide_count == 0:
                warnings.append("No header slides detected. Ensure header slides have layouts with names starting with 'HEADER'")
                inspection_results["warnings"] = warnings

        return inspection_results

    except Exception as e:
        logging.error(f"Error in inspect_files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/generators/")
async def list_generators():
    """
    List all available generators.

    Returns:
        List of available generators and the default generator ID
    """
    try:
        from insightgen.registry import GeneratorRegistry
        registry = GeneratorRegistry()
        generators = registry.list_generators()
        default_generator_id = registry.get_default_generator_id()
        return {"generators": generators, "default_generator_id": default_generator_id}
    except Exception as e:
        logging.error(f"Error listing generators: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing generators: {str(e)}")

@app.get("/generators/{generator_id}")
async def get_generator(generator_id: str):
    """
    Get a generator by ID.

    Returns:
        The generator details
    """
    try:
        from insightgen.registry import GeneratorRegistry
        registry = GeneratorRegistry()
        generator = registry.get_generator(generator_id)

        if not generator:
            raise HTTPException(status_code=404, detail=f"Generator with ID '{generator_id}' not found")

        return generator
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting generator {generator_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting generator: {str(e)}")

@app.post("/api/auth/register", response_model=UserResponse)
async def register_user(registration_data: RegistrationRequest):
    """
    Register a new user.
    Performs validation and writes to the users table in BigQuery.
    """
    from insightgen.pipeline_utils import insert_user
    import uuid
    import re

    # Basic validation
    validation_errors = []

    # Username validation (only alphanumeric and underscore, 3-20 chars)
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', registration_data.username):
        validation_errors.append("Username must be 3-20 characters and contain only letters, numbers, and underscores")

    # Password validation (at least 8 chars, 1 uppercase, 1 lowercase, 1 digit)
    if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$', registration_data.password):
        validation_errors.append("Password must be at least 8 characters and include uppercase, lowercase, and digits")

    # Email validation
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', registration_data.email):
        validation_errors.append("Please enter a valid email address")

    # Full name validation (not empty)
    if not registration_data.full_name or len(registration_data.full_name.strip()) < 2:
        validation_errors.append("Full name is required (minimum 2 characters)")

    # Return validation errors if any
    if validation_errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Validation failed", "errors": validation_errors}
        )

    # Check if username already exists
    query = f"""
    SELECT COUNT(*) as count
    FROM `{USERS_TABLE}`
    WHERE login_id = @login_id
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("login_id", "STRING", registration_data.username)
        ]
    )

    query_job = bq.query(query, job_config=job_config)
    results = list(query_job.result())

    if results[0]['count'] > 0:
        raise HTTPException(
            status_code=400,
            detail={"message": "Registration failed", "errors": ["Username already exists"]}
        )

    # Check if email already exists
    query = f"""
    SELECT COUNT(*) as count
    FROM `{USERS_TABLE}`
    WHERE email = @email
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("email", "STRING", registration_data.email)
        ]
    )

    query_job = bq.query(query, job_config=job_config)
    results = list(query_job.result())

    if results[0]['count'] > 0:
        raise HTTPException(
            status_code=400,
            detail={"message": "Registration failed", "errors": ["Email already exists"]}
        )

    try:
        # Generate user ID
        user_id = str(uuid.uuid4())

        # Hash the password
        password_bytes = registration_data.password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

        # Prepare user data for insertion
        user_data = {
            "user_id": user_id,
            "login_id": registration_data.username,
            "hashed_password": hashed_password,
            "full_name": registration_data.full_name,
            "email": registration_data.email,
            "company": registration_data.company,
            "designation": registration_data.designation,
            "access_granted": True,  # Default to granted for new registrations
            "access_level": registration_data.access_level,
            "extra_info": {"source": "self_registration"}
        }

        # Insert user into BigQuery
        inserted_user = insert_user(user_data, table_id=USERS_TABLE)

        # Generate token for immediate login
        token = generate_token(
            user_id=user_id,
            login_id=registration_data.username,
            access_level=registration_data.access_level,
            full_name=registration_data.full_name,
            email=registration_data.email
        )

        # Create the response
        response_data = {
            "user_id": user_id,
            "login_id": registration_data.username,
            "full_name": registration_data.full_name,
            "email": registration_data.email,
            "access_level": registration_data.access_level,
            "registered_at": inserted_user["registered_at"],
            "token": token
        }

        # Return the response
        return UserResponse(**response_data)

    except Exception as e:
        logging.error(f"Error registering user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"message": "Registration failed due to a server error", "errors": [str(e)]}
        )
