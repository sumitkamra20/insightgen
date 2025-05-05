"""
Headline Service - Contains functions for generating observations and headlines.

This module handles the headline generation functionality of InsightGen.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_headlines(
    slide_metadata: Dict,
    user_prompt: str,
    pdf_file_content: Optional[bytes] = None,
    generator_id: Optional[str] = None,
    context_window_size: Optional[int] = None,
    few_shot_examples: Optional[str] = None,
    batch_size: int = 10
) -> Tuple[Dict, Dict]:
    """
    Generate observations and headlines for slides.

    Args:
        slide_metadata: Dictionary containing slide data
        user_prompt: User prompt with market and brand information
        pdf_file_content: PDF file content as bytes
        generator_id: ID of the generator to use
        context_window_size: Number of previous headlines to maintain in context
        few_shot_examples: Optional examples of observation-headline pairs
        batch_size: Number of slides to process in one batch

    Returns:
        Tuple of updated slide metadata and performance metrics
    """
    # Import here to avoid circular imports
    from insightgen.openai_client import generate_observations_and_headlines as original_generate_function

    # Initialize metrics
    metrics = {
        "start_time": datetime.now().isoformat(),
        "generator_id": generator_id if generator_id else "default"
    }

    # Call the original function to preserve functionality for now
    updated_slide_metadata, metrics = original_generate_function(
        slide_metadata,
        user_prompt,
        pdf_file_content=pdf_file_content,
        generator_id=generator_id,
        context_window_size=context_window_size,
        few_shot_examples=few_shot_examples,
        batch_size=batch_size
    )

    return updated_slide_metadata, metrics

# Compatibility function with the same signature as the original
def generate_observations_and_headlines(
    slide_metadata: Dict,
    user_prompt: str,
    pdf_file_content: Optional[bytes] = None,
    generator_id: Optional[str] = None,
    context_window_size: Optional[int] = None,
    few_shot_examples: Optional[str] = None,
    batch_size: int = 10
) -> Tuple[Dict, Dict]:
    """Compatibility wrapper that maintains the old function signature."""
    return generate_headlines(
        slide_metadata,
        user_prompt,
        pdf_file_content=pdf_file_content,
        generator_id=generator_id,
        context_window_size=context_window_size,
        few_shot_examples=few_shot_examples,
        batch_size=batch_size
    )
