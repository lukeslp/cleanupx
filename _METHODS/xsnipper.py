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
    
    processed_dir = os.path.join(base_dir, "xsnippet_processed")
    if not os.path.isdir(processed_dir):
        os.makedirs(processed_dir)
    
    return {"base": base_dir, "log": log_file, "summary": summary_file, "snippets": snippets_file, "archive": archive_dir, "batches": batches_dir, "final": final_dir, "processed": processed_dir}

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

def process_file_for_snippets(file_path, mode, verbose=False):
    """
    For the given file, use the X.AI API to extract important snippet(s) by processing in batches.
    Return a dict with keys "best" and "alternatives".
    """
    content = read_file(file_path)
    if verbose:
        print(f"Processing file for snippet extraction: {file_path}")
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
                print(f"Batch {batch_index + 1} results written to {batch_output_file}")
                
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
        if verbose:
            print(f"Final document written to {final_output_file}")
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
            print(f"Project summary written to {snipper_paths['summary']}")
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
            export_path = input("Enter the export file path (e.g., formatted_snippets.md): ").strip()
            if export_path:
                export_formatted_snippetfile(export_path, verbose=True)
            else:
                print("Export path cannot be empty.")
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
    
    args = parser.parse_args()
    
    if not args.directory:
        interactive_cli()
    else:
        output_file = args.output if args.output else "final_combined.md"
        process_directory(args.directory, args.mode, args.verbose, output_file, recursive=args.recursive)
        if args.export:
            export_formatted_snippetfile(args.export, verbose=args.verbose)

if __name__ == "__main__":
    main()