
"""
xai_alt.py - Process image files in a directory to generate comprehensive alt text.

This script:
1. Scans a directory for image files (optionally recursively)
2. Uses X.AI Vision API (grok-2-vision-latest) to generate detailed alt text for each image
3. Creates a markdown file with the same name as each image containing the alt text.
   If a .md file already exists (indicating prior processing), the image is skipped and the
   existing markdown file is copied to the .cleanupx log folder.
   (You can override this behavior with the --override-md option.)
4. Maintains a cache file (alt_text_cache.json) to avoid re-processing images
5. Optionally renames image files based on their content
6. Provides an interactive CLI for directory selection and processing options
7. [Test Option] When enabled, checks image metadata before and after embedding alt text

Usage:
  python xai_alt.py                      # Run in interactive CLI mode
  python xai_alt.py --dir PATH [--recursive] [--force] [--rename] [--override-md] [--test]  # Process directory with options
"""

import os
import sys
import json
import argparse
import time
import base64
import gc
import tempfile
import shutil
from io import BytesIO
from pathlib import Path
import openai
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- Check for optional dependencies ---
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/Pillow not installed. Some features will be limited. Install with: pip install Pillow")

try:
    import pyheif
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False
    logger.warning("pyheif not installed. HEIC/HEIF conversion will be limited. Install with: pip install pyheif")

# Optional dependency for better JPEG metadata handling
try:
    import piexif
    PIEEXIF_AVAILABLE = True
except ImportError:
    PIEEXIF_AVAILABLE = False
    logger.warning("piexif not installed. Extended metadata embedding for JPEG images may not work as expected. Install with: pip install piexif")

