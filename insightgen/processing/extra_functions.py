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
    Keep it limited to 25 words or less and use plain text.
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


# Function to ascertain if pdf file and pptx have same number of slides
def pdf_pptx_match(pdf_path, pptx_path):
    pdf_slides = convert_pdf_to_images(pdf_path)
    pptx_slides = pptx_path.slides
    return len(pdf_slides) == len(pptx_slides)
