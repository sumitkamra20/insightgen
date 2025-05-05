import os
import logging
from pathlib import Path
from datetime import datetime
from insightgen.process_slides import extract_slide_metadata, insert_headlines_into_pptx
from insightgen.services import headline_service
from typing import Tuple, Dict, Union, Optional, BinaryIO, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_presentation(
    input_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    user_prompt: str = "",
    generator_id: Optional[str] = None,
    context_window_size: Optional[int] = None,
    few_shot_examples: Optional[str] = None,
    pptx_file_content: Optional[bytes] = None,
    pdf_file_content: Optional[bytes] = None,
    pptx_filename: Optional[str] = None,
    batch_size: int = 10,  # For batch processing
    operation_type: str = "generate_headlines",  # New parameter for operation type
    task_description: str = "",  # New parameter for task description
    refine_parameters: Optional[Dict] = None  # New parameter for refine options
) -> Tuple[Union[str, Tuple[str, bytes]], Dict]:
    """
    Main function to process the presentation:
    1. Extract slide metadata
    2. Generate observations and headlines using the service layer
    3. Insert headlines and observations into the PPTX

    Args:
        input_dir (str, optional): Directory containing input PDF and PPTX files
        output_dir (str, optional): Directory to save the output files
        user_prompt (str): User prompt containing market and brand information
        generator_id (str, optional): ID of the generator to use. If None, uses the default generator.
        context_window_size (int, optional): Number of previous headlines to maintain in context.
        few_shot_examples (str, optional): Examples of observation-headline pairs for few-shot learning.
        pptx_file_content (bytes, optional): PPTX file content as bytes
        pdf_file_content (bytes, optional): PDF file content as bytes
        pptx_filename (str, optional): Name of the PPTX file when provided as bytes
        batch_size (int, optional): Number of slides to convert to images at once. Defaults to 10.
        operation_type (str, optional): Type of operation to perform. Defaults to "generate_headlines".
        task_description (str, optional): Description of the task being performed.
        refine_parameters (Dict, optional): Parameters for refining headlines (when operation_type is "refine_headlines").

    Returns:
        Tuple[Union[str, Tuple[str, bytes]], Dict]: A tuple containing:
            - Either path to the modified PPTX file (str) or a tuple of (filename, bytes)
            - Performance metrics dictionary
    """
    try:
        # Determine if we're working with files on disk or in memory
        using_files_on_disk = input_dir is not None and output_dir is not None
        using_memory_files = pptx_file_content is not None and pdf_file_content is not None

        if not (using_files_on_disk or using_memory_files):
            raise ValueError("Either provide input_dir and output_dir for files on disk, or provide pptx_file_content and pdf_file_content for in-memory processing")

        # Step 1: Extract slide metadata
        slide_metadata = extract_slide_metadata(
            input_folder=input_dir if using_files_on_disk else None,
            pptx_file_content=pptx_file_content if using_memory_files else None,
            pptx_filename=pptx_filename if using_memory_files else None
        )

        # Set run-level information
        slide_metadata["run_info"]["task_description"] = task_description
        slide_metadata["run_info"]["generator_id"] = generator_id if generator_id else "default"

        # Store operation details directly in run_info (simplified structure)
        if operation_type == "generate_headlines":
            slide_metadata["run_info"]["operation_type"] = operation_type
            slide_metadata["run_info"]["context_window_size"] = context_window_size
            slide_metadata["run_info"]["batch_size"] = batch_size
            slide_metadata["run_info"]["has_few_shot_examples"] = few_shot_examples is not None
        elif operation_type == "refine_headlines":
            slide_metadata["run_info"]["operation_type"] = operation_type
            if refine_parameters:
                # Add individual refine parameters directly to run_info
                for key, value in refine_parameters.items():
                    slide_metadata["run_info"][f"refine_{key}"] = value

        # If using files on disk, read the PDF content for batch processing
        pdf_content_for_processing = pdf_file_content
        if using_files_on_disk and not pdf_content_for_processing:
            pdf_files = [f for f in os.listdir(input_dir) if f.endswith('.pdf')]
            if pdf_files:
                pdf_path = os.path.join(input_dir, pdf_files[0])
                with open(pdf_path, 'rb') as f:
                    pdf_content_for_processing = f.read()
                logging.info(f"Read PDF file from disk: {pdf_path}")

        # Step 2: Process based on operation type
        if operation_type == "generate_headlines":
            # Call the headline service to generate observations and headlines
            logging.info("Generating observations and headlines")
            slide_metadata, metrics = headline_service.generate_headlines(
                slide_metadata,
                user_prompt,
                pdf_file_content=pdf_content_for_processing,
                generator_id=generator_id,
                context_window_size=context_window_size,
                few_shot_examples=few_shot_examples,
                batch_size=batch_size
            )
        elif operation_type == "refine_headlines":
            # This will be implemented later
            logging.info("Refining headlines operation not yet implemented")
            metrics = {
                "total_slides": len([k for k in slide_metadata.keys() if k != "run_info"]),
                "content_slides_processed": 0,
                "headlines_refined": 0,
                "generator_id": generator_id if generator_id else "default",
                "start_time": datetime.now().isoformat(),
                "end_time": datetime.now().isoformat(),
                "total_time_seconds": 0,
                "average_time_per_content_slide": 0,
                "errors": 0,
                "operation_type": operation_type
            }
        else:
            raise ValueError(f"Unknown operation type: {operation_type}")

        # Step 3: Insert headlines and observations into PPTX
        result = insert_headlines_into_pptx(
            input_folder=input_dir if using_files_on_disk else None,
            output_folder=output_dir if using_files_on_disk else None,
            slide_data=slide_metadata,
            pptx_file_content=pptx_file_content if using_memory_files else None
        )

        return result, metrics

    except Exception as e:
        logging.error(f"Error in process_presentation: {str(e)}")
        raise

