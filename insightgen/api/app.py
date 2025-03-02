from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, List
import logging
import json
from datetime import datetime

from insightgen.main import process_presentation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

@app.get("/")
async def root():
    return {"message": "Welcome to InsightGen API", "version": "0.1.0"}

@app.post("/upload-and-process/")
async def upload_and_process(
    background_tasks: BackgroundTasks,
    pptx_file: UploadFile = File(...),
    pdf_file: UploadFile = File(...),
    user_prompt: str = Form(...),
    context_window_size: int = Form(20),
    few_shot_examples: Optional[str] = Form(None),
):
    """
    Upload PPTX and PDF files and process them to generate insights and headlines.
    """
    # Create unique job ID
    job_id = str(uuid.uuid4())

    try:
        # Read file contents
        pptx_content = await pptx_file.read()
        pdf_content = await pdf_file.read()

        # Initialize job status
        jobs[job_id] = {
            "status": "processing",
            "message": "Files uploaded, processing started",
            "output_file": None,
            "metrics": None,
            "created_at": datetime.now().isoformat(),
            "pptx_filename": pptx_file.filename,
            "pdf_filename": pdf_file.filename
        }

        # Process in background
        background_tasks.add_task(
            process_job,
            job_id,
            pptx_content,
            pdf_content,
            pptx_file.filename,
            user_prompt,
            context_window_size,
            few_shot_examples
        )

        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Files uploaded, processing started"
        }

    except Exception as e:
        logging.error(f"Error in upload_and_process: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def process_job(
    job_id: str,
    pptx_content: bytes,
    pdf_content: bytes,
    pptx_filename: str,
    user_prompt: str,
    context_window_size: int,
    few_shot_examples: Optional[str]
):
    """
    Process the job in the background.
    """
    try:
        # Process presentation
        result, metrics = process_presentation(
            pptx_file_content=pptx_content,
            pdf_file_content=pdf_content,
            pptx_filename=pptx_filename,
            user_prompt=user_prompt,
            context_window_size=context_window_size,
            few_shot_examples=few_shot_examples
        )

        # Extract filename and content from result
        output_filename, output_content = result

        # Update job status
        jobs[job_id] = {
            "status": "completed",
            "message": "Processing completed successfully",
            "output_filename": output_filename,
            "output_content": output_content,  # Store binary content
            "metrics": metrics,
            "completed_at": datetime.now().isoformat()
        }

        logging.info(f"Job {job_id} completed successfully")

    except Exception as e:
        logging.error(f"Error processing job {job_id}: {str(e)}")
        jobs[job_id] = {
            "status": "failed",
            "message": f"Processing failed: {str(e)}",
            "output_filename": None,
            "output_content": None,
            "metrics": None,
            "completed_at": datetime.now().isoformat()
        }

@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of a job.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id].copy()

    # Remove binary content from response
    if "output_content" in job:
        del job["output_content"]

    return job

@app.get("/download/{job_id}")
async def download_result(job_id: str):
    """
    Download the processed PPTX file.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    if not job.get("output_content"):
        raise HTTPException(status_code=404, detail="Output file not found")

    return Response(
        content=job["output_content"],
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename={job['output_filename']}"}
    )

@app.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a job and its associated files.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    # Remove job from jobs dictionary
    del jobs[job_id]

    return {"message": "Job deleted successfully"}

@app.get("/jobs")
async def list_jobs():
    """
    List all jobs with their status.
    """
    job_list = []
    for job_id, job_data in jobs.items():
        job_info = {
            "job_id": job_id,
            "status": job_data["status"],
            "message": job_data["message"],
            "created_at": job_data.get("created_at"),
            "completed_at": job_data.get("completed_at")
        }
        job_list.append(job_info)

    return {"jobs": job_list}
