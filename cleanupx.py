#!/usr/bin/env python3
"""
cleanupx_updated.py - Improved file organization tool with forced renaming and document compatibility.

Features:
- Generates alt text for images and embeds it in metadata.
- Renames files with descriptive names based on content analysis.
- Processes text files and document files (.pdf, .docx, etc.) with content-based descriptions.
- Forces file renaming by appending a suffix if the generated name matches the original.
- Uses X.AI API for content analysis with structured output via function calling.
"""

import os
import sys
import json
import logging
import argparse
import base64
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Tuple

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI package not installed. Install with: pip install openai")
    sys.exit(1)

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL/Pillow not installed. Install with: pip install Pillow")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.progress import Progress, TaskID
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Rich not installed. Install with: pip install rich")
    sys.exit(1)

try:
    import inquirer
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False
    print("Inquirer not installed. Install with: pip install inquirer")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize console for rich output
console = Console()

# API Configuration (using hardcoded credentials as requested)
XAI_API_KEY = "xai-8zAk5VIaL3Vxpu3fO3r2aiWqqeVAZ173X04VK2R1m425uYpWOIOQJM3puq1Q38xJ2sHfbq3mX4PBxJXC"
XAI_MODEL_TEXT = "grok-2-latest"
XAI_MODEL_VISION = "grok-2-vision-latest"

# File type constants
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
TEXT_EXTENSIONS = {'.txt', '.md', '.markdown', '.rst', '.text', '.log', '.csv', '.tsv', '.json', '.xml', '.yaml', '.yml', '.html', '.htm', '.py', '.zip'}
MEDIA_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.mp4', '.avi', '.mov', '.mkv'}
DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.doc', '.ppt', '.pptx'}

# Cache and rename log files
CACHE_FILE = "generated_alts.json"
RENAME_LOG_FILE = "rename_log.json"

# Function schemas for API calls
IMAGE_FUNCTION_SCHEMA = {
    "name": "analyze_image",
    "description": "Analyze an image file and return a short title and a detailed alt_text for accessibility.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "A short, descriptive title for the image."
            },
            "alt_text": {
                "type": "string",
                "description": "A detailed description of the image content for accessibility."
            },
            "suggested_filename": {
                "type": "string",
                "description": "A succinct, descriptive filename (without extension) using underscores."
            }
        },
        "required": ["title", "alt_text", "suggested_filename"]
    }
}

# Prompt constants for file analysis
FILE_IMAGE_PROMPT = """Analyze this image carefully and provide:
1. A clear, concise title capturing the main subject.
2. A detailed description covering all visible elements, colors, text, and context.
3. A suggested filename that is descriptive, consisting of 5-7 words, all lowercase with underscores."""

FILE_TEXT_PROMPT = """Analyze this {suffix} file and provide structured information.
File name: {name}
File type: {suffix}

Content:
```
{content}
```

Based on the above content, please provide:
1. A detailed description of what this document contains and its purpose.
2. The type of document (e.g., code, notes, configuration, data).
3. A suggested filename that reflects the content (5-7 words, lowercase with underscores, no extension)."""

FILE_DOCUMENT_PROMPT = """Analyze this document and provide structured information.
File name: {name}
File type: {suffix}

Content:
```
{text_content}
```

Provide:
1. A detailed description of the document's content.
2. The type of document (e.g., report, article, notes).
3. A suggested filename (5-7 words, lowercase with underscores, no extension)."""

# Duplicate prompt system for archives (initially the same as file prompts)
ARCHIVE_IMAGE_PROMPT = FILE_IMAGE_PROMPT
ARCHIVE_TEXT_PROMPT = FILE_TEXT_PROMPT
ARCHIVE_DOCUMENT_PROMPT = FILE_DOCUMENT_PROMPT

DOCUMENT_FUNCTION_SCHEMA = {
    "name": "analyze_document",
    "description": "Analyze a document and return a detailed content description, a document type, and a suggested filename.",
    "parameters": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "A detailed description of the file content."
            },
            "document_type": {
                "type": "string",
                "description": "A classification of the document (e.g., report, article, notes)."
            },
            "suggested_filename": {
                "type": "string",
                "description": "A descriptive filename (without extension, lowercase with underscores)."
            }
        },
        "required": ["description", "document_type", "suggested_filename"]
    }
}

