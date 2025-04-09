#!/usr/bin/env python3
"""
Image processor for CleanupX.
"""

import os
import logging
import base64
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.error("PIL/Pillow not installed. Install with: pip install Pillow")

from cleanupx.config import IMAGE_FUNCTION_SCHEMA, FILE_IMAGE_PROMPT, XAI_MODEL_VISION, IMAGE_EXTENSIONS
from cleanupx.utils.common import get_image_dimensions, convert_heic_to_jpeg, convert_webp_to_jpeg
from cleanupx.utils.cache import save_cache
from cleanupx.api import call_xai_api, timeout, TimeoutError
from cleanupx.processors.base import generate_new_filename, rename_file

# Configure logging
logger = logging.getLogger(__name__)

def encode_image(image_path: Union[str, Path]) -> Optional[str]:
    """Encode image to base64, with resizing if needed."""
    try:
        file_path = Path(image_path)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        # Always ensure we're dealing with an image format the API can handle
        if PIL_AVAILABLE:
            # For all images, convert to JPEG to ensure compatibility
            try:
                with Image.open(file_path) as img:
                    # Check if image needs to be converted to RGB mode
                    if img.mode != 'RGB':
                        logger.info(f"Converting image from mode {img.mode} to RGB")
                        img = img.convert('RGB')
                    
                    # Handle large files by resizing
                    if file_size_mb > 5:
                        logger.info(f"Image is too large ({file_size_mb:.1f}MB). Resizing...")
                        
                        # Determine target size based on original file size
                        original_width, original_height = img.size
                        scaling_factor = min(1.0, (5.0 / file_size_mb) ** 0.5)
                        
                        # Scale down more aggressively for very large images
                        if file_size_mb > 20:
                            scaling_factor *= 0.7
                        
                        new_width = max(100, int(original_width * scaling_factor))
                        new_height = max(100, int(original_height * scaling_factor))
                        
                        logger.info(f"Resizing from {original_width}x{original_height} to {new_width}x{new_height}")
                        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                    else:
                        resized_img = img
                    
                    # Create a temporary JPEG
                    temp_jpg = file_path.parent / f"{file_path.stem}_temp_encode.jpg"
                    resized_img.save(temp_jpg, format='JPEG', quality=90, optimize=True)
                    
                    # Read the JPEG data and encode it
                    with open(temp_jpg, "rb") as f:
                        img_data = f.read()
                    
                    # Clean up temp file
                    try:
                        if temp_jpg.exists():
                            os.remove(temp_jpg)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to remove temporary file: {cleanup_error}")
                    
                    # Return the base64 encoded data
                    return base64.b64encode(img_data).decode('utf-8')
            except Exception as conversion_error:
                logger.error(f"Error during image conversion/resize: {conversion_error}")
                # Fall back to direct encoding if conversion fails
                logger.warning("Conversion failed, trying direct encoding...")
        
        # Direct encoding path (fallback or if PIL not available)
        try:
            with open(file_path, "rb") as f:
                img_data = f.read()
            # Ensure we're actually getting image data
            if len(img_data) == 0:
                logger.error(f"Read zero bytes from {file_path}")
                return None
            return base64.b64encode(img_data).decode('utf-8')
        except Exception as direct_error:
            logger.error(f"Error in direct encoding: {direct_error}")
            return None
    
    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {e}")
        return None

