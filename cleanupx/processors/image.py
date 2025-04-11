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
from cleanupx.utils.cache import save_cache, ensure_metadata_dir, get_description_path, save_description
from cleanupx.api import call_xai_api, timeout, TimeoutError
from cleanupx.processors.base import BaseProcessor

# Configure logging
logger = logging.getLogger(__name__)

# Timeout for image processing (in seconds)
process_timeout = 30

class ImageProcessor(BaseProcessor):
    """Processor for image files."""
    
    def __init__(self):
        """Initialize the image processor."""
        super().__init__()
        self.supported_extensions = IMAGE_EXTENSIONS
        self.max_size_mb = 25.0
        
    def process(self, file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Dict:
        """
        Process an image file.
        
        Args:
            file_path: Path to the image file
            cache: Cache dictionary for storing/retrieving image descriptions
            rename_log: Optional log for tracking renames
            
        Returns:
            Dictionary with processing results
        """
        file_path = Path(file_path)
        result = {
            'original_path': str(file_path),
            'new_path': None,
            'description': None,
            'metadata_updated': False,
            'renamed': False,
            'error': None
        }
        
        try:
            # Check if we can process this file
            if not self.can_process(file_path):
                result['error'] = f"Unsupported file type: {file_path.suffix}"
                return result
                
            # Check file size
            if not self.check_file_size(file_path):
                result['error'] = f"File size exceeds maximum ({self.max_size_mb}MB)"
                return result
                
            # Check cache
            cache_key = str(file_path)
            if cache_key in cache:
                logger.info(f"Using cached description for {file_path.name}")
                description = cache[cache_key]
            else:
                # Analyze image
                description = self._analyze_image(file_path)
                if description:
                    cache[cache_key] = description
                    save_cache(cache)
                    
            if not description:
                result['error'] = "Failed to analyze image"
                return result
                
            # Generate new filename
            new_name = self.generate_new_filename(file_path, description)
            if not new_name:
                result['error'] = "Failed to generate new filename"
                return result
                
            # Rename file using inherited method
            new_path = super().rename_file(file_path, new_name, rename_log)
            if new_path:
                result['new_path'] = str(new_path)
                result['renamed'] = True
                
            # Update metadata
            if PIL_AVAILABLE:
                try:
                    embed_alt_text_into_image(new_path or file_path, description.get('alt_text', ''))
                    result['metadata_updated'] = True
                except Exception as e:
                    logger.error(f"Error updating image metadata: {e}")
                    
            # Generate markdown
            self._generate_markdown(file_path, description)
            
            result['description'] = description
            return result
            
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {e}")
            result['error'] = str(e)
            return result
            
    def _analyze_image(self, image_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
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
        if file_size_mb > 10 and PIL_AVAILABLE:
            try:
                with Image.open(analysis_path) as img:
                    if img.width > 2000 or img.height > 2000:
                        logger.info(f"Resizing large image for analysis: {analysis_path.name}")
                        
                        ratio = min(2000 / img.width, 2000 / img.height)
                        new_width = int(img.width * ratio)
                        new_height = int(img.height * ratio)
                        
                        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                        
                        temp_path = analysis_path.with_name(f"temp_resized_{analysis_path.name}")
                        resized_img.save(temp_path, quality=85)
                        
                        if temp_converted and temp_converted != analysis_path:
                            try:
                                os.remove(temp_converted)
                            except Exception as e:
                                logger.error(f"Error removing temporary file {temp_converted}: {e}")
                                
                        temp_converted = temp_path
                        analysis_path = temp_path
                        
                        resized_img = None
                    img = None
                    
                    gc.collect()
                    
            except Exception as e:
                logger.error(f"Error resizing large image: {e}")
                
        try:
            with timeout(process_timeout):
                image_data = self._encode_image(analysis_path)
                if not image_data:
                    logger.error(f"Failed to encode image: {analysis_path}")
                    self._cleanup_temp_files(temp_converted)
                    gc.collect()
                    return None
                    
                result = call_xai_api(XAI_MODEL_VISION, FILE_IMAGE_PROMPT, IMAGE_FUNCTION_SCHEMA, image_data)
                if result:
                    logger.info(f"Successfully analyzed image: {original_path.name}")
                else:
                    logger.error(f"Failed to analyze image: {original_path.name}")
                    
        except TimeoutError as e:
            logger.error(f"Image analysis timed out after {process_timeout} seconds: {original_path.name}")
            if file_size_mb > 10:
                logger.info(f"Consider using the --skip-images flag for large images or process them separately.")
            self._cleanup_temp_files(temp_converted)
            gc.collect()
            return None
        except Exception as e:
            logger.error(f"Error during image analysis: {e}")
            self._cleanup_temp_files(temp_converted)
            gc.collect()
            return None
            
        self._cleanup_temp_files(temp_converted)
        image_data = None
        gc.collect()
        
        return result
        
    def _encode_image(self, image_path: Union[str, Path]) -> Optional[str]:
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
            
    def _cleanup_temp_files(self, temp_file_path):
        """Helper function to safely clean up temporary files"""
        if temp_file_path and Path(temp_file_path).exists():
            try:
                logger.info(f"Removed temporary file: {temp_file_path}")
                os.remove(temp_file_path)
            except Exception as e:
                logger.error(f"Error removing temporary file {temp_file_path}: {e}")
                
    def generate_new_filename(self, file_path: Union[str, Path], description: Optional[Dict[str, Any]] = None) -> Optional[str]:
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
        
        # Get dimensions
        dimensions = get_image_dimensions(file_path)
        
        # Get base name
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
            
        # Append dimensions
        if dimensions:
            width, height = dimensions
            return f"{base_name}_{width}x{height}{ext}"
        else:
            return f"{base_name}{ext}"
            
    def _generate_markdown(self, file_path: Path, description: Dict[str, Any]):
        """
        Generate markdown description for the image.
        
        Args:
            file_path: Path to the image file
            description: Dictionary with image description
        """
        try:
            ensure_metadata_dir(file_path.parent)
            md_path = get_description_path(file_path)
            
            content = [
                f"# {file_path.stem}",
                "",
                f"**Description:** {description.get('description', 'No description available')}",
                f"**Alt Text:** {description.get('alt_text', 'No alt text available')}",
                "",
                "## Metadata",
                f"- **Dimensions:** {description.get('dimensions', 'Unknown')}",
                f"- **Format:** {description.get('format', 'Unknown')}",
                f"- **Size:** {description.get('size', 'Unknown')}",
                "",
                "## Tags",
                "\n".join(f"- {tag}" for tag in description.get('tags', []))
            ]
            
            with open(md_path, 'w') as f:
                f.write('\n'.join(content))
                
            logger.info(f"Generated markdown description: {md_path}")
        except Exception as e:
            logger.error(f"Error generating markdown for {file_path}: {e}")