# API request helper
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
            messages = [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                    {"type": "text", "text": prompt}
                ]
            }]
        else:
            messages = [{"role": "user", "content": prompt}]
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[{"type": "function", "function": function_schema}],
            tool_choice={"type": "function", "function": {"name": function_schema["name"]}}
        )
        
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            return json.loads(tool_call.function.arguments)
        
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
                    result["suggested_filename"] = clean_filename(result["title"])
                elif "description" in function_schema["parameters"]["properties"]:
                    desc_match = re.search(r'[Dd]escription:?\s*(.*?)(?:\n|$)', content)
                    result["description"] = desc_match.group(1) if desc_match else content
                    result["document_type"] = "document"
                    result["suggested_filename"] = clean_filename(Path(content).stem)
            return result
        
        return {}
    except Exception as e:
        logger.error(f"Error calling X.AI API: {e}")
        return {}

def encode_image(image_path: Union[str, Path]) -> Optional[str]:
    """Encode image to base64, with resizing if needed."""
    try:
        file_path = Path(image_path)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 5 and PIL_AVAILABLE:
            logger.info(f"Image is too large ({file_size_mb:.1f}MB). Resizing...")
            with Image.open(file_path) as img:
                resized_path = file_path.with_name(f"{file_path.stem}_resized{file_path.suffix}")
                quality = 85
                img.save(resized_path, quality=quality, optimize=True)
                while resized_path.stat().st_size / (1024 * 1024) > 5:
                    width, height = img.size
                    width = int(width * 0.8)
                    height = int(height * 0.8)
                    if width < 100 or height < 100:
                        break
                    resized_img = img.resize((width, height), Image.LANCZOS)
                    resized_img.save(resized_path, quality=quality, optimize=True)
                with open(resized_path, "rb") as f:
                    img_data = f.read()
                try:
                    os.remove(resized_path)
                except:
                    pass
                return base64.b64encode(img_data).decode('utf-8')
        with open(file_path, "rb") as f:
            img_data = f.read()
        return base64.b64encode(img_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {e}")
        return None

def read_text_file(file_path: Union[str, Path], max_chars: int = 10000) -> str:
    """Read content from a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read(max_chars)
    except Exception as e:
        logger.error(f"Error reading text file {file_path}: {e}")
        return ""

def get_image_dimensions(image_path: Union[str, Path]) -> Optional[Tuple[int, int]]:
    """Get the dimensions of an image file."""
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        logger.error(f"Error getting dimensions for {image_path}: {e}")
        return None

def convert_heic_to_jpeg(file_path: Union[str, Path]) -> Optional[Path]:
    """Convert HEIC image to JPEG format."""
    file_path = Path(file_path)
    if file_path.suffix.lower() not in {'.heic', '.heif'}:
        return file_path
    try:
        try:
            import pillow_heif
            console.print("[yellow]Converting HEIC/HEIF to JPEG using pillow_heif...[/yellow]")
            pillow_heif.register_heif_opener()
            with Image.open(file_path) as img:
                jpeg_path = file_path.with_suffix(".jpg")
                img.save(jpeg_path, "JPEG", quality=90)
            console.print("[green]HEIC conversion successful.[/green]")
            return jpeg_path
        except ImportError:
            pass
        try:
            import pyheif
            console.print("[yellow]Converting HEIC/HEIF to JPEG using pyheif...[/yellow]")
            heif_file = pyheif.read(file_path)
            image = Image.frombytes(
                heif_file.mode, 
                heif_file.size, 
                heif_file.data,
                "raw",
                heif_file.mode,
                heif_file.stride,
            )
            jpeg_path = file_path.with_suffix(".jpg")
            image.save(jpeg_path, "JPEG", quality=90)
            console.print("[green]HEIC conversion successful.[/green]")
            return jpeg_path
        except ImportError:
            console.print("[yellow]Neither pillow_heif nor pyheif are installed. Skipping HEIC conversion.[/yellow]")
            console.print("[yellow]To enable HEIC support, install one of these packages:[/yellow]")
            console.print("[yellow]  pip install pillow-heif[/yellow]")
            console.print("[yellow]  pip install pyheif[/yellow]")
            return file_path
    except Exception as e:
        console.print(f"[bold red]Error converting HEIC image: {e}[/bold red]")
        return file_path

def clean_filename(text: str, max_length: int = 50) -> str:
    """Clean text to make a valid filename."""
    clean = re.sub(r'[^\w\s-]', '', text.lower())
    clean = re.sub(r'[-\s]+', '_', clean).strip('_')
    if len(clean) > max_length:
        clean = clean[:max_length]
    if not clean:
        clean = "unnamed_file"
    return clean

def embed_alt_text_into_image(image_path: Path, alt_text: str) -> None:
    """Embed alt text as metadata in an image file."""
    try:
        if not PIL_AVAILABLE:
            logger.warning("PIL/Pillow not installed. Cannot embed alt text.")
            return
        with Image.open(image_path) as img:
            exif_data = img.info.get('exif', b'')
            img.info['alt_text'] = alt_text
            img.save(image_path, exif=exif_data, quality=95)
            logger.info(f"Alt text embedded in {image_path}")
    except Exception as e:
        logger.error(f"Error embedding alt text in {image_path}: {e}")

def load_cache() -> Dict[str, str]:
    """Load the cache file if it exists, otherwise return an empty dictionary."""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading cache: {e}")
    return {}

def save_cache(cache: Dict[str, str]) -> None:
    """Save the cache dictionary to the cache file."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving cache: {e}")

