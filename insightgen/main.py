import os
import logging
from pathlib import Path
from insightgen.processing.process_slides import extract_slide_metadata, generate_slide_images_base64, insert_headlines_into_pptx
from insightgen.api.openai_client import generate_observations_and_headlines
from typing import Tuple, Dict, Union, Optional, BinaryIO

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_presentation(
    input_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    user_prompt: str = "",
    context_window_size: int = 20,
    few_shot_examples: Optional[str] = None,
    pptx_file_content: Optional[bytes] = None,
    pdf_file_content: Optional[bytes] = None,
    pptx_filename: Optional[str] = None
) -> Tuple[Union[str, Tuple[str, bytes]], Dict]:
    """
    Main function to process the presentation:
    1. Extract slide metadata
    2. Generate slide images and store in base64
    3. Generate observations and headlines using OpenAI
    4. Insert headlines and observations into the PPTX

    Args:
        input_dir (str, optional): Directory containing input PDF and PPTX files
        output_dir (str, optional): Directory to save the output files
        user_prompt (str): User prompt containing market and brand information
        context_window_size (int): Number of previous headlines to maintain in context (default: 20)
        few_shot_examples (str, optional): Examples of observation-headline pairs for few-shot learning
        pptx_file_content (bytes, optional): PPTX file content as bytes
        pdf_file_content (bytes, optional): PDF file content as bytes
        pptx_filename (str, optional): Name of the PPTX file when provided as bytes

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

        # Step 2: Generate slide images and store in base64
        slide_metadata = generate_slide_images_base64(
            input_folder=input_dir if using_files_on_disk else None,
            slide_data=slide_metadata,
            pdf_file_content=pdf_file_content if using_memory_files else None
        )

        # Step 3: Generate observations and headlines
        slide_metadata, metrics = generate_observations_and_headlines(
            slide_metadata,
            user_prompt,
            context_window_size=context_window_size,
            few_shot_examples=few_shot_examples
        )

        # Step 4: Insert headlines and observations into PPTX
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
    print(f"Processing Summary:")
    print(f"  • Total Slides: {metrics['total_slides']}")
    print(f"  • Content Slides Processed: {metrics['content_slides_processed']}")
    print(f"  • Observations Generated: {metrics['observations_generated']}")
    print(f"  • Headlines Generated: {metrics['headlines_generated']}")
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

    # Optional: Custom few-shot examples
    custom_examples = """
    Example 1:
    Observations: Brand Power trends show Heineken maintaining leadership at 120 index points, while Tiger experiences decline from 115 to 108. Competitor 333 shows steady growth from 95 to 102 index points over the same period.
    Headline: Heineken maintains category leadership despite competitive pressure, while Tiger's Brand Power decline creates opportunity for 333's continued growth momentum.

    Example 2:
    Observations: Meaningful scores reveal Tiger's emotional connection weakening among young urban consumers (25-35), dropping from 65% to 58% endorsement. Meanwhile, Saigon Beer gains ground in this segment, improving from 45% to 52%.
    Headline: Tiger's weakening emotional connection with young urban consumers creates vulnerability, as Saigon Beer successfully strengthens its appeal in this crucial segment.
    """

    try:
        # Process with default context window size (20) and custom examples
        modified_pptx, metrics = process_presentation(
            str(input_dir),
            str(output_dir),
            user_prompt,
            few_shot_examples=custom_examples
        )
        logging.info(f"Successfully processed presentation. Output saved to: {modified_pptx}")

        # Display the metrics in a nicely formatted way
        display_metrics(metrics)

    except Exception as e:
        logging.error(f"Failed to process presentation: {str(e)}")

if __name__ == "__main__":
    main()
