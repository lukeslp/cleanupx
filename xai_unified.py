#!/usr/bin/env python3
"""
Unified X.AI API Module

This module provides a consistent interface for interacting with the X.AI API
across different scripts in the cleanupx project. It handles authentication,
request formatting, error handling, and response parsing.
"""

import os
import sys
import json
import re
import time
import logging
import requests
from typing import Dict, List, Any, Optional, Union
from functools import wraps
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Constants and configuration
DEFAULT_MODEL_TEXT = "grok-3-mini-latest"
DEFAULT_MODEL_VISION = "grok-2-vision-latest"
API_BASE_URL = "https://api.x.ai/v1"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Decorator to retry API calls with exponential backoff
def retry_with_backoff(func):
    """Decorator to retry API calls with exponential backoff."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        retries = 0
        while retries < MAX_RETRIES:
            try:
                return func(*args, **kwargs)
            except (requests.HTTPError, requests.ConnectionError) as e:
                retries += 1
                if retries >= MAX_RETRIES:
                    logger.error(f"Max retries reached. Last error: {e}")
                    raise
                
                sleep_time = RETRY_DELAY * (2 ** (retries - 1))
                logger.warning(f"API call failed: {e}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
        return func(*args, **kwargs)  # One last try
    return wrapper

class XAIClient:
    """
    Client for interacting with the X.AI API.
    
    This class provides methods for authenticating and making requests to
    the X.AI API, with built-in error handling and retry logic.
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the client with API credentials.
        
        Args:
            api_key: X.AI API key (defaults to XAI_API_KEY environment variable)
        """
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        if not self.api_key:
            logger.error("X.AI API key not found. Set XAI_API_KEY environment variable.")
            raise ValueError("X.AI API key not found. Set XAI_API_KEY environment variable.")
        
        self.base_url = API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        
    @retry_with_backoff
    def chat(self, messages, model=DEFAULT_MODEL_TEXT, temperature=0.3, functions=None):
        """
        Send a chat completion request to the X.AI API.
        
        Args:
            messages: List of message objects with role and content
            model: X.AI model identifier to use
            temperature: Sampling temperature (0-1)
            functions: Optional function calling configuration
            
        Returns:
            Parsed JSON response from the API
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        # Add function calling if provided
        if functions:
            payload["tools"] = [{"type": "function", "function": f} for f in functions]
            if len(functions) == 1:
                payload["tool_choice"] = {
                    "type": "function", 
                    "function": {"name": functions[0]["name"]}
                }
        
        try:
            logger.debug(f"Sending request to {url}")
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            error_details = "No response details available"
            if e.response is not None:
                try:
                    error_details = e.response.json()
                except json.JSONDecodeError:
                    error_details = e.response.text
            
            logger.error(f"API error: {e}\nResponse details: {error_details}")
            raise
    
    def extract_tool_result(self, response):
        """
        Extract function call result from API response.
        
        Args:
            response: JSON response from chat completion API
            
        Returns:
            Extracted function arguments as dictionary
        """
        try:
            message = response["choices"][0]["message"]
            
            # Check for tool calls in the response
            if "tool_calls" in message and message["tool_calls"]:
                tool_call = message["tool_calls"][0]
                if tool_call["type"] == "function":
                    function_args = json.loads(tool_call["function"]["arguments"])
                    return function_args
            
            # Fallback to content parsing if no tool calls
            content = message.get("content", "")
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Return the raw content as fallback
            return {"content": content}
            
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Error extracting tool result: {e}")
            return {}

def get_xai_client():
    """
    Get an initialized X.AI client instance.
    
    Returns:
        XAIClient instance
    """
    try:
        return XAIClient()
    except ValueError as e:
        logger.error(f"Failed to initialize XAI client: {e}")
        return None

# Convenience functions for common API operations

