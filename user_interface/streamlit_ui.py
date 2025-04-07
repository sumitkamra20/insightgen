import streamlit as st
import requests
import time
import os
from pathlib import Path
import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API URL configuration
# In local development: use localhost
# In production: use the Cloud Run URL
# Set DEPLOYMENT_ENV=production in your Streamlit Cloud environment variables
is_production = os.getenv("DEPLOYMENT_ENV") == "production"
API_URL = os.getenv("API_URL", "https://insightgen-api-195411721870.us-central1.run.app" if is_production else "http://localhost:8080")

# Log the API URL being used (helpful for debugging)
print(f"Using API URL: {API_URL}")

# Function to fetch available generators
def fetch_generators():
    try:
        response = requests.get(f"{API_URL}/generators/")
        if response.status_code == 200:
            # Extract the generators list from the response
            response_data = response.json()
            return response_data.get("generators", [])
        else:
            st.error(f"Failed to fetch generators: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error fetching generators: {str(e)}")
        return []

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

# Create a session state to track the inspection status
if 'inspection_done' not in st.session_state:
    st.session_state.inspection_done = False
if 'inspection_results' not in st.session_state:
    st.session_state.inspection_results = None
if 'selected_generator_id' not in st.session_state:
    st.session_state.selected_generator_id = ""
if 'current_prompt' not in st.session_state:
    st.session_state.current_prompt = ""
if 'generators_cache' not in st.session_state:
    st.session_state.generators_cache = []

# File upload section
with st.form("upload_form", clear_on_submit=False):
    col1, col2 = st.columns(2)

    with col1:
        pptx_file = st.file_uploader("Upload PPTX file", type=["pptx"])

    with col2:
        pdf_file = st.file_uploader("Upload PDF file", type=["pdf"])

    # Only show the inspect button if both files are uploaded
    inspect_button = st.form_submit_button("Submit")

# Function to update generator selection when changed
def update_generator_selection():
    generator_name = st.session_state.generator_selector
    generator_id = generator_options[generator_name]

    # Update the generator ID in session state
    st.session_state.selected_generator_id = generator_id

    # Update the prompt text for the selected generator
    if generator_id:
        # Use generators from cache if available
        generators_list = st.session_state.generators_cache

        # Find the selected generator in the list
        for generator in generators_list:
            if generator["id"] == generator_id:
                # Set the example prompt from the generator
                st.session_state.current_prompt = generator.get("example_prompt", "")
                break

