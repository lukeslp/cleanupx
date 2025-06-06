"""
File Purpose: Comprehensive cleanup module for CleanupX with AI-powered processing
Primary Functions/Classes: 
- CleanupProcessor: Main class for all cleanup operations
- XAIIntegration: AI-powered analysis and processing
- ImageProcessor: Alt text generation for images
- FilenameScrambler: Filename randomization utilities
- cleanup_directory: Main entry point for directory processing

Inputs and Outputs (I/O):
- Input: Directory paths, configuration options, processing flags
- Output: Processed files, metadata, analysis reports, renamed files

This module handles comprehensive file cleanup operations including:
- File organization and deduplication
- AI-powered code analysis and snippet extraction
- Image alt text generation using X.AI Vision API
- Filename scrambling for privacy
- Citation processing and metadata extraction
- Smart merging and consolidation

MIT License by Luke Steuber, lukesteuber.com, assisted.site
luke@lukesteuber.com; bluesky @lukesteuber.com
linkedin https://www.linkedin.com/in/lukesteuber/
"""

import os
import sys
import json
import re
import time
import random
import string
import base64
import gc
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Union, Optional, List, Tuple
from functools import wraps
from dotenv import load_dotenv
import inquirer
from rich.console import Console
from rich.progress import Progress

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Rich console
console = Console()

# Constants and configuration
DEFAULT_MODEL_TEXT = "grok-3-mini-latest"
DEFAULT_MODEL_VISION = "grok-2-vision-latest"
API_BASE_URL = "https://api.x.ai/v1"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
MAX_FILE_SIZE_MB = 20
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif'}
CACHE_FILE = "alt_text_cache.json"

# Import existing utilities (if they exist)
try:
    from .config import DEFAULT_EXTENSIONS, PROTECTED_PATTERNS
    from .utils import (
        get_file_metadata,
        is_protected_file,
        normalize_path,
        ensure_metadata_dir
    )
    from .organization import organize_files
    from .citations import process_citations
    from .snippets import process_snippets
except ImportError:
    # Fallback definitions if modules don't exist
    DEFAULT_EXTENSIONS = {'.py', '.js', '.html', '.css', '.md', '.txt'}
    PROTECTED_PATTERNS = ['.git', '__pycache__', 'node_modules']
    
    def get_file_metadata(file_path):
        """Fallback metadata function."""
        return {'size': os.path.getsize(file_path), 'modified': os.path.getmtime(file_path)}
    
    def is_protected_file(file_path):
        """Fallback protection check."""
        return any(pattern in str(file_path) for pattern in PROTECTED_PATTERNS)
    
    def normalize_path(path):
        """Fallback path normalization."""
        return Path(path).resolve()
    
    def ensure_metadata_dir(directory):
        """Fallback metadata directory creation."""
        metadata_dir = Path(directory) / '.cleanupx'
        metadata_dir.mkdir(exist_ok=True)
        return metadata_dir
    
    def organize_files(directory, **kwargs):
        """Fallback organization function."""
        return {'stats': {'organized_files': 0}}
    
    def process_citations(directory, **kwargs):
        """Fallback citation processing."""
        return {'stats': {'total_citations': 0}}
    
    def process_snippets(directory, **kwargs):
        """Fallback snippet processing."""
        return {'stats': {'total_snippets': 0}}

# Decorator for API retry logic
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
        return func(*args, **kwargs)
    return wrapper

