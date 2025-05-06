import os
import base64
from openai import OpenAI
import logging
from typing import List, Dict, Tuple, Any, Optional
from dotenv import load_dotenv
import time
from datetime import datetime
import concurrent.futures
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===== NEW API CLIENT FUNCTIONS =====

def get_openai_client():
    """Get configured OpenAI client instance"""
    # Try to load from .env file, but continue if it doesn't exist
    try:
        load_dotenv()
    except:
        pass

    openai_api_key = os.getenv('OPENAI_API')
    if not openai_api_key:
        raise ValueError("Missing OPENAI_API key in environment variables.")

    return OpenAI(api_key=openai_api_key)

def generate_completion(
    client: OpenAI,
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> Tuple[Optional[str], Optional[str]]:
    """Generate a chat completion from OpenAI"""
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages
        )
        return response.choices[0].message.content.strip(), None
    except Exception as e:
        logging.error(f"OpenAI API error: {str(e)}")
        return None, str(e)

def generate_image_completion(
    client: OpenAI,
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> Tuple[Optional[str], Optional[str]]:
    """Generate a completion that includes image analysis"""
    # This is the same as generate_completion for now, but may be enhanced in the future
    # for image-specific optimizations
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages
        )
        return response.choices[0].message.content.strip(), None
    except Exception as e:
        logging.error(f"OpenAI API error: {str(e)}")
        return None, str(e)