if inspect_button and pptx_file and pdf_file:
    with st.spinner("Inspecting files..."):
        # Prepare files for inspection
        files = {
            "pptx_file": (pptx_file.name, pptx_file.getvalue(), "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
            "pdf_file": (pdf_file.name, pdf_file.getvalue(), "application/pdf"),
        }

        try:
            # Call the inspect-files endpoint
            response = requests.post(f"{API_URL}/inspect-files/", files=files)

            # Check for HTTP errors
            if response.status_code >= 400:
                error_detail = response.json().get("detail", "Unknown error")
                st.error(f"❌ Error during inspection: {error_detail}")
                st.stop()

            # Process successful response
            inspection_results = response.json()
            st.session_state.inspection_results = inspection_results
            st.session_state.inspection_done = True

        except requests.RequestException as e:
            st.error(f"Error connecting to API: {str(e)}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Display inspection results if available
if st.session_state.inspection_done and st.session_state.inspection_results:
    results = st.session_state.inspection_results

    # Display warnings
    if results["warnings"]:
        st.subheader("⚠️ Warnings")
        for warning in results["warnings"]:
            st.warning(warning)

    # Display slide statistics in a simpler format
    if "slide_stats" in results and results["slide_stats"]:
        stats = results["slide_stats"]

        st.subheader("📊 Inspection Results")

        # Total slides
        st.markdown(f"**Total Slides:** {stats['total_slides']}")

        # Header slides
        header_count = stats["header_slides"]["count"]
        if header_count > 0:
            st.markdown(f"✅ **Header Slides:** {header_count} slides (no headlines will be generated for these)")
            with st.expander("View header slide numbers"):
                st.write(f"Slide numbers: {', '.join(map(str, stats['header_slides']['slide_numbers']))}")
        else:
            st.markdown("⚠️ **Header Slides:** 0 slides (no header slides detected)")
            st.markdown("*Consider defining header slides in your presentation by using layouts with names starting with 'HEADER'*")

        # Content slides
        content_count = stats["content_slides"]["count"]
        st.markdown(f"📝 **Content Slides:** {content_count} slides (headlines will be generated for these)")

        # Missing placeholders
        missing_count = stats["missing_placeholders"]["count"]
        if missing_count == 0:
            st.markdown("✅ **Title Placeholders:** All content slides have title placeholders")
        else:
            st.markdown(f"❌ **Title Placeholders:** {missing_count} content slides are missing title placeholders")
            with st.expander("View slides missing title placeholders"):
                st.write(f"Slide numbers: {', '.join(map(str, stats['missing_placeholders']['slide_numbers']))}")
            st.markdown("*Headlines cannot be inserted into slides without title placeholders*")

# Processing form - only show if inspection is done and valid
if st.session_state.inspection_done and st.session_state.inspection_results and st.session_state.inspection_results["is_valid"]:
    st.subheader("Generate Insights")

    # Fetch available generators
    generators = fetch_generators()

    # Update generators cache
    if generators:
        st.session_state.generators_cache = generators

    # Create generator selection dropdown with "Select" as first option
    generator_options = {"Select a generator": ""} if generators else {"Brand Growth Study (Default)": "bgs_default"}
    if generators:
        generator_options.update({g["name"]: g["id"] for g in generators})

    generator_names = list(generator_options.keys())

    # Add generator selector OUTSIDE the form
    st.selectbox(
        "Select Generator",
        options=generator_names,
        index=0,
        help="Choose the type of analysis to perform",
        key="generator_selector",
        on_change=update_generator_selection
    )

    # Show the current selection status
    is_generator_selected = st.session_state.selected_generator_id != ""
    if not is_generator_selected:
        st.info("Please select a generator to enable submission.")

    # Now create the form without the generator selector
    with st.form("processing_form"):
        user_prompt = st.text_area(
            "Prompt: Market, Brand Context and Additional Instructions",
            st.session_state.current_prompt,  # Use the prompt from session state
            height=130,
        )

        context_window_size = st.slider(
            "Slide Memory",
            min_value=0,
            max_value=50,
            value=20,
            help="Number of previous slides to maintain in context"
        )

        # Use the session state to determine if the button should be disabled
        submit_button = st.form_submit_button("Submit", disabled=not is_generator_selected)

    if submit_button:
        with st.spinner("Uploading files and starting processing..."):
            # Prepare form data
            files = {
                "pptx_file": (pptx_file.name, pptx_file.getvalue(), "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
                "pdf_file": (pdf_file.name, pdf_file.getvalue(), "application/pdf"),
            }

            data = {
                "user_prompt": user_prompt,
                "context_window_size": str(context_window_size),
                "generator_id": st.session_state.selected_generator_id,  # Use the generator ID from session state
            }

            # Submit job
            try:
                response = requests.post(f"{API_URL}/upload-and-process/", files=files, data=data)

                # Check for HTTP errors (4xx, 5xx)
                if response.status_code >= 400:
                    error_detail = response.json().get("detail", "Unknown error")

                    # Handle specific validation errors
                    if "Slide count mismatch" in error_detail:
                        st.error(f"❌ {error_detail}")
                        st.warning("Please ensure both files have the same number of slides before proceeding.")
                    elif "Unsupported or corrupt" in error_detail:
                        st.error(f"❌ {error_detail}")
                        st.warning("Please check your files and try again with valid formats.")
                    elif "Invalid or corrupt" in error_detail:
                        st.error(f"❌ {error_detail}")
                        st.warning("Please check your files and try again with valid formats.")
                    else:
                        st.error(f"❌ Error: {error_detail}")

                    # Stop processing
                    st.stop()

                # Process successful response
                response_data = response.json()
                job_id = response_data["job_id"]

                # Display any warnings
                if "warnings" in response_data and response_data["warnings"]:
                    for warning in response_data["warnings"]:
                        if "Filename mismatch" in warning:
                            st.error(f"⚠️ {warning}")
                            st.warning("Processing will continue, but please consider using matching filenames in the future.")

                # Create progress bar and status text
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Set initial stage
                current_stage = "Slide processing"
                progress_bar.progress(5)
                status_text.info(f"Stage 1/4: {current_stage} - Preparing slides for analysis...")

                # Poll for job status
                completed = False
                start_time = time.time()
                last_status_update = time.time()

                # Track processing stage
                processing_stage = 1

                while not completed and time.time() - start_time < 3600:  # 1 hour timeout
                    status_response = requests.get(f"{API_URL}/job-status/{job_id}")

                    if status_response.status_code == 200:
                        job_status = status_response.json()
                        status = job_status["status"]

                        # Display any warnings from job status
                        if "warnings" in job_status and job_status["warnings"] and not completed:
                            for warning in job_status["warnings"]:
                                if "Filename mismatch" in warning and not completed:
                                    st.error(f"⚠️ {warning}")
                                    st.warning("Processing will continue, but please consider using matching filenames in the future.")

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
                            # Update progress based on elapsed time and estimated stage durations
                            elapsed = time.time() - start_time

                            # Update processing stage based on elapsed time
                            # These thresholds are estimates and should be adjusted based on actual processing times
                            if elapsed > 5 and processing_stage == 1:
                                # Move to stage 2 after 5 seconds
                                processing_stage = 2
                                current_stage = "Generating observations"
                                progress_value = 20
                                status_text.info(f"Stage 2/4: {current_stage} - Analyzing slide content...")
                                progress_bar.progress(progress_value)
                            elif elapsed > 30 and processing_stage == 2:
                                # Move to stage 3 after 30 seconds (adjust based on actual timing)
                                processing_stage = 3
                                current_stage = "Generating headlines"
                                progress_value = 80
                                status_text.info(f"Stage 3/4: {current_stage} - Creating impactful headlines...")
                                progress_bar.progress(progress_value)
                            elif elapsed > 45 and processing_stage == 3:
                                # Move to stage 4 after 45 seconds (adjust based on actual timing)
                                processing_stage = 4
                                current_stage = "Updating presentation"
                                progress_value = 95
                                status_text.info(f"Stage 4/4: {current_stage} - Inserting headlines into slides...")
                                progress_bar.progress(progress_value)
                            elif time.time() - last_status_update > 5:
                                # Update progress within the current stage
                                if processing_stage == 1:
                                    # Stage 1: 5% to 20%
                                    progress_value = min(5 + (elapsed / 5) * 15, 20)
                                elif processing_stage == 2:
                                    # Stage 2: 20% to 80%
                                    progress_value = min(20 + ((elapsed - 5) / 25) * 60, 80)
                                elif processing_stage == 3:
                                    # Stage 3: 80% to 95%
                                    progress_value = min(80 + ((elapsed - 30) / 15) * 15, 95)
                                else:
                                    # Stage 4: 95% to 99%
                                    progress_value = min(95 + ((elapsed - 45) / 15) * 4, 99)

                                progress_bar.progress(int(progress_value))
                                last_status_update = time.time()

                    time.sleep(1)  # Poll more frequently for smoother updates

                if not completed:
                    status_text.error("Processing timed out. Please check the job status manually.")

            except requests.RequestException as e:
                st.error(f"Error connecting to API: {str(e)}")
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
