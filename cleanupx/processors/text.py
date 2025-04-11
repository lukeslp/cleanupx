#!/usr/bin/env python3
"""
Text file processor for CleanupX.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any
from datetime import datetime

from cleanupx.config import TEXT_EXTENSIONS, DOCUMENT_FUNCTION_SCHEMA, FILE_TEXT_PROMPT, XAI_MODEL_TEXT
from cleanupx.utils.common import read_text_file
from cleanupx.utils.cache import save_cache, ensure_metadata_dir, get_description_path
from cleanupx.api import call_xai_api
from cleanupx.processors.base import BaseProcessor

# Configure logging
logger = logging.getLogger(__name__)

class TextProcessor(BaseProcessor):
    """Processor for text files."""
    
    def __init__(self):
        """Initialize the text processor."""
        super().__init__()
        self.supported_extensions = TEXT_EXTENSIONS
        self.max_size_mb = 5.0  # Text files are typically smaller
        
    def process(self, file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Dict:
        """
        Process a text file.
        
        Args:
            file_path: Path to the text file
            cache: Cache dictionary for storing/retrieving text descriptions
            rename_log: Optional log for tracking renames
            
        Returns:
            Dictionary with processing results
        """
        file_path = Path(file_path)
        result = {
            'original_path': str(file_path),
            'new_path': None,
            'description': None,
            'content_analyzed': False,
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
                # Analyze text file
                description = self._analyze_text(file_path)
                if description:
                    cache[cache_key] = description
                    save_cache(cache)
                    
            if not description:
                result['error'] = "Failed to analyze text"
                return result
                
            # Generate new filename using inherited method
            new_name = super().generate_new_filename(file_path, description)
            if not new_name:
                result['error'] = "Failed to generate new filename"
                return result
                
            # Rename file using inherited method
            new_path = super().rename_file(file_path, new_name, rename_log)
            if new_path:
                result['new_path'] = str(new_path)
                result['renamed'] = True
                
            # Generate markdown
            self._generate_markdown(file_path, description)
            
            result['description'] = description
            result['content_analyzed'] = True
            return result
            
        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {e}")
            result['error'] = str(e)
            return result
            
    def _analyze_text(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        Analyze text file content using AI.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Dictionary with text analysis or None if analysis failed
        """
        try:
            file_path = Path(file_path)
            content = read_text_file(file_path)
            if not content.strip():
                logger.error(f"No content found in {file_path}")
                return None
                
            # Get file metadata
            file_stats = file_path.stat()
            file_size_kb = file_stats.st_size / 1024
            modified_time = datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            line_count = content.count('\n') + 1
            
            # Limit content length to avoid token limits
            max_text_length = 10000
            if len(content) > max_text_length:
                logger.info(f"Truncating text from {len(content)} to {max_text_length} characters")
                content = content[:max_text_length] + "\n[... TRUNCATED ...]"
                
            # Call API for analysis
            prompt = FILE_TEXT_PROMPT
            result = call_xai_api(
                XAI_MODEL_TEXT, 
                prompt, 
                DOCUMENT_FUNCTION_SCHEMA,
                content,
                filename=file_path.name,
                file_size=f"{file_size_kb:.2f} KB",
                modified_date=modified_time,
                line_count=line_count
            )
            
            if not result:
                logger.error(f"Failed to analyze text file: {file_path}")
                return None
                
            # Add metadata
            result['file_size'] = f"{file_size_kb:.2f} KB"
            result['modified_date'] = modified_time
            result['line_count'] = line_count
            
            logger.info(f"Successfully analyzed text file: {file_path.name}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing text file {file_path}: {e}")
            return None
            
    def _generate_markdown(self, file_path: Path, description: Dict[str, Any]):
        """
        Generate markdown description for the text file.
        
        Args:
            file_path: Path to the text file
            description: Dictionary with text description
        """
        try:
            ensure_metadata_dir(file_path.parent)
            md_path = get_description_path(file_path)
            
            content = [
                f"# {description.get('title', file_path.stem)}",
                "",
                f"**Summary:** {description.get('summary', 'No summary available')}",
                "",
                "## File Information",
                f"- **Original Filename:** {file_path.name}",
                f"- **File Size:** {description.get('file_size', 'Unknown')}",
                f"- **Modified Date:** {description.get('modified_date', 'Unknown')}",
                f"- **Line Count:** {description.get('line_count', 'Unknown')}"
            ]
            
            content.extend([
                "",
                "## Content Analysis",
                f"- **File Type:** {description.get('file_type', 'Unknown')}",
                f"- **Language:** {description.get('language', 'Unknown')}",
                "",
                "## Keywords",
                "\n".join(f"- {keyword}" for keyword in description.get('keywords', []))
            ])
            
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
            logger.info(f"Generated markdown description: {md_path}")
        except Exception as e:
            logger.error(f"Error generating markdown for {file_path}: {e}")

# Keep for backward compatibility
def analyze_text_file(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Analyze text file content using X.AI API.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        Dictionary with text file analysis or None if analysis failed
    """
    processor = TextProcessor()
    return processor._analyze_text(file_path)

def process_text_file(file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Dict) -> Tuple[Path, Optional[Path], Optional[Dict]]:
    """
    Process a text file - analyze content and rename based on content.
    
    Args:
        file_path: Path to the text file
        cache: Cache dictionary for storing/retrieving file descriptions
        rename_log: Log for tracking renames
        
    Returns:
        Tuple of (original_path, new_path, description)
    """
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
    new_name = super().generate_new_filename(file_path, description)
    new_path = None
    if new_name:
        new_path = super().rename_file(file_path, new_name, rename_log)
        if new_path and new_path != file_path and cache_key in cache:
            cache[str(new_path)] = cache[cache_key]
            del cache[cache_key]
            save_cache(cache)
    return file_path, new_path, description
