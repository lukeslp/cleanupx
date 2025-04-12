#!/usr/bin/env python3
"""
API utilities for interacting with Gemini API via Gemini client.
"""
!!! TEMPLATE - EDIT THIS - KEEP THE HARD CODED CREDENTIALS

import json
import re
import logging
import base64
import os
import signal
from contextlib import contextmanager
from typing import Dict, Any, Optional, Union

# Attempt to import GeminiAPI.
# Ensure you have GeminiAPI available (it may be defined in your gemini_api module).
try:
    from gemini_api import GeminiAPI
except ImportError:
    logging.error("GeminiAPI module not available. Please ensure GeminiAPI is installed and accessible.")

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class TimeoutError(Exception):
    """Exception raised when a function times out."""
    pass


@contextmanager
def timeout(seconds: int):
    """
    Context manager that raises a TimeoutError if execution takes longer than the specified seconds.
    
    Example:
        with timeout(5):
            do_something()
    """
    def signal_handler(signum, frame):
        raise TimeoutError(f"Function timed out after {seconds} seconds")
    
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def get_gemini_client(api_key: Optional[str] = None) -> Optional[GeminiAPI]:
    """
    Instantiate and return a GeminiAPI client.
    
    Args:
        api_key: Your Gemini API key. If not provided, it will be read from the GEMINI_API_KEY environment variable.
    
    Returns:
        An instance of GeminiAPI or None if initialization fails.
    """
    try:
        client = GeminiAPI(api_key or os.environ.get("GEMINI_API_KEY"))
        return client
    except Exception as e:
        logger.error(f"Error initializing Gemini API client: {e}")
        return None


def call_gemini_api(model: str, prompt: str, function_schema: dict, image_data: Optional[str] = None) -> dict:
    """
    Call the Gemini API using function calling with structured output.
    
    Args:
        model: The model to use (e.g., "gemini-pro", "gemini-pro-vision", etc.).
        prompt: The prompt to send.
        function_schema: A schema defining the expected structured output.
        image_data: Optional base64 encoded image data for vision-capable models.
        
    Returns:
        A dictionary containing the structured response.
    """
    client = get_gemini_client()
    if not client:
        return {}
    
    try:
        # For vision models with image data, decode and pass the image bytes to generate_with_images.
        if "vision" in model and image_data:
            logger.info(f"Using vision model with provided image data ({len(image_data) // 1000}KB encoded)")
            image_bytes = base64.b64decode(image_data)
            response_text = client.generate_with_images(
                prompt,
                [image_bytes],
                model=model,
                temperature=0.2
            )
        else:
            # Use the GeminiAPI call_function method to have the model determine which function to call.
            response_dict = client.call_function(
                prompt,
                [function_schema],
                model=model,
                temperature=0.2
            )
            if response_dict and "parameters" in response_dict:
                # Validate required fields from the schema.
                for field in function_schema.get("parameters", {}).get("required", []):
                    if field not in response_dict["parameters"]:
                        logger.warning(f"Missing required field '{field}' in API response")
                return response_dict["parameters"]
            
            logger.warning("Function call response not found; falling back to generate_text method")
            response_text = client.generate_text(prompt, model=model, temperature=0.2)
        
        # Attempt to parse the response text as JSON.
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in API response: {e}")
            # Try to extract JSON snippet using a regex if possible.
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(1))
                    return result
                except json.JSONDecodeError:
                    pass
            # Fallback parsing based on expected schema properties.
            if "title" in function_schema.get("parameters", {}).get("properties", {}):
                title_match = re.search(r'[Tt]itle:?\s*(.*?)(?:\n|$)', response_text)
                result = {
                    "title": title_match.group(1) if title_match else "Untitled",
                    "alt_text": response_text
                }
                return result
            elif "description" in function_schema.get("parameters", {}).get("properties", {}):
                desc_match = re.search(r'[Dd]escription:?\s*(.*?)(?:\n|$)', response_text)
                result = {
                    "description": desc_match.group(1) if desc_match else response_text,
                    "document_type": "document"
                }
                return result
            return {}
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return {}


if __name__ == "__main__":
    # Example usage of the Gemini API utilities.
    gemini_api_key = "AIzaSyB6YEhNp-Bt5I4vUbST0Q2cspvA95Oho4k"
    if not gemini_api_key:
        logger.error("Please set the GEMINI_API_KEY environment variable.")
        exit(1)
        
    # Define an example function schema for structured output.
    example_schema = {
       "name": "analyze_feedback",
       "parameters": {
          "type": "object",
          "properties": {
              "summary": {"type": "string"},
              "keyPoints": {"type": "array", "items": {"type": "string"}},
              "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]}
          },
          "required": ["summary", "keyPoints"]
       }
    }
    
    prompt = "Analyze the customer feedback: 'I love the product but shipping was slow'"
    
    result = call_gemini_api("gemini-pro", prompt, example_schema)
    print("Function call result:", result)