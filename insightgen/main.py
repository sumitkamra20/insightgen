import os
import logging
import shutil
from pathlib import Path
from pptx import Presentation
from insightgen.processing.process_slides import pdf_pptx_match, convert_pdf_to_images
from insightgen.api.openai_client import generate_headlines

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_slide_images(input_dir: str, output_dir: str, images_dir: str) -> bool:
    """
    Step 1: Convert PDF slides to images

    Args:
        input_dir (str): Directory containing input PDF and PPTX files
        output_dir (str): Base output directory
        images_dir (str): Directory to save generated images

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Find PDF and PPTX files
        pdf_files = [f for f in os.listdir(input_dir) if f.endswith('.pdf')]
        pptx_files = [f for f in os.listdir(input_dir) if f.endswith('.pptx')]

        if not pdf_files or not pptx_files:
            logging.error("Missing required files. Need both PDF and PPTX files in input directory.")
            return False

        if len(pdf_files) > 1 or len(pptx_files) > 1:
            logging.error("Multiple PDF or PPTX files found. Please keep only one of each.")
            return False

        pdf_path = os.path.join(input_dir, pdf_files[0])
        pptx_path = os.path.join(input_dir, pptx_files[0])

        # Load PPTX
        pptx = Presentation(pptx_path)

        # Check if slides match
        if not pdf_pptx_match(pdf_path, pptx):
            logging.error("Number of slides in PDF and PPTX do not match!")
            return False

        # Create fresh output directories
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(images_dir, exist_ok=True)

        # Convert PDF to images
        image_buffers = convert_pdf_to_images(pdf_path, output_folder=images_dir)

        if image_buffers:
            return True
        else:
            logging.error("Failed to convert PDF to images.")
            return False

    except Exception as e:
        logging.error(f"Error in create_slide_images: {str(e)}")
        return False

def generate_slide_headlines(images_dir: str, brand: str) -> bool:
    """
    Step 2: Generate headlines for slides using OpenAI

    Args:
        images_dir (str): Directory containing slide images
        brand (str): Brand name for analysis

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        headlines = generate_headlines(images_dir, brand)

        if headlines:
            logging.info(f"Successfully generated {len(headlines)} headlines!")
            for i, headline in enumerate(headlines, 1):
                print(f"Slide {i}: {headline}")
            return True
        else:
            logging.error("Failed to generate headlines.")
            return False

    except Exception as e:
        logging.error(f"Error in generate_slide_headlines: {str(e)}")
        return False

def main():
    # Define paths
    input_dir = "/Users/sumitkamra/code/sumitkamra20/insightgen/data/input"
    output_dir = os.path.join(os.path.dirname(input_dir), "output")
    images_dir = os.path.join(output_dir, "images")
    """
    # Step 1: Create slide images
    success = create_slide_images(input_dir, output_dir, images_dir)
    if not success:
        return

    """

    # Step 2: Generate headlines (commented out for now)

    brand = "Lifebuoy"
    success = generate_slide_headlines(images_dir, brand)
    if not success:
        return


if __name__ == "__main__":
    main()
