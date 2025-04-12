#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
xnamer.py - X.AI-powered File Analyzer and Renamer

This script processes files of various types (images, documents, archives) to:
1. Generate descriptive names using X.AI
2. Create markdown summaries with file analysis
3. Process files individually or in directories

Usage Examples:
    # Process a single file
    python xnamer.py --file example.jpg
    
    # Process all files in a directory
    python xnamer.py --dir ~/Documents/files
    
    # Process recursively with specific file types
    python xnamer.py --dir ~/Documents/files --recursive --types jpg,pdf,zip
    
    # Run in test mode to verify functionality
    python xnamer.py --test
    
    # Interactive mode (default when no arguments provided)
    python xnamer.py
"""

import os
import sys
import base64
import json
import argparse
import re
import logging
import traceback
import hashlib
import time
import tempfile
import glob
import shutil
import mimetypes
import datetime
import random
import string
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from io import BytesIO
from dataclasses import dataclass
from datetime import datetime

# Create xnamer directory in user's home for logs and cache
xnamer_dir = Path.home() / '.xnamer'
xnamer_dir.mkdir(exist_ok=True)

# Set up logging
log_file = xnamer_dir / 'xnamer.log'
logger = logging.getLogger("xnamer")
logger.setLevel(logging.INFO)

# Remove any existing handlers to avoid duplicate logging
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Add both console and file handlers
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(console_handler)

file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Prevent log propagation to avoid duplicate messages
logger.propagate = False

# Optionally add a proper logging level filter
class MaxLevelFilter(logging.Filter):
    def __init__(self, max_level):
        super().__init__()
        self.max_level = max_level
        
    def filter(self, record):
        return record.levelno <= self.max_level

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try to load from both locations - root directory first, then _METHODS
    root_env = Path('.env')
    methods_env = Path('_METHODS/.env')
    
    if root_env.exists():
        load_dotenv(root_env)
        logger.info(f"Loaded environment from {root_env.absolute()}")
    elif methods_env.exists():
        load_dotenv(methods_env)
        logger.info(f"Loaded environment from {methods_env.absolute()}")
    else:
        logger.warning("No .env file found in root or _METHODS directory")
except ImportError:
    pass  # dotenv not installed, continuing without it

# Constants
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
# Always use the official API endpoint
XAI_API_BASE = "https://api.assisted.space/v2"
XAI_API_MODEL = os.environ.get("XAI_API_MODEL", "vision")
API_TIMEOUT = 25  # Timeout for API calls in seconds
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2

# Check for API key and warn if not found
if not XAI_API_KEY:
    logger.warning("XAI_API_KEY not found in environment variables. You'll need to provide it when prompted.")

# File types and extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif", ".heic", ".heif"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".rtf", ".md", ".csv", ".xls", ".xlsx", ".ppt", ".pptx"}
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".tar", ".gz", ".7z", ".bz2"}

# Maximum file sizes (in MB)
MAX_IMAGE_SIZE_MB = 25
MAX_DOCUMENT_SIZE_MB = 30
MAX_ARCHIVE_SIZE_MB = 50

# Cache
CACHE_FILE = xnamer_dir / "xnamer_cache.json"

# Feature flags
try:
    import PIL
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not available. Image processing will be limited.")

try:
    import pyheif
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False
    logger.warning("PyHEIF not available. HEIC/HEIF support will be limited.")
    
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("python-docx not available. DOCX processing will be limited.")
    
try:
    import PyPDF2
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    logger.warning("PyPDF2 not available. PDF processing will be limited.")
    
try:
    import rarfile
    RAR_AVAILABLE = True
except ImportError:
    RAR_AVAILABLE = False
    logger.warning("rarfile not available. RAR processing will be limited.")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available. Using alternative API methods.")

# --- Configuration ---
# API key is already loaded above - don't override it
if not XAI_API_KEY:
    logger.warning("XAI_API_KEY not found or invalid. The script requires a valid API key to function.")

# File Types and Extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif', '.heic', '.heif'}
DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt', '.md', '.rtf', '.odt', '.html', '.htm'}
ARCHIVE_EXTENSIONS = {'.zip', '.rar', '.tar', '.gz', '.7z', '.bz2', '.xz', '.tar.gz', '.tgz'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}

# Combined set of all supported extensions
ALL_EXTENSIONS = IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS | ARCHIVE_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

# Maximum file sizes (in MB) for different file types
MAX_SIZES = {
    'image': 25,
    'document': 25,
    'archive': 100,
    'audio': 50,
    'video': 100,
    'default': 25
}

# Cache file for storing generated file descriptions
CACHE_FILE = xnamer_dir / "xnamer_cache.json"

# Timeout for API calls (in seconds)
API_TIMEOUT = 30

# --- X.AI API Configuration ---
DEFAULT_MODEL_TEXT = "grok-3-mini-latest"
DEFAULT_MODEL_VISION = "grok-2-vision-latest"

# --- Helper Classes ---

class TimeoutError(Exception):
    """Exception raised when a function times out."""
    pass

def timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutError("Function timed out")

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
        self.api_key = api_key or XAI_API_KEY
        if not self.api_key:
            logger.error("X.AI API key not found. Set XAI_API_KEY environment variable.")
            raise ValueError("X.AI API key not found. Set XAI_API_KEY environment variable.")
        
        self.client = openai.Client(
            api_key=self.api_key,
            base_url=XAI_API_BASE,
        )
    
    def analyze_text(self, text: str, prompt: str, schema: Dict = None, 
                     model: str = DEFAULT_MODEL_TEXT, temperature: float = 0.01,
                     max_retries: int = 3):
        """
        Analyze text content using X.AI API with function calling.
        
        Args:
            text: Text content to analyze
            prompt: System prompt to guide the analysis
            schema: JSON schema for function calling
            model: Model to use
            temperature: Sampling temperature
            max_retries: Number of retry attempts
            
        Returns:
            Dictionary with analysis results
        """
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI library not installed. Install with: pip install openai")
            return None
        
        retries = 0
        while retries <= max_retries:
            try:
                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ]
                
                # Setup tools for function calling
                tools = None
                if schema:
                    tools = [
                        {
                            "type": "function",
                            "function": schema
                        }
                    ]
                
                # Make the API call
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    tools=tools,
                    tool_choice={"type": "function", "function": {"name": schema["name"]}} if schema else None,
                    response_format={"type": "json_object"} if not schema else None
                )
                
                # Extract result
                if schema:
                    tool_calls = response.choices[0].message.tool_calls
                    if tool_calls:
                        return json.loads(tool_calls[0].function.arguments)
                else:
                    return json.loads(response.choices[0].message.content)
                    
            except Exception as e:
                retries += 1
                logger.warning(f"API call failed (attempt {retries}/{max_retries}): {e}")
                if retries > max_retries:
                    logger.error(f"Max retries reached: {e}")
                    return None
                time.sleep(2 ** retries)  # Exponential backoff
        
        return None
    
    def analyze_image(self, image_data: str, prompt: str, schema: Dict = None, 
                     model: str = DEFAULT_MODEL_VISION, temperature: float = 0.01,
                     max_retries: int = 3):
        """
        Analyze image content using X.AI Vision API with function calling.
        
        Args:
            image_data: Base64 encoded image data
            prompt: System prompt to guide the analysis
            schema: JSON schema for function calling
            model: Vision model to use
            temperature: Sampling temperature
            max_retries: Number of retry attempts
            
        Returns:
            Dictionary with analysis results
        """
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI library not installed. Install with: pip install openai")
            return None
        
        retries = 0
        while retries <= max_retries:
            try:
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}",
                                    "detail": "high"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
                
                # Make the API call
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"}
                )
                
                # Parse JSON response
                content = response.choices[0].message.content
                return json.loads(content)
                    
            except Exception as e:
                retries += 1
                logger.warning(f"Vision API call failed (attempt {retries}/{max_retries}): {e}")
                if retries > max_retries:
                    logger.error(f"Max retries reached: {e}")
                    return None
                time.sleep(2 ** retries)  # Exponential backoff
        
        return None

# --- Utility Functions ---

def load_cache():
    """Load the file description cache if it exists."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception as e:
            logger.error(f"Error loading cache file: {e}")
    return {}

