#!/usr/bin/env python3
"""
Ollama Cleaner (osnipper.py)

This script processes a directory of code (or snippet) files and uses the local Ollama API
to extract and synthesize the most important and unique code snippets. It is an adaptation
of X.AI Cleaner (@xsnipper.py), tailored to use a local Ollama instance with model 'llama3.2:3b'.

Usage examples:
  python osnipper.py --directory /path/to/code --mode code --verbose --output final_combined.md
  python osnipper.py --directory /path/to/snippets --mode snippet --verbose
"""

import os
import sys
import argparse
import time
import json
import requests
from functools import wraps
from dotenv import load_dotenv

# Load environment variables from .env (if available)
load_dotenv()

# Constants and configuration for local Ollama
DEFAULT_MODEL_OLLAMA = "llama3.2:3b"
OLLAMA_API_BASE_URL = "http://localhost:11434/api"   # Local Ollama API endpoint
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Logger for consistent logging output
class Logger:
    """Simple logger for standardized output formatting."""
    @staticmethod
    def info(message: str) -> None:
        print(f"[INFO] {message}")

    @staticmethod
    def warning(message: str) -> None:
        print(f"[WARNING] {message}", file=sys.stderr)

    @staticmethod
    def error(message: str) -> None:
        print(f"[ERROR] {message}", file=sys.stderr)

    @staticmethod
    def debug(message: str) -> None:
        if os.getenv("DEBUG", "").lower() in ("1", "true", "yes"):
            print(f"[DEBUG] {message}")

logger = Logger()

