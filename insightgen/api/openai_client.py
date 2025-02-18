import os
import base64
from openai import OpenAI
import logging
from typing import List, Dict
from dotenv import load_dotenv
import time
from datetime import datetime

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


def generate_observations_and_headlines(
    slide_data: dict,
    user_prompt: str,
    additional_system_instructions: str = "",
    context_window_size: int = 20,
    few_shot_examples: str = None
) -> tuple[dict, dict]:
    """
    1) Generates textual observations for each content slides using a ChatCompletion call with OBSERVATIONS_SYSTEM_PROMPT.
    2) Generates headlines using ChatCompletion while maintaining context of previous headlines.

    Args:
        slide_data (dict): Dictionary containing slide metadata
        user_prompt (str): User prompt with market and brand information
        additional_system_instructions (str): Additional instructions for headline generation
        context_window_size (int): Number of previous headlines to maintain in context (default: 20)
        few_shot_examples (str): Optional examples of observation-headline pairs for few-shot learning

    Returns:
        tuple[dict, dict]: A tuple containing:
            - The updated slide_data dictionary
            - A metrics dictionary with performance statistics
    """
    # Initialize metrics
    start_time = time.time()
    total_slides = len(slide_data)
    content_slides = sum(1 for slide in slide_data.values() if slide.get("content_slide", False))

    metrics = {
        "total_slides": total_slides,
        "content_slides": content_slides,
        "content_slides_processed": 0,
        "observations_generated": 0,
        "headlines_generated": 0,
        "errors": 0,
        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    load_dotenv()
    openai_api_key = os.getenv('OPENAI_API')
    if not openai_api_key:
        raise ValueError("Missing OPENAI_API key in environment variables.")

    # Initialize the OpenAI client
    client = OpenAI(api_key=openai_api_key)

    # Get system prompts from params
    from insightgen.processing.params import OBSERVATIONS_SYSTEM_PROMPT, HEADLINE_SYSTEM_INSTRUCTIONS, DEFAULT_FEW_SHOT_EXAMPLES

    # Use provided examples or default ones
    few_shot_examples = few_shot_examples or DEFAULT_FEW_SHOT_EXAMPLES

    # Format the headline system instructions with examples and additional instructions
    formatted_headline_instructions = HEADLINE_SYSTEM_INSTRUCTIONS.format(
        few_shot_examples=few_shot_examples,
        additional_system_instructions=additional_system_instructions
    )

    # Initialize context storage for headlines
    headline_context = []

    # First pass: Generate observations for all content slides
    print("\nGenerating Observations:")
    print("="*50)

    for slide_number, slide in slide_data.items():
        progress = (slide_number / total_slides) * 100
        print(f"\rProcessing Slide {slide_number} of {total_slides} [{progress:.1f}%]", end="")

        # Process only content slides
        if not slide.get("content_slide"):
            print(f" - Skipped (Header slide)")
            slide["slide_observations"] = ""
            slide["slide_headline"] = "HEADER SLIDE"
            slide["status"] = "Skipped (Non-content slide)"
            continue

        metrics["content_slides_processed"] += 1

        base64_image = slide.get("image_base64", "")
        if not base64_image:
            print(f" - Error (Missing image)")
            logging.error(f"Slide {slide_number}: Missing base64 image.")
            slide["slide_observations"] = ""
            slide["slide_headline"] = "Error: Missing slide image"
            slide["status"] = "Error"
            metrics["errors"] += 1
            continue

        # Generate Observations via ChatCompletion
        try:
            obs_response = client.chat.completions.create(
                model="gpt-4o",
                temperature=0.6,
                max_tokens=4000,
                messages=[
                    {"role": "system", "content": OBSERVATIONS_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"(Slide {slide_number}) {user_prompt}"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ]
            )
            observations_text = obs_response.choices[0].message.content.strip()
            slide["slide_observations"] = observations_text
            metrics["observations_generated"] += 1
            print(f" - Observations generated")
        except Exception as e:
            print(f" - Error (Failed to generate observations)")
            logging.error(f"Slide {slide_number}: Error generating observations: {str(e)}")
            slide["slide_observations"] = "Error in observations generation"
            slide["slide_headline"] = ""
            slide["status"] = "Error"
            metrics["errors"] += 1
            continue

    # Second pass: Generate headlines with context
    print("\n\nGenerating Headlines:")
    print("="*50)

    current_headline = 0
    for slide_number, slide in slide_data.items():
        if not slide.get("content_slide") or not slide.get("slide_observations"):
            continue

        current_headline += 1
        progress = (current_headline / content_slides) * 100
        print(f"\rProcessing Slide {slide_number} of {total_slides} [{progress:.1f}%]", end="")

        try:
            # Prepare context from previous headlines
            context_text = ""
            if headline_context:
                context_text = "Previous headlines for context:\n"
                for prev_num, prev_headline in headline_context[-context_window_size:]:
                    context_text += f"Slide {prev_num}: {prev_headline}\n"
                context_text += "\n"

            # Generate headline with context
            headline_response = client.chat.completions.create(
                model="gpt-4o",
                temperature=0.7,
                max_tokens=200,  # Headlines are short
                messages=[
                    {"role": "system", "content": formatted_headline_instructions},
                    {"role": "user", "content": f"""
                    {context_text}For Slide {slide_number}, generate a headline based on these observations:
                    {slide['slide_observations']}

                    You can reference insights from previous slides when relevant, as you have their headlines in the context above.
                    Keep the headline concise and impactful."""}
                ]
            )

            headline = headline_response.choices[0].message.content.strip()
            headline = headline.replace("Assistant:", "").strip()

            slide["slide_headline"] = headline
            slide["status"] = "Headline generated"
            metrics["headlines_generated"] += 1
            print(f" - Headline generated")

            # Add to context for next iterations
            headline_context.append((slide_number, headline))

        except Exception as e:
            print(f" - Error (Failed to generate headline)")
            logging.error(f"Slide {slide_number}: Error generating headline: {str(e)}")
            slide["slide_headline"] = "Error in headline generation"
            slide["status"] = "Error"
            metrics["errors"] += 1

    print("\n")  # Clear the progress line

    # Calculate final metrics
    end_time = time.time()
    total_time = end_time - start_time
    metrics.update({
        "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_time_seconds": total_time,
        "average_time_per_content_slide": total_time / metrics["content_slides_processed"] if metrics["content_slides_processed"] > 0 else 0
    })

    # Log metrics
    logging.info("\nPerformance Metrics:")
    logging.info(f"Total Slides: {metrics['total_slides']}")
    logging.info(f"Content Slides Processed: {metrics['content_slides_processed']}")
    logging.info(f"Observations Generated: {metrics['observations_generated']}")
    logging.info(f"Headlines Generated: {metrics['headlines_generated']}")
    logging.info(f"Errors Encountered: {metrics['errors']}")
    logging.info(f"Total Time: {metrics['total_time_seconds']:.2f} seconds")
    logging.info(f"Average Time per Content Slide: {metrics['average_time_per_content_slide']:.2f} seconds")
    logging.info(f"Start Time: {metrics['start_time']}")
    logging.info(f"End Time: {metrics['end_time']}")

    return slide_data, metrics
