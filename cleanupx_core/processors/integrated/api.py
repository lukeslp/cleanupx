"""
API module for making external API calls.
"""

import os
import json
import logging
import signal
import requests
from typing import Optional, Dict, Any, Union
from functools import wraps
from .config import API_BASE_URL, API_TIMEOUT, XAI_API_KEY

logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    """Exception raised when an operation times out."""
    pass

def timeout(seconds: int):
    """
    Decorator to timeout a function after specified seconds.
    
    Args:
        seconds: Number of seconds before timeout
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            def handler(signum, frame):
                raise TimeoutError(f"Function call timed out after {seconds} seconds")
                
            # Set the timeout handler
            original_handler = signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
            finally:
                # Restore the original handler
                signal.alarm(0)
                signal.signal(signal.SIGALRM, original_handler)
                
            return result
        return wrapper
    return decorator

def call_xai_api(
    model: str,
    prompt: str,
    function_schema: Dict[str, Any],
    content: Optional[str] = None,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Call the X.AI API with function calling.
    
    Args:
        model: Model to use
        prompt: System prompt
        function_schema: Function schema for structured output
        content: Optional content to analyze
        **kwargs: Additional parameters to include in function call
        
    Returns:
        API response or None if call failed
    """
    try:
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            logger.error("XAI_API_KEY environment variable not set")
            return None

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        data = {
            'model': model,
            'messages': [
                {
                    'role': 'system',
                    'content': prompt
                }
            ],
            'functions': [function_schema],
            'function_call': {'name': function_schema['name']}
        }
        
        # Add content if provided
        if content:
            data['messages'].append({
                'role': 'user',
                'content': content
            })
            
        # Add additional parameters
        for key, value in kwargs.items():
            if value is not None:
                data[key] = value
                
        logger.debug(f"Making API call to {API_BASE_URL}/chat/completions")
        logger.debug(f"Request data: {json.dumps(data, indent=2)}")
                
        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            headers=headers,
            json=data,
            timeout=API_TIMEOUT
        )
        
        if response.status_code != 200:
            logger.error(f"API call failed with status {response.status_code}: {response.text}")
            return None
            
        result = response.json()
        logger.debug(f"API response: {json.dumps(result, indent=2)}")
        
        # Extract function call result
        if 'choices' in result and result['choices']:
            message = result['choices'][0]['message']
            
            # Handle direct content response
            if 'content' in message:
                try:
                    return json.loads(message['content'])
                except json.JSONDecodeError:
                    return {'content': message['content']}
            
            # Handle function call response
            if 'function_call' in message:
                try:
                    return json.loads(message['function_call']['arguments'])
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing function call result: {e}")
                    return None
                    
        logger.error("No valid response found in API response")
        return None
        
    except requests.RequestException as e:
        logger.error(f"API request error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error calling API: {e}")
        return None 