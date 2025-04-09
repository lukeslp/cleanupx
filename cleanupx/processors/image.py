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
        
        # Handle large files more aggressively
        if file_size_mb > 5 and PIL_AVAILABLE:
            logger.info(f"Image is too large ({file_size_mb:.1f}MB). Resizing...")
            
            # For extremely large files (>20MB), apply more aggressive initial resize
            initial_quality = 85
            optimize_flag = True
            
            # For very large PNGs, disable optimization which can cause hanging
            if file_size_mb > 10 and file_path.suffix.lower() in ['.png']:
                optimize_flag = False
                logger.info("Large PNG detected, disabling optimization to prevent hanging")
            
            # Apply more aggressive initial resize for very large images
            initial_scale = 1.0
            if file_size_mb > 20:
                initial_scale = 0.5  # 50% reduction for very large files
            elif file_size_mb > 10:
                initial_scale = 0.7  # 30% reduction for large files
                
            try:
                with Image.open(file_path) as img:
                    resized_path = file_path.with_name(f"{file_path.stem}_resized{file_path.suffix}")
                    
                    # Apply initial resize if needed
                    if initial_scale < 1.0:
                        width, height = img.size
                        new_width = int(width * initial_scale)
                        new_height = int(height * initial_scale)
                        img = img.resize((new_width, new_height), Image.LANCZOS)
                        logger.info(f"Initial resize to {new_width}x{new_height}")
                    
                    # Save with appropriate settings based on file type
                    if file_path.suffix.lower() in ['.jpg', '.jpeg']:
                        img.save(resized_path, quality=initial_quality, optimize=optimize_flag)
                    elif file_path.suffix.lower() in ['.png']:
                        # Use different settings for PNG to avoid hanging
                        img.save(resized_path, optimize=optimize_flag, compress_level=6)
                    else:
                        img.save(resized_path, quality=initial_quality, optimize=optimize_flag)
                    
                    # Maximum resize iterations to prevent infinite loops
                    max_iterations = 5
                    iterations = 0
                    
                    # Resize loop with iteration limit
                    while resized_path.stat().st_size / (1024 * 1024) > 5 and iterations < max_iterations:
                        iterations += 1
                        logger.info(f"Resize iteration {iterations}, current size: {resized_path.stat().st_size / (1024 * 1024):.1f}MB")
                        
                        with Image.open(resized_path) as resize_img:
                            width, height = resize_img.size
                            width = int(width * 0.8)
                            height = int(height * 0.8)
                            
                            if width < 100 or height < 100:
                                logger.info("Image dimensions too small, stopping resize")
                                break
                                
                            resized_img = resize_img.resize((width, height), Image.LANCZOS)
                            
                            # Save with appropriate settings
                            if file_path.suffix.lower() in ['.jpg', '.jpeg']:
                                resized_img.save(resized_path, quality=initial_quality, optimize=optimize_flag)
                            elif file_path.suffix.lower() in ['.png']:
                                # For PNG, each iteration reduces compression quality
                                compress_level = max(1, 6 - iterations)
                                resized_img.save(resized_path, optimize=optimize_flag, compress_level=compress_level)
                            else:
                                resized_img.save(resized_path, quality=initial_quality, optimize=optimize_flag)
                    
                    # If we hit max iterations and file is still large, log a warning
                    if iterations >= max_iterations and resized_path.stat().st_size / (1024 * 1024) > 5:
                        logger.warning(f"Could not resize image below 5MB after {max_iterations} attempts. Using current version.")
                    
                    # Read the resized file
                    with open(resized_path, "rb") as f:
                        img_data = f.read()
                    
                    # Remove temporary file
                    try:
                        os.remove(resized_path)
                    except:
                        pass
                    
                    return base64.b64encode(img_data).decode('utf-8')
            except Exception as e:
                logger.error(f"Error during image resize: {e}")
                # Fall back to the original image if resize fails
                logger.warning("Resize failed, using original image")
                
        # For small files or if resize failed, use the original
        with open(file_path, "rb") as f:
            img_data = f.read()
        return base64.b64encode(img_data).decode('utf-8')
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
    
    if original_path.suffix.lower() in {'.heic', '.heif'}:
        temp_converted = convert_heic_to_jpeg(original_path)
        if temp_converted and temp_converted != original_path:
            analysis_path = temp_converted
    elif original_path.suffix.lower() == '.webp':
        temp_converted = convert_webp_to_jpeg(original_path)
        if temp_converted and temp_converted != original_path:
            analysis_path = temp_converted
    
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