def display_metrics(metrics: Dict):
    """
    Display the performance metrics in a formatted way.
    """
    print("\n" + "="*50)
    print("PERFORMANCE METRICS")
    print("="*50)

    # Display generator information if available
    if "generator_name" in metrics:
        print(f"Generator Information:")
        print(f"  • Generator: {metrics['generator_name']}")
        print(f"  • Generator ID: {metrics['generator_id']}")
        print(f"  • Generator Version: {metrics['generator_version']}")
        print()

    print(f"Processing Summary:")
    print(f"  • Total Slides: {metrics['total_slides']}")
    print(f"  • Content Slides Processed: {metrics['content_slides_processed']}")

    if "operation_type" in metrics and metrics["operation_type"] == "refine_headlines":
        print(f"  • Headlines Refined: {metrics['headlines_refined']}")
    else:
        print(f"  • Observations Generated: {metrics.get('observations_generated', 0)}")
        print(f"  • Headlines Generated: {metrics.get('headlines_generated', 0)}")

    print(f"\nError Summary:")
    print(f"  • Errors Encountered: {metrics['errors']}")
    print(f"\nTiming Information:")
    print(f"  • Total Processing Time: {metrics['total_time_seconds']:.2f} seconds")
    print(f"  • Average Time per Slide: {metrics['average_time_per_content_slide']:.2f} seconds")
    print(f"  • Start Time: {metrics['start_time']}")
    print(f"  • End Time: {metrics['end_time']}")
    print("="*50 + "\n")

def main():
    # Define paths
    base_dir = Path(__file__).parent.parent
    input_dir = base_dir / "data" / "input"
    output_dir = base_dir / "data" / "output"

    # Ensure directories exist
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Example user prompt
    user_prompt = """
    Market: Vietnam,
    Client brands: Heineken, Tiger, Bia Viet, Larue, Bivina
    Competitors: 333, Saigon Beer, Hanoi Beer
    """

    # Example task description
    task_description = "Generate headlines for Heineken Vietnam market analysis"

    try:
        # Process with the default generator
        modified_pptx, metrics = process_presentation(
            str(input_dir),
            str(output_dir),
            user_prompt,
            generator_id="BGS_Default",
            task_description=task_description
        )
        logging.info(f"Successfully processed presentation. Output saved to: {modified_pptx}")

        # Display the metrics in a nicely formatted way
        display_metrics(metrics)

    except Exception as e:
        logging.error(f"Failed to process presentation: {str(e)}")

if __name__ == "__main__":
    main()
