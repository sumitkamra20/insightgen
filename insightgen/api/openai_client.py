import os
import base64
from openai import OpenAI
import logging
from typing import List, Dict, Tuple, Any
from dotenv import load_dotenv
import time
from datetime import datetime
import concurrent.futures
from tqdm import tqdm

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


def generate_observation_for_slide(
    slide_number: int,
    slide: Dict[str, Any],
    client: OpenAI,
    user_prompt: str,
    system_prompt: str
) -> Tuple[int, Dict[str, Any], bool, str]:
    """
    Generate observations for a single slide.

    Args:
        slide_number (int): The slide number
        slide (Dict[str, Any]): The slide data
        client (OpenAI): The OpenAI client
        user_prompt (str): User prompt with market and brand information
        system_prompt (str): System prompt for observation generation

    Returns:
        Tuple[int, Dict[str, Any], bool, str]: A tuple containing:
            - The slide number
            - The updated slide data
            - A boolean indicating success or failure
            - A status message
    """
    # Skip non-content slides
    if not slide.get("content_slide"):
        slide["slide_observations"] = ""
        slide["slide_headline"] = "HEADER SLIDE"
        slide["status"] = "Skipped (Non-content slide)"
        return slide_number, slide, False, "Skipped (Header slide)"

    base64_image = slide.get("image_base64", "")
    if not base64_image:
        slide["slide_observations"] = ""
        slide["slide_headline"] = "Error: Missing slide image"
        slide["status"] = "Error"
        return slide_number, slide, False, "Error (Missing image)"

    # Generate Observations via ChatCompletion
    try:
        obs_response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.6,
            max_tokens=4000,
            messages=[
                {"role": "system", "content": system_prompt},
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
        slide["status"] = "Observations generated"
        return slide_number, slide, True, "Observations generated"
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Slide {slide_number}: Error generating observations: {error_msg}")
        slide["slide_observations"] = "Error in observations generation"
        slide["slide_headline"] = ""
        slide["status"] = "Error"
        return slide_number, slide, False, f"Error: {error_msg[:50]}..."


def generate_observations_parallel(
    slide_data: Dict[int, Dict[str, Any]],
    client: OpenAI,
    user_prompt: str,
    system_prompt: str,
    parallel_slides: int = 5
) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Any]]:
    """
    Generate observations for all content slides in parallel.

    Args:
        slide_data (Dict[int, Dict[str, Any]]): Dictionary containing slide metadata
        client (OpenAI): The OpenAI client
        user_prompt (str): User prompt with market and brand information
        system_prompt (str): System prompt for observation generation
        parallel_slides (int): Number of slides to process in parallel (default: 5)

    Returns:
        Tuple[Dict[int, Dict[str, Any]], Dict[str, Any]]: A tuple containing:
            - The updated slide_data dictionary
            - Metrics about the observation generation process
    """
    # Initialize metrics
    metrics = {
        "content_slides_processed": 0,
        "observations_generated": 0,
        "errors": 0,
    }

    print("\nGenerating Observations (Parallel Processing):")
    print("="*50)
    print(f"Processing up to {parallel_slides} slides in parallel...")

    # Prepare slides for parallel processing
    slides_to_process = []
    for slide_number, slide in slide_data.items():
        # Skip non-content slides immediately
        if not slide.get("content_slide"):
            print(f"Slide {slide_number} - Skipped (Header slide)")
            slide["slide_observations"] = ""
            slide["slide_headline"] = "HEADER SLIDE"
            slide["status"] = "Skipped (Non-content slide)"
            continue

        # Check for missing images
        if not slide.get("image_base64", ""):
            print(f"Slide {slide_number} - Error (Missing image)")
            logging.error(f"Slide {slide_number}: Missing base64 image.")
            slide["slide_observations"] = ""
            slide["slide_headline"] = "Error: Missing slide image"
            slide["status"] = "Error"
            metrics["errors"] += 1
            continue

        # Add to processing queue
        slides_to_process.append((slide_number, slide))

    # Process slides in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_slides) as executor:
        # Submit all tasks
        future_to_slide = {
            executor.submit(
                generate_observation_for_slide,
                slide_number,
                slide.copy(),  # Create a copy to avoid race conditions
                client,
                user_prompt,
                system_prompt
            ): slide_number
            for slide_number, slide in slides_to_process
        }

        # Process results as they complete
        for future in tqdm(concurrent.futures.as_completed(future_to_slide),
                          total=len(future_to_slide),
                          desc="Generating Observations"):
            slide_number = future_to_slide[future]
            try:
                slide_num, updated_slide, success, message = future.result()
                # Update the original slide_data with the results
                slide_data[slide_num].update(updated_slide)

                if success:
                    metrics["observations_generated"] += 1
                    metrics["content_slides_processed"] += 1
                    print(f"Slide {slide_num} - {message}")
                else:
                    if "Error" in message:
                        metrics["errors"] += 1
                        metrics["content_slides_processed"] += 1
                    print(f"Slide {slide_num} - {message}")

            except Exception as e:
                print(f"Slide {slide_number} - Error: {str(e)}")
                logging.error(f"Slide {slide_number}: Unexpected error: {str(e)}")
                slide_data[slide_number]["slide_observations"] = "Error in observations generation"
                slide_data[slide_number]["status"] = "Error"
                metrics["errors"] += 1

    return slide_data, metrics