def save_cache(cache):
    """Save the file description cache to file."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as fp:
            json.dump(cache, fp, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving cache file: {e}")

def get_cache_key(file_path):
    """
    Create a unique cache key for a file based on its path and modification time.
    
    Args:
        file_path: Path to the file
        
    Returns:
        String cache key
    """
    try:
        stats = os.stat(file_path)
        mod_time = stats.st_mtime
        return f"{file_path}:{mod_time}"
    except Exception as e:
        logger.error(f"Error creating cache key for {file_path}: {e}")
        # Fallback to just using the path
        return str(file_path)

def clean_filename(filename):
    """
    Clean a filename to be safe for file systems.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Replace characters that are not allowed in filenames
    forbidden_chars = r'[<>:"/\\|?*]'
    cleaned = re.sub(forbidden_chars, '_', filename)
    
    # Replace multiple spaces or underscores with a single underscore
    cleaned = re.sub(r'[\s_]+', '_', cleaned)
    
    # Remove leading/trailing spaces and dots
    cleaned = cleaned.strip('. ')
    
    # Ensure the filename isn't too long (max 255 chars for most file systems)
    if len(cleaned) > 255:
        cleaned = cleaned[:255]
    
    return cleaned

def strip_media_suffixes(filename):
    """
    Remove common suffixes like IMG_, DSC_, VID_, etc. from filenames.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Common prefixes to remove
    prefixes = [
        'IMG_', 'DSC_', 'VID_', 'PHOTO_', 'IMAGE_', 'SCAN_', 'PIC_', 'CAPTURE_',
        'DCIM', 'DSCN', 'PICT', 'SCREENSHOT_', 'SCREEN_SHOT_', 'SNAP_', 'DOC_',
        'DOCUMENT_', 'FILE_', 'ATTACHMENT_', 'UPLOAD_', 'DOWNLOAD_', 'EXPORT_',
        'IMPORT_', 'UNTITLED_', 'NEW_', 'COPY_OF_', 'BACKUP_OF_', 'DRAFT_',
        'FINAL_', 'REV_', 'REVISION_', 'VERSION_', 'V', 'ARCHIVE_'
    ]
    
    # Try to remove prefixes (case insensitive)
    for prefix in prefixes:
        if filename.upper().startswith(prefix):
            filename = filename[len(prefix):]
    
    # Remove date stamps
    date_patterns = [
        r'^\d{4}-\d{2}-\d{2}_',
        r'^\d{2}-\d{2}-\d{4}_',
        r'^\d{8}_',
        r'^\d{6}_',
        r'^\d{2}\.\d{2}\.\d{4}_',
        r'^\d{4}\.\d{2}\.\d{2}_',
    ]
    
    for pattern in date_patterns:
        filename = re.sub(pattern, '', filename)
    
    # Remove trailing numbers (common in auto-generated files)
    filename = re.sub(r'_\d+$', '', filename)
    
    return filename

def scan_directory(directory, recursive=False, file_types=None):
    """
    Scan a directory for files of specified types.
    
    Args:
        directory: Path to directory to scan
        recursive: Whether to scan subdirectories recursively
        file_types: Set of file extensions to include, or None for all
        
    Returns:
        List of file paths
    """
    file_paths = []
    directory = Path(directory)
    
    if not file_types:
        file_types = ALL_EXTENSIONS
    
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in file_types:
                    file_paths.append(str(file_path))
    else:
        for item in directory.iterdir():
            if item.is_file() and item.suffix.lower() in file_types:
                file_paths.append(str(item))
    
    return file_paths

def get_file_type(file_path):
    """
    Determine the type of file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        String indicating file type: 'image', 'document', 'archive', 'audio', 'video', or 'unknown'
    """
    ext = Path(file_path).suffix.lower()
    
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    elif ext in DOCUMENT_EXTENSIONS:
        return 'document'
    elif ext in ARCHIVE_EXTENSIONS:
        return 'archive'
    elif ext in AUDIO_EXTENSIONS:
        return 'audio'
    elif ext in VIDEO_EXTENSIONS:
        return 'video'
    else:
        return 'unknown'

def check_file_size(file_path, file_type=None):
    """
    Check if a file is within the size limit for its type.
    
    Args:
        file_path: Path to the file
        file_type: Type of file ('image', 'document', etc.) or None to auto-detect
        
    Returns:
        True if the file is within size limits, False otherwise
    """
    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        if file_type is None:
            file_type = get_file_type(file_path)
        
        max_size = MAX_SIZES.get(file_type, MAX_SIZES['default'])
        
        if file_size_mb > max_size:
            logger.warning(f"File size exceeds maximum ({file_size_mb:.1f} MB > {max_size} MB): {file_path}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking file size: {e}")
        return False

def get_file_metadata(file_path):
    """
    Get metadata for a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary containing file metadata
    """
    file_path = Path(file_path)
    try:
        stat = file_path.stat()
        return {
            'size': stat.st_size,
            'size_mb': stat.st_size / (1024 * 1024),
            'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'accessed': datetime.fromtimestamp(stat.st_atime).strftime('%Y-%m-%d %H:%M:%S'),
            'is_file': file_path.is_file(),
            'is_dir': file_path.is_dir(),
            'extension': file_path.suffix.lower(),
            'name': file_path.name,
            'stem': file_path.stem,
            'parent': str(file_path.parent),
            'file_type': get_file_type(file_path)
        }
    except Exception as e:
        logger.error(f"Error getting metadata for {file_path}: {e}")
        return {}

def ensure_directory(path):
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Path to the directory
        
    Returns:
        True if directory exists or was created, False otherwise
    """
    try:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
        return False

