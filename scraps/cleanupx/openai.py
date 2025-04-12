#!/usr/bin/env python3
"""
OpenAI API Integration

This module provides an interface to OpenAI's API using function calling.
It supports:
  - Text input (and optional image attachments, if using a vision-enabled model)
  - Function calling (to return structured JSON output)
  - Proper error handling and logging
"""

import json
import re
import logging
import base64
import os
from typing import Dict, Any, Optional
from openai import OpenAI
from .config import XAI_MODEL_VISION, XAI_MODEL_TEXT, API_BASE_URL, API_TIMEOUT

# Configure logging
logger = logging.getLogger(__name__)

def call_openai_api(
    model: str,
    prompt: str,
    function_schema: dict,
    image_data: Optional[str] = None,
    api_key: Optional[str] = None
) -> dict:
    """
    Call the OpenAI API using function calling.

    Args:
        model: The model to use (e.g. XAI_MODEL_TEXT or XAI_MODEL_VISION)
        prompt: The text prompt to send
        function_schema: A JSON schema defining the expected structured output
        image_data: Optional base64 encoded image data (used if model supports vision)
        api_key: Optional API key to override environment variable

    Returns:
        A dictionary representing the structured response from the function call
    """
    try:
        # Initialize OpenAI client
        client = OpenAI(
            api_key=api_key or os.getenv('OPENAI_API_KEY'),
            base_url=API_BASE_URL,
            timeout=API_TIMEOUT
        )

        messages = []
        if model == XAI_MODEL_VISION and image_data:
            logger.info(f"Using vision model with image data ({len(image_data) // 1000}KB encoded)")
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                    }
                ]
            })
        else:
            messages.append({"role": "user", "content": prompt})

        logger.info(f"Calling OpenAI model {model} with prompt: {prompt}")

        # Make the API call with function calling
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            functions=[function_schema],
            function_call={"name": function_schema["name"]}
        )

        message = response.choices[0].message
        if hasattr(message, 'function_call'):
            func_call = message.function_call
            try:
                result = json.loads(func_call.arguments)
                for field in function_schema.get("parameters", {}).get("required", []):
                    if field not in result:
                        logger.warning(f"Missing required field '{field}' in API response")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode function call arguments: {e}")
                return {}
        else:
            # Extract structured data from message content if no function call
            content = message.content or ""
            result = {}
            
            # Try to extract JSON from code blocks
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
                    
            # Fallback extraction based on schema
            if not result:
                schema_props = function_schema.get("parameters", {}).get("properties", {})
                if "title" in schema_props:
                    title_match = re.search(r'[Tt]itle:?\s*(.*?)(?:\n|$)', content)
                    result["title"] = title_match.group(1) if title_match else "Untitled"
                    result["alt_text"] = content
                elif "description" in schema_props:
                    desc_match = re.search(r'[Dd]escription:?\s*(.*?)(?:\n|$)', content)
                    result["description"] = desc_match.group(1) if desc_match else content
                    result["document_type"] = "document"
                    
            return result

    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return {}


def web_search_function(query: str) -> Dict[str, Any]:
    """
    Dummy web search function.

    In production, you might replace this with a real web search API integration.
    
    Args:
        query: The search query string.

    Returns:
        A dictionary with search results.
    """
    # Simulated search result output.
    return {
        "results": [
            {"title": "Search Result 1", "url": "https://example.com/1", "snippet": "This is the first search result."},
            {"title": "Search Result 2", "url": "https://example.com/2", "snippet": "This is the second search result."},
            {"title": "Search Result 3", "url": "https://example.com/3", "snippet": "This is the third search result."}
        ]
    }


# Example usage:
if __name__ == "__main__":
    # Define a sample function schema for a web search.
    sample_schema = {
        "name": "web_search",
        "description": "Perform a web search and return structured results.",
        "parameters": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                            "snippet": {"type": "string"}
                        },
                        "required": ["title", "url", "snippet"]
                    }
                }
            },
            "required": ["results"]
        }
    }
    
    # A sample prompt that asks the model to perform a web search.
    sample_prompt = (
        "Please perform a web search for 'latest advancements in quantum computing' "
        "and return the search results in a structured JSON format."
    )
    
    structured_response = call_openai_api(XAI_MODEL_TEXT, sample_prompt, sample_schema)
    print("Structured Response:")
    print(json.dumps(structured_response, indent=2))