class XAIIntegration:
    """
    Unified X.AI API integration for AI-powered processing.
    
    Provides methods for:
    - Code analysis and snippet extraction
    - Duplicate detection and consolidation
    - Content synthesis and merging
    - Image analysis and alt text generation
    """
    
    def __init__(self, api_key=None):
        """Initialize XAI client with API credentials."""
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        if not self.api_key:
            logger.error("X.AI API key not found. Set XAI_API_KEY environment variable.")
            self.client = None
            return
        
        self.base_url = API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        self.client = self
        
    def is_available(self):
        """Check if XAI client is available."""
        return self.client is not None
    
    @retry_with_backoff
    def chat(self, messages, model=DEFAULT_MODEL_TEXT, temperature=0.3, functions=None, response_format=None):
        """Send a chat completion request to the X.AI API."""
        if not self.is_available():
            raise ValueError("XAI client not available")
            
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if response_format:
            payload["response_format"] = response_format
        
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
        """Extract function call result from API response."""
        try:
            message = response["choices"][0]["message"]
            
            if "tool_calls" in message and message["tool_calls"]:
                tool_call = message["tool_calls"][0]
                if tool_call["type"] == "function":
                    function_args = json.loads(tool_call["function"]["arguments"])
                    return function_args
            
            content = message.get("content", "")
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            return {"content": content}
            
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Error extracting tool result: {e}")
            return {}
    
    def analyze_code_snippet(self, code, context=None, model=DEFAULT_MODEL_TEXT):
        """Analyze a code snippet to extract its important parts."""
        if not self.is_available():
            return {"error": "XAI client not available"}
        
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
            response = self.chat(messages, model=model)
            content = response["choices"][0]["message"]["content"]
            
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
    
    def find_duplicates(self, files, threshold=0.7, model=DEFAULT_MODEL_TEXT):
        """Use X.AI to identify duplicate content across multiple files."""
        if not self.is_available():
            return {"error": "XAI client not available"}
        
        file_content = ""
        for filename, content in files.items():
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
            response = self.chat(messages, model=model, functions=[function_schema])
            result = self.extract_tool_result(response)
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