def analyze_code_snippet(code, context=None, model=DEFAULT_MODEL_TEXT):
    """
    Analyze a code snippet to extract its important parts.
    
    Args:
        code: Code content to analyze
        context: Optional context about the code (e.g., filename, purpose)
        model: X.AI model to use
        
    Returns:
        Dictionary with analysis results
    """
    client = get_xai_client()
    if not client:
        return {"error": "Failed to initialize API client"}
    
    # Construct the prompt
    context_str = f"\nContext: {context}" if context else ""
    prompt = (
        f"Extract the most important and unique code snippets or documentation "
        f"segments from the following code.{context_str}\n\n"
        f"Format your response as:\n\n"
        f"Best Version:\n<best snippet>\n\n"
        f"Alternatives:\n<alternative snippet(s)>\n\n"
        f"Code:\n{code}"
    )
    
    messages = [{"role": "system", "content": prompt}]
    
    try:
        response = client.chat(messages, model=model)
        content = response["choices"][0]["message"]["content"]
        
        # Parse the response format
        best = ""
        alternatives = ""
        
        if "Best Version:" in content:
            parts = content.split("Best Version:")
            remainder = parts[1]
            if "Alternatives:" in remainder:
                best, alt_part = remainder.split("Alternatives:", 1)
                best = best.strip()
                alternatives = alt_part.strip()
            else:
                best = remainder.strip()
        else:
            best = content.strip()
        
        return {
            "success": True,
            "best": best,
            "alternatives": alternatives,
            "raw_response": content
        }
    except Exception as e:
        logger.error(f"Error analyzing code snippet: {e}")
        return {
            "success": False,
            "error": str(e),
            "best": "",
            "alternatives": ""
        }

def find_duplicates(files, threshold=0.7, model=DEFAULT_MODEL_TEXT):
    """
    Use X.AI to identify duplicate content across multiple files.
    
    Args:
        files: Dictionary mapping filenames to content
        threshold: Similarity threshold (0-1)
        model: X.AI model to use
        
    Returns:
        Dictionary with duplicate analysis
    """
    client = get_xai_client()
    if not client:
        return {"error": "Failed to initialize API client"}
    
    # Create a formatted list of files for the prompt
    file_content = ""
    for filename, content in files.items():
        # Truncate very large files
        preview = content[:5000] + "..." if len(content) > 5000 else content
        file_content += f"\n\n## File: {filename}\n```\n{preview}\n```"
    
    prompt = (
        f"Analyze the following files to identify duplicates or near-duplicates "
        f"with at least {threshold*100}% similarity. For each group of similar files, "
        f"create a consolidated version that contains the best parts.\n\n"
        f"Return your analysis in JSON format with the following structure:\n"
        f"{{\"groups\": [{{\n"
        f"  \"files\": [\"file1.py\", \"file2.py\"],\n"
        f"  \"analysis\": \"Brief analysis of similarities\",\n"
        f"  \"consolidated\": \"Best combined version\"\n"
        f"}}]}}\n\n"
        f"Files to analyze:{file_content}"
    )
    
    messages = [{"role": "system", "content": prompt}]
    
    function_schema = {
        "name": "analyze_duplicates",
        "description": "Analyze groups of potential duplicate files and create consolidated versions",
        "parameters": {
            "type": "object",
            "properties": {
                "groups": {
                    "type": "array",
                    "description": "List of file groups with duplicates",
                    "items": {
                        "type": "object",
                        "properties": {
                            "files": {
                                "type": "array",
                                "description": "List of duplicate file names",
                                "items": {"type": "string"}
                            },
                            "analysis": {
                                "type": "string",
                                "description": "Analysis of similarities and differences"
                            },
                            "consolidated": {
                                "type": "string",
                                "description": "Consolidated best version from all duplicates"
                            }
                        }
                    }
                }
            }
        }
    }
    
    try:
        response = client.chat(messages, model=model, functions=[function_schema])
        result = client.extract_tool_result(response)
        return {
            "success": True,
            "groups": result.get("groups", []),
            "raw_response": response
        }
    except Exception as e:
        logger.error(f"Error finding duplicates: {e}")
        return {
            "success": False,
            "error": str(e),
            "groups": []
        }

def synthesize_snippets(snippets, model=DEFAULT_MODEL_TEXT):
    """
    Combine multiple code snippets into a cohesive document.
    
    Args:
        snippets: Dictionary mapping file names to code snippets
        model: X.AI model to use
        
    Returns:
        Dictionary with synthesized result
    """
    client = get_xai_client()
    if not client:
        return {"error": "Failed to initialize API client"}
    
    # Format the snippets
    combined_text = ""
    for filename, snippet in snippets.items():
        combined_text += f"\n\n## File: {filename}\n```\n{snippet}\n```"
    
    prompt = (
        f"Combine the following code snippets from various files into a "
        f"cohesive document that retains only the most important and unique segments. "
        f"Eliminate redundancies and organize the content logically.\n\n"
        f"Snippets:{combined_text}"
    )
    
    messages = [{"role": "system", "content": prompt}]
    
    try:
        response = client.chat(messages, model=model)
        content = response["choices"][0]["message"]["content"]
        
        return {
            "success": True,
            "result": content,
            "raw_response": response
        }
    except Exception as e:
        logger.error(f"Error synthesizing snippets: {e}")
        return {
            "success": False,
            "error": str(e),
            "result": ""
        }

# Export a default client instance for convenience
client = get_xai_client()