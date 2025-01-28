import os
import base64
from openai import OpenAI
import logging
from typing import List
from dotenv import load_dotenv

def encode_image_to_base64(image_path: str) -> str:
    """
    Encode an image file to base64 string.

    Args:
        image_path (str): Path to the image file

    Returns:
        str: Base64 encoded string of the image
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logging.error(f"Error encoding image {image_path}: {str(e)}")
        return ""

def generate_headlines(image_folder: str, brand: str) -> List[str]:
    """
    Generate headlines for slides using OpenAI's Vision API.

    Args:
        image_folder (str): Path to the folder containing slide images
        brand (str): Brand name for the analysis

    Returns:
        List[str]: List of generated headlines for each slide
    """
    # Load environment variables and initialize OpenAI client
    load_dotenv()
    client = OpenAI(api_key=os.getenv('OPENAI_API'))

    headlines = []

    prompt = f'''
    Act as an expert market analyst writing a brand health study for {brand}.
    For this slide:
    1. Analyze key performance metrics and trends
    2. Identify significant competitor movements or market dynamics
    3. Provide strategic implications or recommendations for {brand}

    Synthesize these into a clear, insightful headline that captures the main story and its business impact.
    Focus on actionable insights and quantitative findings when present.
    Capitalize only brand names and proper nouns.
    '''

    try:
        # Get all image files from the folder and sort them naturally
        def get_slide_number(filename):
            # Extract number from filenames like 's1.jpeg', 's10.jpeg'
            return int(''.join(filter(str.isdigit, filename)))

        image_files = [f for f in os.listdir(image_folder)
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        image_files.sort(key=get_slide_number)

        for image_file in image_files:
            image_path = os.path.join(image_folder, image_file)
            base64_image = encode_image_to_base64(image_path)

            if not base64_image:
                logging.error(f"Failed to process image: {image_file}")
                headlines.append("Error: Failed to process slide")
                continue

            # Create message for OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o", # Keep this model as this is the updated model
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )

            headline = response.choices[0].message.content.strip()
            headlines.append(headline)
            logging.info(f"Generated headline for {image_file}: {headline}")

    except Exception as e:
        logging.error(f"Error generating headlines: {str(e)}")

    return headlines