def analyze_image(image_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Analyze image content using X.AI API.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary with image analysis or None if analysis failed
    """
    original_path = Path(image_path)
    # Determine the file to use for analysis. If the file is HEIC/HEIF or WebP, convert it temporarily.
    analysis_path = original_path
    temp_converted = None
    
    # Get file size for timeout calculation
    file_size_mb = original_path.stat().st_size / (1024 * 1024)
    # Scale timeout based on file size (30 seconds base + 1 second per MB up to a limit)
    process_timeout = min(300, 30 + int(file_size_mb))
    logger.info(f"Setting timeout of {process_timeout} seconds for image analysis")
    
    # Check file extension and convert if needed
    ext = original_path.suffix.lower()
    if ext in {'.heic', '.heif'}:
        temp_converted = convert_heic_to_jpeg(original_path)
        if temp_converted and temp_converted != original_path:
            analysis_path = temp_converted
    elif ext == '.webp':
        temp_converted = convert_webp_to_jpeg(original_path)
        if temp_converted and temp_converted != original_path:
            analysis_path = temp_converted
    elif ext == '.gif':
        # Convert GIF to JPEG to handle API limitations
        try:
            from PIL import Image
            temp_converted = original_path.parent / f"{original_path.stem}_temp.jpg"
            with Image.open(original_path) as img:
                # Convert to RGB (since GIFs can be indexed color)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # Get the first frame for animated GIFs
                img.save(temp_converted, format='JPEG', quality=95)
                logger.info(f"Converted GIF to JPEG for analysis: {temp_converted}")
                analysis_path = temp_converted
        except Exception as e:
            logger.error(f"Failed to convert GIF to JPEG: {e}")
            # Continue with original file
    # Check if the file is a PNG that might need conversion
    elif ext == '.png':
        try:
            # Convert PNG to JPEG to avoid potential issues with transparency
            from PIL import Image
            temp_converted = original_path.parent / f"{original_path.stem}_temp.jpg"
            with Image.open(original_path) as img:
                # Convert to RGB to handle transparency
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                    background.save(temp_converted, format='JPEG', quality=95)
                    logger.info(f"Converted PNG with transparency to JPEG: {temp_converted}")
                    analysis_path = temp_converted
                elif img.mode != 'RGB':
                    # Convert other non-RGB modes
                    img = img.convert('RGB')
                    img.save(temp_converted, format='JPEG', quality=95)
                    logger.info(f"Converted PNG to RGB JPEG: {temp_converted}")
                    analysis_path = temp_converted
        except Exception as e:
            logger.error(f"Failed to convert PNG: {e}")
            # Continue with original file
    
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
        # Clean up temporary file if exists
        if temp_converted and temp_converted.exists():
            try:
                os.remove(temp_converted)
            except Exception as e:
                logger.error(f"Error removing temporary file {temp_converted}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error during image analysis: {e}")
        # Clean up temporary file if exists
        if temp_converted and temp_converted.exists():
            try:
                os.remove(temp_converted)
            except Exception as e:
                logger.error(f"Error removing temporary file {temp_converted}: {e}")
        return None
    
    # Remove the temporary converted file after processing
    if temp_converted and temp_converted.exists():
        try:
            os.remove(temp_converted)
            logger.info(f"Removed temporary file: {temp_converted}")
        except Exception as e:
            logger.error(f"Error removing temporary file {temp_converted}: {e}")
    
    return result

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

def process_image_file(file_path: Path, cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Tuple[Path, Optional[Path], Optional[Dict[str, Any]]]:
    """
    Process an image file - analyze, generate alt text, and rename.
    
    Args:
        file_path: Path to the image file
        cache: Cache dictionary for storing/retrieving image descriptions
        rename_log: Optional log for tracking renames
        
    Returns:
        Tuple of (original_path, new_path, description)
    """
    try:
        # Check file size first - add a warning for extremely large images
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 30:
            logger.warning(f"Image is extremely large ({file_size_mb:.1f}MB). Processing may take a long time.")
            
        cache_key = str(file_path)
        if cache_key in cache:
            logger.info(f"Using cached description for {file_path.name}")
            data = cache[cache_key]
        else:
            logger.info(f"Analyzing image: {file_path.name}")
            analysis = analyze_image(file_path)
            if not analysis:
                logger.warning(f"Failed to analyze image: {file_path.name}")
                return file_path, None, None
            data = analysis
            if not data:
                logger.warning(f"No analysis data generated for image: {file_path.name}")
                return file_path, None, None
            cache[cache_key] = data
        alt_text = data.get("alt_text")
        if not alt_text:
            logger.warning(f"Failed to get alt text for image: {file_path.name}")
            return file_path, None, None
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
                    
                    # More aggressive resizing for very large images
                    quality = 85
                    optimize_flag = True
                    compress_level = 6
                    
                    # For very large PNGs, disable optimization which can cause hanging
                    if file_size_mb > 10 and file_path.suffix.lower() in ['.png']:
                        optimize_flag = False
                        logger.info("Large PNG detected, disabling optimization to prevent hanging")
                    
                    # Calculate target size based on original file size
                    target_size_mb = min(4.5, max(1.0, 5.0 * (5.0 / file_size_mb)))
                    size_ratio = (target_size_mb / file_size_mb) ** 0.5
                    
                    # More aggressive reduction for larger files
                    if file_size_mb > 20:
                        size_ratio *= 0.7
                    
                    new_width = max(100, int(width * size_ratio))
                    new_height = max(100, int(height * size_ratio))
                    
                    logger.info(f"Resizing to {new_width}x{new_height} (ratio: {size_ratio:.2f})")
                    
                    # Apply the resize with error handling
                    try:
                        resized_img = new_img.resize((new_width, new_height), Image.LANCZOS)
                        temp_path = file_path.parent / f"{file_path.stem}_temp{file_path.suffix}"
                        
                        # Use appropriate save parameters based on file type
                        if file_path.suffix.lower() in ['.jpg', '.jpeg']:
                            resized_img.save(temp_path, quality=quality, optimize=optimize_flag)
                        elif file_path.suffix.lower() in ['.png']:
                            resized_img.save(temp_path, optimize=optimize_flag, compress_level=compress_level)
                        else:
                            resized_img.save(temp_path, quality=quality, optimize=optimize_flag)
                        
                        new_size_mb = temp_path.stat().st_size / (1024 * 1024)
                        
                        # Check if resize was effective
                        if new_size_mb > 5:
                            logger.warning(f"Resized image still too large ({new_size_mb:.2f} MB). Using original image.")
                            if temp_path.exists():
                                temp_path.unlink()
                        else:
                            # Close the original image before replacing it
                            del new_img
                            del img
                            new_img = Image.open(temp_path)
                            logger.info(f"Image resized to {new_width}x{new_height}")
                            
                            # Clean up temp file
                            if temp_path.exists():
                                temp_path.unlink()
                    except Exception as e:
                        logger.error(f"Error during image resizing: {e}")
                        logger.warning("Using original image due to resize error")
                
                # Use a different approach to save metadata to avoid memory issues
                try:
                    # Use a more controlled approach for saving based on file type
                    if file_path.suffix.lower() in ['.jpg', '.jpeg']:
                        new_img.save(file_path, quality=85)
                    elif file_path.suffix.lower() in ['.png']:
                        new_img.save(file_path, optimize=False)
                    else:
                        new_img.save(file_path)
                except Exception as e:
                    logger.error(f"Error saving image with metadata: {e}")
                
                # Explicitly close and cleanup to prevent memory issues
                new_img.close()
                del new_img
        except Exception as e:
            logger.warning(f"Failed to embed metadata in image: {e}")
            return file_path, None, None
        new_filename = generate_image_filename(file_path, data)
        if not new_filename:
            logger.warning(f"Failed to generate new filename for image: {file_path.name}")
            return file_path, None, None
        try:
            new_path = file_path.parent / new_filename
            if new_path != file_path:
                file_path.rename(new_path)
                logger.info(f"Renamed {file_path.name} to {new_filename}")
                if cache_key in cache:
                    cache[str(new_path)] = cache.pop(cache_key)
                    save_cache(cache)
                
                # Create markdown file with the image description
                # Get the base name without extension for the markdown file
                md_base_name = os.path.splitext(new_filename)[0]
                md_filename = f"{md_base_name}.md"
                md_path = new_path.parent / md_filename
                with open(md_path, 'w', encoding='utf-8') as md_file:
                    title = data.get("title", "Image Description")
                    md_file.write(f"# {title}\n\n")
                    
                    # Add resolution information to the markdown
                    dimensions = get_image_dimensions(new_path)
                    if dimensions:
                        width, height = dimensions
                        md_file.write(f"**Resolution:** {width}x{height}\n\n")
                    
                    md_file.write(alt_text)
                logger.info(f"Created markdown description file: {md_path}")
                
                return file_path, new_path, data
            
            # Create markdown file even if the image is not renamed
            # Extract the basename without extension
            md_base_name = os.path.splitext(file_path.name)[0]
            md_filename = f"{md_base_name}.md"
            md_path = file_path.parent / md_filename
            with open(md_path, 'w', encoding='utf-8') as md_file:
                title = data.get("title", "Image Description")
                md_file.write(f"# {title}\n\n")
                
                # Add resolution information to the markdown
                dimensions = get_image_dimensions(file_path)
                if dimensions:
                    width, height = dimensions
                    md_file.write(f"**Resolution:** {width}x{height}\n\n")
                
                md_file.write(alt_text)
            logger.info(f"Created markdown description file: {md_path}")
            
            return file_path, file_path, data
        except Exception as e:
            logger.warning(f"Failed to rename file {file_path.name}: {e}")
            return file_path, None, None
    except Exception as e:
        logger.warning(f"Error processing image {file_path.name}: {e}")
        return file_path, None, None
