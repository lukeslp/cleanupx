#!/usr/bin/env python3
"""
X.AI Cleaner (xsnipper.py)

This script ingests a directory of code (or snippet) files, uses the X.AI API to extract and
synthesize the most important and unique snippets (or documentation), and processes them in batches:
  - Processes files in batches of 25
  - Generates intermediate optimized results for each batch
  - Performs a final sweep to evaluate all batch results
  - Combines the best snippets into a final document,
  - Archives alternative snippets separately,
  - Logs every step in snipper/log.txt,
  - Maintains a summary of impressions (purpose of the snippets/project) in snipper/summary.txt,
  - Updates an ongoing snippet collection (and any encountered links/citations) in snipper/snippets.txt.

Mode options explained:
  - 'code': Process source code files to extract significant snippets. Use this when dealing with full source files.
  - 'snippet': Evaluate existing code snippets for uniqueness/importance. Use this when files are already snippets.

Usage examples:
  python xsnipper.py --directory /path/to/code --mode code --verbose --output final_combined.md
  python xsnipper.py --directory /path/to/snippets --mode snippet --verbose
If no arguments are provided, an interactive CLI is launched.
"""

import os
import sys
import argparse
import re
import time
import shutil
import json
import requests
import difflib  # Added for diff-based grouping of chunks
from functools import wraps
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Union

# Load environment variables from .env file
load_dotenv()

# Constants and configuration
DEFAULT_MODEL_TEXT = "grok-3-mini-latest"
DEFAULT_MODEL_VISION = "grok-2-vision-latest"
API_BASE_URL = "https://api.x.ai/v1"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Configure basic logging
class Logger:
    """Simple logging class for consistent output formatting."""
    
    @staticmethod
    def info(message):
        """Log an info message."""
        print(f"INFO: {message}")
    
    @staticmethod
    def warning(message):
        """Log a warning message."""
        print(f"WARNING: {message}", file=sys.stderr)
    
    @staticmethod
    def error(message):
        """Log an error message."""
        print(f"ERROR: {message}", file=sys.stderr)
        
    @staticmethod
    def debug(message):
        """Log a debug message."""
        if os.getenv("DEBUG", "").lower() in ("1", "true", "yes"):
            print(f"DEBUG: {message}")

logger = Logger()

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
            # Added timeout to prevent hanging (e.g., when processing images)
            response = self.session.post(url, json=payload, timeout=30)
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

# Convenience functions for common API operations

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
        return {"success": False, "error": "Failed to initialize API client"}
    
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
        return {"success": False, "error": "Failed to initialize API client"}
    
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
        return {"success": False, "error": "Failed to initialize API client"}
    
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

# -----------------------------------------------------------------------------
# Helper function: group_chunks
# -----------------------------------------------------------------------------
def group_chunks(chunks, threshold=0.8):
    """
    Group similar chunks together using difflib to determine similarity.
    If the similarity ratio between consecutive chunks exceeds the threshold,
    merge them into a single group.
    """
    if not chunks:
        return []
    grouped = []
    current_group = [chunks[0]]
    for chunk in chunks[1:]:
        similarity = difflib.SequenceMatcher(None, current_group[-1], chunk).ratio()
        if (similarity > threshold):
            current_group.append(chunk)
        else:
            grouped.append("\n".join(current_group))
            current_group = [chunk]
    grouped.append("\n".join(current_group))
    return grouped

# -----------------------------------------------------------------------------
# Helper function: group_batches
# -----------------------------------------------------------------------------
def group_batches(items, batch_size=25):
    """
    Divide the list 'items' into batches of size 'batch_size'.
    """
    return [items[i:i+batch_size] for i in range(0, len(items), batch_size)]

# =============================================================================
# Helper functions for I/O and logging in the snipper directory
# =============================================================================

def init_snipper_directory(target_directory):
    """
    Ensure the snipper directory and its subdirectories exist in the target directory; 
    return their paths.
    """
    base_dir = os.path.join(target_directory, ".xsnippet")
    if not os.path.isdir(base_dir):
        os.makedirs(base_dir)
    
    # Create subdirectories for organization
    batches_dir = os.path.join(base_dir, "batches")
    archive_dir = os.path.join(base_dir, "archive")
    final_dir = os.path.join(base_dir, "final")
    
    for directory in [batches_dir, archive_dir, final_dir]:
        if not os.path.isdir(directory):
            os.makedirs(directory)
    
    # Define file paths
    log_file = os.path.join(base_dir, "log.txt")
    summary_file = os.path.join(base_dir, "summary.txt")
    snippets_file = os.path.join(base_dir, "snippets.txt")
    
    # Create empty files if they don't exist
    for file in [log_file, summary_file, snippets_file]:
        if not os.path.exists(file):
            with open(file, "w", encoding="utf-8") as f:
                f.write("")
    
    # Create API credentials file
    api_creds_file = os.path.join(base_dir, "api_credentials.txt")
    if not os.path.exists(api_creds_file):
        with open(api_creds_file, "w", encoding="utf-8") as f:
            f.write("# API Credentials and Endpoints Found\n\n")
    
    processed_dir = os.path.join(base_dir, "xsnippet_processed")
    if not os.path.isdir(processed_dir):
        os.makedirs(processed_dir)
    
    return {"base": base_dir, "log": log_file, "summary": summary_file, "snippets": snippets_file, "archive": archive_dir, "batches": batches_dir, "final": final_dir, "processed": processed_dir, "api_creds": api_creds_file}

def current_timestamp():
    """Return the current timestamp string."""
    return time.strftime("%Y-%m-%d %H:%M:%S")

def log_message(message, log_path):
    """Append a log message with timestamp to the log file."""
    timestamp = current_timestamp()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def extract_links(text):
    """Return a list of URLs found in the given text."""
    url_regex = r'(https?://[^\s]+)'
    return re.findall(url_regex, text)

def update_snippet_collection(best_snippet, log_data, snippets_path):
    """
    Append the best snippet along with any links and citations to the ongoing snippet collection.
    'log_data' is a dict with optional keys 'filename' and 'links' for context.
    """
    header = f"\n=== File: {log_data.get('filename', 'Unknown')} | {current_timestamp()} ===\n"
    separator = "\n--------------------\n"
    content = header + best_snippet + separator
    if log_data.get("links"):
        content += "Links/Citations:\n" + "\n".join(log_data["links"]) + separator
    with open(snippets_path, "a", encoding="utf-8") as f:
        f.write(content)

# =============================================================================
# File I/O functions for code/snippet processing
# =============================================================================