# --- Configuration and Setup ---
# NOTE: In production, do not hardcode your API key; use environment variables instead.
XAI_API_KEY = "xai-8zAk5VIaL3Vxpu3fO3r2aiWqqeVAZ173X04VK2R1m425uYpWOIOQJM3puq1Q38xJ2sHfbq3mX4PBxJXC"
client = openai.Client(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

# Cache file for storing generated alt texts
CACHE_FILE = "alt_text_cache.json"

# Image file extensions to process
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif', '.heic', '.heif'}

# Maximum file size to process in MB
MAX_FILE_SIZE_MB = 25

# Timeout for image processing (in seconds)
PROCESS_TIMEOUT = 30

# Prompt text used for alt text generation
PROMPT_TEXT = (
    "You are an AI specializing in describing images for accessibility purposes. "
    "Write comprehensive alt text for this image, as though for a blind engineer who needs "
    "to understand every detail of the information including text. "
    "Also suggest a descriptive filename based on the content of the image. "
    "Format your response in this exact JSON structure:\n"
    "{\n"
    "  \"description\": \"A comprehensive description of every detail of the image as well as tones, themes, cultural references, and other relevant information, capturing all text and technical details as though for a blind engineer who needs to understand maps and schematics.\",\n"
    "  \"alt_text\": \"A comprehensive description of the image, including all that would be wanted as alt text, under 1000 characters.\",\n"
    "  \"suggested_filename\": \"descriptive_filename_without_extension_six_to_twelve_words\",\n"
    "  \"tags\": [\"tag1\", \"tag2\", ...]\n"
    "}"
)

# --- Helper Functions ---

def load_cache():
    """Load the alt text cache if it exists."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as fp:
            return json.load(fp)
    return {}

def save_cache(cache):
    """Save the alt text cache to file."""
    with open(CACHE_FILE, "w", encoding="utf-8") as fp:
        json.dump(cache, fp, indent=4, ensure_ascii=False)

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
            jpeg_path = image_path.with_suffix('.jpg')
            temp_path = Path(tempfile.gettempdir()) / f"temp_{image_path.stem}.jpg"
            
            # Don't overwrite existing files
            if jpeg_path.exists():
                jpeg_path = image_path.with_name(f"{image_path.stem}_converted.jpg")
            
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
        import subprocess
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
        import subprocess
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

def convert_gif_to_jpeg(image_path):
    """
    Convert GIF to JPEG format for processing.
    Uses the first frame of the GIF.
    
    Args:
        image_path: Path to the GIF image
        
    Returns:
        Path to the converted JPEG image or None if conversion failed
    """
    image_path = Path(image_path)
    
    # Method 1: using PIL/Pillow
    if PIL_AVAILABLE:
        try:
            temp_path = Path(tempfile.gettempdir()) / f"temp_{image_path.stem}.jpg"
            with Image.open(image_path) as img:
                # Take first frame of GIF
                img.seek(0)
                img = img.convert("RGB")
                img.save(temp_path, "JPEG", quality=95)
                logger.info(f"Converted GIF to JPEG: {image_path} -> {temp_path}")
                return temp_path
        except Exception as e:
            logger.error(f"Error converting GIF to JPEG using PIL: {e}")
    
    # Method 2: using system commands
    try:
        import subprocess
        temp_path = Path(tempfile.gettempdir()) / f"temp_{image_path.stem}.jpg"
        
        # Try using ImageMagick's convert (with [0] to extract first frame)
        subprocess.run(['convert', f"{image_path}[0]", str(temp_path)], 
                       check=True, capture_output=True)
        if temp_path.exists():
            logger.info(f"Converted GIF to JPEG using ImageMagick: {image_path} -> {temp_path}")
            return temp_path
    except Exception as e:
        logger.error(f"Error converting GIF to JPEG using system commands: {e}")
    
    logger.error(f"Failed to convert GIF image: {image_path}")
    return None

def get_image_dimensions(image_path):
    """
    Get the dimensions of an image.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Tuple of (width, height) or None if dimensions could not be determined
    """
    image_path = Path(image_path)
    
    # Method 1: using PIL/Pillow
    if PIL_AVAILABLE:
        try:
            with Image.open(image_path) as img:
                return img.width, img.height
        except Exception as e:
            logger.error(f"Error getting image dimensions using PIL: {e}")
    
    # Method 2: using system commands
    try:
        import subprocess
        
        # Try using identify from ImageMagick
        result = subprocess.run(['identify', '-format', '%w %h', str(image_path)], 
                                capture_output=True, text=True, check=True)
        width, height = map(int, result.stdout.strip().split())
        return width, height
    except Exception as e:
        logger.error(f"Error getting image dimensions using system commands: {e}")
    
    return None

def resize_large_image(image_path, max_dimension=2000, quality=85):
    """
    Resize a large image to prevent memory issues.
    
    Args:
        image_path: Path to the image file
        max_dimension: Maximum width or height
        quality: JPEG quality for the resized image
        
    Returns:
        Path to the resized image or None if resizing failed
    """
    if not PIL_AVAILABLE:
        logger.warning("PIL/Pillow not available, skipping image resizing")
        return None
    
    image_path = Path(image_path)
    
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            
            # Only resize if the image is larger than max_dimension
            if width <= max_dimension and height <= max_dimension:
                return None
            
            # Calculate new dimensions
            ratio = min(max_dimension / width, max_dimension / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            # Resize the image
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Save the resized image
            temp_path = Path(tempfile.gettempdir()) / f"temp_resized_{image_path.name}"
            if image_path.suffix.lower() in ('.jpg', '.jpeg'):
                resized_img.save(temp_path, "JPEG", quality=quality)
            else:
                resized_img.save(temp_path, quality=quality)
            
            logger.info(f"Resized image: {image_path.name} ({width}x{height} -> {new_width}x{new_height})")
            return temp_path
    except Exception as e:
        logger.error(f"Error resizing image: {e}")
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

def check_alt_metadata(image_path):
    """
    Check and return the alt metadata from an image.
    
    Args:
        image_path: Path to the image file
    Returns:
        Alt metadata string if available, otherwise "Not present"
    """
    try:
        with Image.open(image_path) as img:
            return img.info.get("alt", "Not present")
    except Exception as e:
        logger.error(f"Failed to read alt metadata from {image_path}: {e}")
        return "Error"

def copy_md_to_log(md_file_path):
    """
    Copy an existing markdown file to the .cleanupx log folder.
    
    Args:
        md_file_path: Path to the markdown file
        
    Returns:
        Destination path of the copied markdown file or None if copy failed.
    """
    try:
        md_file_path = Path(md_file_path)
        log_folder = md_file_path.parent / ".cleanupx"
        log_folder.mkdir(parents=True, exist_ok=True)
        dest_file = log_folder / md_file_path.name
        if dest_file.exists():
            base = dest_file.stem
            ext = dest_file.suffix
            counter = 1
            while (log_folder / f"{base}_{counter}{ext}").exists():
                counter += 1
            dest_file = log_folder / f"{base}_{counter}{ext}"
        shutil.copy2(md_file_path, dest_file)
        logger.info(f"Copied existing markdown {md_file_path} to log folder {dest_file}")
        return dest_file
    except Exception as e:
        logger.error(f"Error copying markdown file {md_file_path} to log folder: {e}")
        return None

class TimeoutError(Exception):
    """Exception raised when a function times out."""
    pass

def timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutError("Function timed out")

def with_timeout(seconds):
    """Decorator that applies a timeout to a function."""
    import signal
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Set the timeout handler
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
                # Disable the alarm if function completes
                signal.alarm(0)
                return result
            except TimeoutError:
                raise
            finally:
                # Ensure the alarm is disabled
                signal.alarm(0)
        
        return wrapper
    
    return decorator

def generate_alt_text(image_path):
    """
    Call the X.AI API with the image and prompt.
    Returns the generated alt text (dictionary) if successful; otherwise, returns None.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Generated description dictionary or None if an error occurred
    """
    original_path = Path(image_path)
    analysis_path = original_path
    temp_converted = None
    
    logger.info(f"Analyzing image: {original_path.name}")
    
    try:
        # Check file size
        file_size_mb = os.path.getsize(original_path) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            logger.error(f"Image too large ({file_size_mb:.1f} MB > {MAX_FILE_SIZE_MB} MB): {original_path}")
            return None
        
        # Convert HEIC/HEIF to JPEG for analysis
        if original_path.suffix.lower() in {'.heic', '.heif'}:
            jpeg_path = convert_heic_to_jpeg(original_path)
            if jpeg_path and jpeg_path != original_path:
                analysis_path = jpeg_path
                temp_converted = jpeg_path
        
        # Convert WebP to JPEG for analysis
        elif original_path.suffix.lower() == '.webp':
            jpeg_path = convert_webp_to_jpeg(original_path)
            if jpeg_path and jpeg_path != original_path:
                analysis_path = jpeg_path
                temp_converted = jpeg_path
        
        # Convert GIF to JPEG (first frame) for analysis
        elif original_path.suffix.lower() == '.gif':
            jpeg_path = convert_gif_to_jpeg(original_path)
            if jpeg_path and jpeg_path != original_path:
                analysis_path = jpeg_path
                temp_converted = jpeg_path
        
        # Resize large images to prevent memory issues
        if file_size_mb > 10:
            resized_path = resize_large_image(analysis_path)
            if resized_path:
                if temp_converted and temp_converted != analysis_path:
                    cleanup_temp_files(temp_converted)
                temp_converted = resized_path
                analysis_path = resized_path
        
        # Encode the image to base64
        base64_image = encode_image(analysis_path)
        if not base64_image:
            logger.error(f"Failed to encode image: {analysis_path}")
            cleanup_temp_files(temp_converted)
            return None
        
        # Call API with timeout protection
        try:
            # Implement a timeout mechanism with a context manager if possible
            # For this example, we'll use a simple approach
            import signal
            
            # Define timeout handler
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Image analysis timed out after {PROCESS_TIMEOUT} seconds")
            
            # Set the timeout alarm
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(PROCESS_TIMEOUT)
            
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
                            "text": PROMPT_TEXT
                        }
                    ]
                }
            ]
            
            completion = client.chat.completions.create(
                model="grok-2-vision-latest",
                messages=messages,
                temperature=0.01,
                response_format={"type": "json_object"}
            )
            
            # Turn off the alarm
            signal.alarm(0)
            
            generated_text = completion.choices[0].message.content.strip()
            
            # Parse JSON
            try:
                result = json.loads(generated_text)
                logger.info(f"Successfully analyzed image: {original_path.name}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {e}")
                logger.debug(f"Raw response: {generated_text}")
                # Try to extract JSON if it's embedded in the response
                import re
                json_match = re.search(r'{[\s\S]*}', generated_text)
                if json_match:
                    try:
                        result = json.loads(json_match.group(0))
                        return result
                    except:
                        pass
                return None
            
        except TimeoutError as e:
            logger.error(f"Image analysis timed out: {original_path.name}")
            return None
        except Exception as e:
            logger.error(f"Error during API call: {e}")
            return None
        
    except Exception as e:
        logger.error(f"Error generating alt text for {original_path}: {e}")
        return None
    finally:
        # Clean up temporary files
        cleanup_temp_files(temp_converted)
        
        # Force garbage collection to prevent memory issues with large images
        gc.collect()

def get_cache_key(file_path):
    """
    Create a unique cache key for an image file based on its path and modification time.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        String cache key
    """
    stats = os.stat(file_path)
    mod_time = stats.st_mtime
    return f"{file_path}:{mod_time}"

def scan_directory(directory, recursive=False):
    """
    Scan a directory for image files.
    
    Args:
        directory: Path to directory to scan
        recursive: Whether to scan subdirectories recursively
        
    Returns:
        List of image file paths
    """
    image_files = []
    
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path) and os.path.splitext(file_path)[1].lower() in IMAGE_EXTENSIONS:
                    image_files.append(file_path)
    else:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and os.path.splitext(file_path)[1].lower() in IMAGE_EXTENSIONS:
                image_files.append(file_path)
    
    return image_files

def clean_filename(filename):
    """
    Clean a filename to be safe for file systems.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Replace characters that are not allowed in filenames
    import re
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

def generate_new_filename(file_path, description):
    """
    Generate a new filename based on image description.
    
    Args:
        file_path: Path to the image file
        description: Dictionary with image description
        
    Returns:
        New filename with extension
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    
    # Get suggested name from description
    if description and isinstance(description, dict):
        suggested_name = description.get("suggested_filename")
        if suggested_name and isinstance(suggested_name, str):
            base_name = clean_filename(suggested_name)
        else:
            base_name = clean_filename(file_path.stem)
    else:
        base_name = clean_filename(file_path.stem)
    
    # Optionally add dimensions
    dimensions = get_image_dimensions(file_path)
    if dimensions:
        width, height = dimensions
        return f"{base_name}_{width}x{height}{ext}"
    else:
        return f"{base_name}{ext}"

def rename_file(original_path, new_name):
    """
    Rename a file with a new name.
    
    Args:
        original_path: Original file path
        new_name: New filename (with extension)
        
    Returns:
        Path to renamed file or None if rename failed
    """
    original_path = Path(original_path)
    new_path = original_path.parent / new_name
    
    # Don't rename if the new name is the same as the old one
    if original_path.name == new_name:
        return original_path
    
    # Don't overwrite existing files
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

def embed_alt_text_into_image(image_path, alt_text):
    """
    Embed alt text into image metadata if possible.
    
    Args:
        image_path: Path to the image file
        alt_text: Alt text to embed
        
    Returns:
        True if successful, False otherwise

    Note:
        For JPEG images, if piexif is available, the alt text is embedded into the EXIF ImageDescription tag.
        For PNG images, the alt text is added using a PngInfo object.
        For other formats, a fallback approach using the image's info dictionary is attempted.
    """
    if not PIL_AVAILABLE:
        return False
    
    image_path = Path(image_path)
    
    try:
        # Only supports certain formats
        if image_path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp'}:
            return False
        
        # For JPEG images, use piexif to embed metadata if available
        if image_path.suffix.lower() in {'.jpg', '.jpeg'} and PIEEXIF_AVAILABLE:
            exif_dict = piexif.load(str(image_path))
            # Use the ImageDescription (tag 0x010E) to embed alt text
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = alt_text.encode("utf-8")
            exif_bytes = piexif.dump(exif_dict)
            img = Image.open(image_path)
            img.save(image_path, "jpeg", exif=exif_bytes)
        # For PNG images, use PngInfo to add metadata
        elif image_path.suffix.lower() == ".png":
            from PIL.PngImagePlugin import PngInfo
            img = Image.open(image_path)
            pnginfo = PngInfo()
            pnginfo.add_text("alt", alt_text)
            img.save(image_path, pnginfo=pnginfo)
        else:
            # Fallback for other formats: update metadata via the info dictionary
            with Image.open(image_path) as img:
                info = img.info
                info["alt"] = alt_text
                img.save(image_path, **info)
        
        logger.info(f"Embedded alt text into image: {image_path}")
        return True
    except Exception as e:
        logger.error(f"Error embedding alt text into image {image_path}: {e}")
        return False

def create_markdown_file(image_path, description):
    """
    Create a markdown file with the same base name as the image containing the alt text.
    
    Args:
        image_path: Path to the image file
        description: Dictionary with image description
        
    Returns:
        Path to created markdown file
    """
    # Get the base name without extension
    image_path = Path(image_path)
    base_name = image_path.stem
    # Get the directory of the image
    directory = image_path.parent
    # Create markdown file path
    md_file_path = directory / f"{base_name}.md"
    
    # Get dimensions
    dimensions = get_image_dimensions(image_path)
    dimensions_str = f"{dimensions[0]}x{dimensions[1]}" if dimensions else "Unknown"
    
    # Get file size
    try:
        file_size_bytes = os.path.getsize(image_path)
        if file_size_bytes > 1024 * 1024:
            file_size = f"{file_size_bytes / (1024 * 1024):.2f} MB"
        else:
            file_size = f"{file_size_bytes / 1024:.2f} KB"
    except:
        file_size = "Unknown"
    
    # Create markdown content
    content = [
        f"# {base_name}",
        "",
        f"**Description:** {description.get('description', 'No description available')}",
        "",
        f"**Alt Text:** {description.get('alt_text', 'No alt text available')}",
        "",
        "## Metadata",
        f"- **Original Filename:** {image_path.name}",
        f"- **Dimensions:** {dimensions_str}",
        f"- **Format:** {image_path.suffix.upper().replace('.', '')}",
        f"- **Size:** {file_size}",
        "",
        "## Tags",
    ]
    
    # Add tags if available
    tags = description.get('tags', [])
    if tags and isinstance(tags, list):
        for tag in tags:
            content.append(f"- {tag}")
    else:
        content.append("- No tags available")
    
    # Write markdown file
    with open(md_file_path, "w", encoding="utf-8") as fp:
        fp.write('\n'.join(content))
    
    logger.info(f"Created markdown description: {md_file_path}")
    return md_file_path

def process_image_file(image_path, cache, force=False, rename=False, test=False, override_md=False):
    """
    Process a single image file: generate alt text, create markdown file, optionally rename,
    and (if test is enabled) display metadata before and after embedding alt text.
    
    Args:
        image_path: Path to the image file
        cache: Alt text cache dictionary
        force: Whether to force regeneration of alt text even if in cache
        rename: Whether to rename the image file based on description
        test: Whether to check and display metadata before and after embedding alt text
        override_md: Whether to override the check for existing markdown file and reprocess the image
        
    Returns:
        Tuple of (success, message, new_image_path)
    """
    # Convert to Path object
    image_path = Path(image_path)
    
    # Check file extension
    if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
        return False, f"Unsupported file type: {image_path.suffix}", image_path

    # Check if a markdown file already exists for this image and skip processing if not overriding
    md_candidate = image_path.parent / f"{image_path.stem}.md"
    if md_candidate.exists() and not override_md:
        logger.info(f"Markdown file {md_candidate} already exists for {image_path}. Skipping processing.")
        copy_md_to_log(md_candidate)
        return True, f"Skipped processing for {image_path} (existing markdown file copied to log folder)", image_path
    
    # Get cache key for this image
    cache_key = get_cache_key(str(image_path))
    
    # Check if already in cache and not forcing regeneration
    if cache_key in cache and not force:
        logger.info(f"Found cached alt text for {image_path}")
        description = cache[cache_key]
    else:
        logger.info(f"Generating alt text for {image_path}...")
        description = generate_alt_text(image_path)
        
        if not description:
            return False, f"Failed to generate alt text for {image_path}", image_path
        
        # Store in cache (using the original path as key)
        cache[cache_key] = description
        save_cache(cache)
    
    # Track the current path of the image (may change if renamed)
    current_image_path = image_path
    
    # Rename the file if requested
    if rename and description:
        new_filename = generate_new_filename(image_path, description)
        renamed_path = rename_file(image_path, new_filename)
        if renamed_path:
            current_image_path = renamed_path
    
    # Embed alt text into image if possible; also perform test check if enabled
    if PIL_AVAILABLE:
        if test:
            before_alt = check_alt_metadata(current_image_path)
            logger.info(f"Before embedding: alt metadata: {before_alt}")
        try:
            embed_alt_text_into_image(current_image_path, description.get('alt_text', ''))
        except Exception as e:
            logger.error(f"Error embedding alt text: {e}")
        if test:
            after_alt = check_alt_metadata(current_image_path)
            logger.info(f"After embedding: alt metadata: {after_alt}")
    
    # Create markdown file
    md_file_path = create_markdown_file(current_image_path, description)
    
    return True, f"Created {md_file_path}", current_image_path

def process_directory(directory, recursive=False, force=False, rename=False, test=False, override_md=False):
    """
    Process all image files in a directory.
    
    Args:
        directory: Path to directory to process
        recursive: Whether to scan subdirectories recursively
        force: Whether to force regeneration of alt text even if in cache
        rename: Whether to rename image files based on description
        test: Whether to check and display metadata before and after embedding alt text
        override_md: Whether to override existing markdown files and reprocess images
        
    Returns:
        Dictionary with processing statistics
    """
    # Load cache
    cache = load_cache()
    logger.info(f"Cache loaded with {len(cache)} entries")
    
    # Scan directory for image files
    image_files = scan_directory(directory, recursive)
    logger.info(f"Found {len(image_files)} image files in {directory}")
    
    # Initialize statistics
    stats = {
        "total": len(image_files),
        "success": 0,
        "error": 0,
        "renamed": 0
    }
    
    # Process each image
    for i, image_path in enumerate(image_files, 1):
        logger.info(f"\n[{i}/{stats['total']}] Processing {image_path}")
        
        success, message, new_path = process_image_file(image_path, cache, force, rename, test, override_md)
        logger.info(message)
        
        if success:
            stats["success"] += 1
            if new_path != image_path:
                stats["renamed"] += 1
        else:
            stats["error"] += 1
        
        # Sleep briefly to avoid rate limits
        time.sleep(0.5)
    
    # Print summary
    logger.info("\n======= Processing Complete =======")
    logger.info(f"Total images: {stats['total']}")
    logger.info(f"Successfully processed: {stats['success']}")
    logger.info(f"Files renamed: {stats['renamed']}")
    logger.info(f"Errors during processing: {stats['error']}")
    
    return stats

def interactive_cli():
    """Run the interactive CLI mode."""
    print("\nWelcome to X.AI Alt Text Generator!")
    print("This script generates alt text for images and creates markdown files.")
    
    while True:
        print("\nPlease choose an option:")
        print("  1. Process a directory of images")
        print("  2. Exit")
        
        choice = input("Enter your choice (1/2): ").strip()
        
        if choice == "1":
            directory = input("Enter the directory path: ").strip()
            if not os.path.isdir(directory):
                print(f"Error: {directory} is not a valid directory.")
                continue
            
            recursive_input = input("Process subdirectories recursively? (y/n): ").strip().lower()
            recursive = recursive_input == "y"
            
            force_input = input("Force regeneration of alt text even if cached? (y/n): ").strip().lower()
            force = force_input == "y"
            
            rename_input = input("Rename files based on image content? (y/n): ").strip().lower()
            rename = rename_input == "y"
            
            test_input = input("Check metadata before and after embedding? (y/n): ").strip().lower()
            test = test_input == "y"
            
            override_input = input("Override existing markdown files and reprocess images? (y/n): ").strip().lower()
            override_md = override_input == "y"
            
            process_directory(directory, recursive, force, rename, test, override_md)
            
        elif choice == "2":
            print("Exiting. Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Process image files to generate alt text and create markdown files."
    )
    parser.add_argument("--dir", help="Directory containing images to process")
    parser.add_argument("--recursive", "-r", action="store_true", help="Process subdirectories recursively")
    parser.add_argument("--force", "-f", action="store_true", help="Force regeneration of alt text even if cached")
    parser.add_argument("--rename", "-n", action="store_true", help="Rename files based on image content")
    parser.add_argument("--test", "-t", action="store_true", help="Check metadata before and after embedding alt text")
    parser.add_argument("--override-md", "-o", action="store_true", help="Override existing markdown file check and reprocess images")
    
    args = parser.parse_args()
    
    if args.dir:
        # Command-line mode
        if not os.path.isdir(args.dir):
            logger.error(f"Error: {args.dir} is not a valid directory.")
            sys.exit(1)
        
        process_directory(args.dir, args.recursive, args.force, args.rename, args.test, args.override_md)
    else:
        # Interactive mode
        interactive_cli()

if __name__ == "__main__":
    main()