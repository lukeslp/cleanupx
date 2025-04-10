#!/usr/bin/env python3
"""
Image processor for CleanupX.
"""

import os
import logging
import base64
import gc
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any
from datetime import datetime

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.error("PIL/Pillow not installed. Install with: pip install Pillow")

from cleanupx.config import IMAGE_FUNCTION_SCHEMA, FILE_IMAGE_PROMPT, XAI_MODEL_VISION, IMAGE_EXTENSIONS
from cleanupx.utils.common import get_image_dimensions, convert_heic_to_jpeg, convert_webp_to_jpeg, embed_alt_text_into_image
from cleanupx.utils.cache import save_cache, ensure_metadata_dir, get_description_path
from cleanupx.api import call_xai_api, timeout, TimeoutError
from cleanupx.processors.base import generate_new_filename, rename_file

# Configure logging
logger = logging.getLogger(__name__)

# Timeout for image processing (in seconds)
process_timeout = 30

def encode_image(image_path: Union[str, Path]) -> Optional[str]:
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

def analyze_image(image_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Analyze an image using X.AI Vision API.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary with image analysis or None if analysis failed
    """
    original_path = Path(image_path)
    analysis_path = original_path
    temp_converted = None
    
    logger.info(f"Analyzing image: {original_path.name}")
    logger.info(f"Setting timeout of {process_timeout} seconds for image analysis")
    
    # Get file size in MB
    try:
        file_size_mb = original_path.stat().st_size / (1024 * 1024)
    except Exception:
        file_size_mb = 0
    
    # Convert HEIC to JPEG for analysis
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
    
    # Try to optimize large images to prevent memory issues
    if file_size_mb > 10:
        try:
            from PIL import Image
            # Create a temporary resized image for analysis
            with Image.open(analysis_path) as img:
                # Only resize if actually large
                if img.width > 2000 or img.height > 2000:
                    logger.info(f"Resizing large image for analysis: {analysis_path.name}")
                    
                    # Calculate new dimensions while maintaining aspect ratio
                    ratio = min(2000 / img.width, 2000 / img.height)
                    new_width = int(img.width * ratio)
                    new_height = int(img.height * ratio)
                    
                    # Create resized image
                    resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                    
                    # Save to temporary file
                    temp_path = analysis_path.with_name(f"temp_resized_{analysis_path.name}")
                    resized_img.save(temp_path, quality=85)
                    
                    # If we already had a temp file, remove it
                    if temp_converted and temp_converted != analysis_path:
                        try:
                            os.remove(temp_converted)
                        except Exception as e:
                            logger.error(f"Error removing temporary file {temp_converted}: {e}")
                    
                    # Use the resized image for analysis
                    temp_converted = temp_path
                    analysis_path = temp_path
                    
                    # Explicitly close and delete references to free memory
                    resized_img = None
                img = None
                
                # Force garbage collection to prevent memory leaks
                gc.collect()
                
        except Exception as e:
            logger.error(f"Error resizing large image: {e}")
    
    try:
        # Use timeout for the encoding process
        with timeout(process_timeout):
            image_data = encode_image(analysis_path)
            if not image_data:
                logger.error(f"Failed to encode image: {analysis_path}")
                # Clean up temporary file if exists
                if temp_converted and temp_converted.exists():
                    try:
                        os.remove(temp_converted)
                    except Exception as e:
                        logger.error(f"Error removing temporary file {temp_converted}: {e}")
                
                # Force garbage collection
                gc.collect()
                return None
            
            prompt = FILE_IMAGE_PROMPT
            result = call_xai_api(XAI_MODEL_VISION, prompt, IMAGE_FUNCTION_SCHEMA, image_data)
            if result:
                logger.info(f"Successfully analyzed image: {original_path.name}")
            else:
                logger.error(f"Failed to analyze image: {original_path.name}")
    except TimeoutError as e:
        logger.error(f"Image analysis timed out after {process_timeout} seconds: {original_path.name}")
        if file_size_mb > 10:
            logger.info(f"Consider using the --skip-images flag for large images or process them separately.")

        # Clean up and return None
        cleanup_temp_files(temp_converted)
        gc.collect()
        return None
    except Exception as e:
        logger.error(f"Error during image analysis: {e}")
        cleanup_temp_files(temp_converted)
        gc.collect()
        return None
    
    # Clean up temporary file if exists
    cleanup_temp_files(temp_converted)
    
    # Force garbage collection to prevent memory leaks
    image_data = None
    gc.collect()
    
    return result

def cleanup_temp_files(temp_file_path):
    """Helper function to safely clean up temporary files"""
    if temp_file_path and Path(temp_file_path).exists():
        try:
            logger.info(f"Removed temporary file: {temp_file_path}")
            os.remove(temp_file_path)
        except Exception as e:
            logger.error(f"Error removing temporary file {temp_file_path}: {e}")

def generate_image_filename(file_path: Union[str, Path], description: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Generate a filename specifically for images, including resolution.
    
    Args:
        file_path: Path to the image file
        description: Dictionary with image analysis
        
    Returns:
        New filename with resolution (with extension) or None if generation failed
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    
    # Get dimensions first
    dimensions = get_image_dimensions(file_path)
    
    # Get base name (either from AI suggestion or original)
    if description and isinstance(description, dict):
        suggested_name = description.get("suggested_filename")
        if suggested_name and isinstance(suggested_name, str):
            from cleanupx.utils.common import clean_filename
            base_name = clean_filename(suggested_name)
        else:
            from cleanupx.utils.common import strip_media_suffixes
            base_name = strip_media_suffixes(file_path.stem)
    else:
        from cleanupx.utils.common import strip_media_suffixes
        base_name = strip_media_suffixes(file_path.stem)
    
    # Append dimensions to the base name
    if dimensions:
        width, height = dimensions
        return f"{base_name}_{width}x{height}{ext}"
    else:
        return f"{base_name}{ext}"

def process_image_file(file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Tuple[Path, Optional[Path], Optional[Dict[str, Any]]]:
    """
    Process an image file - extract metadata and generate description.
    
    Args:
        file_path: Path to the image file
        cache: Cache dictionary for storing/retrieving image descriptions
        rename_log: Optional log for tracking renames
        
    Returns:
        Tuple of (original_path, new_path, description) where:
            - original_path: Original file path
            - new_path: New file path if renamed, None if not renamed
            - description: Dictionary with image metadata if available, None if not available
    """
    try:
        file_path = Path(file_path)
        
        # Check if already processed
        cache_key = str(file_path)
        if cache_key in cache:
            logger.info(f"Using cached description for {file_path.name}")
            data = cache[cache_key]
        else:
            # Get image dimensions
            dimensions = get_image_dimensions(file_path)
            
            # Convert HEIC to JPEG if needed
            if file_path.suffix.lower() == '.heic':
                file_path = convert_heic_to_jpeg(file_path)
                if not file_path:
                    logger.error(f"Failed to convert HEIC image: {file_path}")
                    return file_path, None, None
            
            # Convert WebP to JPEG if needed
            if file_path.suffix.lower() == '.webp':
                file_path = convert_webp_to_jpeg(file_path)
                if not file_path:
                    logger.error(f"Failed to convert WebP image: {file_path}")
                    return file_path, None, None
            
            # Encode image for API
            encoded_image = encode_image(file_path)
            if not encoded_image:
                logger.error(f"Failed to encode image: {file_path}")
                return file_path, None, None
            
            # Call API to get description
            try:
                with timeout(process_timeout):
                    response = call_xai_api(
                        model=XAI_MODEL_VISION,
                        messages=[
                            {"role": "system", "content": FILE_IMAGE_PROMPT},
                            {"role": "user", "content": [
                                {"type": "text", "text": "Describe this image in detail."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                            ]}
                        ],
                        functions=[IMAGE_FUNCTION_SCHEMA],
                        function_call={"name": "describe_image"}
                    )
                    
                    if response and "function_call" in response:
                        data = json.loads(response["function_call"]["arguments"])
                        data["dimensions"] = dimensions
                        cache[cache_key] = data
                        save_cache(cache)
                    else:
                        logger.error(f"Failed to get image description for {file_path}")
                        return file_path, None, None
            except TimeoutError:
                logger.error(f"Timeout processing image: {file_path}")
                return file_path, None, None
            except Exception as e:
                logger.error(f"Error processing image {file_path}: {e}")
                return file_path, None, None
        
        # Generate new filename
        new_path = generate_new_filename(file_path, data)
        if new_path:
            # Create markdown file with image description in .cleanupx/descriptions
            description_path = get_description_path(file_path)
            try:
                with open(description_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {data.get('title', file_path.stem)}\n\n")
                    if "dimensions" in data:
                        width, height = data["dimensions"]
                        f.write(f"**Resolution:** {width}x{height}\n\n")
                    f.write(f"{data.get('description', 'No description available')}\n\n")
                    f.write(f"**Original Name:** {file_path.name}\n")
                    f.write(f"**Current Name:** {new_path.name}\n")
                    f.write(f"**File Size:** {file_path.stat().st_size / 1024:.2f} KB\n")
                    f.write(f"**Last Modified:** {datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n")
                logger.info(f"Created description file: {description_path}")
            except Exception as e:
                logger.error(f"Failed to create description file for {file_path}: {e}")
            
            # Rename file
            success = rename_file(file_path, new_path, rename_log)
            if success:
                logger.info(f"Renamed {file_path.name} to {new_path.name}")
                return file_path, new_path, data
            else:
                logger.error(f"Failed to rename {file_path.name}")
                return file_path, None, data
        else:
            logger.warning(f"No new filename generated for {file_path.name}")
            return file_path, None, data
            
    except Exception as e:
        logger.error(f"Error processing image {file_path}: {e}")
        return file_path, None, None
