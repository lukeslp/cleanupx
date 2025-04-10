#!/usr/bin/env python3
"""
Common utility functions for the CleanupX file organization tool.
"""

import os
import re
import logging
import random
import string
from pathlib import Path
from typing import Optional, Union, Tuple, Dict, Any
from datetime import datetime

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.error("PIL/Pillow not installed. Install with: pip install Pillow")

# Configure logging
logger = logging.getLogger(__name__)

def clean_filename(text: str, max_length: int = 50) -> str:
    """
    Clean text to make a valid filename.
    Ensures the filename doesn't start with a dot to prevent hidden files.
    """
    # First, remove any leading dots
    text = text.lstrip('.')
    
    # Then apply standard filename cleaning
    clean = re.sub(r'[^\w\s-]', '', text.lower())
    clean = re.sub(r'[-\s]+', '_', clean).strip('_')
    
    # Truncate if too long
    if len(clean) > max_length:
        clean = clean[:max_length]
    
    # Ensure we have a valid name
    if not clean or clean.startswith('.'):
        clean = "unnamed_file"
    
    return clean

def strip_media_suffixes(stem: str) -> str:
    """
    Remove duplicate appended resolution and duration patterns from a filename stem.
    """
    # Remove any occurrence of _<number>x<number> (e.g., _1920x1080)
    stem = re.sub(r'_(\d+x\d+)', '', stem)
    # Remove any occurrence of _HH:MM:SS (e.g., _01:23:45 where HH, MM, SS are two digits)
    stem = re.sub(r'_(\d{2}:\d{2}:\d{2})', '', stem)
    # Remove "_renamed" suffix if present
    stem = re.sub(r'_renamed', '', stem)
    # Clean up any stray underscores
    return stem.strip('_')

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

def format_duration(seconds: float) -> str:
    """Format seconds into HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def get_media_dimensions(file_path: Union[str, Path]) -> Optional[Tuple[int, int]]:
    """Get dimensions of media files using OpenCV."""
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
    """
    Get duration of media files in seconds.
    
    Tries multiple methods to get the most accurate duration:
    1. For MP3/audio files: Uses mutagen
    2. For video files: Uses OpenCV
    3. Fallback: Uses ffprobe if available
    
    Args:
        file_path: Path to the media file
        
    Returns:
        Duration in seconds, or None if duration could not be determined
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    
    # First try mutagen for audio files (more accurate for MP3s)
    if ext in {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'}:
        try:
            import mutagen
            audio = mutagen.File(file_path)
            if audio is not None and hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                return audio.info.length
        except ImportError:
            logger.warning("Mutagen not installed, falling back to other methods for audio duration")
        except Exception as e:
            logger.error(f"Error getting audio duration with mutagen: {e}")
    
    # Try OpenCV for video files
    try:
        import cv2
        cap = cv2.VideoCapture(str(file_path))
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else None
            cap.release()
            if duration and duration > 0:
                return duration
        else:
            cap.release()
    except Exception as e:
        logger.error(f"Error getting media duration with OpenCV: {e}")
    
    # Fallback to ffprobe
    try:
        import subprocess
        import json
        cmd = [
            'ffprobe', 
            '-v', 'quiet', 
            '-print_format', 'json', 
            '-show_format', 
            '-show_streams', 
            str(file_path)
        ]
        output = subprocess.check_output(cmd)
        data = json.loads(output)
        
        # Try to get duration from format
        if 'format' in data and 'duration' in data['format']:
            return float(data['format']['duration'])
        
        # Try from streams
        if 'streams' in data:
            for stream in data['streams']:
                if 'duration' in stream:
                    return float(stream['duration'])
                    
    except (subprocess.SubprocessError, ImportError, json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Error using ffprobe for duration: {e}")
    
    # If all methods fail
    logger.warning(f"Could not determine duration for {file_path}")
    return None

def convert_heic_to_jpeg(file_path: Union[str, Path]) -> Optional[Path]:
    """Convert HEIC image to JPEG format."""
    file_path = Path(file_path)
    if file_path.suffix.lower() not in {'.heic', '.heif'}:
        return file_path
    try:
        try:
            import pillow_heif
            logger.info("Converting HEIC/HEIF to JPEG using pillow_heif...")
            pillow_heif.register_heif_opener()
            with Image.open(file_path) as img:
                jpeg_path = file_path.with_suffix(".jpg")
                img.save(jpeg_path, "JPEG", quality=90)
            logger.info("HEIC conversion successful.")
            return jpeg_path
        except ImportError:
            pass
        try:
            import pyheif
            logger.info("Converting HEIC/HEIF to JPEG using pyheif...")
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
            logger.info("HEIC conversion successful.")
            return jpeg_path
        except ImportError:
            logger.warning("Neither pillow_heif nor pyheif are installed. Skipping HEIC conversion.")
            logger.warning("To enable HEIC support, install one of these packages:")
            logger.warning("  pip install pillow-heif")
            logger.warning("  pip install pyheif")
            return file_path
    except Exception as e:
        logger.error(f"Error converting HEIC image: {e}")
        return file_path

def convert_webp_to_jpeg(file_path: Union[str, Path]) -> Optional[Path]:
    """Convert a WebP image to JPEG format."""
    file_path = Path(file_path)
    if file_path.suffix.lower() != '.webp':
        return file_path
    try:
        logger.info("Converting WebP to JPEG...")
        with Image.open(file_path) as img:
            jpeg_path = file_path.with_suffix('.jpg')
            img.save(jpeg_path, "JPEG", quality=90)
        logger.info("WebP conversion successful.")
        return jpeg_path
    except Exception as e:
        logger.error(f"Error converting WebP image: {e}")
        return file_path