class ImageProcessor:
    """
    Image processing functionality for alt text generation and analysis.
    
    Uses X.AI Vision API to generate comprehensive alt text for images
    and create markdown documentation files.
    """
    
    def __init__(self, xai_client):
        """Initialize with XAI client."""
        self.xai_client = xai_client
        self.cache = self.load_cache()
        self.prompt_text = (
            "You are an AI specializing in describing images for accessibility purposes. "
            "Write comprehensive alt text for this image, as though for a blind engineer who needs "
            "to understand every detail of the information including text. "
            "Also suggest a descriptive filename based on the content of the image. "
            "Format your response in this exact JSON structure:\n"
            "{\n"
            "  \"description\": \"Detailed description of the image\",\n"
            "  \"alt_text\": \"Concise alt text for the image\",\n"
            "  \"suggested_filename\": \"descriptive_filename_without_extension\",\n"
            "  \"tags\": [\"tag1\", \"tag2\", ...]\n"
            "}"
        )
    
    def load_cache(self):
        """Load the alt text cache if it exists."""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as fp:
                    return json.load(fp)
            except:
                return {}
        return {}
    
    def save_cache(self):
        """Save the alt text cache to file."""
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as fp:
                json.dump(self.cache, fp, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def encode_image(self, image_path):
        """Encode an image file as base64 for API transmission."""
        try:
            with open(image_path, "rb") as image_file:
                image_bytes = image_file.read()
                return base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image {image_path}: {e}")
            return None
    
    def generate_alt_text(self, image_path):
        """Generate alt text for an image using X.AI Vision API."""
        if not self.xai_client or not self.xai_client.is_available():
            return None
            
        try:
            # Check file size
            file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                logger.warning(f"Image too large ({file_size_mb:.1f} MB > {MAX_FILE_SIZE_MB} MB): {image_path}")
                return None
            
            # Encode the image
            base64_image = self.encode_image(image_path)
            if not base64_image:
                return None
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        },
                        {
                            "type": "text",
                            "text": self.prompt_text
                        }
                    ]
                }
            ]
            
            response = self.xai_client.chat(
                messages,
                model=DEFAULT_MODEL_VISION,
                temperature=0.01,
                response_format={"type": "json_object"}
            )
            
            generated_text = response["choices"][0]["message"]["content"].strip()
            
            try:
                result = json.loads(generated_text)
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {e}")
                # Try to extract JSON if embedded
                json_match = re.search(r'{[\s\S]*}', generated_text)
                if json_match:
                    try:
                        result = json.loads(json_match.group(0))
                        return result
                    except:
                        pass
                return None
            
        except Exception as e:
            logger.error(f"Error generating alt text for {image_path}: {e}")
            return None
        finally:
            gc.collect()
    
    def get_cache_key(self, file_path):
        """Create a unique cache key for an image file."""
        stats = os.stat(file_path)
        mod_time = stats.st_mtime
        return f"{file_path}:{mod_time}"
    
    def create_markdown_file(self, image_path, description):
        """Create a markdown file with alt text information."""
        image_path = Path(image_path)
        base_name = image_path.stem
        directory = image_path.parent
        md_file_path = directory / f"{base_name}.md"
        
        content = [
            f"# {base_name}",
            "",
            f"**Description:** {description.get('description', 'No description available')}",
            "",
            f"**Alt Text:** {description.get('alt_text', 'No alt text available')}",
            "",
            "## Metadata",
            f"- **Original Filename:** {image_path.name}",
            "",
            "## Tags",
        ]
        
        tags = description.get('tags', [])
        if tags and isinstance(tags, list):
            for tag in tags:
                content.append(f"- {tag}")
        else:
            content.append("- No tags available")
        
        try:
            with open(md_file_path, "w", encoding="utf-8") as fp:
                fp.write('\n'.join(content))
            return md_file_path
        except Exception as e:
            logger.error(f"Error creating markdown file: {e}")
            return None
    
    def process_image(self, image_path, force=False, rename=False):
        """Process a single image file."""
        image_path = Path(image_path)
        cache_key = self.get_cache_key(str(image_path))
        
        # Check cache
        if cache_key in self.cache and not force:
            logger.info(f"Found cached alt text for {image_path}")
            description = self.cache[cache_key]
        else:
            logger.info(f"Generating alt text for {image_path}...")
            description = self.generate_alt_text(image_path)
            
            if not description:
                return False, f"Failed to generate alt text for {image_path}", image_path
            
            self.cache[cache_key] = description
            self.save_cache()
        
        current_image_path = image_path
        
        # Rename if requested
        if rename and description:
            new_filename = self.generate_new_filename(image_path, description)
            renamed_path = self.rename_file(image_path, new_filename)
            if renamed_path:
                current_image_path = renamed_path
        
        # Create markdown file
        md_file_path = self.create_markdown_file(current_image_path, description)
        
        return True, f"Created {md_file_path}", current_image_path
    
    def clean_filename(self, filename):
        """Clean a filename to be safe for file systems."""
        forbidden_chars = r'[<>:"/\\|?*]'
        cleaned = re.sub(forbidden_chars, '_', filename)
        cleaned = re.sub(r'[\s_]+', '_', cleaned)
        cleaned = cleaned.strip('. ')
        
        if len(cleaned) > 255:
            cleaned = cleaned[:255]
        
        return cleaned
    
    def generate_new_filename(self, file_path, description):
        """Generate a new filename based on image description."""
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        
        if description and isinstance(description, dict):
            suggested_name = description.get("suggested_filename")
            if suggested_name and isinstance(suggested_name, str):
                base_name = self.clean_filename(suggested_name)
            else:
                base_name = self.clean_filename(file_path.stem)
        else:
            base_name = self.clean_filename(file_path.stem)
        
        return f"{base_name}{ext}"
    
    def rename_file(self, original_path, new_name):
        """Rename a file with a new name."""
        original_path = Path(original_path)
        new_path = original_path.parent / new_name
        
        if original_path.name == new_name:
            return original_path
        
        if new_path.exists():
            base_name = new_path.stem
            ext = new_path.suffix
            counter = 1
            while new_path.exists():
                new_path = original_path.parent / f"{base_name}_{counter}{ext}"
                counter += 1
        
        try:
            os.rename(original_path, new_path)
            logger.info(f"Renamed: {original_path} -> {new_path}")
            return new_path
        except Exception as e:
            logger.error(f"Error renaming file {original_path}: {e}")
            return None