# ===== EXISTING FUNCTIONS, KEPT FOR BACKWARDS COMPATIBILITY =====

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
    system_prompt: str,
    model: str = "gpt-4o",
    temperature: float = 0.6,
    max_tokens: int = 4000,
    base64_image: str = None
) -> Tuple[int, Dict[str, Any], bool, str]:
    """
    Generate observations for a single slide.

    DEPRECATED: Use headline_service.generate_observation_for_slide instead.

    Args:
        slide_number (int): The slide number
        slide (Dict[str, Any]): The slide data
        client (OpenAI): The OpenAI client
        user_prompt (str): User prompt with market and brand information
        system_prompt (str): System prompt for observation generation
        model (str): The model to use for observation generation
        temperature (float): The temperature for observation generation
        max_tokens (int): The maximum number of tokens for observation generation
        base64_image (str, optional): Base64 encoded image of the slide. If None, tries to get from slide data.

    Returns:
        Tuple[int, Dict[str, Any], bool, str]: A tuple containing:
            - The slide number
            - The updated slide data
            - A boolean indicating success or failure
            - A status message
    """
    logging.warning("DEPRECATED: Use headline_service.generate_observation_for_slide instead.")

    # Skip non-content slides
    if not slide.get("content_slide"):
        slide["slide_observations"] = ""
        slide["slide_headline"] = "HEADER SLIDE"
        slide["status"] = "Skipped (Non-content slide)"
        return slide_number, slide, False, "Skipped (Header slide)"

    # Get image from parameter or from slide data
    if base64_image is None:
        base64_image = slide.get("image_base64", "")

    if not base64_image:
        slide["slide_observations"] = ""
        slide["slide_headline"] = "Error: Missing slide image"
        slide["status"] = "Error"
        return slide_number, slide, False, "Error (Missing image)"

    # Generate Observations via ChatCompletion
    try:
        obs_response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
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
    pdf_file_content: bytes = None,
    model: str = "gpt-4o",
    temperature: float = 0.6,
    max_tokens: int = 4000,
    parallel_slides: int = 5,
    batch_size: int = 10
) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Any]]:
    """
    Generate observations for all content slides in parallel, processing images in batches.

    DEPRECATED: Use headline_service.generate_observations_parallel instead.

    Args:
        slide_data (Dict[int, Dict[str, Any]]): Dictionary containing slide metadata
        client (OpenAI): The OpenAI client
        user_prompt (str): User prompt with market and brand information
        system_prompt (str): System prompt for observation generation
        pdf_file_content (bytes, optional): PDF file content as bytes for batch processing
        model (str): The model to use for observation generation
        temperature (float): The temperature for observation generation
        max_tokens (int): The maximum number of tokens for observation generation
        parallel_slides (int): Number of slides to process in parallel (default: 5)
        batch_size (int): Number of slides to convert to images at once (default: 10)

    Returns:
        Tuple[Dict[int, Dict[str, Any]], Dict[str, Any]]: A tuple containing:
            - The updated slide_data dictionary
            - Metrics about the observation generation process
    """
    logging.warning("DEPRECATED: Use headline_service.generate_observations_parallel instead.")

    # Initialize metrics
    metrics = {
        "content_slides_processed": 0,
        "observations_generated": 0,
        "errors": 0,
    }

    # Import the batch image generation function
    from insightgen.process_slides import generate_slide_images_batch

    print("\nGenerating Observations (Batch Processing):")
    print("="*50)

    # Get all content slides that need processing
    content_slides = [(slide_number, slide) for slide_number, slide in slide_data.items()
                    if slide.get("content_slide")]

    if not content_slides:
        logging.warning("No content slides found for processing")
        return slide_data, metrics

    # Process slides in batches to conserve memory
    content_slide_count = len(content_slides)
    print(f"Processing {content_slide_count} content slides in batches of {batch_size}...")

    batch_indices = list(range(0, content_slide_count, batch_size))
    for batch_idx in batch_indices:
        batch_end = min(batch_idx + batch_size, content_slide_count)
        current_batch = content_slides[batch_idx:batch_end]

        # Get slide numbers in this batch
        batch_slide_numbers = [slide_number for slide_number, _ in current_batch]
        min_slide_number = min(batch_slide_numbers)
        max_slide_number = max(batch_slide_numbers)

        print(f"\nProcessing batch {batch_idx//batch_size + 1}/{len(batch_indices)}: "
              f"Slides {min_slide_number}-{max_slide_number}")

        # Generate images for this batch only if pdf_file_content is provided
        batch_images = {}
        if pdf_file_content:
            try:
                # The PDF pages are 0-indexed but slide numbers are 1-indexed
                batch_images = generate_slide_images_batch(
                    pdf_file_content=pdf_file_content,
                    batch_start=min_slide_number,
                    batch_size=max_slide_number - min_slide_number + 1
                )
                print(f"Generated {len(batch_images)} images for this batch")
            except Exception as e:
                logging.error(f"Error generating batch images: {str(e)}")
                continue

        # Process this batch in parallel
        slides_to_process = [(num, slide) for num, slide in current_batch]
        total_in_batch = len(slides_to_process)

        with ThreadPoolExecutor(max_workers=parallel_slides) as executor:
            # Create a dictionary to store futures
            future_to_slide = {}

            for slide_number, slide in slides_to_process:
                # Get the image for this slide from batch_images if available,
                # or from slide_data if not using batch processing
                slide_image = batch_images.get(slide_number, slide.get("image_base64", ""))

                future = executor.submit(
                    generate_observation_for_slide,
                    slide_number,
                    slide,
                    client,
                    user_prompt,
                    system_prompt,
                    model,
                    temperature,
                    max_tokens,
                    slide_image  # Pass the image directly
                )
                future_to_slide[future] = slide_number

            # Process results as they complete
            for i, future in enumerate(as_completed(future_to_slide), 1):
                slide_number = future_to_slide[future]
                progress = (i / total_in_batch) * 100

                try:
                    _, slide, success, message = future.result()
                    slide_data[slide_number] = slide

                    if success:
                        metrics["observations_generated"] += 1
                        print(f"Slide {slide_number} [{progress:.1f}%] - {message}")
                    else:
                        metrics["errors"] += 1
                        print(f"Slide {slide_number} [{progress:.1f}%] - {message}")

                    metrics["content_slides_processed"] += 1

                except Exception as e:
                    metrics["errors"] += 1
                    print(f"Slide {slide_number} [{progress:.1f}%] - Error: {str(e)[:50]}...")
                    logging.error(f"Slide {slide_number}: Unexpected error: {str(e)}")

        # Clear batch images to free memory
        batch_images.clear()

    print("\nObservation generation completed.")
    return slide_data, metrics