def load_rename_log() -> Dict:
    """Load the rename log file if it exists, otherwise return an empty log."""
    try:
        if os.path.exists(RENAME_LOG_FILE):
            with open(RENAME_LOG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading rename log: {e}")
    return {"renames": [], "timestamp": ""}

def save_rename_log(log: Dict) -> None:
    """Save the rename log to the log file."""
    try:
        with open(RENAME_LOG_FILE, 'w') as f:
            json.dump(log, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving rename log: {e}")

# New: Document file helper functions
def extract_text_from_docx(file_path: Union[str, Path]) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ""

def extract_text_from_pdf(file_path: Union[str, Path]) -> str:
    try:
        import PyPDF2
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted
            return text
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ""

# File analysis functions
def analyze_image(image_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    file_path = Path(image_path)
    if file_path.suffix.lower() in {'.heic', '.heif'}:
        converted_path = convert_heic_to_jpeg(file_path)
        if converted_path and converted_path != file_path:
            file_path = converted_path
    image_data = encode_image(file_path)
    if not image_data:
        logger.error(f"Failed to encode image: {file_path}")
        return None
    prompt = FILE_IMAGE_PROMPT
    result = call_xai_api(XAI_MODEL_VISION, prompt, IMAGE_FUNCTION_SCHEMA, image_data)
    if result:
        logger.info(f"Successfully analyzed image: {file_path.name}")
        return result
    logger.error(f"Failed to analyze image: {file_path.name}")
    return None

def analyze_text_file(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    file_path = Path(file_path)
    content = read_text_file(file_path)
    if not content.strip():
        logger.error(f"No content found in {file_path}")
        return None
    prompt = FILE_TEXT_PROMPT.format(suffix=file_path.suffix, name=file_path.name, content=content[:10000])
    result = call_xai_api(XAI_MODEL_TEXT, prompt, DOCUMENT_FUNCTION_SCHEMA)
    if result:
        logger.info(f"Successfully analyzed text file: {file_path.name}")
        return result
    logger.error(f"Failed to analyze text file: {file_path.name}")
    return None

def generate_new_filename(file_path: Union[str, Path], description: Optional[Dict[str, Any]] = None) -> Optional[str]:
    file_path = Path(file_path)
    if description and isinstance(description, dict):
        suggested_name = description.get("suggested_filename")
        if suggested_name and isinstance(suggested_name, str):
            clean_name = clean_filename(suggested_name)
            return f"{clean_name}{file_path.suffix}"
    ext = file_path.suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        dimensions = get_image_dimensions(file_path)
        if dimensions:
            width, height = dimensions
            fallback_name = f"{file_path.stem}_{width}x{height}"
        else:
            fallback_name = file_path.stem
    else:
        fallback_name = clean_filename(file_path.stem)
    return f"{fallback_name}{file_path.suffix}"

def rename_file(original_path: Path, new_name: str, rename_log: Optional[Dict] = None) -> Optional[Path]:
    """
    Rename a file, forcing a new name if the generated name equals the original.
    The rename log is updated if provided.
    """
    try:
        if not os.path.splitext(new_name)[1]:
            new_name = f"{new_name}{original_path.suffix}"
        new_path = original_path.parent / new_name
        counter = 1
        base_name, ext = os.path.splitext(new_name)
        # Force renaming if new_path equals original_path
        if new_path == original_path:
            new_name = f"{base_name}_renamed{ext}"
            new_path = original_path.parent / new_name
            logger.info(f"Forced rename: changing {original_path.name} to {new_path.name}")
        while new_path.exists() and new_path != original_path:
            new_name = f"{base_name}_{counter}{ext}"
            new_path = original_path.parent / new_name
            counter += 1
        try:
            os.replace(str(original_path), str(new_path))
            logger.info(f"Renamed: {original_path} -> {new_path}")
        except OSError:
            logger.warning(f"Atomic rename failed, falling back to copy + delete for {original_path}")
            try:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(str(original_path), str(new_path))
                if new_path.exists() and new_path.stat().st_size == original_path.stat().st_size:
                    original_path.unlink()
                    logger.info(f"Completed copy + delete rename from {original_path} to {new_path}")
                else:
                    raise OSError("File copy verification failed")
            except Exception as e:
                logger.error(f"Copy + delete rename failed: {e}")
                if new_path.exists():
                    try:
                        new_path.unlink()
                    except:
                        pass
                return None
        if rename_log is not None:
            rename_entry = {
                "original_path": str(original_path),
                "new_path": str(new_path),
                "timestamp": datetime.now().isoformat()
            }
            rename_log["renames"].append(rename_entry)
        return new_path
    except Exception as e:
        logger.error(f"Error renaming file {original_path}: {e}")
        return None

def process_image_file(file_path: Path, cache: Dict[str, Any], web_search: bool = False) -> Optional[Dict[str, Any]]:
    try:
        cache_key = str(file_path)
        if cache_key in cache:
            logger.info(f"Using cached description for {file_path.name}")
            data = cache[cache_key]
        else:
            logger.info(f"Analyzing image: {file_path.name}")
            analysis = analyze_image(file_path)
            if not analysis:
                logger.warning(f"Failed to analyze image: {file_path.name}")
                return None
            data = analysis
            if not data:
                logger.warning(f"No analysis data generated for image: {file_path.name}")
                return None
            cache[cache_key] = data
        alt_text = data.get("alt_text")
        if not alt_text:
            logger.warning(f"Failed to get alt text for image: {file_path.name}")
            return None
        try:
            from PIL import Image, PngImagePlugin
            with Image.open(file_path) as img:
                new_img = img.copy()
                if isinstance(new_img.info, dict):
                    new_img.info["Description"] = alt_text
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if file_size_mb > 5:
                    logger.info(f"Image size ({file_size_mb:.2f} MB) exceeds limit. Resizing...")
                    width, height = new_img.size
                    quality = 85
                    temp_path = file_path.parent / f"{file_path.stem}_temp{file_path.suffix}"
                    target_size_mb = 4.5
                    size_ratio = (target_size_mb / file_size_mb) ** 0.5
                    new_width = int(width * size_ratio)
                    new_height = int(height * size_ratio)
                    if new_width < 100 or new_height < 100:
                        new_width = max(100, new_width)
                        new_height = max(100, new_height)
                    resized_img = new_img.resize((new_width, new_height), Image.LANCZOS)
                    resized_img.save(temp_path, quality=quality, optimize=True)
                    new_size_mb = temp_path.stat().st_size / (1024 * 1024)
                    if new_size_mb > 5:
                        logger.warning(f"Resized image still too large ({new_size_mb:.2f} MB). Using original image.")
                        temp_path.unlink()
                    else:
                        new_img = resized_img
                        logger.info(f"Image resized to {new_width}x{new_height}")
                new_img.save(file_path)
        except Exception as e:
            logger.warning(f"Failed to embed metadata in image: {e}")
            return None
        new_filename = generate_new_filename(file_path, data)
        if not new_filename:
            logger.warning(f"Failed to generate new filename for image: {file_path.name}")
            return None
        try:
            new_path = file_path.parent / new_filename
            if new_path != file_path:
                file_path.rename(new_path)
                logger.info(f"Renamed {file_path.name} to {new_filename}")
                if cache_key in cache:
                    cache[str(new_path)] = cache.pop(cache_key)
                return {"old_path": file_path, "new_path": new_path, "analysis": data}
            return {"old_path": file_path, "new_path": file_path, "analysis": data}
        except Exception as e:
            logger.warning(f"Failed to rename file {file_path.name}: {e}")
            return None
    except Exception as e:
        logger.warning(f"Error processing image {file_path.name}: {e}")
        return None

def process_text_file(file_path: Union[str, Path], cache: Dict[str, str], rename_log: Dict) -> Tuple[Path, Optional[Path], Optional[Dict]]:
    file_path = Path(file_path)
    cache_key = str(file_path)
    cached_result = cache.get(cache_key)
    description = None
    if cached_result:
        try:
            if isinstance(cached_result, str):
                description = json.loads(cached_result)
            else:
                description = cached_result
            logger.info(f"Using cached description for {file_path}")
        except json.JSONDecodeError:
            description = None
    if not description:
        description = analyze_text_file(file_path)
        if description:
            cache[cache_key] = description
            save_cache(cache)
    if not description:
        logger.warning(f"Could not analyze text file: {file_path}")
        return file_path, None, None
    new_name = generate_new_filename(file_path, description)
    new_path = None
    if new_name:
        new_path = rename_file(file_path, new_name, rename_log)
        if new_path and new_path != file_path and cache_key in cache:
            cache[str(new_path)] = cache[cache_key]
            del cache[cache_key]
            save_cache(cache)
    return file_path, new_path, description

# New: Process document file for PDFs, DOCX, etc.
def process_document_file(file_path: Union[str, Path], cache: Dict[str, str], rename_log: Dict) -> Tuple[Path, Optional[Path], Optional[Dict]]:
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    if ext == ".docx":
        text_content = extract_text_from_docx(file_path)
    elif ext == ".pdf":
        text_content = extract_text_from_pdf(file_path)
    else:
        text_content = read_text_file(file_path)
    if not text_content.strip():
        logger.error(f"No text could be extracted from {file_path}")
        return file_path, None, None
    prompt = FILE_DOCUMENT_PROMPT.format(name=file_path.name, suffix=ext, text_content=text_content[:10000])
    result = call_xai_api(XAI_MODEL_TEXT, prompt, DOCUMENT_FUNCTION_SCHEMA)
    description = result
    cache_key = str(file_path)
    if description:
        cache[cache_key] = description
        save_cache(cache)
    new_name = generate_new_filename(file_path, description)
    new_path = None
    if new_name:
        new_path = rename_file(file_path, new_name, rename_log)
        if new_path and new_path != file_path and cache_key in cache:
            cache[str(new_path)] = cache[cache_key]
            del cache[cache_key]
            save_cache(cache)
    return file_path, new_path, description

def get_media_dimensions(file_path: Union[str, Path]) -> Optional[Tuple[int, int]]:
    try:
        import cv2
        cap = cv2.VideoCapture(str(file_path))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        return width, height
    except Exception as e:
        logger.error(f"Error getting media dimensions: {e}")
        return None

def get_media_duration(file_path: Union[str, Path]) -> Optional[float]:
    try:
        import cv2
        cap = cv2.VideoCapture(str(file_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else None
        cap.release()
        return duration
    except Exception as e:
        logger.error(f"Error getting media duration: {e}")
        return None

def format_duration(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def process_media_file(file_path: Union[str, Path], cache: Dict[str, str], rename_log: Dict) -> Tuple[Path, Optional[Path], Optional[Dict]]:
    file_path = Path(file_path)
    duration = get_media_duration(file_path)
    dimensions = get_media_dimensions(file_path)
    if dimensions:
        resolution = f"{dimensions[0]}x{dimensions[1]}"
    else:
        resolution = "unknown"
    if duration:
        duration_str = format_duration(duration)
    else:
        duration_str = "unknown"
    if file_path.suffix.lower() in {'.mp3', '.wav', '.ogg', '.flac', '.mp4', '.avi', '.mov', '.mkv'}:
        new_name = f"{file_path.stem}_{resolution}_{duration_str}{file_path.suffix}"
    elif file_path.suffix.lower() in IMAGE_EXTENSIONS:
        new_name = f"{file_path.stem}_{resolution}{file_path.suffix}"
    else:
        return file_path, None, None
    new_path = rename_file(file_path, new_name, rename_log)
    return file_path, new_path, None

def process_file(file_path: Union[str, Path], cache: Dict[str, str], rename_log: Dict) -> Tuple[Path, Optional[Path], Optional[Dict]]:
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    if ext in MEDIA_EXTENSIONS:
        return process_media_file(file_path, cache, rename_log)
    elif ext in IMAGE_EXTENSIONS:
        return process_image_file(file_path, cache)
    elif ext in TEXT_EXTENSIONS:
        return process_text_file(file_path, cache, rename_log)
    elif ext in DOCUMENT_EXTENSIONS:
        return process_document_file(file_path, cache, rename_log)
    else:
        logger.info(f"Skipping unsupported file type: {file_path}")
        return file_path, None, None

def process_directory(directory: Union[str, Path], recursive: bool = False, skip_renamed: bool = True) -> Dict[str, int]:
    directory = Path(directory)
    stats = {
        "images": 0,
        "text": 0,
        "documents": 0,
        "skipped": 0,
        "failed": 0,
        "total": 0
    }
    cache = load_cache()
    rename_log = load_rename_log()
    renamed_paths = set()
    if skip_renamed:
        for entry in rename_log.get("renames", []):
            renamed_paths.add(entry.get("original_path"))
    files = []
    if recursive:
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                files.append(Path(root) / filename)
    else:
        files = [f for f in directory.iterdir() if f.is_file()]
    if RICH_AVAILABLE:
        with Progress() as progress:
            task = progress.add_task("[cyan]Processing files...", total=len(files))
            for file_path in files:
                progress.update(task, advance=1, description=f"Processing {file_path.name}")
                if skip_renamed and str(file_path) in renamed_paths:
                    stats["skipped"] += 1
                    continue
                ext = file_path.suffix.lower()
                stats["total"] += 1
                try:
                    orig_path, new_path, description = process_file(file_path, cache, rename_log)
                    if new_path:
                        if ext in IMAGE_EXTENSIONS:
                            stats["images"] += 1
                        elif ext in TEXT_EXTENSIONS:
                            stats["text"] += 1
                        elif ext in DOCUMENT_EXTENSIONS:
                            stats["documents"] += 1
                    else:
                        stats["failed"] += 1
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    stats["failed"] += 1
                save_rename_log(rename_log)
    else:
        for i, file_path in enumerate(files):
            print(f"Processing {i+1}/{len(files)}: {file_path.name}")
            if skip_renamed and str(file_path) in renamed_paths:
                stats["skipped"] += 1
                continue
            ext = file_path.suffix.lower()
            stats["total"] += 1
            try:
                orig_path, new_path, description = process_file(file_path, cache, rename_log)
                if new_path:
                    if ext in IMAGE_EXTENSIONS:
                        stats["images"] += 1
                    elif ext in TEXT_EXTENSIONS:
                        stats["text"] += 1
                    elif ext in DOCUMENT_EXTENSIONS:
                        stats["documents"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats["failed"] += 1
            if i % 10 == 0:
                save_rename_log(rename_log)
    save_rename_log(rename_log)
    return stats

def interactive_mode():
    console.print("[bold cyan]Welcome to cleanupx (updated)![/bold cyan]")
    console.print("This tool helps organize your files by analyzing their content and renaming them appropriately.\n")
    questions = [
        inquirer.Path(
            'directory',
            message="Enter the directory path to process",
            exists=True,
            path_type=inquirer.Path.DIRECTORY,
        ),
        inquirer.List(
            'scope',
            message="How would you like to process the directory?",
            choices=[
                ('Current directory only', 'single'),
                ('Include subdirectories (recursive)', 'recursive')
            ],
        ),
        inquirer.List(
            'renamed_files',
            message="How should previously renamed files be handled?",
            choices=[
                ('Skip previously renamed files', 'skip'),
                ('Process all files', 'all')
            ],
        ),
        inquirer.List(
            'cache',
            message="How should the cache be handled?",
            choices=[
                ('Use existing cache', 'use'),
                ('Clear cache before starting', 'clear')
            ],
        ),
        inquirer.Checkbox(
            'file_types',
            message="Which file types would you like to process?",
            choices=[
                ('Images (jpg, png, etc.)', 'images'),
                ('Text files (txt, md, etc.)', 'text'),
                ('Documents (pdf, docx, etc.)', 'documents')
            ],
            default=['images', 'text', 'documents']
        ),
        inquirer.Confirm(
            'proceed',
            message="Ready to start processing?",
            default=True
        ),
    ]
    try:
        answers = inquirer.prompt(questions)
        if not answers or not answers['proceed']:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
            return 1
        directory = Path(answers['directory'])
        recursive = answers['scope'] == 'recursive'
        skip_renamed = answers['renamed_files'] == 'skip'
        clear_cache = answers['cache'] == 'clear'
        selected_types = set(answers['file_types'])
        if clear_cache and os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            console.print("[yellow]Cache cleared[/yellow]")
        global IMAGE_EXTENSIONS, TEXT_EXTENSIONS, DOCUMENT_EXTENSIONS
        if 'images' not in selected_types:
            IMAGE_EXTENSIONS = set()
        if 'text' not in selected_types:
            TEXT_EXTENSIONS = set()
        if 'documents' not in selected_types:
            DOCUMENT_EXTENSIONS = set()
        console.print(f"\n[bold]Processing directory: {directory}[/bold]")
        console.print(f"Recursive: {recursive}")
        console.print(f"Skip renamed: {skip_renamed}")
        console.print(f"Selected file types: {', '.join(selected_types)}\n")
        stats = process_directory(directory, recursive=recursive, skip_renamed=skip_renamed)
        console.print("\n[bold green]Processing complete![/bold green]")
        console.print(f"[cyan]Total files processed:[/cyan] {stats['total']}")
        console.print(f"[cyan]Images processed:[/cyan] {stats['images']}")
        console.print(f"[cyan]Text files processed:[/cyan] {stats['text']}")
        console.print(f"[cyan]Documents processed:[/cyan] {stats['documents']}")
        console.print(f"[cyan]Files skipped:[/cyan] {stats['skipped']}")
        console.print(f"[cyan]Files failed:[/cyan] {stats['failed']}")
        if stats['total'] > 0:
            show_log = inquirer.confirm(
                message="Would you like to see the rename log?",
                default=False
            )
            if show_log:
                rename_log = load_rename_log()
                if rename_log and rename_log.get("renames"):
                    console.print("\n[bold]Rename Log:[/bold]")
                    for entry in rename_log["renames"]:
                        original = Path(entry["original_path"]).name
                        new = Path(entry["new_path"]).name
                        console.print(f"[yellow]{original}[/yellow] → [green]{new}[/green]")
                else:
                    console.print("\n[yellow]No rename log entries found[/yellow]")
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        return 1

def main():
    parser = argparse.ArgumentParser(
        description="Process images, text files, and documents to generate descriptions and rename them."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        help="Directory containing files to process"
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Process subdirectories recursively"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Process all files, including previously renamed ones"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache before processing"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    args = parser.parse_args()
    if not args.directory or args.interactive:
        return interactive_mode()
    directory = Path(args.directory)
    if not directory.is_dir():
        console.print(f"[bold red]Error: {directory} is not a valid directory[/bold red]")
        return 1
    if args.clear_cache and os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        console.print("[yellow]Cache cleared[/yellow]")
    console.print(f"[bold]Processing directory: {directory}[/bold]")
    console.print(f"Recursive: {args.recursive}")
    console.print(f"Skip renamed: {not args.force}")
    stats = process_directory(directory, recursive=args.recursive, skip_renamed=not args.force)
    console.print("\n[bold green]Processing complete![/bold green]")
    console.print(f"[cyan]Total files processed:[/cyan] {stats['total']}")
    console.print(f"[cyan]Images processed:[/cyan] {stats['images']}")
    console.print(f"[cyan]Text files processed:[/cyan] {stats['text']}")
    console.print(f"[cyan]Documents processed:[/cyan] {stats['documents']}")
    console.print(f"[cyan]Files skipped:[/cyan] {stats['skipped']}")
    console.print(f"[cyan]Files failed:[/cyan] {stats['failed']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())