# Decorator to retry API calls with exponential backoff
def retry_with_backoff(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        retries = 0
        while retries < MAX_RETRIES:
            try:
                return func(*args, **kwargs)
            except requests.RequestException as e:
                retries += 1
                if retries >= MAX_RETRIES:
                    logger.error(f"Max retries reached. Error: {e}")
                    raise
                sleep_time = RETRY_DELAY * (2 ** (retries - 1))
                logger.warning(f"API call failed: {e}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
        return func(*args, **kwargs)
    return wrapper

class OllamaClient:
    """
    Client for interacting with the local Ollama API.
    
    This client sends chat completion requests to the Ollama API, using the default model
    'llama3.2:3b' if no other model is specified.
    """
    def __init__(self, model: str = DEFAULT_MODEL_OLLAMA) -> None:
        self.model = model
        self.base_url = OLLAMA_API_BASE_URL
        self.session = requests.Session()
        # Local Ollama typically requires JSON content-type; authentication is omitted.
        self.session.headers.update({
            "Content-Type": "application/json"
        })
    
    @retry_with_backoff
    def chat(self, messages: list, model: str = None, temperature: float = 0.3) -> dict:
        """
        Send a chat completion request to the local Ollama API.
        
        Args:
            messages: List of message objects with 'role' and 'content'.
            model: Optional model to use (defaults to self.model).
            temperature: Sampling temperature (default: 0.3).
        
        Returns:
            Parsed JSON response from the API.
        
        Raises:
            requests.RequestException if the request fails after retries.
        """
        model_to_use = model if model is not None else self.model
        url = f"{self.base_url}/chat"
        payload = {
            "model": model_to_use,
            "messages": messages,
            "temperature": temperature,
            "stream": False,   # Single response mode (no streaming)
            "format": "json"   # Ensure JSON formatted response
        }
        logger.debug(f"Sending request to {url} with payload: {payload}")
        response = self.session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

def get_ollama_client() -> OllamaClient:
    """
    Initialize and return an OllamaClient instance.
    
    Returns:
        Instance of OllamaClient.
    """
    try:
        return OllamaClient()
    except Exception as e:
        logger.error(f"Failed to initialize Ollama client: {e}")
        sys.exit(1)

def analyze_code_snippet(code: str, context: str = None, model: str = None) -> dict:
    """
    Analyze a code snippet to extract its important parts using the Ollama API.
    
    Constructs a prompt with the provided code and optional context, then sends it to the API.
    
    Args:
        code: The code snippet to analyze.
        context: Optional context information (e.g. filename, purpose).
        model: Optional model name (defaults to 'llama3.2:3b').
    
    Returns:
        A dictionary containing:
            - success: Boolean indicating success.
            - result: Extracted snippet results.
            - raw_response: The API response (if any).
    """
    client = get_ollama_client()
    context_str = f"\nContext: {context}" if context else ""
    prompt = (
        f"Extract the most important and unique code snippets or documentation segments "
        f"from the following code.{context_str}\n\n"
        f"Format your response as:\n\n"
        f"Best Version:\n<best snippet>\n\n"
        f"Alternatives:\n<alternative snippet(s)>\n\n"
        f"Code:\n{code}"
    )
    messages = [{"role": "system", "content": prompt}]
    try:
        response = client.chat(messages, model=model)
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {
            "success": True,
            "result": content,
            "raw_response": response
        }
    except Exception as e:
        logger.error(f"Error analyzing code snippet: {e}")
        return {
            "success": False,
            "error": str(e),
            "result": ""
        }

def process_directory(directory: str, mode: str, verbose: bool, output: str, recursive: bool) -> None:
    """
    Process the directory of files, analyze each file's code/snippets, and generate a final output.
    This is a simplified placeholder implementation.
    
    Args:
        directory: Path to the directory to process.
        mode: Either 'code' or 'snippet'.
        verbose: Enable verbose output.
        output: Path to the output file.
        recursive: Whether to process subdirectories recursively.
    """
    if verbose:
        logger.info(f"Processing directory '{directory}' with mode '{mode}' (Recursive: {recursive})")
    
    # List all files within the directory (filtering can be added as needed)
    file_list = []
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                file_list.append(os.path.join(root, file))
    else:
        file_list = [os.path.join(directory, f) for f in os.listdir(directory)
                     if os.path.isfile(os.path.join(directory, f))]
    
    combined_results = []
    for file_path in file_list:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            analysis = analyze_code_snippet(code, context=file_path)
            if analysis.get("success"):
                combined_results.append(f"## {os.path.basename(file_path)}\n{analysis.get('result')}")
            elif verbose:
                logger.warning(f"Analysis failed for {file_path}")
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    final_output = "\n\n---\n\n".join(combined_results)
    try:
        with open(output, "w", encoding="utf-8") as f:
            f.write(final_output)
        logger.info(f"Final output written to {output}")
    except Exception as e:
        logger.error(f"Error writing output file: {e}")

def interactive_cli() -> None:
    """
    Interactive command-line interface for Ollama Cleaner.
    """
    print("\nWelcome to Ollama Cleaner Interactive CLI!")
    directory = input("Enter the full path to the directory: ").strip()
    mode = input("Enter the mode ('code' or 'snippet'): ").strip().lower()
    verbose = input("Enable verbose output? (y/n): ").strip().lower() == "y"
    recursive = input("Process subdirectories recursively? (y/n): ").strip().lower() == "y"
    output = input("Enter an output file name (default: final_combined.md): ").strip() or "final_combined.md"
    process_directory(directory, mode, verbose, output, recursive)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ollama Cleaner: Process a directory of code/snippet files using the local Ollama API."
    )
    parser.add_argument("--directory", help="Path to a directory to process for code/snippets")
    parser.add_argument("--mode", choices=["code", "snippet"], default="code", help="Processing mode (default: code)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--output", "-o", default="final_combined.md", help="Output file name (default: final_combined.md)")
    parser.add_argument("--recursive", "-r", action="store_true", help="Process subdirectories recursively")
    
    args = parser.parse_args()
    
    if not args.directory:
        interactive_cli()
    else:
        process_directory(args.directory, args.mode, args.verbose, args.output, args.recursive)

if __name__ == "__main__":
    main()