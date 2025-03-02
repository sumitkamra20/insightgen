import streamlit as st
import requests
import time
import os
from pathlib import Path
import tempfile
from dotenv import load_dotenv
from insightgen.processing.params import DEFAULT_FEW_SHOT_EXAMPLES

# Load environment variables
load_dotenv()

# API URL (change if needed)
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="InsightGen",
    page_icon="📊",
    layout="wide",
)

st.title("InsightGen: AI-Powered Insights")
st.markdown("""
Generate insightful headlines for your market research presentations.
Currently supporting BGS studies only.
Upload your PPTX and PDF files, provide some context, and let AI do the rest!
""")

with st.form("upload_form"):
    col1, col2 = st.columns(2)

    with col1:
        pptx_file = st.file_uploader("Upload PPTX file", type=["pptx"])

    with col2:
        pdf_file = st.file_uploader("Upload PDF file", type=["pdf"])

    user_prompt = st.text_area(
        "Prompt: Market, Brand Context and Additional Instructions",
        """Market: Vietnam;
Client brands: Heineken, Tiger, Bia Viet, Larue, Bivina;
Competitors: 333, Saigon Beer, Hanoi Beer;
Additional instructions: """,
        height=130,
    )

    context_window_size = st.slider(
        "Slide Memory",
        min_value=0,
        max_value=50,
        value=20,
        help="Number of previous slides to maintain in context"
    )

    few_shot_examples = st.text_area(
        "Custom Examples - Edit or add more examples (Optional)",
        f'{DEFAULT_FEW_SHOT_EXAMPLES}',
        height=150,
        help="Provide custom examples to guide the headline generation"
    )

    submit_button = st.form_submit_button("Generate Insights")

if submit_button:
    if not pptx_file or not pdf_file:
        st.error("Please upload both PPTX and PDF files.")
    else:
        with st.spinner("Uploading files and starting processing..."):
            # Prepare form data
            files = {
                "pptx_file": (pptx_file.name, pptx_file.getvalue(), "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
                "pdf_file": (pdf_file.name, pdf_file.getvalue(), "application/pdf"),
            }

            data = {
                "user_prompt": user_prompt,
                "context_window_size": str(context_window_size),
            }

            if few_shot_examples:
                data["few_shot_examples"] = few_shot_examples

            # Submit job
            try:
                response = requests.post(f"{API_URL}/upload-and-process/", files=files, data=data)
                response.raise_for_status()
                job_id = response.json()["job_id"]

                # Create progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Poll for job status
                completed = False
                start_time = time.time()

                while not completed and time.time() - start_time < 3600:  # 1 hour timeout
                    status_response = requests.get(f"{API_URL}/job-status/{job_id}")

                    if status_response.status_code == 200:
                        job_status = status_response.json()
                        status = job_status["status"]

                        if status == "completed":
                            progress_bar.progress(100)
                            status_text.success("Processing completed successfully!")

                            # Display metrics
                            if "metrics" in job_status and job_status["metrics"]:
                                metrics = job_status["metrics"]

                                st.subheader("Performance Metrics")
                                col1, col2 = st.columns(2)

                                with col1:
                                    st.metric("Total Slides", metrics.get("total_slides", 0))
                                    st.metric("Content Slides Processed", metrics.get("content_slides_processed", 0))
                                    st.metric("Observations Generated", metrics.get("observations_generated", 0))
                                    st.metric("Headlines Generated", metrics.get("headlines_generated", 0))

                                with col2:
                                    st.metric("Errors", metrics.get("errors", 0))
                                    st.metric("Total Processing Time (s)", round(metrics.get("total_time_seconds", 0), 2))
                                    st.metric("Avg. Time per Slide (s)", round(metrics.get("average_time_per_content_slide", 0), 2))

                            # Download button
                            st.download_button(
                                "Download Processed Presentation",
                                requests.get(f"{API_URL}/download/{job_id}").content,
                                file_name=job_status.get("output_filename", f"processed_{pptx_file.name}"),
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                            )

                            completed = True

                        elif status == "failed":
                            progress_bar.progress(100)
                            status_text.error(f"Processing failed: {job_status.get('message', 'Unknown error')}")
                            completed = True

                        else:  # processing
                            # Simulate progress based on time
                            elapsed = time.time() - start_time
                            # Assume processing takes about 10 minutes max
                            progress = min(95, int(elapsed / 600 * 100))
                            progress_bar.progress(progress)
                            status_text.info(f"Processing in progress... ({progress}%)")

                    time.sleep(5)  # Poll every 5 seconds

                if not completed:
                    status_text.error("Processing timed out. Please check the job status manually.")

            except Exception as e:
                st.error(f"Error: {str(e)}")


# Add sidebar with additional information
with st.sidebar:
    st.header("About InsightGen")
    st.markdown("""
    InsightGen uses vision and launguage AI to analyze market research reports
    and generate insightful headlines and observations.\n
    #### Version: 0.1.0
    #### Developed by: Sumit Kamra
    """)
    st.header("Instructions")
    st.markdown("""
    - Currently only supports BGS studies
    - Ensure PPTX has not hidden slides PDF is identical to PPTX
    - Ensure header slides layout start with "HEADER"
    - Ensure client brands, competitors, market, etc. are mentioned in the prompt
    - Add any additional user instructions can be added in the prompt
    """)

    # Add API status check
    st.subheader("API Status")
    try:
        api_response = requests.get(f"{API_URL}/")
        if api_response.status_code == 200:
            st.success(f"API is online (v{api_response.json().get('version', 'unknown')})")
        else:
            st.error("API is not responding correctly")
    except:
        st.error("Cannot connect to API")
