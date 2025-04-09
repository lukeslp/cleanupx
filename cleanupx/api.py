#!/usr/bin/env python3
"""
API utilities for interacting with X.AI API via OpenAI client.
"""

import json
import re
import logging
from typing import Dict, Any, Optional
import base64
from pathlib import Path
from contextlib import contextmanager
import signal
import time
from typing import Union

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.error("OpenAI package not installed. Install with: pip install openai")

from cleanupx.config import XAI_API_KEY, XAI_MODEL_TEXT, XAI_MODEL_VISION

# Configure logging
logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    """Exception raised when a function times out."""
    pass

@contextmanager
def timeout(seconds: int):
    """Context manager that raises a TimeoutError if execution takes longer than specified seconds."""
    def signal_handler(signum, frame):
        raise TimeoutError(f"Function timed out after {seconds} seconds")
    
    # Set the timeout handler
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        # Disable the alarm
        signal.alarm(0)

def get_api_client():
    """Get an OpenAI client configured for X.AI API."""
    try:
        client = OpenAI(
            api_key=XAI_API_KEY,
            base_url="https://api.x.ai/v1"
        )
        return client
    except Exception as e:
        logger.error(f"Error initializing API client: {e}")
        return None

def call_xai_api(model: str, prompt: str, function_schema: dict, image_data: Optional[str] = None) -> dict:
    """
    Call the X.AI API using OpenAI's function calling with structured output.
    
    Args:
        model: The model to use (XAI_MODEL_TEXT or XAI_MODEL_VISION)
        prompt: The prompt to send.
        function_schema: Schema defining expected structured output.
        image_data: Optional base64 encoded image for vision models.
        
    Returns:
        Dictionary containing the structured response.
    """
    client = get_api_client()
    if not client:
        return {}
    
    try:
        messages = []
        if model == XAI_MODEL_VISION and image_data:
            # Log for debugging
            logger.info(f"Using vision model with image data ({len(image_data) // 1000}KB encoded)")
            
            # Verify the image data looks valid
            if len(image_data) < 100:
                logger.error("Image data too small, likely invalid")
                return {}
                
            # For vision models with images
            messages = [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                    {"type": "text", "text": prompt}
                ]
            }]
        else:
            # For text-only models
            messages = [{"role": "user", "content": prompt}]
        
        # Log before making API call
        logger.info(f"HTTP Request: POST https://api.x.ai/v1/chat/completions")
        
        # Make the API call
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[{"type": "function", "function": function_schema}],
            tool_choice={"type": "function", "function": {"name": function_schema["name"]}}
        )
        
        # Log success
        logger.info(f"HTTP Request: POST https://api.x.ai/v1/chat/completions \"HTTP/1.1 200 OK\"")
        
        # Parse the response
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            # Check for valid JSON
            try:
                result = json.loads(tool_call.function.arguments)
                # Validate required fields
                for field in function_schema["parameters"].get("required", []):
                    if field not in result:
                        logger.warning(f"Missing required field '{field}' in API response")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in API response: {e}")
        
        logger.warning("Function call response not found, attempting to parse message content")
        if hasattr(response.choices[0].message, 'content'):
            content = response.choices[0].message.content
            result = {}
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            if not result:
                if "title" in function_schema["parameters"]["properties"]:
                    title_match = re.search(r'[Tt]itle:?\s*(.*?)(?:\n|$)', content)
                    result["title"] = title_match.group(1) if title_match else "Untitled image"
                    result["alt_text"] = content
                    from cleanupx.utils.common import clean_filename
                    result["suggested_filename"] = clean_filename(result["title"])
                elif "description" in function_schema["parameters"]["properties"]:
                    desc_match = re.search(r'[Dd]escription:?\s*(.*?)(?:\n|$)', content)
                    result["description"] = desc_match.group(1) if desc_match else content
                    result["document_type"] = "document"
                    from cleanupx.utils.common import clean_filename
                    result["suggested_filename"] = clean_filename(Path(content).stem)
            return result
        
        logger.error("Could not extract structured result from API response")
        return {}
    except Exception as e:
        logger.error(f"Error calling X.AI API: {e}")
        return {}