def generate_headlines_sequential(
    slide_data: Dict[int, Dict[str, Any]],
    client: OpenAI,
    formatted_headline_instructions: str,
    model: str,
    temperature: float,
    max_tokens: int,
    context_window_size: int = 20
) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Any]]:
    """
    Generate headlines for all content slides sequentially, maintaining context between slides.

    DEPRECATED: Use headline_service.generate_headlines_sequential instead.

    Args:
        slide_data (Dict[int, Dict[str, Any]]): Dictionary containing slide metadata with observations
        client (OpenAI): The OpenAI client
        formatted_headline_instructions (str): Formatted system instructions for headline generation
        model (str): The model to use for headline generation
        temperature (float): The temperature for headline generation
        max_tokens (int): The maximum number of tokens for headline generation
        context_window_size (int): Number of previous headlines to maintain in context (default: 20)

    Returns:
        Tuple[Dict[int, Dict[str, Any]], Dict[str, Any]]: A tuple containing:
            - The updated slide_data dictionary
            - Metrics about the headline generation process
    """
    logging.warning("DEPRECATED: Use headline_service.generate_headlines_sequential instead.")

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
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
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
    pdf_file_content: bytes = None,
    generator_id: str = None,
    additional_system_instructions: str = "",
    context_window_size: int = 20,
    few_shot_examples: str = None,
    parallel_slides: int = None,
    batch_size: int = 10
) -> tuple[dict, dict]:
    """
    Main function that:
    1) Generates textual observations for each content slide using parallel processing
    2) Generates headlines sequentially while maintaining context of previous headlines

    DEPRECATED: Use insightgen.services.headline_service.generate_headlines instead.

    Args:
        slide_data (dict): Dictionary containing slide metadata
        user_prompt (str): User prompt with market and brand information
        pdf_file_content (bytes, optional): PDF file content as bytes for batch processing
        generator_id (str, optional): ID of the generator to use. If None, uses the default generator.
        additional_system_instructions (str): Additional instructions for headline generation
        context_window_size (int, optional): Number of previous headlines to maintain in context.
            Defaults to 20.
        few_shot_examples (str, optional): Optional examples of observation-headline pairs for few-shot learning.
            If None, uses the examples from the generator.
        parallel_slides (int, optional): Number of slides to process in parallel for observations.
            If None, uses the value from the generator's workflow.
        batch_size (int, optional): Number of slides to convert to images at once. Defaults to 10.

    Returns:
        tuple[dict, dict]: A tuple containing:
            - The updated slide_data dictionary
            - A metrics dictionary with performance statistics
    """
    logging.warning("DEPRECATED: Use insightgen.services.headline_service.generate_headlines instead.")

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

    # Try to load from .env file, but continue if it doesn't exist
    try:
        load_dotenv()
    except:
        pass  # Silently continue if .env file doesn't exist

    # Get API key and model configurations from environment variables
    openai_api_key = os.getenv('OPENAI_API')
    observations_model = os.getenv('OPENAI_OBSERVATIONS_MODEL', 'gpt-4o')
    headlines_model = os.getenv('OPENAI_HEADLINES_MODEL', 'gpt-4o')
    parallel_slides = int(os.getenv('PARALLEL_SLIDES', '5'))  # Get from environment variable

    if not openai_api_key:
        raise ValueError("Missing OPENAI_API key in environment variables.")

    # Initialize the OpenAI client
    client = OpenAI(api_key=openai_api_key)

    # Load the generator from the registry
    from insightgen.registry import GeneratorRegistry
    registry = GeneratorRegistry()

    # If no generator_id is provided, use the default
    if not generator_id:
        generator_id = registry.get_default_generator_id()

    # Get the generator
    generator = registry.get_generator(generator_id)
    if not generator:
        raise ValueError(f"Generator with ID '{generator_id}' not found")

    # Log which generator is being used
    logging.info(f"Using generator: {generator['name']} (ID: {generator_id}, Version: {generator['version']})")

    # Get generator configuration
    obs_config = generator["prompts"]["observations"]
    headline_config = generator["prompts"]["headlines"]

    # For observations, just use the system prompt directly
    formatted_obs_instructions = obs_config["system_prompt"]

    # Format the headline system prompt with knowledge base and examples
    headline_knowledge_base = headline_config.get("knowledge_base", "")
    headline_few_shot = headline_config.get("few_shot_examples", "")

    # Only include knowledge base and few-shot examples if they exist
    formatted_headline_instructions = headline_config["system_prompt"]
    if headline_knowledge_base:
        formatted_headline_instructions += f"\n\nKnowledge Base:\n{headline_knowledge_base}"
    if headline_few_shot:
        formatted_headline_instructions += f"\n\nFew-shot Examples:\n{headline_few_shot}"
    if additional_system_instructions:
        formatted_headline_instructions += f"\n\nAdditional Instructions:\n{additional_system_instructions}"

    # Step 1: Generate observations in parallel
    slide_data, obs_metrics = generate_observations_parallel(
        slide_data=slide_data,
        client=client,
        user_prompt=user_prompt,
        system_prompt=formatted_obs_instructions,
        pdf_file_content=pdf_file_content,
        model=observations_model,
        temperature=obs_config.get("temperature", 0.6),
        max_tokens=obs_config.get("max_tokens", 4000),
        parallel_slides=parallel_slides,
        batch_size=batch_size
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
        model=headlines_model,
        temperature=headline_config.get("temperature", 0.7),
        max_tokens=headline_config.get("max_tokens", 200),
        context_window_size=context_window_size
    )

    # Update metrics with headline generation results
    metrics.update({
        "headlines_generated": headline_metrics["headlines_generated"],
        "errors": metrics["errors"] + headline_metrics["errors"]
    })

    # Add generator info to metrics
    metrics.update({
        "generator_id": generator_id,
        "generator_name": generator["name"],
        "generator_version": generator["version"]
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
    logging.info(f"Generator: {metrics['generator_name']} (ID: {metrics['generator_id']}, Version: {metrics['generator_version']})")
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