class FilenameScrambler:
    """
    Filename scrambling functionality for privacy and testing.
    
    Provides methods to randomize filenames while preserving extensions
    and maintaining rename logs for reversal.
    """
    
    def __init__(self):
        """Initialize the scrambler."""
        pass
    
    def scramble_directory(self, directory_path=None, interactive=True):
        """Scramble filenames in a directory."""
        if interactive and not directory_path:
            questions = [
                inquirer.Path(
                    'directory',
                    message="Select directory to scramble filenames",
                    path_type=inquirer.Path.DIRECTORY,
                    exists=True
                ),
                inquirer.Confirm(
                    'confirm',
                    message="This will rename ALL files in the directory. Continue?",
                    default=False
                )
            ]
            
            answers = inquirer.prompt(questions)
            
            if not answers or not answers['confirm']:
                console.print("[yellow]Operation cancelled.[/yellow]")
                return {"success": False, "message": "Operation cancelled"}
            
            directory_path = answers['directory']
        
        if not directory_path:
            return {"success": False, "message": "No directory specified"}
        
        target_dir = Path(directory_path)
        if not target_dir.exists() or not target_dir.is_dir():
            return {"success": False, "message": f"Invalid directory: {directory_path}"}
        
        files = list(target_dir.glob('*'))
        files = [f for f in files if f.is_file()]
        
        if not files:
            console.print("[yellow]No files found in directory.[/yellow]")
            return {"success": False, "message": "No files found"}
        
        console.print(f"[cyan]Found {len(files)} files to rename in {target_dir}[/cyan]")
        
        rename_log = []
        
        with Progress() as progress:
            task = progress.add_task("[green]Scrambling filenames...", total=len(files))
            
            for file_path in files:
                random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                new_name = f"{random_name}{file_path.suffix}"
                new_path = file_path.parent / new_name
                
                # Handle name collisions
                while new_path.exists():
                    random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                    new_name = f"{random_name}{file_path.suffix}"
                    new_path = file_path.parent / new_name
                
                try:
                    file_path.rename(new_path)
                    rename_log.append((str(file_path), str(new_path)))
                    console.print(f"Renamed: {file_path.name} → {new_name}")
                except Exception as e:
                    console.print(f"[bold red]Error renaming {file_path.name}: {e}[/bold red]")
                
                progress.update(task, advance=1)
        
        # Save rename log
        log_path = target_dir / "scramble_rename_log.txt"
        try:
            with open(log_path, 'w') as f:
                f.write("Original Name,New Name\n")
                for original, new in rename_log:
                    f.write(f"{original},{new}\n")
            console.print(f"[green]Rename log saved to {log_path}[/green]")
        except Exception as e:
            console.print(f"[bold red]Error saving rename log: {e}[/bold red]")
        
        console.print(f"[green]Successfully scrambled {len(rename_log)} filenames![/green]")
        
        return {
            "success": True,
            "message": f"Scrambled {len(rename_log)} files",
            "renamed_count": len(rename_log),
            "log_file": str(log_path)
        }

class CleanupProcessor:
    """
    Main cleanup processor that integrates all functionality.
    
    Coordinates file organization, AI analysis, image processing,
    and other cleanup operations in a unified workflow.
    """
    
    def __init__(self, api_key=None):
        """Initialize the cleanup processor with all sub-components."""
        self.xai_client = XAIIntegration(api_key)
        self.image_processor = ImageProcessor(self.xai_client)
        self.filename_scrambler = FilenameScrambler()
        
        logger.info(f"CleanupProcessor initialized - XAI available: {self.xai_client.is_available()}")
    
    def scan_directory(self, directory, recursive=False):
        """Scan directory for different file types."""
        directory = Path(directory)
        
        files = {
            'images': [],
            'code': [],
            'documents': [],
            'other': []
        }
        
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        for file_path in directory.glob(pattern):
            if not file_path.is_file() or is_protected_file(file_path):
                continue
            
            suffix = file_path.suffix.lower()
            
            if suffix in IMAGE_EXTENSIONS:
                files['images'].append(file_path)
            elif suffix in {'.py', '.js', '.html', '.css', '.md', '.txt', '.json', '.yaml', '.yml'}:
                files['code'].append(file_path)
            elif suffix in {'.pdf', '.doc', '.docx', '.rtf'}:
                files['documents'].append(file_path)
            else:
                files['other'].append(file_path)
        
        return files
    
    def process_images(self, image_files, force=False, rename=False):
        """Process all image files for alt text generation."""
        if not image_files:
            return {"success": True, "processed": 0}
        
        logger.info(f"Processing {len(image_files)} image files...")
        results = {
            "success": True,
            "processed": 0,
            "failed": 0,
            "renamed": 0,
            "details": []
        }
        
        for image_path in image_files:
            success, message, new_path = self.image_processor.process_image(
                image_path, force=force, rename=rename
            )
            
            if success:
                results["processed"] += 1
                if new_path != image_path:
                    results["renamed"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "file": str(image_path),
                "success": success,
                "message": message,
                "new_path": str(new_path) if new_path != image_path else None
            })
            
            # Brief pause to avoid rate limits
            time.sleep(0.5)
        
        return results
    
    def analyze_code_files(self, code_files):
        """Analyze code files for snippets and duplicates."""
        if not code_files or not self.xai_client.is_available():
            return {"success": False, "message": "No files or XAI not available"}
        
        logger.info(f"Analyzing {len(code_files)} code files...")
        
        # Read file contents
        file_contents = {}
        for file_path in code_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if len(content.strip()) > 0:  # Skip empty files
                        file_contents[str(file_path)] = content
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
        
        if not file_contents:
            return {"success": False, "message": "No readable code files found"}
        
        # Find duplicates
        duplicate_results = self.xai_client.find_duplicates(file_contents)
        
        # Analyze individual snippets
        snippet_results = {}
        for file_path, content in file_contents.items():
            if len(content) > 100:  # Only analyze substantial files
                analysis = self.xai_client.analyze_code_snippet(
                    content, 
                    context=f"File: {Path(file_path).name}"
                )
                snippet_results[file_path] = analysis
        
        return {
            "success": True,
            "duplicates": duplicate_results,
            "snippets": snippet_results,
            "total_files": len(file_contents)
        }

