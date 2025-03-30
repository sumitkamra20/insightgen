from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import logging
import json
from datetime import datetime

from insightgen.main import process_presentation
from insightgen.process_slides import validate_files, extract_slide_metadata

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
):
    """
    Upload PPTX and PDF files and process them to generate insights and headlines.

    Args:
        background_tasks: FastAPI BackgroundTasks
        pptx_file: The PPTX file to process
        pdf_file: The PDF file to process
        user_prompt: User prompt with market and brand information
        generator_id: ID of the generator to use (optional)
        context_window_size: Number of previous headlines to maintain in context (optional)
        few_shot_examples: Optional examples of observation-headline pairs for few-shot learning
    """
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
            generator_id,
            context_window_size,
            few_shot_examples
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
    few_shot_examples: Optional[str]
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
    """
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
            few_shot_examples=few_shot_examples
        )

        # Extract filename and content from result
        output_filename, output_content = result

        # Update job status
        jobs[job_id] = {
            "status": "completed",
            "message": "Processing completed successfully",
            "warnings": warnings,  # Preserve warnings
            "output_filename": output_filename,
            "output_content": output_content,  # Store binary content
            "metrics": metrics,
            "completed_at": datetime.now().isoformat()
        }

        logging.info(f"Job {job_id} completed successfully")

    except Exception as e:
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

@app.post("/inspect-files/")
async def inspect_files(
    pptx_file: UploadFile = File(...),
    pdf_file: UploadFile = File(...),
):
    """
    Inspect PPTX and PDF files before processing to provide detailed information about the files.
    """
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
