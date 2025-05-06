import os
import base64
from openai import OpenAI
import logging
from typing import List, Dict, Tuple, Any, Optional
from dotenv import load_dotenv
import time
from datetime import datetime

# ===== API CLIENT FUNCTIONS =====

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

# ===== UTILITY FUNCTIONS =====

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