def read_file(file_path):
    """Read the entire contents of a file; exit on error."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        sys.exit(1)

def split_into_chunks(text, max_chunk_size=6000):
    """
    Split a text into chunks no larger than max_chunk_size characters.
    Splitting is done at newlines to preserve structure.
    """
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_size = 0

    for line in lines:
        line_size = len(line)
        if current_size + line_size > max_chunk_size and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_size = 0
        current_chunk.append(line)
        current_size += line_size
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    return chunks

# =============================================================================
# X.AI API functions for snippet extraction and synthesis
# =============================================================================

def scan_for_api_credentials(content, filename):
    """
    Scan a file's content for potential API credentials, endpoints, and schema.
    
    Args:
        content: The file content to scan
        filename: Name of the file being scanned
        
    Returns:
        Dictionary with found credentials and endpoints
    """
    credentials = {
        "api_keys": [],
        "endpoints": [],
        "schemas": []
    }
    
    # Common patterns for API keys
    key_patterns = [
        r'(?:api[_-]?key|apikey|access[_-]?token|auth[_-]?token|client[_-]?secret)["\']?\s*(?::|=|:=|\+=)\s*["\']([a-zA-Z0-9_\-\.]{20,})["\']',
        r'bearer\s+([a-zA-Z0-9_\-\.]{20,})',
        r'token["\']?\s*(?::|=|:=|\+=)\s*["\']([a-zA-Z0-9_\-\.]{20,})["\']'
    ]
    
    # Patterns for API endpoints
    endpoint_patterns = [
        r'https?://([a-zA-Z0-9][-a-zA-Z0-9]*\.)*api\.[-a-zA-Z0-9.]+\.[a-zA-Z]{2,}/[-a-zA-Z0-9/%_.~?&=]*',
        r'https?://([a-zA-Z0-9][-a-zA-Z0-9]*\.)*[-a-zA-Z0-9.]+\.[a-zA-Z]{2,}/api/[-a-zA-Z0-9/%_.~?&=]*',
        r'(?:endpoint|url|uri|base[_-]?url)["\']?\s*(?::|=|:=|\+=)\s*["\']([^"\']+api[^"\']+)["\']'
    ]
    
    # Patterns for API schema definitions
    schema_patterns = [
        r'(?:schema|model)\s*=\s*{[\s\S]*?}',
        r'@app\.(?:get|post|put|delete)\(["\']([^"\']+)["\']',
        r'function\s+\w+\([^)]*\)\s*{[\s\S]*?fetch\(["\']([^"\']+)["\']',
        r'(?:routes|endpoints)\s*=\s*\[[\s\S]*?\]'
    ]
    
    # Scan for API keys
    for pattern in key_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            # Don't add placeholder/example keys
            if not any(x in match.lower() for x in ['yourkey', 'example', 'placeholder', 'xxxxxx']):
                credentials["api_keys"].append(match)
    
    # Scan for endpoints
    for pattern in endpoint_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[-1]  # Sometimes the regex returns tuples
            if match and not any(x in match.lower() for x in ['example', 'placeholder']):
                credentials["endpoints"].append(match)
    
    # Scan for schema definitions
    for pattern in schema_patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        for match in matches:
            if match:
                if isinstance(match, tuple):
                    match = match[-1]
                credentials["schemas"].append(match)
    
    # Remove duplicates
    for key in credentials:
        credentials[key] = list(set(credentials[key]))
    
    return credentials

def process_file_for_snippets(file_path, mode, verbose=False):
    """
    For the given file, use the X.AI API to extract important snippet(s) by processing in batches.
    Return a dict with keys "best" and "alternatives".
    """
    content = read_file(file_path)
    if verbose:
        print(f"Processing file for snippet extraction: {file_path}")
    
    # Scan for API credentials
    filename = os.path.basename(file_path)
    credentials = scan_for_api_credentials(content, filename)
    if any(credentials.values()) and 'snipper_paths' in globals() and snipper_paths:
        # Log to api_credentials.txt file
        with open(snipper_paths["api_creds"], "a", encoding="utf-8") as f:
            f.write(f"\n## From file: {filename}\n")
            if credentials["api_keys"]:
                f.write("### API Keys\n")
                for key in credentials["api_keys"]:
                    f.write(f"- `{key}`\n")
            if credentials["endpoints"]:
                f.write("### Endpoints\n")
                for endpoint in credentials["endpoints"]:
                    f.write(f"- `{endpoint}`\n")
            if credentials["schemas"]:
                f.write("### Schemas\n")
                for schema in credentials["schemas"]:
                    f.write(f"- ```\n{schema}\n```\n")
        if verbose:
            print(f"Found API credentials in {filename} and stored in {snipper_paths['api_creds']}")
    
    # Split content into chunks based on size limits
    chunks = [content] if len(content) <= 6000 else split_into_chunks(content)
    # Optionally, you can still group similar chunks to minimize redundancy:
    if len(chunks) > 1:
        chunks = group_chunks(chunks, threshold=0.8)
    
    # Group the chunks into batches of 25
    batches = group_batches(chunks, batch_size=25)
    batch_responses = []
    
    # Process each batch
    for batch_index, batch in enumerate(batches):
        # Combine all chunks in this batch into a single prompt
        combined_batch = "\n\n===== BATCH DIVIDER =====\n\n".join(batch)
        if mode == "code":
            prompt = (
                "You are a helpful coding assistant. Extract the most important and unique code snippets "
                "or documentation segments from the following code. Return your answer formatted as follows:\n\n"
                "Best Version:\n<best snippet>\n\nAlternatives:\n<alternative snippet(s)>\n\n"
                "Code:\n" + combined_batch
            )
        else:  # mode == "snippet"
            prompt = (
                "You are a helpful coding assistant. Evaluate the following code snippet for its uniqueness and importance. "
                "If it is significant, return it as the Best Version; otherwise, indicate that it is not significant. "
                "Format your answer as follows (if significant):\n\n"
                "Best Version:\n<best snippet>\n\nAlternatives:\n<alternative snippet(s)>\n\n"
                "Snippet:\n" + combined_batch
            )
        
        conversation_history = [{"role": "system", "content": prompt}]
        if verbose:
            print(f"Sending batch {batch_index+1}/{len(batches)} (with {len(batch)} chunks) to X.AI API...")
        
        try:
            client = get_xai_client()
            if client:
                # Use the client to analyze the snippet
                result = analyze_code_snippet(
                    code=combined_batch,
                    context=f"Mode: {mode}, File: {file_path}",
                    model=DEFAULT_MODEL_TEXT
                )
                if result.get("success", False):
                    batch_responses.append(result.get("raw_response", ""))
                else:
                    raise Exception(result.get("error", "Unknown error"))
            else:
                raise Exception("Failed to initialize API client")
        except Exception as e:
            error_message = str(e)
            print(f"API error: {error_message}")
            log_message(f"Error processing batch {batch_index+1} in {file_path}: {error_message}", snipper_paths["log"])
    
    # If multiple batches were processed, synthesize their outputs in a final review step.
    if len(batch_responses) > 1:
        combined_responses = "\n\n===== BATCH RESPONSES DIVIDER =====\n\n".join(batch_responses)
        synthesis_prompt = (
            "You are a coding expert tasked with reviewing several batch outputs from a code snippet extraction task. "
            "Review the following outputs and combine them into one final cohesive result, retaining only the most unique and important snippets. "
            "Preserve the formatting with 'Best Version:' and 'Alternatives:' as in the individual responses.\n\n"
            "Batch Responses:\n" + combined_responses
        )
        conversation_history = [{"role": "system", "content": synthesis_prompt}]
        try:
            client = get_xai_client()
            if client:
                result = synthesize_snippets({"combined": combined_responses}, model=DEFAULT_MODEL_TEXT)
                if result.get("success", False):
                    final_response = result.get("result", "")
                else:
                    raise Exception(result.get("error", "Unknown error"))
            else:
                raise Exception("Failed to initialize API client")
        except Exception as e:
            error_message = str(e)
            print(f"API error during synthesis: {error_message}")
            log_message(f"Error synthesizing batch responses for {file_path}: {error_message}", snipper_paths["log"])
            final_response = combined_responses
    else:
        final_response = batch_responses[0] if batch_responses else ""
    
    # Parse the final_response to extract best and alternative snippets.
    best = ""
    alternatives = ""
    if "Best Version:" in final_response:
        parts = final_response.split("Best Version:")
        remainder = parts[1]
        if "Alternatives:" in remainder:
            best, alt_part = remainder.split("Alternatives:", 1)
            best = best.strip()
            alternatives = alt_part.strip()
        else:
            best = remainder.strip()
    else:
        best = final_response.strip()
    
    return {"best": best, "alternatives": alternatives}

def synthesize_overall_snippets(best_snippets, verbose=False):
    """
    Use the X.AI API to combine best snippets from all files into a cohesive final document.
    """
    combined_text = ""
    for file_name, snippet in best_snippets.items():
        combined_text += f"\n\nFile: {file_name}\nBest Version:\n{snippet}\n"
    
    synthesis_prompt = (
        "You are an expert coding assistant. Combine the following code/documentation snippets from various files "
        "into a cohesive final document that retains only the most important and unique segments. "
        "Eliminate any redundancies and format the output clearly.\n\n"
        "Snippets:" + combined_text
    )
    conversation_history = [{"role": "system", "content": synthesis_prompt}]
    
    try:
        client = get_xai_client()
        if client:
            result = synthesize_snippets(best_snippets, model=DEFAULT_MODEL_TEXT)
            if result.get("success", False):
                final_document = result.get("result", "")
            else:
                raise Exception(result.get("error", "Unknown error"))
        else:
            raise Exception("Failed to initialize API client")
    except Exception as e:
        error_message = str(e)
        print(f"API error: {error_message}")
        log_message(f"Error synthesizing overall snippets: {error_message}", snipper_paths["log"])
        final_document = combined_text
    return final_document

def generate_project_summary(best_snippets, verbose=False):
    """
    Use the X.AI API to generate a summary of impressions regarding the purpose and nature of the snippets/project.
    """
    combined_text = ""
    for file_name, snippet in best_snippets.items():
        combined_text += f"\n\nFile: {file_name}\n{snippet}\n"
    
    summary_prompt = (
        "You are an expert coding assistant. Based on the following code/documentation snippets from a project, "
        "provide a concise summary of the overall purpose, functionality, and design impressions of the project. "
        "Focus on the unique and important aspects.\n\n"
        "Snippets:" + combined_text
    )
    conversation_history = [{"role": "system", "content": summary_prompt}]
    
    try:
        client = get_xai_client()
        if client:
            # Using the synthesize_snippets function as it's suitable for this task too
            result = synthesize_snippets(
                {"project_code": combined_text},
                model=DEFAULT_MODEL_TEXT
            )
            if result.get("success", False):
                summary = result.get("result", "")
            else:
                raise Exception(result.get("error", "Unknown error"))
        else:
            raise Exception("Failed to initialize API client")
    except Exception as e:
        error_message = str(e)
        print(f"API error: {error_message}")
        log_message(f"Error generating project summary: {error_message}", snipper_paths["log"])
        summary = "Summary generation failed due to error."
    return summary

# =============================================================================
# Main processing functions
# =============================================================================

def process_directory(directory, mode, verbose=False, output_file="final_combined.md", recursive=False):
    """
    Process every file in the specified directory in batches of 25:
      - Extract snippets via the X.AI API,
      - Archive alternative snippets,
      - Generate batch-level optimizations,
      - Perform a final sweep to synthesize all batches,
      - Generate a project summary,
      - Update ongoing snippet collection and logs.
    """
    # Initialize snipper file paths in the target directory
    global snipper_paths
    snipper_paths = init_snipper_directory(directory)
    # Store the absolute path of the directory for later use
    global source_directory_path
    source_directory_path = os.path.abspath(directory)
    log_message(f"Started processing directory: {directory} (mode: {mode})", snipper_paths["log"])
    
    if not os.path.isdir(directory):
        log_message(f"Invalid directory: {directory}", snipper_paths["log"])
        print(f"Error: {directory} is not a valid directory.", file=sys.stderr)
        sys.exit(1)
    
    # Collect all valid files while skipping common image types
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg'}
    all_files = []
    if recursive:
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.') and not d.startswith('_') and d not in (".xsnippet", "xsnippet_processed")]
            for file in files:
                if file.startswith('.') or file.startswith('_'):
                    continue
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file)
                if ext.lower() in image_extensions:
                    log_message(f"Skipping image file: {file_path}", snipper_paths["log"])
                    continue
                all_files.append(file_path)
    else:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and not file.startswith('.') and not file.startswith('_') and file not in (".xsnippet", "xsnippet_processed"):
                _, ext = os.path.splitext(file)
                if ext.lower() in image_extensions:
                    log_message(f"Skipping image file: {file}", snipper_paths["log"])
                    continue
                all_files.append(file_path)
    
    if not all_files:
        log_message(f"No valid files found in directory: {directory}", snipper_paths["log"])
        print(f"No valid files found in directory: {directory}", file=sys.stderr)
        sys.exit(1)
    
    # Split files into batches of 25
    batch_size = 25
    batches = [all_files[i:i+batch_size] for i in range(0, len(all_files), batch_size)]
    
    # Process each batch
    batch_results = {}
    for batch_index, batch_files in enumerate(batches):
        if verbose:
            print(f"\nProcessing batch {batch_index + 1}/{len(batches)}...")
        log_message(f"Processing batch {batch_index + 1}/{len(batches)}", snipper_paths["log"])
        
        # Process each file in the batch
        best_snippets_in_batch = {}
        for file in batch_files:
            file_path = file
            log_message(f"Processing file: {file}", snipper_paths["log"])
            if verbose:
                print(f"Processing {file}...")
            result = process_file_for_snippets(file_path, mode, verbose)
            best_snippet = result.get("best", "")
            best_snippets_in_batch[file] = best_snippet
            
            # Archive alternatives if any
            alternatives = result.get("alternatives", "")
            if alternatives:
                # Create a file-specific directory in the archive folder
                file_archive_dir = os.path.join(snipper_paths["archive"], os.path.splitext(file)[0])
                archive_file = os.path.join(snipper_paths["archive"], f"{file}_alternatives.md")
                try:
                    with open(archive_file, "w", encoding="utf-8") as f:
                        f.write(f"# Alternatives for {file}\n\n{alternatives}")
                    log_message(f"Archived alternatives for {file} to {archive_file}", snipper_paths["log"])
                except Exception as e:
                    log_message(f"Error archiving alternatives for {file}: {e}", snipper_paths["log"])
            
            # Extract any links and update the ongoing snippet collection file
            links = extract_links(best_snippet)
            update_snippet_collection(best_snippet, {"filename": file, "links": links}, snipper_paths["snippets"])
            
            # Move processed file to "xsnippet_processed" folder
            try:
                processed_dest = os.path.join(snipper_paths["processed"], os.path.basename(file_path))
                shutil.move(file_path, processed_dest)
                log_message(f"Moved processed file {file_path} to {processed_dest}", snipper_paths["log"])
            except Exception as e:
                log_message(f"Error moving file {file_path}: {e}", snipper_paths["log"])
        
        # Generate optimized result for this batch
        if verbose:
            print(f"Synthesizing batch {batch_index + 1} results...")
        batch_output_file = os.path.join(snipper_paths["batches"], f"batch_{batch_index + 1}_combined.md")
        batch_document = synthesize_overall_snippets(best_snippets_in_batch, verbose)
        
        try:
            with open(batch_output_file, "w", encoding="utf-8") as f:
                f.write(f"# Batch {batch_index + 1} Combined Snippets\n\n")
                f.write(batch_document)
            log_message(f"Batch {batch_index + 1} results written to {batch_output_file}", snipper_paths["log"])
            if verbose:
                # Use relative path for display
                rel_path = os.path.relpath(batch_output_file, source_directory_path)
                print(f"Batch {batch_index + 1} results written to {rel_path}")
                
            # Add this batch's results to the overall results
            batch_results[f"Batch {batch_index + 1}"] = batch_document
        except Exception as e:
            log_message(f"Error writing batch {batch_index + 1} output: {e}", snipper_paths["log"])
            print(f"Error writing batch {batch_index + 1} output: {e}", file=sys.stderr)
    
    # Final sweep to evaluate all batch results
    if verbose:
        print("\nPerforming final sweep to evaluate all batch results...")
    log_message("Starting final sweep across all batches", snipper_paths["log"])
    
    final_document = synthesize_final_results(batch_results, verbose)
    
    try:
        final_output_file = os.path.join(snipper_paths["final"], "final_combined.md")
        with open(final_output_file, "w", encoding="utf-8") as f:
            f.write("# Final Combined Snippets\n\n")
            f.write(final_document)
        log_message(f"Final combined document written to {final_output_file}", snipper_paths["log"])
        
        # Create a copy of the final output in the main directory
        main_output_file = os.path.join(directory, output_file)
        with open(main_output_file, "w", encoding="utf-8") as f:
            f.write("# Final Combined Snippets\n\n")
            f.write(final_document)
        log_message(f"Created visible copy at {main_output_file}", snipper_paths["log"])
        
        if verbose:
            # Use relative path for display
            rel_path = os.path.relpath(final_output_file, source_directory_path)
            print(f"Final document written to {rel_path}")
            print(f"Visible copy created at: {output_file}")
    except Exception as e:
        log_message(f"Error writing final output: {e}", snipper_paths["log"])
        print(f"Error writing final output: {e}", file=sys.stderr)
    
    # Generate project summary based on the final document
    if verbose:
        print("Generating project summary...")
    summary = generate_project_summary({"Final Document": final_document}, verbose)
    try:
        with open(snipper_paths["summary"], "w", encoding="utf-8") as f:
            f.write("# Project Summary\n\n")
            f.write(summary)
        log_message("Project summary updated.", snipper_paths["log"])
        if verbose:
            # Use relative path for display
            rel_path = os.path.relpath(snipper_paths["summary"], source_directory_path)
            print(f"Project summary written to {rel_path}")
    except Exception as e:
        log_message(f"Error writing project summary: {e}", snipper_paths["log"])
        print(f"Error writing project summary: {e}", file=sys.stderr)
    
    log_message("Processing complete.", snipper_paths["log"])

def synthesize_final_results(batch_results, verbose=False):
    """
    Final sweep to evaluate all batch results and create the consolidated output.
    
    Args:
        batch_results: Dictionary mapping batch names to their synthesized content
        verbose: Whether to print verbose output
        
    Returns:
        Consolidated final document
    """
    if verbose:
        print("Synthesizing final results from all batches...")
    
    client = get_xai_client()
    if not client:
        return "\n\n".join(batch_results.values())
    
    # Format the prompt with all batch results
    combined_text = ""
    for batch_name, content in batch_results.items():
        combined_text += f"\n\n## {batch_name}\n{content}\n"
    
    prompt = (
        f"You are performing a final evaluation of multiple batches of code snippets that have "
        f"already been analyzed and optimized. Your task is to:\n"
        f"1. Identify the most important and unique snippets across all batches\n"
        f"2. Remove any duplicated content or redundancies\n"
        f"3. Organize the content in a logical, coherent manner\n"
        f"4. Preserve critically important code and documentation\n\n"
        f"Create a final consolidated document that represents the best subset of all content.\n\n"
        f"Batch Results:{combined_text}"
    )
    
    messages = [{"role": "system", "content": prompt}]
    
    try:
        response = client.chat(messages, model=DEFAULT_MODEL_TEXT)
        content = response["choices"][0]["message"]["content"]
        return content
    except Exception as e:
        logger.error(f"Error synthesizing final results: {e}")
        # Fallback: concatenate all batch results
        return "# Final Consolidated Results\n\n" + "\n\n---\n\n".join(batch_results.values())

def export_formatted_snippetfile(export_path, source_directory=None, include_api_creds=False, verbose=False):
    """
    Export the snippets from the .xsnippet folder into a formatted snippet file.
    
    Reads the final combined document and summary (if exists) and combines them
    into a formatted snippet file.
    
    Args:
        export_path: Path for the exported formatted snippet file.
        source_directory: Directory containing the .xsnippet folder. If None, will use the global snipper_paths.
        include_api_creds: Whether to include API credentials in the export.
        verbose: Whether to print progress.
    
    Returns:
        The formatted snippet content or None if operation failed.
    """
    global snipper_paths
    
    # If export_path is not an absolute path and doesn't include directories, place it in current directory
    if not os.path.isabs(export_path) and not os.path.dirname(export_path):
        export_path = os.path.join(os.getcwd(), export_path)
        if verbose:
            print(f"Using absolute export path: {export_path}")
    
    # Initialize snipper_paths if needed
    if source_directory:
        source_directory = os.path.abspath(source_directory)
        if verbose:
            print(f"Initializing from source directory: {source_directory}")
        snipper_paths = init_snipper_directory(source_directory)
        # Store the absolute directory path
        global source_directory_path
        source_directory_path = source_directory
    
    if 'snipper_paths' not in globals() or not snipper_paths:
        print("Error: No source directory specified and no previous processing detected.")
        return None
    
    if verbose:
        print(f"Looking for files in: {snipper_paths['base']}")
        print(f"Directory structure:")
        for root, dirs, files in os.walk(snipper_paths['base']):
            print(f"Dir: {root}")
            for f in files:
                print(f"  - {f}")
    
    # Initialize content sections
    snippets_content = ""
    summary_content = ""
    api_content = ""
    
    # Try to get snippets content
    final_combined_file = os.path.join(snipper_paths["final"], "final_combined.md")
    if os.path.exists(final_combined_file):
        try:
            with open(final_combined_file, "r", encoding="utf-8") as f:
                snippets_content = f.read()
            if verbose:
                print(f"Successfully read snippets from: {final_combined_file}")
        except Exception as e:
            print(f"Warning: Error reading combined snippets file: {e}")
    else:
        # Try to see if there are any batch files we can use
        batch_dir = snipper_paths.get("batches", "")
        if batch_dir and os.path.exists(batch_dir):
            batch_files = [f for f in os.listdir(batch_dir) if f.endswith(".md")]
            if batch_files:
                try:
                    # Use the most recent batch file
                    latest_batch = sorted(batch_files)[-1]
                    batch_path = os.path.join(batch_dir, latest_batch)
                    with open(batch_path, "r", encoding="utf-8") as f:
                        snippets_content = f.read()
                    if verbose:
                        print(f"Using batch file as fallback: {batch_path}")
                except Exception as e:
                    print(f"Warning: Error reading batch file: {e}")
        
        if not snippets_content:
            print(f"Warning: No snippets found at expected path: {final_combined_file}")
            if verbose:
                try:
                    final_dir = os.path.dirname(final_combined_file)
                    if os.path.exists(final_dir):
                        print(f"Contents of final directory: {os.listdir(final_dir)}")
                except Exception:
                    pass
    
    # Try to get summary content
    summary_file = snipper_paths.get("summary", "")
    if summary_file and os.path.exists(summary_file):
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                summary_content = f.read()
            if verbose:
                print(f"Successfully read summary from: {summary_file}")
        except Exception as e:
            print(f"Warning: Error reading summary file: {e}")
    
    # Include API credentials if requested
    if include_api_creds:
        api_creds_file = snipper_paths.get("api_creds", "")
        if api_creds_file and os.path.exists(api_creds_file):
            try:
                with open(api_creds_file, "r", encoding="utf-8") as f:
                    api_content = f.read()
                if api_content.strip() == "# API Credentials and Endpoints Found":
                    api_content = ""  # Empty or default content, don't include
                if verbose and api_content:
                    print(f"Successfully read API credentials from: {api_creds_file}")
            except Exception as e:
                print(f"Warning: Error reading API credentials file: {e}")
    
    # Create output content
    formatted_output = "# Exported Snippets\n\n"
    
    if snippets_content:
        formatted_output += snippets_content
    else:
        formatted_output += "No snippets were found. Please run processing first.\n\n"
    
    if summary_content:
        formatted_output += "\n\n## Project Summary\n\n" + summary_content
    
    if api_content:
        formatted_output += "\n\n## API Credentials and Endpoints\n\n" + api_content
    
    try:
        # Ensure the output directory exists
        output_dir = os.path.dirname(export_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Write the output file
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(formatted_output)
        print(f"Successfully exported snippet file to: {export_path}")
        
        return formatted_output
    except Exception as e:
        print(f"Error writing export file: {e}")
        print(f"Attempted to write to: {export_path}")
        return None

# =============================================================================
# Interactive CLI and Main entry point
# =============================================================================

def interactive_cli():
    """Interactive command-line interface for X.AI Cleaner."""
    print("\nWelcome to X.AI Cleaner Interactive CLI!")
    print("Ensure your XAI_API_KEY environment variable is set.")
    
    while True:
        print("\nChoose an option:")
        print("  1. Process a directory of code/snippet files")
        print("  2. Export snippets")
        print("  3. Exit")
        choice = input("Enter your choice (1/2/3): ").strip()
        if choice == "1":
            directory = input("Enter the full path to the directory: ").strip()
            mode = input("Enter the mode ('code' or 'snippet'): ").strip().lower()
            verbose_in = input("Enable verbose output? (y/n): ").strip().lower()
            verbose = verbose_in == "y"
            recursive_in = input("Process subdirectories recursively? (y/n): ").strip().lower()
            recursive = recursive_in == "y"
            output = input("Enter an output file name (default: final_combined.md): ").strip()
            if not output:
                output = "final_combined.md"
            process_directory(directory, mode, verbose, output, recursive)
        elif choice == "2":
            source_dir = input("Enter the source directory containing the .xsnippet folder: ").strip()
            if not source_dir:
                print("Source directory cannot be empty.")
                continue
            export_path = input("Enter the export file path (e.g., formatted_snippets.md): ").strip()
            if not export_path:
                print("Export path cannot be empty.")
                continue
            include_creds_input = input("Include API credentials in the export? (y/n): ").strip().lower()
            include_creds = include_creds_input == "y"
            export_formatted_snippetfile(export_path, source_directory=source_dir, include_api_creds=include_creds, verbose=True)
        elif choice == "3":
            print("Exiting X.AI Cleaner. Goodbye!")
            break
        else:
            print("Invalid choice, please try again.")

def main():
    parser = argparse.ArgumentParser(
        description="X.AI Cleaner: Process a directory of code/snippet files to extract, combine, and summarize important snippets.\n" +
                    "If no arguments are provided, an interactive CLI is launched."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--directory", help="Path to a directory to process for code/snippets")
    parser.add_argument("--mode", choices=["code", "snippet"], default="code",
                        help="Operation mode: 'code' for source code files or 'snippet' for pre-made snippet files (default: code)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--output", "-o", help="Output file path for the final combined snippets (default: final_combined.md)")
    parser.add_argument("--recursive", "-r", action="store_true", help="Recursively process subdirectories")
    parser.add_argument("--export", "-e", help="Export the snippets into a formatted snippet file")
    parser.add_argument("--include-creds", "-c", action="store_true", help="Include API credentials in the export")
    
    args = parser.parse_args()
    
    if not args.directory:
        interactive_cli()
    else:
        output_file = args.output if args.output else "final_combined.md"
        
        # If output_file is not absolute and contains no path separators, it's just a filename
        # In this case, make sure it will be created in the current directory
        if not os.path.isabs(output_file) and not os.path.dirname(output_file):
            if verbose:
                print(f"Output will be created as: {os.path.join(os.getcwd(), output_file)}")
        
        process_directory(args.directory, args.mode, args.verbose, output_file, recursive=args.recursive)
        if args.export:
            export_formatted_snippetfile(args.export, source_directory=args.directory, include_api_creds=args.include_creds, verbose=args.verbose)

if __name__ == "__main__":
    main()


#     ### POTENTIALLY USEFUL SNIPPETS - EVALUATE TO INCLUDE FOR NEW FUNCTIONALITY
# 
# def is_meaningful_code(text: str) -> bool:
#     """
#     Determine if a code snippet is meaningful enough to keep.
#     
#     Filters out:
#     - Empty or whitespace-only snippets
#     - Simple __init__ files
#     - Basic imports only
#     - Single-line assignments
#     - Common boilerplate
#     
#     Args:
#         text: Code snippet to analyze
#         
#     Returns:
#         True if the snippet is meaningful, False otherwise
#     """
#     # Remove empty or whitespace-only snippets
#     if not text.strip():
#         return False
#         
#     # Try to parse as Python code
#     try:
#         tree = ast.parse(text)
#         
#         # Count meaningful nodes (excluding imports, simple assignments, etc.)
#         meaningful_nodes = 0
#         total_nodes = 0
#         
#         for node in ast.walk(tree):
#             total_nodes += 1
#             
#             # Skip imports
#             if isinstance(node, (ast.Import, ast.ImportFrom)):
#                 continue
#                 
#             # Skip simple assignments (e.g., VERSION = "1.0.0")
#             if isinstance(node, ast.Assign) and len(node.targets) == 1:
#                 if isinstance(node.value, (ast.Str, ast.Num, ast.NameConstant)):
#                     continue
#             
#             # Skip empty __init__ files
#             if isinstance(node, ast.Module) and len(node.body) <= 2:
#                 if all(isinstance(n, (ast.Import, ast.ImportFrom)) for n in node.body):
#                     return False
#             
#             meaningful_nodes += 1
#         
#         # Require a minimum number of meaningful nodes
#         if meaningful_nodes < 3:
#             return False
#             
#         # Require a minimum ratio of meaningful to total nodes
#         if meaningful_nodes / total_nodes < 0.3:
#             return False
#             
#     except SyntaxError:
#         # If it's not valid Python, check for other meaningful patterns
#         lines = text.strip().split('\n')
#         
#         # Skip if too short
#         if len(lines) < 3:
#             return False
#             
#         # Skip if mostly imports or simple assignments
#         meaningful_lines = 0
#         for line in lines:
#             line = line.strip()
#             if not line:
#                 continue
#             if line.startswith(('import ', 'from ')):
#                 continue
#             if re.match(r'^[A-Z_]+\s*=\s*["\'].*["\']$', line):
#                 continue
#             meaningful_lines += 1
#         
#         if meaningful_lines < 3:
#             return False
#     
#     return True
# 
# def extract_code_snippets(file_path: Path) -> List[Tuple[str, str]]:
#     """
#     Extract meaningful code snippets from a file.
#     
#     Args:
#         file_path: Path to the file
#         
#     Returns:
#         List of (snippet_name, snippet_text) tuples
#     """
#     try:
#         with open(file_path, 'r', encoding='utf-8') as f:
#             content = f.read()
#     except Exception as e:
#         logger.error(f"Error reading {file_path}: {e}")
#         return []
#     
#     snippets = []
#     
#     # Try to parse as Python code
#     try:
#         tree = ast.parse(content)
#         
#         # Extract classes and functions
#         for node in ast.walk(tree):
#             if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
#                 snippet_text = ast.get_source_segment(content, node)
#                 if snippet_text and is_meaningful_code(snippet_text):
#                     snippet_name = f"{node.name}"
#                     snippets.append((snippet_name, snippet_text))
#                     
#     except SyntaxError:
#         # If not valid Python, try to extract blocks based on indentation
#         lines = content.split('\n')
#         current_block = []
#         current_indent = 0
#         
#         for line in lines:
#             if not line.strip():
#                 continue
#                 
#             indent = len(line) - len(line.lstrip())
#             
#             # Start of a new block
#             if not current_block or indent > current_indent:
#                 current_block.append(line)
#                 current_indent = indent
#             # End of current block
#             elif indent < current_indent:
#                 block_text = '\n'.join(current_block)
#                 if is_meaningful_code(block_text):
#                     # Try to extract a meaningful name from the first line
#                     first_line = current_block[0].strip()
#                     name_match = re.search(r'(?:def|class|function)\s+(\w+)', first_line)
#                     name = name_match.group(1) if name_match else "snippet"
#                     snippets.append((name, block_text))
#                 current_block = [line]
#                 current_indent = indent
#             # Continue current block
#             else:
#                 current_block.append(line)
#     
#     return snippets
# 
# def find_similar_snippets(directory: Path, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> Dict[str, List[Tuple[str, str, Path]]]:
#     """
#     Find groups of similar code snippets in a directory.
#     
#     Args:
#         directory: Directory to scan for snippets
#         similarity_threshold: Threshold for considering snippets similar
#         
#     Returns:
#         Dictionary mapping group IDs to lists of (name, text, source_file) tuples
#     """
#     # Get all Python and text files
#     all_files = []
#     for ext in ['.py', '.python', '.txt']:
#         all_files.extend(directory.glob(f"**/*{ext}"))
#     
#     logger.info(f"Found {len(all_files)} files to analyze in {directory}")
#     
#     # Extract snippets from all files
#     all_snippets = []
#     for file_path in all_files:
#         try:
#             snippets = extract_code_snippets(file_path)
#             for name, text in snippets:
#                 all_snippets.append((name, text, file_path))
#         except Exception as e:
#             logger.error(f"Error processing {file_path}: {e}")
#     
#     logger.info(f"Extracted {len(all_snippets)} meaningful code snippets")
#     
#     # Group similar snippets
#     similar_groups = {}
#     processed_snippets = set()
#     group_id = 0
#     
#     for i, (name1, text1, file1) in enumerate(all_snippets):
#         if i in processed_snippets:
#             continue
#             
#         # Start a new group
#         current_group = [(name1, text1, file1)]
#         processed_snippets.add(i)
#         
#         # Find similar snippets
#         for j, (name2, text2, file2) in enumerate(all_snippets):
#             if i == j or j in processed_snippets:
#                 continue
#                 
#             # Check similarity
#             similarity = calculate_similarity(text1, text2)
#             if similarity >= similarity_threshold:
#                 current_group.append((name2, text2, file2))
#                 processed_snippets.add(j)
#         
#         # Only add groups with multiple snippets
#         if len(current_group) > 1:
#             similar_groups[f"group_{group_id}"] = current_group
#             group_id += 1
#     
#     logger.info(f"Found {len(similar_groups)} groups of similar snippets")
#     return similar_groups
# 
# def merge_snippet_group(group: List[Tuple[str, str, Path]], output_dir: Path, 
#                        group_name: str) -> Tuple[Path, List[Path]]:
#     """
#     Merge a group of similar code snippets into a definitive version.
#     
#     Args:
#         group: List of (name, text, source_file) tuples for similar snippets
#         output_dir: Directory to save the merged snippet
#         group_name: Name of the snippet group
#         
#     Returns:
#         Tuple of (path to merged snippet, list of source files)
#     """
#     names = [n for n, _, _ in group]
#     texts = [t for _, t, _ in group]
#     files = [f for _, _, f in group]
#     
#     # Determine the best snippet to use as base
#     best_idx = select_best_snippet(names, texts)
#     best_name = names[best_idx]
#     best_text = texts[best_idx]
#     
#     # Create a prompt for the language model to merge the snippets
#     prompt = f"""
# I need to merge these {len(group)} similar code snippets into one optimized version.
# The snippets are different implementations or variations of similar functionality.
# 
# Here are the snippets:
# 
# {'-' * 40}
# BASE SNIPPET: {best_name}
# {'-' * 40}
# {best_text}
# {'-' * 40}
# 
# """
#     
#     # Add other snippets
#     for i, (name, text, _) in enumerate(group):
#         if i != best_idx:
#             prompt += f"""
# ALTERNATIVE VERSION: {name}
# {'-' * 40}
# {text}
# {'-' * 40}
# """
#     
#     prompt += """
# Create a merged version that:
# 1. Combines the best aspects of each implementation
# 2. Uses modern and efficient coding practices
# 3. Includes comprehensive error handling
# 4. Has clear documentation and type hints
# 5. Maintains compatibility with all use cases
# 6. Removes any redundant or unnecessary code
# 
# Return ONLY the final merged code. Do not include explanations or snippet names.
# """
#     
#     # Call the language model to merge the snippets
#     try:
#         # Create a basic function schema for text generation
#         merge_function_schema = {
#             "name": "merge_snippets",
#             "description": "Merge multiple code snippets into one optimized version",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "merged_code": {
#                         "type": "string",
#                         "description": "The merged and optimized code combining the best parts of all snippets"
#                     }
#                 },
#                 "required": ["merged_code"]
#             }
#         }
#         
#         # Call the API
#         result = call_xai_api(model=XAI_MODEL_TEXT, prompt=prompt, function_schema=merge_function_schema)
#         merged_text = result.get("merged_code", best_text)
#     except Exception as e:
#         logger.error(f"Error calling language model API: {e}")
#         merged_text = best_text
#         logger.info(f"Using best snippet as fallback due to API error")
#     
#     # Create a meaningful name for the merged file
#     timestamp = datetime.now().strftime("%Y%m%d")
#     output_file = output_dir / f"snippet_{clean_filename(best_name)}_{timestamp}.py"
#     output_file.parent.mkdir(parents=True, exist_ok=True)
#     
#     # Save the merged content
#     try:
#         with open(output_file, 'w', encoding='utf-8') as f:
#             f.write(merged_text)
#             
#         # Create an accompanying metadata file
#         meta_file = output_file.with_suffix('.meta.json')
#         import json
#         with open(meta_file, 'w', encoding='utf-8') as f:
#             json.dump({
#                 "name": best_name,
#                 "group_id": group_name,
#                 "source_files": [str(f) for f in files],
#                 "timestamp": datetime.now().isoformat(),
#                 "similarity_threshold": DEFAULT_SIMILARITY_THRESHOLD
#             }, f, indent=2)
#             
#         logger.info(f"Created merged snippet at {output_file}")
#     except Exception as e:
#         logger.error(f"Error saving merged snippet: {e}")
#         return None, files
#     
#     return output_file, files
# 
# def select_best_snippet(names: List[str], texts: List[str]) -> int:
#     """
#     Select the best snippet to use as a base for merging.
#     
#     Args:
#         names: List of snippet names
#         texts: List of snippet texts
#         
#     Returns:
#         Index of the best snippet
#     """
#     scores = []
#     
#     for i, (name, text) in enumerate(zip(names, texts)):
#         score = 0
#         
#         # Prefer longer snippets (more comprehensive)
#         score += len(text) / 100  # Length factor
#         
#         # Prefer snippets with docstrings
#         if '"""' in text or "'''" in text:
#             score += 10
#         
#         # Prefer snippets with type hints
#         if re.search(r':\s*[A-Z][A-Za-z]*[\[\],\s]*', text):
#             score += 5
#         
#         # Prefer snippets with error handling
#         if 'try:' in text:
#             score += 5
#         
#         # Prefer snippets with comments
#         score += 2 * len(re.findall(r'#.*$', text, re.MULTILINE))
#         
#         # Prefer descriptive names
#         score += len(name.split('_'))
#         
#         scores.append(score)
#     
#     # Return index of snippet with highest score
#     return scores.index(max(scores))
# 
# def merge_code_snippets(