def create_backup(file_path):
    """
    Create a backup of a file before renaming it.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Path to the backup file or None if backup failed
    """
    try:
        import shutil
        file_path = Path(file_path)
        backup_dir = file_path.parent / ".xnamer_backups"
        ensure_directory(backup_dir)
        
        backup_path = backup_dir / file_path.name
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup at {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Error creating backup for {file_path}: {e}")
        return None

def rename_file(original_path, new_name, create_backup_file=True):
    """
    Rename a file with a new name.
    
    Args:
        original_path: Original file path
        new_name: New filename (with extension)
        create_backup_file: Whether to create a backup of the original file
        
    Returns:
        Tuple of (success, new_path)
    """
    try:
        original_path = Path(original_path)
        
        # Don't rename if the new name is the same as the old one
        if original_path.name == new_name:
            return True, original_path
        
        new_path = original_path.parent / new_name
        
        # Don't overwrite existing files
        if new_path.exists():
            base_name = new_path.stem
            ext = new_path.suffix
            counter = 1
            while new_path.exists():
                new_path = original_path.parent / f"{base_name}_{counter}{ext}"
                counter += 1
        
        # Create backup if requested
        if create_backup_file:
            backup_path = create_backup(original_path)
        
        # Perform the rename
        original_path.rename(new_path)
        logger.info(f"Renamed: {original_path} -> {new_path}")
        return True, new_path
    
    except Exception as e:
        logger.error(f"Error renaming file {original_path}: {e}")
        return False, original_path

def create_markdown_description(file_path, description, file_type):
    """
    Create a markdown file with the same base name as the file containing the description.
    
    Args:
        file_path: Path to the file
        description: Dictionary with file description
        file_type: Type of file ('image', 'document', etc.)
        
    Returns:
        Path to created markdown file
    """
    try:
        # Get the base name without extension
        file_path = Path(file_path)
        base_name = file_path.stem
        
        # Get the directory of the file
        directory = file_path.parent
        
        # Create metadata directory if it doesn't exist
        metadata_dir = directory / ".metadata"
        ensure_directory(metadata_dir)
        
        # Create markdown file path
        md_file_path = metadata_dir / f"{base_name}.md"
        
        # Get file metadata
        metadata = get_file_metadata(file_path)
        
        # Create common markdown header
        content = [
            f"# {description.get('title', base_name)}",
            "",
            f"**Description:** {description.get('description', 'No description available')}",
            "",
            "## File Information",
            f"- **Original Filename:** {file_path.name}",
            f"- **File Type:** {file_type.upper()}",
            f"- **File Size:** {metadata.get('size_mb', 0):.2f} MB",
            f"- **Created:** {metadata.get('created', 'Unknown')}",
            f"- **Modified:** {metadata.get('modified', 'Unknown')}",
            "",
        ]
        
        # Add type-specific content
        if file_type == 'image':
            # Add image-specific information
            dimensions = description.get('dimensions', 'Unknown')
            content.extend([
                "## Image Information",
                f"- **Dimensions:** {dimensions}",
                f"- **Format:** {metadata.get('extension', '').upper().replace('.', '')}",
                "",
                "## Content",
                f"**Alt Text:** {description.get('alt_text', 'No alt text available')}",
                "",
                "## Tags",
                "\n".join(f"- {tag}" for tag in description.get('tags', []))
            ])
        
        elif file_type == 'document':
            # Add document-specific information
            content.extend([
                "## Document Information",
                f"- **Document Type:** {description.get('document_type', 'Unknown')}",
                f"- **Page Count:** {description.get('page_count', 'Unknown')}",
                f"- **Language:** {description.get('language', 'Unknown')}",
                "",
                "## Content",
                f"**Summary:** {description.get('summary', 'No summary available')}",
                "",
                "## Keywords",
                "\n".join(f"- {keyword}" for keyword in description.get('keywords', []))
            ])
            
            # Add citations if available
            if 'citations' in description and description['citations']:
                content.extend([
                    "",
                    "## Citations",
                    "\n".join(f"- {citation}" for citation in description['citations'])
                ])
        
        elif file_type == 'archive':
            # Add archive-specific information
            content.extend([
                "## Archive Information",
                f"- **Archive Type:** {description.get('archive_type', 'Unknown').upper()}",
                f"- **File Count:** {description.get('file_count', 'Unknown')}",
                f"- **Directory Count:** {description.get('directory_count', 'Unknown')}",
                "",
                "## Content Types",
                "\n".join(f"- {content_type}" for content_type in description.get('content_types', [])),
                "",
                "## Content Summary",
                description.get('content_summary', 'No content summary available')
            ])
        
        elif file_type in ('audio', 'video'):
            # Add audio/video-specific information
            content.extend([
                f"## {file_type.capitalize()} Information",
                f"- **Duration:** {description.get('duration', 'Unknown')}",
                f"- **Format:** {metadata.get('extension', '').upper().replace('.', '')}",
                f"- **Codec:** {description.get('codec', 'Unknown')}",
                f"- **Bitrate:** {description.get('bitrate', 'Unknown')}",
                "",
                "## Content",
                f"**Summary:** {description.get('summary', 'No summary available')}",
                "",
                "## Tags",
                "\n".join(f"- {tag}" for tag in description.get('tags', []))
            ])
        
        # Write markdown file
        with open(md_file_path, "w", encoding="utf-8") as fp:
            fp.write("\n".join(content))
        
        logger.info(f"Created markdown description: {md_file_path}")
        return md_file_path
    
    except Exception as e:
        logger.error(f"Error creating markdown for {file_path}: {e}")
        return None

# --- File Type Handlers ---

# --- Image Processing ---

def encode_image(image_path):
    """
    Encode an image file as base64 for API transmission.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded image or None if encoding failed
    """
    try:
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
            return base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {e}")
        return None

def convert_heic_to_jpeg(image_path):
    """
    Convert HEIC/HEIF image to JPEG format for processing.
    
    Args:
        image_path: Path to the HEIC/HEIF image
        
    Returns:
        Path to the converted JPEG image or None if conversion failed
    """
    image_path = Path(image_path)
    
    # First method: using pyheif if available
    if HEIF_AVAILABLE and PIL_AVAILABLE:
        try:
            temp_path = Path(tempfile.gettempdir()) / f"temp_{image_path.stem}.jpg"
            
            heif_file = pyheif.read(str(image_path))
            image = Image.frombytes(
                heif_file.mode, 
                heif_file.size, 
                heif_file.data,
                "raw",
                heif_file.mode,
                heif_file.stride,
            )
            image.save(temp_path, "JPEG", quality=95)
            logger.info(f"Converted HEIC to JPEG: {image_path} -> {temp_path}")
            return temp_path
        except Exception as e:
            logger.error(f"Error converting HEIC to JPEG using pyheif: {e}")
    
    # Second method: using system commands
    try:
        temp_path = Path(tempfile.gettempdir()) / f"temp_{image_path.stem}.jpg"
        
        # Try using sips on macOS
        if sys.platform == 'darwin':
            subprocess.run(['sips', '-s', 'format', 'jpeg', str(image_path), '--out', str(temp_path)], 
                           check=True, capture_output=True)
            if temp_path.exists():
                logger.info(f"Converted HEIC to JPEG using sips: {image_path} -> {temp_path}")
                return temp_path
        
        # Try using ImageMagick's convert
        subprocess.run(['convert', str(image_path), str(temp_path)], 
                       check=True, capture_output=True)
        if temp_path.exists():
            logger.info(f"Converted HEIC to JPEG using ImageMagick: {image_path} -> {temp_path}")
            return temp_path
    except Exception as e:
        logger.error(f"Error converting HEIC to JPEG using system commands: {e}")
    
    logger.error(f"Failed to convert HEIC/HEIF image: {image_path}")
    return None

def convert_webp_to_jpeg(image_path):
    """
    Convert WebP image to JPEG format for processing.
    
    Args:
        image_path: Path to the WebP image
        
    Returns:
        Path to the converted JPEG image or None if conversion failed
    """
    image_path = Path(image_path)
    
    # Method 1: using PIL/Pillow
    if PIL_AVAILABLE:
        try:
            temp_path = Path(tempfile.gettempdir()) / f"temp_{image_path.stem}.jpg"
            with Image.open(image_path) as img:
                if img.mode in ('RGBA', 'LA'):
                    # Handle transparency by adding white background
                    background = Image.new('RGBA', img.size, (255, 255, 255))
                    img = Image.alpha_composite(background.convert(img.mode), img)
                
                img = img.convert("RGB")
                img.save(temp_path, "JPEG", quality=95)
                logger.info(f"Converted WebP to JPEG: {image_path} -> {temp_path}")
                return temp_path
        except Exception as e:
            logger.error(f"Error converting WebP to JPEG using PIL: {e}")
    
    # Method 2: using system commands
    try:
        temp_path = Path(tempfile.gettempdir()) / f"temp_{image_path.stem}.jpg"
        
        # Try using ImageMagick's convert
        subprocess.run(['convert', str(image_path), str(temp_path)], 
                       check=True, capture_output=True)
        if temp_path.exists():
            logger.info(f"Converted WebP to JPEG using ImageMagick: {image_path} -> {temp_path}")
            return temp_path
    except Exception as e:
        logger.error(f"Error converting WebP to JPEG using system commands: {e}")
    
    logger.error(f"Failed to convert WebP image: {image_path}")
    return None

def get_image_dimensions(image_path):
    """
    Get the dimensions of an image.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Tuple of (width, height) or None if dimensions could not be determined
    """
    # Method 1: using PIL/Pillow
    if PIL_AVAILABLE:
        try:
            with Image.open(image_path) as img:
                return img.width, img.height
        except Exception as e:
            logger.error(f"Error getting image dimensions using PIL: {e}")
    
    # Method 2: using system commands
    try:
        # Try using identify from ImageMagick
        result = subprocess.run(['identify', '-format', '%w %h', str(image_path)], 
                               capture_output=True, text=True, check=True)
        width, height = map(int, result.stdout.strip().split())
        return width, height
    except Exception as e:
        logger.error(f"Error getting image dimensions using system commands: {e}")
    
    return None

def cleanup_temp_files(temp_file_path):
    """
    Helper function to safely clean up temporary files.
    
    Args:
        temp_file_path: Path to the temporary file
    """
    if temp_file_path and Path(temp_file_path).exists():
        try:
            os.remove(temp_file_path)
            logger.info(f"Removed temporary file: {temp_file_path}")
        except Exception as e:
            logger.error(f"Error removing temporary file {temp_file_path}: {e}")

def process_image(file_path, cache=None, force=False):
    """
    Process an image file: analyze its content, generate description.
    
    Args:
        file_path: Path to the image file
        cache: Optional cache dictionary
        force: Whether to force regeneration even if in cache
        
    Returns:
        Tuple of (success, description)
    """
    if cache is None:
        cache = {}
    
    try:
        file_path = Path(file_path)
        logger.info(f"Processing image: {file_path}")
        
        # Check file extension
        if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
            logger.error(f"Unsupported image type: {file_path.suffix}")
            return False, None
        
        # Check file size
        if not check_file_size(file_path, 'image'):
            logger.error(f"Image file size exceeds limit: {file_path}")
            return False, None
        
        # Check cache
        cache_key = get_cache_key(file_path)
        if not force and cache_key in cache:
            logger.info(f"Using cached description for {file_path}")
            return True, cache[cache_key]
        
        # Process image
        analysis_path = file_path
        temp_converted = None
        
        # Convert HEIC to JPEG for analysis
        if file_path.suffix.lower() in {'.heic', '.heif'}:
            jpeg_path = convert_heic_to_jpeg(file_path)
            if jpeg_path and jpeg_path != file_path:
                analysis_path = jpeg_path
                temp_converted = jpeg_path
                
        # Convert WebP to JPEG for analysis
        elif file_path.suffix.lower() == '.webp':
            jpeg_path = convert_webp_to_jpeg(file_path)
            if jpeg_path and jpeg_path != file_path:
                analysis_path = jpeg_path
                temp_converted = jpeg_path
        
        try:
            # Encode image for API transmission
            image_data = encode_image(analysis_path)
            if not image_data:
                logger.error(f"Failed to encode image: {analysis_path}")
                cleanup_temp_files(temp_converted)
                return False, None
            
            # Prepare prompt
            prompt = (
                "You are an AI specializing in describing images for accessibility purposes. "
                "Write comprehensive alt text for this image, as though for a blind engineer who needs "
                "to understand every detail of the information including text. "
                "Also suggest a descriptive filename and title based on the content of the image. "
                "Format your response in this exact JSON structure:\n"
                "{\n"
                "  \"title\": \"Concise title for the image\",\n"
                "  \"description\": \"Detailed description of the image\",\n"
                "  \"alt_text\": \"Concise alt text for the image\",\n"
                "  \"suggested_filename\": \"descriptive_filename_without_extension\",\n"
                "  \"tags\": [\"tag1\", \"tag2\", ...]\n"
                "}"
            )
            
            # Call API for analysis
            client = XAIClient()
            result = client.analyze_image(image_data, prompt)
            
            # Cleanup temporary files
            cleanup_temp_files(temp_converted)
            
            if not result:
                logger.error(f"Failed to analyze image: {file_path}")
                return False, None
            
            # Add dimensions to result
            dimensions = get_image_dimensions(file_path)
            if dimensions:
                result['dimensions'] = f"{dimensions[0]}x{dimensions[1]}"
            
            # Add file metadata
            result['file_size'] = f"{os.path.getsize(file_path) / (1024 * 1024):.2f} MB"
            result['format'] = file_path.suffix.upper().replace('.', '')
            
            # Cache result
            cache[cache_key] = result
            
            return True, result
        
        except Exception as e:
            logger.error(f"Error analyzing image {file_path}: {e}")
            cleanup_temp_files(temp_converted)
            return False, None
            
    except Exception as e:
        logger.error(f"Error processing image {file_path}: {e}")
        return False, None

# --- Document Processing ---

def extract_text_from_pdf(file_path, max_pages=10):
    """
    Extract text from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        max_pages: Maximum number of pages to extract
        
    Returns:
        Extracted text string
    """
    file_path = Path(file_path)
    text = ""
    
    # Method 1: PyPDF2
    if PYPDF_AVAILABLE:
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                pages_to_extract = min(len(reader.pages), max_pages) if max_pages else len(reader.pages)
                
                for i in range(pages_to_extract):
                    try:
                        page = reader.pages[i]
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n\n"
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {i} in {file_path}: {e}")
                        continue
                
                if text:
                    return text
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed for {file_path}: {e}")
    
    # Method 2: pdftotext command line tool
    try:
        page_option = []
        if max_pages:
            page_option = ["-l", str(max_pages)]
            
        result = subprocess.run(
            ["pdftotext"] + page_option + ["-layout", str(file_path), "-"],
            capture_output=True, text=True, check=True
        )
        if result.stdout.strip():
            return result.stdout
    except Exception as e:
        logger.warning(f"pdftotext extraction failed for {file_path}: {e}")
    
    # Method 3: Try reading as text file
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Text file reading failed: {e}")
    
    return text

def extract_text_from_docx(file_path):
    """
    Extract text from a DOCX file.
    
    Args:
        file_path: Path to the DOCX file
        
    Returns:
        Extracted text string
    """
    if DOCX_AVAILABLE:
        try:
            doc = docx.Document(file_path)
            return "\n".join(para.text for para in doc.paragraphs)
        except Exception as e:
            logger.error(f"Error extracting text from DOCX {file_path}: {e}")
    
    # Try using system tools
    try:
        # Try using strings or other command line tools
        result = subprocess.run(['strings', str(file_path)], 
                               capture_output=True, text=True, check=True)
        return result.stdout
    except Exception as e:
        logger.warning(f"System tool extraction failed for {file_path}: {e}")
    
    return ""

def extract_text_from_file(file_path):
    """
    Extract text from a file based on its type.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Extracted text string
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext == '.docx':
        return extract_text_from_docx(file_path)
    elif ext in {'.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm'}:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            return ""
    else:
        logger.warning(f"No specific extraction method for {ext}")
        # Try as text
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception:
            return ""

def get_pdf_page_count(file_path):
    """
    Get the number of pages in a PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Number of pages or None if counting fails
    """
    if PYPDF_AVAILABLE:
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return len(reader.pages)
        except Exception as e:
            logger.error(f"Error getting page count with PyPDF2: {e}")
    
    # Try using pdfinfo if available
    try:
        result = subprocess.run(['pdfinfo', str(file_path)], 
                               capture_output=True, text=True, check=True)
        for line in result.stdout.split('\n'):
            if line.startswith('Pages:'):
                return int(line.split(':')[1].strip())
    except Exception as e:
        logger.error(f"Error getting page count with pdfinfo: {e}")
    
    return None

def process_document(file_path, cache=None, force=False):
    """
    Process a document file: extract text, analyze content, generate description.
    
    Args:
        file_path: Path to the document file
        cache: Optional cache dictionary
        force: Whether to force regeneration even if in cache
        
    Returns:
        Tuple of (success, description)
    """
    if cache is None:
        cache = {}
    
    try:
        file_path = Path(file_path)
        logger.info(f"Processing document: {file_path}")
        
        # Check file extension
        if file_path.suffix.lower() not in DOCUMENT_EXTENSIONS:
            logger.error(f"Unsupported document type: {file_path.suffix}")
            return False, None
        
        # Check file size
        if not check_file_size(file_path, 'document'):
            logger.error(f"Document file size exceeds limit: {file_path}")
            return False, None
        
        # Check cache
        cache_key = get_cache_key(file_path)
        if not force and cache_key in cache:
            logger.info(f"Using cached description for {file_path}")
            return True, cache[cache_key]
        
        # Extract text
        text = extract_text_from_file(file_path)
        if not text or len(text.strip()) < 10:
            logger.error(f"Failed to extract meaningful text from {file_path}")
            return False, None
        
        # Limit text length to avoid token limits
        max_text_length = 15000
        if len(text) > max_text_length:
            logger.info(f"Truncating document text from {len(text)} to {max_text_length} characters")
            text = text[:max_text_length] + "\n[... TRUNCATED ...]"
        
        # Get file metadata
        metadata = get_file_metadata(file_path)
        
        # Get page count for PDFs
        page_count = None
        if file_path.suffix.lower() == '.pdf':
            page_count = get_pdf_page_count(file_path)
        
        # Prepare prompt
        prompt = (
            "You are an AI specializing in analyzing documents. "
            "Analyze the provided document text and extract key information. "
            f"This is a {file_path.suffix.upper().replace('.', '')} document named '{file_path.name}'. "
            "Format your response in this exact JSON structure:\n"
            "{\n"
            "  \"title\": \"Document title or main heading\",\n"
            "  \"document_type\": \"Type of document (e.g., report, manual, article)\",\n"
            "  \"summary\": \"Concise summary of the document content\",\n"
            "  \"language\": \"Primary language of the document\",\n"
            "  \"keywords\": [\"key1\", \"key2\", ...],\n"
            "  \"suggested_filename\": \"descriptive_filename_without_extension\",\n"
            "  \"citations\": [\"citation1\", \"citation2\", ...] (if any)\n"
            "}"
        )
        
        # Call API for analysis
        client = XAIClient()
        result = client.analyze_text(text, prompt)
        
        if not result:
            logger.error(f"Failed to analyze document: {file_path}")
            return False, None
        
        # Add file metadata
        result['file_size'] = f"{metadata['size_mb']:.2f} MB"
        result['modified_date'] = metadata['modified']
        if page_count:
            result['page_count'] = page_count
        
        # Cache result
        cache[cache_key] = result
        
        return True, result
        
    except Exception as e:
        logger.error(f"Error processing document {file_path}: {e}")
        return False, None

# --- Archive Processing ---

def analyze_zip_archive(file_path):
    """
    Analyze the contents of a ZIP archive.
    
    Args:
        file_path: Path to the ZIP file
        
    Returns:
        Dictionary with archive analysis information
    """
    try:
        import zipfile
        file_path = Path(file_path)
        result = {
            "archive_type": "zip",
            "file_count": 0,
            "directory_count": 0,
            "content_types": [],
            "content_summary": []
        }
        
        content_types = {}
        
        with zipfile.ZipFile(file_path, 'r') as zipf:
            file_list = zipf.namelist()
            result["file_count"] = len(file_list)
            result["content_summary"].append(f"Archive contains {len(file_list)} files/directories")
            
            # Analyze file types
            for name in file_list:
                if name.endswith('/'):  # Directory
                    result["directory_count"] += 1
                else:
                    ext = os.path.splitext(name)[1].lower()
                    if ext in content_types:
                        content_types[ext] += 1
                    else:
                        content_types[ext] = 1
                        
            # Get file list preview (limited)
            for i, name in enumerate(file_list[:20]):
                result["content_summary"].append(f"- {name}")
            if len(file_list) > 20:
                result["content_summary"].append(f"... and {len(file_list) - 20} more items")
        
        # Format content types
        for ext, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
            result["content_types"].append(f"{ext}: {count} file(s)")
        
        return result
    
    except Exception as e:
        logger.error(f"Error analyzing ZIP archive {file_path}: {e}")
        return {"error": str(e), "archive_type": "zip"}

def analyze_rar_archive(file_path):
    """
    Analyze the contents of a RAR archive.
    
    Args:
        file_path: Path to the RAR file
        
    Returns:
        Dictionary with archive analysis information
    """
    if not RAR_AVAILABLE:
        return {"error": "rarfile module not installed", "archive_type": "rar"}
    
    try:
        import rarfile
        file_path = Path(file_path)
        result = {
            "archive_type": "rar",
            "file_count": 0,
            "directory_count": 0,
            "content_types": [],
            "content_summary": []
        }
        
        content_types = {}
        
        with rarfile.RarFile(file_path, 'r') as rf:
            file_list = rf.namelist()
            result["file_count"] = len(file_list)
            result["content_summary"].append(f"Archive contains {len(file_list)} files/directories")
            
            # Analyze file types
            for name in file_list:
                if name.endswith('/'):  # Directory
                    result["directory_count"] += 1
                else:
                    ext = os.path.splitext(name)[1].lower()
                    if ext in content_types:
                        content_types[ext] += 1
                    else:
                        content_types[ext] = 1
                        
            # Get file list preview
            for i, name in enumerate(file_list[:20]):
                result["content_summary"].append(f"- {name}")
            if len(file_list) > 20:
                result["content_summary"].append(f"... and {len(file_list) - 20} more items")
        
        # Format content types
        for ext, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
            result["content_types"].append(f"{ext}: {count} file(s)")
        
        return result
    
    except Exception as e:
        logger.error(f"Error analyzing RAR archive {file_path}: {e}")
        return {"error": str(e), "archive_type": "rar"}

def generate_archive_filename(file_path, content_info):
    """
    Generate a suggested filename for an archive based on its content.
    
    Args:
        file_path: Path to the archive file
        content_info: Dictionary with content analysis
        
    Returns:
        Suggested filename without extension
    """
    # Start with the original name
    original_name = strip_media_suffixes(Path(file_path).stem)
    
    # Try to determine main content type
    content_types = {}
    for type_entry in content_info.get('content_types', []):
        try:
            ext, count_text = type_entry.split(':', 1)
            count = int(re.search(r'\d+', count_text).group())
            content_types[ext.strip()] = count
        except:
            continue
    
    # Find most common file type
    most_common_ext = None
    most_common_count = 0
    for ext, count in content_types.items():
        if count > most_common_count:
            most_common_ext = ext
            most_common_count = count
    
    # Create descriptive name
    if most_common_ext and most_common_count > 1:
        # Clean up the extension
        ext_type = most_common_ext.lstrip('.').lower()
        
        # Only use meaningful extension types
        meaningful_extensions = {'jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 
                                'xls', 'xlsx', 'ppt', 'pptx', 'mp3', 'mp4', 'wav',
                                'txt', 'csv', 'json', 'xml', 'html', 'py', 'js'}
        if ext_type in meaningful_extensions:
            # If the original name already contains this extension type, don't add it
            if ext_type.lower() not in original_name.lower():
                return f"{original_name}_{ext_type}_files"
    
    return original_name

def process_archive(file_path, cache=None, force=False):
    """
    Process an archive file: analyze its content, generate description.
    
    Args:
        file_path: Path to the archive file
        cache: Optional cache dictionary
        force: Whether to force regeneration even if in cache
        
    Returns:
        Tuple of (success, description)
    """
    if cache is None:
        cache = {}
    
    try:
        file_path = Path(file_path)
        logger.info(f"Processing archive: {file_path}")
        
        # Check file extension
        if file_path.suffix.lower() not in ARCHIVE_EXTENSIONS:
            logger.error(f"Unsupported archive type: {file_path.suffix}")
            return False, None
        
        # Check file size
        if not check_file_size(file_path, 'archive'):
            logger.error(f"Archive file size exceeds limit: {file_path}")
            return False, None
        
        # Check cache
        cache_key = get_cache_key(file_path)
        if not force and cache_key in cache:
            logger.info(f"Using cached description for {file_path}")
            return True, cache[cache_key]
        
        # Analyze archive content
        content_info = None
        if file_path.suffix.lower() == '.zip':
            content_info = analyze_zip_archive(file_path)
        elif file_path.suffix.lower() == '.rar':
            content_info = analyze_rar_archive(file_path)
        else:
            logger.warning(f"No specific analysis method for {file_path.suffix}")
            content_info = {"archive_type": file_path.suffix.lower().lstrip('.')}
        
        # Get file metadata
        metadata = get_file_metadata(file_path)
        
        # Generate result
        result = {
            "title": Path(file_path).stem,
            "archive_type": content_info.get("archive_type", "unknown"),
            "file_count": content_info.get("file_count", 0),
            "directory_count": content_info.get("directory_count", 0),
            "content_types": content_info.get("content_types", []),
            "content_summary": "\n".join(content_info.get("content_summary", ["No content summary available"])),
            "file_size": f"{metadata['size_mb']:.2f} MB",
            "modified_date": metadata['modified'],
            "suggested_filename": generate_archive_filename(file_path, content_info)
        }
        
        # Cache result
        cache[cache_key] = result
        
        return True, result
        
    except Exception as e:
        logger.error(f"Error processing archive {file_path}: {e}")
        return False, None

# --- Main Processing Functions ---

def process_file(file_path, cache=None, force=False):
    """
    Process a file based on its type.
    
    Args:
        file_path: Path to the file
        cache: Optional cache dictionary
        force: Whether to force regeneration even if in cache
        
    Returns:
        Dictionary with processing results
    """
    if cache is None:
        cache = load_cache()
    
    result = {
        'original_path': str(file_path),
        'new_path': None,
        'description': None,
        'success': False,
        'renamed': False,
        'markdown_created': False,
        'error': None
    }
    
    try:
        file_path = Path(file_path)
        file_type = get_file_type(file_path)
        
        # Process based on file type
        if file_type == 'image':
            success, description = process_image(file_path, cache, force)
        elif file_type == 'document':
            success, description = process_document(file_path, cache, force)
        elif file_type == 'archive':
            success, description = process_archive(file_path, cache, force)
        else:
            result['error'] = f"Unsupported file type: {file_type}"
            return result
        
        if not success or not description:
            result['error'] = "Failed to process file"
            return result
        
        result['description'] = description
        result['success'] = True
        
        # Save the cache
        save_cache(cache)
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        result['error'] = str(e)
        return result

def rename_file_with_description(file_path, description, file_type, create_backup=True):
    """
    Rename a file based on its description.
    
    Args:
        file_path: Path to the file
        description: Dictionary with file description
        file_type: Type of file ('image', 'document', etc.)
        create_backup: Whether to create a backup of the original file
        
    Returns:
        Dictionary with renaming results
    """
    result = {
        'original_path': str(file_path),
        'new_path': None,
        'success': False,
        'error': None
    }
    
    try:
        file_path = Path(file_path)
        
        # Get suggested filename from description
        suggested_name = None
        if description and isinstance(description, dict):
            suggested_name = description.get("suggested_filename")
        
        if not suggested_name:
            # Use original name as fallback
            suggested_name = strip_media_suffixes(file_path.stem)
        
        # Clean the filename
        base_name = clean_filename(suggested_name)
        
        # Add dimensions for images
        if file_type == 'image' and 'dimensions' in description:
            base_name = f"{base_name}_{description['dimensions']}"
        
        # Add extension
        new_name = f"{base_name}{file_path.suffix}"
        
        # Perform the rename
        success, new_path = rename_file(file_path, new_name, create_backup)
        
        if success:
            result['success'] = True
            result['new_path'] = str(new_path)
        else:
            result['error'] = "Failed to rename file"
        
        return result
        
    except Exception as e:
        logger.error(f"Error renaming file {file_path}: {e}")
        result['error'] = str(e)
        return result

def process_and_rename_file(file_path, cache=None, force=False, create_backup=True, create_markdown=True):
    """
    Process a file, generate a description, rename it, and create a markdown summary.
    
    Args:
        file_path: Path to the file
        cache: Optional cache dictionary
        force: Whether to force regeneration even if in cache
        create_backup: Whether to create a backup of the original file
        create_markdown: Whether to create a markdown summary
        
    Returns:
        Dictionary with processing results
    """
    if cache is None:
        cache = load_cache()
    
    # Process the file
    result = process_file(file_path, cache, force)
    
    if not result['success']:
        return result
    
    # Get file type
    file_type = get_file_type(file_path)
    
    # Rename the file
    rename_result = rename_file_with_description(file_path, result['description'], file_type, create_backup)
    result['renamed'] = rename_result['success']
    result['new_path'] = rename_result['new_path']
    
    # Create markdown description
    if create_markdown and rename_result['success']:
        target_path = rename_result['new_path'] or file_path
        md_path = create_markdown_description(target_path, result['description'], file_type)
        result['markdown_created'] = bool(md_path)
    
    # Return combined result
    return result

def process_directory(directory, recursive=False, force=False, file_types=None, 
                     create_backup=True, create_markdown=True):
    """
    Process all files in a directory.
    
    Args:
        directory: Path to directory to process
        recursive: Whether to scan subdirectories recursively
        force: Whether to force regeneration even if in cache
        file_types: Set of file extensions to include, or None for all
        create_backup: Whether to create backups of original files
        create_markdown: Whether to create markdown summaries
        
    Returns:
        Dictionary with processing statistics
    """
    directory = Path(directory)
    
    # Load cache
    cache = load_cache()
    logger.info(f"Cache loaded with {len(cache)} entries")
    
    # Scan directory for files
    file_paths = scan_directory(directory, recursive, file_types)
    logger.info(f"Found {len(file_paths)} files in {directory}")
    
    # Initialize statistics
    stats = {
        "total": len(file_paths),
        "success": 0,
        "error": 0,
        "renamed": 0,
        "markdown_created": 0,
        "by_type": {}
    }
    
    # Process each file
    for i, file_path in enumerate(file_paths, 1):
        logger.info(f"\n[{i}/{stats['total']}] Processing {file_path}")
        
        # Get file type
        file_type = get_file_type(file_path)
        
        # Initialize stats for this file type if it doesn't exist
        if file_type not in stats["by_type"]:
            stats["by_type"][file_type] = {
                "total": 0,
                "success": 0,
                "error": 0,
                "renamed": 0
            }
        
        # Update type-specific total
        stats["by_type"][file_type]["total"] += 1
        
        # Process the file
        result = process_and_rename_file(file_path, cache, force, create_backup, create_markdown)
        
        # Update statistics
        if result['success']:
            stats["success"] += 1
            stats["by_type"][file_type]["success"] += 1
            
            if result['renamed']:
                stats["renamed"] += 1
                stats["by_type"][file_type]["renamed"] += 1
            
            if result.get('markdown_created', False):
                stats["markdown_created"] += 1
        else:
            stats["error"] += 1
            stats["by_type"][file_type]["error"] += 1
            logger.error(f"Error processing {file_path}: {result.get('error', 'Unknown error')}")
        
        # Periodically save cache
        if i % 10 == 0:
            save_cache(cache)
    
    # Final cache save
    save_cache(cache)
    
    # Print summary
    logger.info("\n======= Processing Complete =======")
    logger.info(f"Total files: {stats['total']}")
    logger.info(f"Successfully processed: {stats['success']}")
    logger.info(f"Files renamed: {stats['renamed']}")
    logger.info(f"Markdown files created: {stats['markdown_created']}")
    logger.info(f"Errors during processing: {stats['error']}")
    
    # Print type-specific stats
    for file_type, type_stats in stats["by_type"].items():
        logger.info(f"\n{file_type.upper()} Files:")
        logger.info(f"  Total: {type_stats['total']}")
        logger.info(f"  Successful: {type_stats['success']}")
        logger.info(f"  Renamed: {type_stats['renamed']}")
        logger.info(f"  Errors: {type_stats['error']}")
    
    return stats

# --- CLI Interface ---

def interactive_cli():
    """Run the interactive CLI mode."""
    print("\nWelcome to X.AI File Namer!")
    print("This script analyzes files with AI, renames them descriptively, and creates markdown summaries.")
    
    while True:
        print("\nPlease choose an option:")
        print("  1. Process a single file")
        print("  2. Process a directory of files")
        print("  3. Clear cache")
        print("  4. Exit")
        
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == "1":
            file_path = input("Enter the file path: ").strip()
            if not os.path.isfile(file_path):
                print(f"Error: {file_path} is not a valid file.")
                continue
            
            force_input = input("Force regeneration of description even if cached? (y/n): ").strip().lower()
            force = force_input in ("y", "yes")
            
            backup_input = input("Create backup of original file? (y/n): ").strip().lower()
            backup = backup_input in ("y", "yes")
            
            md_input = input("Create markdown description? (y/n): ").strip().lower()
            markdown = md_input in ("y", "yes")
            
            result = process_and_rename_file(file_path, force=force, create_backup=backup, create_markdown=markdown)
            
            if result['success']:
                print(f"\nSuccessfully processed: {file_path}")
                if result['renamed']:
                    print(f"Renamed to: {result['new_path']}")
                if result.get('markdown_created', False):
                    md_path = Path(result['new_path'] or file_path).parent / ".metadata" / f"{Path(result['new_path'] or file_path).stem}.md"
                    print(f"Created markdown description: {md_path}")
            else:
                print(f"\nError processing {file_path}: {result.get('error', 'Unknown error')}")
            
        elif choice == "2":
            directory = input("Enter the directory path: ").strip()
            if not os.path.isdir(directory):
                print(f"Error: {directory} is not a valid directory.")
                continue
            
            recursive_input = input("Process subdirectories recursively? (y/n): ").strip().lower()
            recursive = recursive_input in ("y", "yes")
            
            force_input = input("Force regeneration of descriptions even if cached? (y/n): ").strip().lower()
            force = force_input in ("y", "yes")
            
            backup_input = input("Create backups of original files? (y/n): ").strip().lower()
            backup = backup_input in ("y", "yes")
            
            md_input = input("Create markdown descriptions? (y/n): ").strip().lower()
            markdown = md_input in ("y", "yes")
            
            file_types_input = input("Enter specific file types to process (comma-separated, e.g., 'jpg,png,pdf') or leave blank for all: ").strip()
            
            file_types = None
            if file_types_input:
                file_types = set()
                for ext in file_types_input.split(','):
                    ext = ext.strip()
                    if not ext.startswith('.'):
                        ext = f".{ext}"
                    file_types.add(ext.lower())
            
            stats = process_directory(directory, recursive, force, file_types, backup, markdown)
            
        elif choice == "3":
            confirm = input("Are you sure you want to clear the cache? (y/n): ").strip().lower()
            if confirm in ("y", "yes"):
                if os.path.exists(CACHE_FILE):
                    os.remove(CACHE_FILE)
                    print("Cache cleared.")
                else:
                    print("No cache file found.")
            
        elif choice == "4":
            print("Exiting. Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

def test_api_connection():
    """
    Test the connection to X.AI API.
    
    Returns:
        True if connection is successful, False otherwise
    """
    if not XAI_API_KEY:
        logger.error("XAI_API_KEY not found. Cannot test API connection.")
        return False
    
    logger.info("Testing X.AI API connection...")
    
    try:
        client = XAIClient()
        test_message = "This is a test message. Please respond with a JSON containing status: success."
        response = client.analyze_text(test_message, "Respond with simple JSON")
        
        if response and isinstance(response, dict) and response.get("status") == "success":
            logger.info("API connection successful.")
            return True
        else:
            logger.info("API responded but with unexpected format.")
            return False
            
    except Exception as e:
        logger.error(f"API connection failed: {e}")
        return False

def test_file_processing():
    """
    Test processing of different file types by creating temp files.
    
    Returns:
        Dict with test results
    """
    results = {
        "image": {"tested": False, "supported": False, "success": False},
        "document": {"tested": False, "supported": False, "success": False},
        "archive": {"tested": False, "supported": False, "success": False}
    }
    
    # Test image processing
    if PIL_AVAILABLE:
        results["image"]["supported"] = True
        results["image"]["tested"] = True
        
        try:
            # Create a test image
            test_img_path = Path(tempfile.gettempdir()) / "xnamer_test.jpg"
            img = Image.new('RGB', (100, 100), color = (73, 109, 137))
            img.save(test_img_path)
            
            # Test processing
            logger.info(f"Testing image processing with {test_img_path}")
            success, _ = process_image(test_img_path, {}, True)
            results["image"]["success"] = success
            
            # Clean up
            if test_img_path.exists():
                os.remove(test_img_path)
                
        except Exception as e:
            logger.error(f"Image test failed: {e}")
    
    # Test document processing
    results["document"]["supported"] = True
    results["document"]["tested"] = True
    
    try:
        # Create a test text file
        test_doc_path = Path(tempfile.gettempdir()) / "xnamer_test.txt"
        with open(test_doc_path, 'w') as f:
            f.write("This is a test document for xnamer. It contains sample text to analyze.")
        
        # Test processing
        logger.info(f"Testing document processing with {test_doc_path}")
        success, _ = process_document(test_doc_path, {}, True)
        results["document"]["success"] = success
        
        # Clean up
        if test_doc_path.exists():
            os.remove(test_doc_path)
            
    except Exception as e:
        logger.error(f"Document test failed: {e}")
    
    # Test archive processing
    try:
        import zipfile
        results["archive"]["supported"] = True
        results["archive"]["tested"] = True
        
        # Create a test zip file
        test_zip_path = Path(tempfile.gettempdir()) / "xnamer_test.zip"
        with zipfile.ZipFile(test_zip_path, 'w') as zf:
            temp_file = Path(tempfile.gettempdir()) / "temp_file_for_zip.txt"
            with open(temp_file, 'w') as f:
                f.write("Test file for archive testing")
            zf.write(temp_file, arcname="test_file.txt")
            if temp_file.exists():
                os.remove(temp_file)
        
        # Test processing
        logger.info(f"Testing archive processing with {test_zip_path}")
        success, _ = process_archive(test_zip_path, {}, True)
        results["archive"]["success"] = success
        
        # Clean up
        if test_zip_path.exists():
            os.remove(test_zip_path)
            
    except Exception as e:
        logger.error(f"Archive test failed: {e}")
    
    return results

def run_test_mode():
    """Run the test mode to verify all functionality."""
    print("\n=== X.AI File Namer (xnamer.py) Test Mode ===\n")
    
    # Test environment and dependencies
    print("\n--- Testing Environment and Dependencies ---")
    print(f"Python version: {sys.version}")
    print(f"Operating system: {sys.platform}")
    print(f"X.AI API Key configured: {'Yes' if XAI_API_KEY else 'No'}")
    print(f"Log directory: {xnamer_dir}")
    print(f"Log file: {log_file}")
    print(f"Cache file: {CACHE_FILE}")
    
    # Test dependencies
    print("\n--- Testing Dependencies ---")
    dependencies = {
        "OpenAI library": OPENAI_AVAILABLE,
        "PIL/Pillow": PIL_AVAILABLE,
        "PyHEIF": HEIF_AVAILABLE,
        "python-docx": DOCX_AVAILABLE,
        "PyPDF2": PYPDF_AVAILABLE,
        "rarfile": RAR_AVAILABLE
    }
    
    for dep, available in dependencies.items():
        print(f"{dep}: {'✓' if available else '✗'}")
    
    # Test API connection
    print("\n--- Testing X.AI API Connection ---")
    api_success = test_api_connection()
    print(f"API connection: {'✓' if api_success else '✗'}")
    
    # Test file processing
    print("\n--- Testing File Processing ---")
    file_results = test_file_processing()
    
    for file_type, result in file_results.items():
        if result["tested"]:
            support_status = "✓" if result["supported"] else "✗"
            test_status = "✓" if result["success"] else "✗"
            print(f"{file_type.capitalize()} processing: Support {support_status} | Test {test_status}")
        else:
            print(f"{file_type.capitalize()} processing: Not tested")
    
    # Test directory creation
    print("\n--- Testing Directory Creation ---")
    test_dir = Path(tempfile.gettempdir()) / "xnamer_test_dir"
    dir_success = ensure_directory(test_dir)
    print(f"Directory creation: {'✓' if dir_success else '✗'}")
    
    if test_dir.exists():
        try:
            os.rmdir(test_dir)
        except:
            pass
    
    # Overall assessment
    print("\n--- Overall Assessment ---")
    critical_components = [
        ("API Connection", api_success),
        ("Image Processing", file_results["image"]["success"] if file_results["image"]["tested"] else False),
        ("Document Processing", file_results["document"]["success"] if file_results["document"]["tested"] else False),
        ("Directory Creation", dir_success)
    ]
    
    all_success = all(status for _, status in critical_components)
    
    if all_success:
        print("\n✓ All critical tests passed. xnamer.py is ready to use.")
    else:
        print("\n✗ Some tests failed. Please check the logs for details.")
        failed_components = [name for name, status in critical_components if not status]
        print(f"Failed components: {', '.join(failed_components)}")
    
    return all_success

# --- Main function updates ---

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Process files to generate descriptive names and markdown summaries using X.AI API."
    )
    parser.add_argument("--dir", help="Directory containing files to process")
    parser.add_argument("--file", help="Single file to process")
    parser.add_argument("--recursive", "-r", action="store_true", help="Process subdirectories recursively")
    parser.add_argument("--force", "-f", action="store_true", help="Force regeneration of descriptions even if cached")
    parser.add_argument("--types", help="Comma-separated list of file extensions to process (e.g., 'jpg,pdf,zip')")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating backups of original files")
    parser.add_argument("--no-markdown", action="store_true", help="Skip creating markdown descriptions")
    parser.add_argument("--clear-cache", action="store_true", help="Clear the cache before processing")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--test", action="store_true", help="Run test mode to verify functionality")
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger("xnamer").setLevel(logging.DEBUG)
    
    # Clear cache if requested
    if args.clear_cache:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            logger.info("Cache cleared.")
    
    # Test mode
    if args.test:
        success = run_test_mode()
        sys.exit(0 if success else 1)
    
    # Process file types
    file_types = None
    if args.types:
        file_types = set()
        for ext in args.types.split(','):
            ext = ext.strip()
            if not ext.startswith('.'):
                ext = f".{ext}"
            file_types.add(ext.lower())
    
    # Process a single file
    if args.file:
        if not os.path.isfile(args.file):
            logger.error(f"Error: {args.file} is not a valid file.")
            sys.exit(1)
        
        result = process_and_rename_file(
            args.file, 
            force=args.force, 
            create_backup=not args.no_backup, 
            create_markdown=not args.no_markdown
        )
        
        if result['success']:
            logger.info(f"Successfully processed: {args.file}")
            if result['renamed']:
                logger.info(f"Renamed to: {result['new_path']}")
        else:
            logger.error(f"Error processing {args.file}: {result.get('error', 'Unknown error')}")
    
    # Process a directory
    elif args.dir:
        if not os.path.isdir(args.dir):
            logger.error(f"Error: {args.dir} is not a valid directory.")
            sys.exit(1)
        
        process_directory(
            args.dir, 
            recursive=args.recursive, 
            force=args.force, 
            file_types=file_types, 
            create_backup=not args.no_backup, 
            create_markdown=not args.no_markdown
        )
    
    # Interactive mode
    else:
        interactive_cli()

if __name__ == "__main__":
    main()