def cleanup_directory(
    directory: Union[str, Path],
    recursive: bool = False,
    max_size: Optional[int] = None,
    extract_citations: bool = True,
    extract_snippets: bool = True,
    organize: bool = True,
    process_images: bool = True,
    scramble_filenames: bool = False,
    ai_analysis: bool = True,
    dry_run: bool = False,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Comprehensive directory cleanup with all integrated functionality.
    
    Args:
        directory: Directory to process
        recursive: Whether to process subdirectories
        max_size: Maximum file size in MB to process
        extract_citations: Whether to extract citations
        extract_snippets: Whether to extract code snippets
        organize: Whether to organize files by type
        process_images: Whether to generate alt text for images
        scramble_filenames: Whether to scramble filenames for privacy
        ai_analysis: Whether to use AI for code analysis
        dry_run: Whether to simulate cleanup
        api_key: Optional XAI API key override
        
    Returns:
        Comprehensive cleanup results
    """
    try:
        directory = normalize_path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        # Initialize processor
        processor = CleanupProcessor(api_key)
        
        # Initialize results
        results = {
            'processed': [],
            'skipped': [],
            'errors': [],
            'stats': {
                'total_files': 0,
                'processed_files': 0,
                'skipped_files': 0,
                'error_files': 0,
                'images_processed': 0,
                'images_renamed': 0,
                'files_scrambled': 0
            },
            'citations': {},
            'snippets': {},
            'organization': {},
            'images': {},
            'ai_analysis': {},
            'scrambling': {}
        }
        
        # Scan directory for file types
        logger.info("Scanning directory for files...")
        file_scan = processor.scan_directory(directory, recursive)
        
        total_files = sum(len(files) for files in file_scan.values())
        results['stats']['total_files'] = total_files
        
        logger.info(f"Found {total_files} files: "
                   f"{len(file_scan['images'])} images, "
                   f"{len(file_scan['code'])} code files, "
                   f"{len(file_scan['documents'])} documents, "
                   f"{len(file_scan['other'])} other files")
        
        # Process images if requested
        if process_images and file_scan['images']:
            logger.info("Processing images for alt text generation...")
            if not dry_run:
                image_results = processor.process_images(
                    file_scan['images'], 
                    force=False, 
                    rename=False
                )
                results['images'] = image_results
                results['stats']['images_processed'] = image_results.get('processed', 0)
                results['stats']['images_renamed'] = image_results.get('renamed', 0)
            else:
                logger.info(f"DRY RUN: Would process {len(file_scan['images'])} images")
        
        # AI analysis of code files
        if ai_analysis and file_scan['code'] and processor.xai_client.is_available():
            logger.info("Performing AI analysis of code files...")
            if not dry_run:
                ai_results = processor.analyze_code_files(file_scan['code'])
                results['ai_analysis'] = ai_results
            else:
                logger.info(f"DRY RUN: Would analyze {len(file_scan['code'])} code files")
        
        # Traditional processing (citations, snippets, organization)
        if extract_citations:
            logger.info("Extracting citations...")
            if not dry_run:
                citation_results = process_citations(
                    directory,
                    recursive=recursive,
                    save_results=True
                )
                results['citations'] = citation_results
                results['stats']['total_citations'] = citation_results.get('stats', {}).get('total_citations', 0)
            else:
                logger.info("DRY RUN: Would extract citations")
        
        if extract_snippets:
            logger.info("Extracting code snippets...")
            if not dry_run:
                snippet_results = process_snippets(
                    directory,
                    recursive=recursive,
                    extract_comments=True,
                    include_metadata=True
                )
                results['snippets'] = snippet_results
                results['stats']['total_snippets'] = snippet_results.get('stats', {}).get('total_snippets', 0)
            else:
                logger.info("DRY RUN: Would extract snippets")
        
        if organize:
            logger.info("Organizing files...")
            if not dry_run:
                org_results = organize_files(
                    directory,
                    recursive=recursive,
                    create_dirs=True,
                    move_files=True,
                    dry_run=False
                )
                results['organization'] = org_results
                results['stats'].update(org_results.get('stats', {}))
            else:
                logger.info("DRY RUN: Would organize files")
        
        # Filename scrambling (if requested)
        if scramble_filenames:
            logger.info("Scrambling filenames...")
            if not dry_run:
                scramble_results = processor.filename_scrambler.scramble_directory(
                    directory, 
                    interactive=False
                )
                results['scrambling'] = scramble_results
                results['stats']['files_scrambled'] = scramble_results.get('renamed_count', 0)
            else:
                logger.info("DRY RUN: Would scramble filenames")
        
        # Update final statistics
        results['stats']['processed_files'] = (
            results['stats'].get('images_processed', 0) +
            results.get('citations', {}).get('stats', {}).get('processed_files', 0) +
            results.get('snippets', {}).get('stats', {}).get('processed_files', 0) +
            results.get('organization', {}).get('stats', {}).get('organized_files', 0)
        )
        
        # Save comprehensive metadata
        if not dry_run:
            metadata_dir = ensure_metadata_dir(directory)
            metadata_file = metadata_dir / 'cleanupx_comprehensive_results.json'
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Comprehensive results saved to {metadata_file}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in comprehensive cleanup of directory {directory}: {e}")
        return {
            'processed': [],
            'skipped': [],
            'errors': [{'file': str(directory), 'error': str(e)}],
            'stats': {
                'total_files': 0,
                'processed_files': 0,
                'skipped_files': 0,
                'error_files': 1,
                'total_citations': 0,
                'total_snippets': 0,
                'images_processed': 0,
                'images_renamed': 0,
                'files_scrambled': 0
            }
        }

# Convenience functions for backward compatibility
def get_xai_client(api_key=None):
    """Get an initialized X.AI client instance."""
    return XAIIntegration(api_key)

def analyze_code_snippet(code, context=None, model=DEFAULT_MODEL_TEXT, api_key=None):
    """Analyze a code snippet to extract its important parts."""
    client = XAIIntegration(api_key)
    return client.analyze_code_snippet(code, context, model)

def find_duplicates(files, threshold=0.7, model=DEFAULT_MODEL_TEXT, api_key=None):
    """Use X.AI to identify duplicate content across multiple files."""
    client = XAIIntegration(api_key)
    return client.find_duplicates(files, threshold, model)

def process_images_directory(directory, recursive=False, force=False, rename=False, api_key=None):
    """Process all images in a directory for alt text generation."""
    processor = CleanupProcessor(api_key)
    file_scan = processor.scan_directory(directory, recursive)
    return processor.process_images(file_scan['images'], force, rename)

def scramble_directory_filenames(directory, interactive=True):
    """Scramble filenames in a directory."""
    scrambler = FilenameScrambler()
    return scrambler.scramble_directory(directory, interactive)

# Export main functionality
__all__ = [
    'cleanup_directory',
    'CleanupProcessor', 
    'XAIIntegration',
    'ImageProcessor',
    'FilenameScrambler',
    'get_xai_client',
    'analyze_code_snippet',
    'find_duplicates',
    'process_images_directory',
    'scramble_directory_filenames'
] 