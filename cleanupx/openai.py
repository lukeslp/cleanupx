#!/usr/bin/env python3
"""
OpenAI Responses API Utilities

This module provides an interface to OpenAI’s responses model using function calling.
It supports:
  - Text input (and optional image attachments, if using a vision-enabled model)
  - Function calling (to return structured JSON output)
  - A sample implementation of a "web_search" function integrated via function calling

For full details see:
https://platform.openai.com/docs/api-reference/responses

Requirements:
    pip install openai
"""
!!! TEMPLATE - EDIT THIS - KEEP THE HARD CODED CREDENTIALS

import openai
import json
import re
import logging
import base64
import os
from typing import Dict, Any, Optional

# Hard-coded credentials for demonstration purposes.
OPENAI_API_KEY = "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"
# Define models: one for text-only and one for vision (if available)
MODEL_TEXT = "gpt-4-0613"
MODEL_VISION = "gpt-4-vision-preview-0613"  # Example; update if needed.

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Set the API key for OpenAI
openai.api_key = OPENAI_API_KEY


def call_openai_responses(
    model: str,
    prompt: str,
    function_schema: dict,
    image_data: Optional[str] = None
) -> dict:
    """
    Call the OpenAI responses model using function calling.

    Args:
        model: The model to use (e.g. MODEL_TEXT or MODEL_VISION).
        prompt: The text prompt to send.
        function_schema: A JSON schema (and metadata) defining the expected structured output.
        image_data: Optional base64 encoded image data (used if model supports vision).

    Returns:
        A dictionary representing the structured response from the function call.
    """
    try:
        messages = []
        if model == MODEL_VISION and image_data:
            logger.info(f"Using vision model with image data ({len(image_data) // 1000}KB encoded)")
            # Embed the image data inline in a markdown image tag.
            messages.append({
                "role": "user",
                "content": f"{prompt}\n\n![image](data:image/jpeg;base64,{image_data})"
            })
        else:
            messages.append({"role": "user", "content": prompt})

        logger.info(f"Calling OpenAI model {model} with prompt: {prompt}")

        # Provide the function definitions (e.g. web_search function) so the model can call them.
        functions = [function_schema]

        # Force the model to use the function call by specifying its name in "function_call"
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            functions=functions,
            function_call={"name": function_schema["name"]}
        )

        message = response.choices[0].message
        if "function_call" in message:
            func_call = message["function_call"]
            try:
                result = json.loads(func_call.get("arguments", "{}"))
                for field in function_schema.get("parameters", {}).get("required", []):
                    if field not in result:
                        logger.warning(f"Missing required field '{field}' in API response")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode function call arguments: {e}")
                return {}
        else:
            # If the response does not include a function call,
            # try to extract JSON from the message content if present.
            content = message.get("content", "")
            result = {}
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            if not result:
                # Fallback extraction based on expected schema keys.
                if "title" in function_schema.get("parameters", {}).get("properties", {}):
                    title_match = re.search(r'[Tt]itle:?\s*(.*?)(?:\n|$)', content)
                    result["title"] = title_match.group(1) if title_match else "Untitled"
                    result["alt_text"] = content
                elif "description" in function_schema.get("parameters", {}).get("properties", {}):
                    desc_match = re.search(r'[Dd]escription:?\s*(.*?)(?:\n|$)', content)
                    result["description"] = desc_match.group(1) if desc_match else content
                    result["document_type"] = "document"
            return result

    except Exception as e:
        logger.error(f"Error calling OpenAI responses model: {e}")
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
    
    structured_response = call_openai_responses(MODEL_TEXT, sample_prompt, sample_schema)
    print("Structured Response:")
    print(json.dumps(structured_response, indent=2))