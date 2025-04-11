#!/usr/bin/env python3
"""
Media file processing utilities for CleanupX.

This module provides functionality for analyzing and processing media files
including audio and video files.
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional, Union
import json

# Configure logging
logger = logging.getLogger(__name__)

def get_media_info(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Get information about a media file using ffprobe.
    
    Args:
        file_path: Path to the media file
        
    Returns:
        Dictionary containing media information or None if analysis failed
    """
    file_path = Path(file_path)
    result = {
        "duration": None,
        "width": None,
        "height": None,
        "format": None,
        "size": None,
        "error": None
    }
    
    try:
        # Get basic file info
        result["size"] = file_path.stat().st_size
        result["format"] = file_path.suffix.lower()
        
        # Use ffprobe to get media info
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(file_path)
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        if process.returncode == 0:
            info = json.loads(process.stdout)
            
            # Get duration
            if "format" in info and "duration" in info["format"]:
                result["duration"] = format_duration(float(info["format"]["duration"]))
            
            # Get video dimensions
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    result["width"] = stream.get("width")
                    result["height"] = stream.get("height")
                    break
                    
        else:
            result["error"] = f"ffprobe failed: {process.stderr}"
            
    except Exception as e:
        logger.error(f"Error analyzing media file {file_path}: {e}")
        result["error"] = str(e)
        
    return result

def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to HH:MM:SS format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def process_media_file(file_path: Union[str, Path], logger: logging.Logger) -> Dict[str, Any]:
    """
    Process a media file and return analysis results.
    
    Args:
        file_path: Path to the media file
        logger: Logger instance
        
    Returns:
        Dictionary with processing results
    """
    file_path = Path(file_path)
    result = {
        "processed": False,
        "error": None,
        "info": None
    }
    
    try:
        # Get media info
        info = get_media_info(file_path)
        if info and not info.get("error"):
            result["processed"] = True
            result["info"] = info
            
            # Generate markdown description
            md_path = file_path.parent / f"{file_path.stem}_description.md"
            with open(md_path, 'w') as f:
                f.write(f"# {file_path.name}\n\n")
                f.write("## Media Information\n\n")
                if info["duration"]:
                    f.write(f"- Duration: {info['duration']}\n")
                if info["width"] and info["height"]:
                    f.write(f"- Resolution: {info['width']}x{info['height']}\n")
                f.write(f"- Format: {info['format']}\n")
                f.write(f"- Size: {info['size']} bytes\n")
                
        else:
            result["error"] = info.get("error") if info else "Failed to analyze media file"
            
    except Exception as e:
        logger.error(f"Error processing media file {file_path}: {e}")
        result["error"] = str(e)
        
    return result 