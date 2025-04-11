#!/usr/bin/env python3
"""
Archive file processor for CleanupX (ZIP, TAR, etc.).
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any
from datetime import datetime

from cleanupx.config import ARCHIVE_FUNCTION_SCHEMA, ARCHIVE_EXTENSIONS, XAI_MODEL_TEXT
from cleanupx.utils.cache import save_cache, ensure_metadata_dir, get_description_path
from cleanupx.api import call_xai_api
from cleanupx.processors.base import BaseProcessor
from cleanupx.utils.common import clean_filename, strip_media_suffixes

# Configure logging
logger = logging.getLogger(__name__)

class ArchiveProcessor(BaseProcessor):
    """Processor for archive files (ZIP, TAR, RAR, etc.)."""
    
    def __init__(self):
        """Initialize the archive processor."""
        super().__init__()
        self.supported_extensions = ARCHIVE_EXTENSIONS
        self.max_size_mb = 100.0  # Archives can be larger
        
    def process(self, file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Dict:
        """
        Process an archive file.
        
        Args:
            file_path: Path to the archive file
            cache: Cache dictionary for storing/retrieving archive descriptions
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
            'error': None,
            'file_count': 0
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
                # Analyze archive
                description = self._analyze_archive(file_path)
                if description:
                    cache[cache_key] = description
                    save_cache(cache)
                    
            if not description:
                result['error'] = "Failed to analyze archive"
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
            if 'file_count' in description:
                result['file_count'] = description['file_count']
                
            return result
            
        except Exception as e:
            logger.error(f"Error processing archive {file_path}: {e}")
            result['error'] = str(e)
            return result
            
    def _analyze_archive(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        Analyze an archive's contents.
        
        Args:
            file_path: Path to the archive file
            
        Returns:
            Dictionary with archive analysis or None if analysis failed
        """
        try:
            file_path = Path(file_path)
            archive_ext = file_path.suffix.lower()
            file_stats = file_path.stat()
            file_size_mb = file_stats.st_size / (1024 * 1024)
            modified_time = datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            # Extract archive info based on type
            content_summary = []
            file_count = 0
            dir_count = 0
            content_types = {}
            
            # Process different archive types
            if archive_ext == '.zip':
                try:
                    import zipfile
                    with zipfile.ZipFile(file_path, 'r') as zipf:
                        file_list = zipf.namelist()
                        file_count = len(file_list)
                        content_summary.append(f"Archive contains {file_count} files/directories")
                        
                        # Analyze file types
                        for name in file_list:
                            if name.endswith('/'):  # Directory
                                dir_count += 1
                            else:
                                ext = os.path.splitext(name)[1].lower()
                                if ext in content_types:
                                    content_types[ext] += 1
                                else:
                                    content_types[ext] = 1
                                    
                        # Get file list preview (limited)
                        for i, name in enumerate(file_list[:20]):
                            content_summary.append(f"- {name}")
                        if len(file_list) > 20:
                            content_summary.append(f"... and {len(file_list) - 20} more items")
                except Exception as e:
                    logger.error(f"Error analyzing ZIP archive {file_path}: {e}")
                    content_summary.append(f"Error reading ZIP: {e}")
                    
            elif archive_ext in {'.tar', '.tgz', '.tar.gz', '.gz'}:
                if archive_ext == '.gz' and not str(file_path).endswith('.tar.gz'):
                    # For solo .gz files, handle differently
                    gz_info = get_gz_info(file_path)
                    content_summary.append(f"Compressed file: {gz_info.get('filename', 'unknown')}")
                    content_summary.append(f"Compressed size: {gz_info.get('compressed_size', 0) / 1024:.1f} KB")
                    if 'original_size' in gz_info:
                        content_summary.append(f"Original size: {gz_info.get('original_size', 0) / 1024:.1f} KB")
                    content_summary.append(f"Content type: {gz_info.get('content_type', 'unknown')}")
                    if 'detail' in gz_info:
                        content_summary.append(f"Details: {gz_info['detail']}")
                    file_count = 1
                else:
                    # For tar archives
                    try:
                        import tarfile
                        with tarfile.open(file_path, 'r') as tar:
                            file_list = tar.getnames()
                            file_count = len(file_list)
                            content_summary.append(f"Archive contains {file_count} files/directories")
                            
                            # Analyze file types
                            for name in file_list:
                                if name.endswith('/'):  # Directory
                                    dir_count += 1
                                else:
                                    ext = os.path.splitext(name)[1].lower()
                                    if ext in content_types:
                                        content_types[ext] += 1
                                    else:
                                        content_types[ext] = 1
                                        
                            # Get file list preview
                            for i, name in enumerate(file_list[:20]):
                                content_summary.append(f"- {name}")
                            if len(file_list) > 20:
                                content_summary.append(f"... and {len(file_list) - 20} more items")
                    except Exception as e:
                        logger.error(f"Error analyzing TAR archive {file_path}: {e}")
                        content_summary.append(f"Error reading TAR archive: {e}")
                        
            elif archive_ext == '.rar':
                try:
                    import rarfile
                    with rarfile.RarFile(file_path, 'r') as rf:
                        file_list = rf.namelist()
                        file_count = len(file_list)
                        content_summary.append(f"Archive contains {file_count} files/directories")
                        
                        # Analyze file types
                        for name in file_list:
                            if name.endswith('/'):  # Directory
                                dir_count += 1
                            else:
                                ext = os.path.splitext(name)[1].lower()
                                if ext in content_types:
                                    content_types[ext] += 1
                                else:
                                    content_types[ext] = 1
                                    
                        # Get file list preview
                        for i, name in enumerate(file_list[:20]):
                            content_summary.append(f"- {name}")
                        if len(file_list) > 20:
                            content_summary.append(f"... and {len(file_list) - 20} more items")
                except ImportError:
                    content_summary.append("rarfile module not installed. Please install with: pip install rarfile")
                except Exception as e:
                    logger.error(f"Error analyzing RAR archive {file_path}: {e}")
                    content_summary.append(f"Error reading RAR archive: {e}")
            else:
                content_summary.append(f"Unsupported archive type: {archive_ext}")
                
            # Create content type summary
            content_type_summary = []
            for ext, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
                content_type_summary.append(f"{ext}: {count} file(s)")
                
            # Build the final result
            result = {
                "file_path": str(file_path),
                "file_size": f"{file_size_mb:.2f} MB",
                "modified_date": modified_time,
                "archive_type": archive_ext.lstrip('.'),
                "file_count": file_count,
                "directory_count": dir_count,
                "content_summary": "\n".join(content_summary),
                "content_types": content_type_summary,
                "suggested_filename": self._generate_suggested_filename(file_path, content_types)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing archive {file_path}: {e}")
            return None
            
    def _generate_suggested_filename(self, file_path: Path, content_types: Dict[str, int]) -> str:
        """
        Generate a suggested filename based on archive contents.
        
        Args:
            file_path: Path to the archive file
            content_types: Dictionary of file extensions and their counts
            
        Returns:
            Suggested filename without extension
        """
        # Start with the original name
        original_name = strip_media_suffixes(file_path.stem)
        
        # If the archive is empty or we couldn't analyze it, just return the original name
        if not content_types:
            return original_name
            
        # Find the most common file type
        most_common_ext = None
        most_common_count = 0
        for ext, count in content_types.items():
            if count > most_common_count:
                most_common_ext = ext
                most_common_count = count
                
        # Append the most common file type to the name if it's significant
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
        
    def _generate_markdown(self, file_path: Path, description: Dict[str, Any]):
        """
        Generate markdown summary for the archive.
        
        Args:
            file_path: Path to the archive file
            description: Dictionary with archive description
        """
        try:
            ensure_metadata_dir(file_path.parent)
            md_path = get_description_path(file_path)
            
            content = [
                f"# {description.get('suggested_filename', file_path.stem)}",
                "",
                "## Archive Information",
                f"- **Original Filename:** {file_path.name}",
                f"- **Archive Type:** {description.get('archive_type', 'Unknown').upper()}",
                f"- **File Size:** {description.get('file_size', 'Unknown')}",
                f"- **Modified Date:** {description.get('modified_date', 'Unknown')}",
                f"- **File Count:** {description.get('file_count', 0)}",
                f"- **Directory Count:** {description.get('directory_count', 0)}",
                "",
                "## Content Types",
            ]
            
            # Add content types
            for content_type in description.get('content_types', []):
                content.append(f"- {content_type}")
                
            # Add content summary
            content.extend([
                "",
                "## Content Summary",
                description.get('content_summary', 'No content summary available')
            ])
            
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
            logger.info(f"Generated markdown summary: {md_path}")
        except Exception as e:
            logger.error(f"Error generating markdown for {file_path}: {e}")

# Keep existing utility functions

def get_gz_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get detailed information about a gzip file and its contents.
    
    Args:
        file_path: Path to the gzip file
        
    Returns:
        Dict with information about the gzip file and its contents
    """
    try:
        import gzip
        file_path = Path(file_path)
        info = {
            "original_size": 0,
            "compressed_size": file_path.stat().st_size,
            "filename": file_path.name,
            "content_preview": "",
            "is_binary": True,
            "content_type": "unknown"
        }
        
        # Try to determine the original filename and examine content
        with gzip.open(file_path, 'rb') as gz:
            # Get original filename if available
            if hasattr(gz, 'name'):
                info["original_filename"] = Path(gz.name).name
            
            # Try to read some content to analyze
            content = gz.read(8192)  # Read first 8KB for better analysis
            
            # Try to detect content type
            import magic
            content_type = "unknown"
            try:
                # Use python-magic if available for better content type detection
                content_type = magic.from_buffer(content, mime=True)
                info["content_type"] = content_type
            except (ImportError, AttributeError):
                # Fallback method if python-magic not available
                if content.startswith(b'<html') or content.startswith(b'<!DOCTYPE html'):
                    content_type = "text/html"
                elif content.startswith(b'<?xml'):
                    content_type = "text/xml"
                elif content.startswith(b'PK\x03\x04'):
                    content_type = "application/zip"
                elif b'\0' not in content[:100]:
                    content_type = "text/plain"
                info["content_type"] = content_type
            
            # Try to decode as text if it appears to be text-based
            if content_type.startswith('text/') or content_type in ['application/json', 'application/xml']:
                try:
                    decoded = content.decode('utf-8', errors='replace')
                    info["content_preview"] = decoded[:2000]  # First 2000 chars
                    info["is_binary"] = False
                except UnicodeDecodeError:
                    info["content_preview"] = f"Binary data ({len(content)} bytes)"
                    info["is_binary"] = True
            else:
                # Handle binary data differently based on content type
                if content_type.startswith('image/'):
                    info["content_preview"] = f"Image data ({len(content)} bytes)"
                elif content_type == 'application/zip':
                    info["content_preview"] = f"Zip archive data ({len(content)} bytes)"
                    # You could try to open this as a zip file and list contents
                    try:
                        import io
                        import zipfile
                        zf = zipfile.ZipFile(io.BytesIO(content))
                        info["zip_contents"] = zf.namelist()[:20]  # List up to 20 files
                    except:
                        pass
                else:
                    info["content_preview"] = f"Binary data ({len(content)} bytes)"
                
            # Try to estimate original size by seeking to end
            try:
                gz.seek(0)
                decompressed = gz.read()
                info["original_size"] = len(decompressed)
                
                # Try to create a more detailed preview based on what we've seen
                if not info["is_binary"]:
                    # For text files, add line count
                    line_count = decompressed.count(b'\n') + 1
                    info["line_count"] = line_count
                    info["detail"] = f"Text file with {line_count} lines"
                elif content_type.startswith('image/'):
                    # For images, try to get dimensions
                    try:
                        import io
                        from PIL import Image
                        img = Image.open(io.BytesIO(decompressed))
                        info["image_dimensions"] = f"{img.width}x{img.height}"
                        info["detail"] = f"Image: {img.width}x{img.height}, {img.format}"
                    except:
                        info["detail"] = "Image file"
                else:
                    info["detail"] = f"Binary file ({content_type})"
                    
            except Exception as e:
                logger.warning(f"Could not determine original size: {e}")
        
        return info
    except Exception as e:
        logger.error(f"Error analyzing gzip file {file_path}: {e}")
        return {
            "error": str(e),
            "filename": Path(file_path).name,
            "compressed_size": Path(file_path).stat().st_size
        }