def generate_headlines_sequential(
    slide_data: Dict[int, Dict[str, Any]],
    client: OpenAI,
    formatted_headline_instructions: str,
    context_window_size: int = 20
) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Any]]:
    """
    Generate headlines for all content slides sequentially, maintaining context between slides.

    Args:
        slide_data (Dict[int, Dict[str, Any]]): Dictionary containing slide metadata with observations
        client (OpenAI): The OpenAI client
        formatted_headline_instructions (str): Formatted system instructions for headline generation
        context_window_size (int): Number of previous headlines to maintain in context (default: 20)

    Returns:
        Tuple[Dict[int, Dict[str, Any]], Dict[str, Any]]: A tuple containing:
            - The updated slide_data dictionary
            - Metrics about the headline generation process
    """
    # Initialize metrics
    metrics = {
        "headlines_generated": 0,
        "errors": 0,
    }

    # Initialize context storage for headlines
    headline_context = []

    print("\nGenerating Headlines (Sequential Processing):")
    print("="*50)

    total_slides = len(slide_data)
    content_slides = sum(1 for slide in slide_data.values()
                         if slide.get("content_slide") and slide.get("slide_observations"))

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

    return slide_data, metrics


def generate_observations_and_headlines(
    slide_data: dict,
    user_prompt: str,
    additional_system_instructions: str = "",
    context_window_size: int = 20,
    few_shot_examples: str = None,
    parallel_slides: int = 5
) -> tuple[dict, dict]:
    """
    Main function that:
    1) Generates textual observations for each content slide using parallel processing
    2) Generates headlines sequentially while maintaining context of previous headlines

    Args:
        slide_data (dict): Dictionary containing slide metadata
        user_prompt (str): User prompt with market and brand information
        additional_system_instructions (str): Additional instructions for headline generation
        context_window_size (int): Number of previous headlines to maintain in context (default: 20)
        few_shot_examples (str): Optional examples of observation-headline pairs for few-shot learning
        parallel_slides (int): Number of slides to process in parallel for observations (default: 5)

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

    # Step 1: Generate observations in parallel
    slide_data, obs_metrics = generate_observations_parallel(
        slide_data=slide_data,
        client=client,
        user_prompt=user_prompt,
        system_prompt=OBSERVATIONS_SYSTEM_PROMPT,
        parallel_slides=parallel_slides
    )

    # Update metrics with observation generation results
    metrics.update({
        "content_slides_processed": obs_metrics["content_slides_processed"],
        "observations_generated": obs_metrics["observations_generated"],
        "errors": obs_metrics["errors"]
    })

    # Step 2: Generate headlines sequentially
    slide_data, headline_metrics = generate_headlines_sequential(
        slide_data=slide_data,
        client=client,
        formatted_headline_instructions=formatted_headline_instructions,
        context_window_size=context_window_size
    )

    # Update metrics with headline generation results
    metrics.update({
        "headlines_generated": headline_metrics["headlines_generated"],
        "errors": metrics["errors"] + headline_metrics["errors"]
    })

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
