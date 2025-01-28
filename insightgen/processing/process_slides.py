# Below function should be included in this file
# pdf conversion to image files
# headline generation function that takes folder with image files as input
# and returns a list of headlines
#
# Final function that inputs the list of headline in pptx file and outputs the pptx file

# Imports
import os
from pdf2image import convert_from_path
import logging
from io import BytesIO

# Function to ascertain if pdf file and pptx have same number of slides
def pdf_pptx_match(pdf_path, pptx_path):
    pdf_slides = convert_pdf_to_images(pdf_path)
    pptx_slides = pptx_path.slides
    return len(pdf_slides) == len(pptx_slides)

def convert_pdf_to_images(pdf_path, output_folder=None, img_format="JPEG", dpi=200):
    """
    Convert PDF file to images and optionally save them in specified folder.

    Args:
        pdf_path (str): Path to the PDF file.
        output_folder (str, optional): Path to folder where images will be saved (None to skip saving to disk).
        img_format (str): Image format (default: JPEG).
        dpi (int): Resolution for the output images (default: 200, reduced for token optimization).

    Returns:
        list: List of image objects (Pillow Image instances).
    """
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=dpi)
        total_slides = len(images)

        # If output_folder is provided, save images to disk
        if output_folder:
            os.makedirs(output_folder, exist_ok=True)
            for i, image in enumerate(images, start=1):
                image_path = os.path.join(output_folder, f"s{i}.{img_format.lower()}")
                image.save(image_path, img_format)

        # Convert images to in-memory bytes (for cloud deployment)
        image_buffers = []
        for image in images:
            img_byte_arr = BytesIO()
            image.save(img_byte_arr, format=img_format)
            img_byte_arr.seek(0)  # Reset buffer position
            image_buffers.append(img_byte_arr)

        if output_folder:
            logging.info(f"Successfully converted PDF to {total_slides} images and saved to {output_folder}")

        return image_buffers

    except Exception as e:
        logging.error(f"Error converting PDF to images: {str(e)}")
        return []

# Function to generate headlines from image files and return a list of headlines