#!/usr/bin/env python3
"""
Code documentation generator for CleanupX.

This module provides functionality to analyze code files
and generate comprehensive documentation.
"""
# 
# import os
# import re
# import logging
# from pathlib import Path
# from typing import Dict, List, Optional, Any, Tuple, Set
# 
# from cleanupx.utils.common import read_text_file, is_ignored_file
# 
# # Configure logging
# logger = logging.getLogger(__name__)
# 
# # Constants for supported languages
# LANGUAGE_INFO = {
#     ".py": {
#         "name": "Python",
#         "class_pattern": r"class\s+(\w+)(?:\(([^)]*)\))?:",
#         "function_pattern": r"def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^:]*))?\s*:",
#         "docstring_pattern": r'"""(.*?)"""',
#         "comment_pattern": r"#\s*(.*)",
#         "module_docstring_pattern": r'^"""(.*?)"""',
#         "multi_line_start": '"""',
#         "multi_line_end": '"""',
#         "import_pattern": r"(?:import|from)\s+([^;\n]+)",
#     },
#     ".js": {
#         "name": "JavaScript",
#         "class_pattern": r"class\s+(\w+)(?:\s+extends\s+([^\s{]+))?",
#         "function_pattern": r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:function|\([^)]*\)\s*=>))",
#         "docstring_pattern": r"/\*\*(.*?)\*/",
#         "comment_pattern": r"//\s*(.*)",
#         "module_docstring_pattern": r"^/\*\*(.*?)\*/",
#         "multi_line_start": "/*",
#         "multi_line_end": "*/",
#         "import_pattern": r"(?:import|require)\s*\(?\s*['\"]([^'\"]+)",
#     },
#     ".ts": {
#         "name": "TypeScript",
#         "class_pattern": r"class\s+(\w+)(?:\s+extends\s+([^\s{]+))?",
#         "function_pattern": r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:function|\([^)]*\)\s*=>)|(?:(\w+)\([^)]*\)\s*:\s*[^{]*)|(?:(\w+)\s*:\s*(?:Function|[^=;]*=>\s*[^=;]*)))",
#         "docstring_pattern": r"/\*\*(.*?)\*/",
#         "comment_pattern": r"//\s*(.*)",
#         "module_docstring_pattern": r"^/\*\*(.*?)\*/",
#         "multi_line_start": "/*",
#         "multi_line_end": "*/",
#         "import_pattern": r"(?:import|from)\s+['\"]([^'\"]+)",
#     },
#     ".java": {
#         "name": "Java",
#         "class_pattern": r"(?:public|private|protected)?\s*class\s+(\w+)(?:\s+extends\s+([^\s{]+))?",
#         "function_pattern": r"(?:public|private|protected)?\s*(?:static)?\s*(?:[\w<>[\],\s]+)\s+(\w+)\s*\(([^)]*)\)",
#         "docstring_pattern": r"/\*\*(.*?)\*/",
#         "comment_pattern": r"//\s*(.*)",
#         "module_docstring_pattern": r"^/\*\*(.*?)\*/",
#         "multi_line_start": "/*",
#         "multi_line_end": "*/",
#         "import_pattern": r"import\s+([^;\n]+)",
#     },
#     ".rb": {
#         "name": "Ruby",
#         "class_pattern": r"class\s+(\w+)(?:\s*<\s*([^\s]+))?",
#         "function_pattern": r"def\s+(\w+)(?:\(([^)]*)\))?",
#         "docstring_pattern": r"=begin(.*?)=end",
#         "comment_pattern": r"#\s*(.*)",
#         "module_docstring_pattern": r"^#\s*(.*)",
#         "multi_line_start": "=begin",
#         "multi_line_end": "=end",
#         "import_pattern": r"(?:require|include)\s+['\"]([^'\"]+)",
#     },
#     ".go": {
#         "name": "Go",
#         "class_pattern": r"type\s+(\w+)\s+struct",
#         "function_pattern": r"func\s+(?:\(([^)]*)\)\s*)?(\w+)\s*\(([^)]*)\)",
#         "docstring_pattern": r"/\*(.*?)\*/",
#         "comment_pattern": r"//\s*(.*)",
#         "module_docstring_pattern": r"^//\s*(.*)",
#         "multi_line_start": "/*",
#         "multi_line_end": "*/",
#         "import_pattern": r"import\s+(?:\([^)]*\)|['\"]([^'\"]+))",
#     },
#     ".cs": {
#         "name": "C#",
#         "class_pattern": r"(?:public|private|protected|internal)?\s*(?:static)?\s*class\s+(\w+)(?:\s*:\s*([^{]+))?",
#         "function_pattern": r"(?:public|private|protected|internal)?\s*(?:static)?\s*(?:[\w<>[\],\s]+)\s+(\w+)\s*\(([^)]*)\)",
#         "docstring_pattern": r"///\s*<summary>(.*?)</summary>",
#         "comment_pattern": r"//\s*(.*)",
#         "module_docstring_pattern": r"^///\s*<summary>(.*?)</summary>",
#         "multi_line_start": "/*",
#         "multi_line_end": "*/",
#         "import_pattern": r"using\s+([^;\n]+)",
#     },
# }
# 
# class CodeFile:
#     """Represents a code file with its parsed components."""
#     
#     def __init__(self, path: Path):
#         self.path = path
#         self.relative_path = path
#         self.language = ""
#         self.name = path.name
#         self.size = 0
#         self.content = ""
#         self.classes: List[Dict[str, Any]] = []
#         self.functions: List[Dict[str, Any]] = []
#         self.imports: List[str] = []
#         self.docstring = ""
#         self.comments: List[Dict[str, Any]] = []
#         self.loc = 0  # Lines of code
#         self.doc_coverage = 0.0  # Documentation coverage
#         
#     def load(self, root_dir: Path) -> bool:
#         """Load and parse the file."""
#         try:
#             self.relative_path = self.path.relative_to(root_dir)
#             self.size = self.path.stat().st_size
#             self.content = read_text_file(self.path)
#             self.loc = len(self.content.splitlines())
#             return True
#         except Exception as e:
#             logger.error(f"Error loading {self.path}: {e}")
#             return False
#     
#     def parse(self) -> bool:
#         """Parse the file contents based on language."""
#         suffix = self.path.suffix.lower()
#         if suffix not in LANGUAGE_INFO:
#             return False
#             
#         language_data = LANGUAGE_INFO[suffix]
#         self.language = language_data["name"]
#         
#         # Extract docstring
#         module_docstring_matches = re.search(language_data["module_docstring_pattern"], self.content, re.DOTALL)
#         if module_docstring_matches:
#             self.docstring = self._clean_docstring(module_docstring_matches.group(1))
#         
#         # Extract classes
#         class_matches = re.finditer(language_data["class_pattern"], self.content)
#         for match in class_matches:
#             class_name = match.group(1)
#             class_info = {
#                 "name": class_name,
#                 "docstring": self._extract_entity_docstring(match.start(), language_data),
#                 "line": self.content[:match.start()].count('\n') + 1,
#                 "methods": [],
#             }
#             
#             if len(match.groups()) > 1 and match.group(2):
#                 class_info["inherits"] = match.group(2).strip()
#                 
#             self.classes.append(class_info)
#         
#         # Extract functions/methods
#         function_matches = re.finditer(language_data["function_pattern"], self.content)
#         for match in class_matches:
#             # Determine function name (patterns may have multiple capture groups for function name)
#             function_name = None
#             for i in range(1, len(match.groups()) + 1):
#                 if match.group(i) and not function_name:
#                     function_name = match.group(i)
#             
#             if not function_name:
#                 continue
#                 
#             function_info = {
#                 "name": function_name,
#                 "docstring": self._extract_entity_docstring(match.start(), language_data),
#                 "line": self.content[:match.start()].count('\n') + 1,
#             }
#             
#             # Add parameter info if available
#             params_index = 2  # Most patterns have params in group 2
#             if len(match.groups()) >= params_index and match.group(params_index):
#                 function_info["parameters"] = match.group(params_index).strip()
#                 
#             self.functions.append(function_info)
#         
#         # Extract imports
#         import_matches = re.finditer(language_data["import_pattern"], self.content)
#         for match in import_matches:
#             import_stmt = match.group(1).strip() if match.group(1) else ""
#             if import_stmt:
#                 self.imports.append(import_stmt)
#         
#         # Extract comments
#         comment_matches = re.finditer(language_data["comment_pattern"], self.content, re.MULTILINE)
#         for match in comment_matches:
#             comment = match.group(1).strip()
#             if comment:
#                 self.comments.append({
#                     "text": comment,
#                     "line": self.content[:match.start()].count('\n') + 1
#                 })
#         
#         # Calculate doc coverage
#         self._calculate_doc_coverage()
#         
#         return True
#     
#     def _extract_entity_docstring(self, start_pos: int, language_data: Dict[str, str]) -> str:
#         """Extract docstring for a class or function."""
#         # Look for docstring after the entity definition
#         content_after = self.content[start_pos:]
#         docstring_match = re.search(language_data["docstring_pattern"], content_after, re.DOTALL)
#         
#         if docstring_match and docstring_match.start() < 50:  # Only consider docstrings close to the definition
#             return self._clean_docstring(docstring_match.group(1))
#             
#         # Look for docstring before the entity definition
#         content_before = self.content[:start_pos]
#         lines_before = content_before.splitlines()
#         if lines_before:
#             # Look at the line just before the entity
#             last_line = lines_before[-1].strip()
#             if last_line.startswith("///") or last_line.startswith("//") or last_line.startswith("#"):
#                 # Try to gather consecutive comment lines
#                 docstring_lines = []
#                 for i in range(len(lines_before) - 1, -1, -1):
#                     line = lines_before[i].strip()
#                     if line.startswith("///") or line.startswith("//") or line.startswith("#"):
#                         docstring_lines.insert(0, line.lstrip("#/").strip())
#                     else:
#                         break
#                 
#                 if docstring_lines:
#                     return "\n".join(docstring_lines)
#         
#         return ""
#     
#     def _clean_docstring(self, docstring: str) -> str:
#         """Clean up a docstring by removing extra whitespace and formatting."""
#         # Remove leading/trailing whitespace from each line
#         lines = [line.strip() for line in docstring.splitlines()]
#         
#         # Remove empty lines from the beginning and end
#         while lines and not lines[0]:
#             lines.pop(0)
#         while lines and not lines[-1]:
#             lines.pop()
#             
#         if not lines:
#             return ""
#             
#         # Determine the minimum indentation
#         indentation = min(len(line) - len(line.lstrip()) for line in lines if line)
#         
#         # Remove the common indentation from all lines
#         cleaned_lines = [line[indentation:] if line else line for line in lines]
#         
#         return "\n".join(cleaned_lines)
#     
#     def _calculate_doc_coverage(self) -> None:
#         """Calculate documentation coverage percentage."""
#         documentable_items = len(self.classes) + len(self.functions) + 1  # +1 for module docstring
#         documented_items = sum(1 for cls in self.classes if cls.get("docstring"))
#         documented_items += sum(1 for func in self.functions if func.get("docstring"))
#         documented_items += 1 if self.docstring else 0
#         
#         self.doc_coverage = (documented_items / documentable_items) * 100 if documentable_items > 0 else 0
# 
# class CodeDocumenter:
#     """Analyzes code files and generates documentation."""
#     
#     def __init__(self, directory: Path, output_path: Optional[Path] = None):
#         """
#         Initialize the code documenter.
#         
#         Args:
#             directory: Directory containing code files
#             output_path: Path to save documentation (defaults to directory/CODE_DOCS.md)
#         """
#         self.directory = Path(directory)
#         self.output_path = output_path or (self.directory / "CODE_DOCS.md")
#         self.code_files: List[CodeFile] = []
#         self.language_stats: Dict[str, int] = {}
#         self.total_loc = 0
#         self.dependencies: Dict[str, Set[str]] = {}  # Maps files to their imports
#         
#     def scan_directory(self, recursive: bool = True) -> int:
#         """
#         Scan directory for code files.
#         
#         Args:
#             recursive: Whether to scan subdirectories
#             
#         Returns:
#             Number of files scanned
#         """
#         logger.info(f"Scanning directory: {self.directory}")
#         
#         # Function to process a file
#         def process_file(file_path: Path) -> None:
#             if is_ignored_file(file_path):
#                 return
#                 
#             # Check if the file is a supported code file
#             if file_path.suffix.lower() in LANGUAGE_INFO:
#                 code_file = CodeFile(file_path)
#                 if code_file.load(self.directory) and code_file.parse():
#                     self.code_files.append(code_file)
#                     self.language_stats[code_file.language] = self.language_stats.get(code_file.language, 0) + 1
#                     self.total_loc += code_file.loc
#         
#         # Walk the directory structure
#         if recursive:
#             for root, dirs, files in os.walk(self.directory):
#                 # Skip ignored directories
#                 dirs[:] = [d for d in dirs if not is_ignored_file(Path(root) / d)]
#                 
#                 # Process each file
#                 for file in files:
#                     process_file(Path(root) / file)
#         else:
#             # Only process files in the root directory
#             for item in self.directory.iterdir():
#                 if item.is_file():
#                     process_file(item)
#         
#         logger.info(f"Scanned {len(self.code_files)} code files.")
#         return len(self.code_files)
#     
#     def build_dependency_graph(self) -> Dict[str, Set[str]]:
#         """
#         Build a graph of file dependencies based on imports.
#         
#         Returns:
#             Dictionary mapping file paths to sets of imported modules
#         """
#         # Build the dependency graph
#         for code_file in self.code_files:
#             file_path = str(code_file.relative_path)
#             self.dependencies[file_path] = set()
#             
#             # Add imports as dependencies
#             for import_stmt in code_file.imports:
#                 # Try to map the import to an actual file in the project
#                 potential_files = self._find_matching_files(import_stmt)
#                 for potential_file in potential_files:
#                     self.dependencies[file_path].add(str(potential_file.relative_path))
#         
#         return self.dependencies
#     
#     def _find_matching_files(self, import_stmt: str) -> List[CodeFile]:
#         """Find code files that match an import statement."""
#         matching_files = []
#         
#         # Remove quotes and common prefixes
#         import_stmt = import_stmt.strip('\'"')
#         
#         for code_file in self.code_files:
#             # Very basic matching - would need to be improved for a real implementation
#             file_path = str(code_file.relative_path)
#             module_name = str(code_file.path.stem)
#             
#             if import_stmt.endswith(module_name) or import_stmt == module_name:
#                 matching_files.append(code_file)
#         
#         return matching_files
#     
#     def generate_markdown_documentation(self) -> Path:
#         """
#         Generate markdown documentation for the code.
#         
#         Returns:
#             Path to the generated documentation file
#         """
#         logger.info(f"Generating documentation for {len(self.code_files)} files")
#         
#         # Calculate overall statistics
#         doc_files = [f for f in self.code_files if f.docstring]
#         doc_coverage = sum(f.doc_coverage for f in self.code_files) / len(self.code_files) if self.code_files else 0
#         
#         # Start the markdown content
#         content = f"# Code Documentation: {self.directory.name}\n\n"
#         content += "Automatically generated by CleanupX\n\n"
#         
#         # Add summary section
#         content += "## Summary\n\n"
#         content += f"- **Files:** {len(self.code_files)}\n"
#         content += f"- **Lines of Code:** {self.total_loc}\n"
#         content += f"- **Languages:** {', '.join(self.language_stats.keys())}\n"
#         content += f"- **Documentation Coverage:** {doc_coverage:.1f}%\n\n"
#         
#         # Add language breakdown
#         content += "### Language Breakdown\n\n"
#         content += "| Language | Files | % of Codebase |\n"
#         content += "|----------|-------|---------------|\n"
#         for language, count in self.language_stats.items():
#             percentage = (count / len(self.code_files)) * 100 if self.code_files else 0
#             content += f"| {language} | {count} | {percentage:.1f}% |\n"
#         content += "\n"
#         
#         # Add file listing
#         content += "## Files\n\n"
#         content += "| File | Language | Lines | Classes | Functions | Doc Coverage |\n"
#         content += "|------|----------|-------|---------|-----------|-------------|\n"
#         
#         # Sort files by relative path
#         sorted_files = sorted(self.code_files, key=lambda f: str(f.relative_path))
#         for code_file in sorted_files:
#             content += f"| [{code_file.relative_path}](#{self._create_anchor(str(code_file.relative_path))}) | {code_file.language} | {code_file.loc} | {len(code_file.classes)} | {len(code_file.functions)} | {code_file.doc_coverage:.1f}% |\n"
#         content += "\n"
#         
#         # Add detailed file documentation
#         content += "## File Details\n\n"
#         for code_file in sorted_files:
#             content += f"### {code_file.relative_path} {{{self._create_anchor(str(code_file.relative_path))}}}\n\n"
#             content += f"**Language:** {code_file.language}  \n"
#             content += f"**Lines:** {code_file.loc}  \n"
#             content += f"**Documentation Coverage:** {code_file.doc_coverage:.1f}%  \n\n"
#             
#             # Add module docstring if available
#             if code_file.docstring:
#                 content += "**Description:**\n\n"
#                 content += f"{code_file.docstring}\n\n"
#             
#             # Add dependencies
#             file_path = str(code_file.relative_path)
#             if file_path in self.dependencies and self.dependencies[file_path]:
#                 content += "**Dependencies:**\n\n"
#                 for dependency in sorted(self.dependencies[file_path]):
#                     content += f"- [{dependency}](#{self._create_anchor(dependency)})\n"
#                 content += "\n"
#             
#             # Add imports
#             if code_file.imports:
#                 content += "**Imports:**\n\n"
#                 for import_stmt in sorted(code_file.imports):
#                     content += f"- `{import_stmt}`\n"
#                 content += "\n"
#             
#             # Add classes
#             if code_file.classes:
#                 content += "**Classes:**\n\n"
#                 for cls in code_file.classes:
#                     content += f"#### {cls['name']}\n\n"
#                     if cls.get("inherits"):
#                         content += f"*Inherits from: {cls['inherits']}*\n\n"
#                     if cls.get("docstring"):
#                         content += f"{cls['docstring']}\n\n"
#                     content += f"*Defined at line {cls['line']}*\n\n"
#             
#             # Add functions
#             if code_file.functions:
#                 content += "**Functions:**\n\n"
#                 for func in code_file.functions:
#                     content += f"#### {func['name']}"
#                     if func.get("parameters"):
#                         content += f"({func['parameters']})"
#                     content += "\n\n"
#                     
#                     if func.get("docstring"):
#                         content += f"{func['docstring']}\n\n"
#                     content += f"*Defined at line {func['line']}*\n\n"
#             
#             # Add a divider between files
#             content += "---\n\n"
#         
#         # Write the content to the output file
#         with open(self.output_path, 'w', encoding='utf-8') as f:
#             f.write(content)
#             
#         logger.info(f"Documentation generated at {self.output_path}")
#         return self.output_path
#     
#     def _create_anchor(self, text: str) -> str:
#         """Create a GitHub-compatible markdown anchor."""
#         # Convert to lowercase, replace spaces with hyphens, remove non-alphanumeric chars
#         anchor = text.lower().replace(' ', '-')
#         anchor = re.sub(r'[^\w\-]', '', anchor)
#         return anchor
# 
# def generate_code_documentation(directory: Path, output_path: Optional[Path] = None) -> Path:
#     """
#     Generate comprehensive documentation for code in a directory.
#     
#     Args:
#         directory: Directory containing code files
#         output_path: Path to save documentation (defaults to directory/CODE_DOCS.md)
#         
#     Returns:
#         Path to the generated documentation file
#     """
#     documenter = CodeDocumenter(directory, output_path)
#     documenter.scan_directory(recursive=True)
#     documenter.build_dependency_graph()
#     return documenter.generate_markdown_documentation() 