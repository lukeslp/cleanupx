"""
Core file processing module for CleanupX.
"""

import os
import re
import logging
import gc
import fnmatch
import mimetypes
import magic
import base64
import io
import subprocess
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Type, Tuple
from datetime import datetime
from abc import ABC, abstractmethod

from .config import (
    IMAGE_EXTENSIONS,
    MEDIA_EXTENSIONS,
    ARCHIVE_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    TEXT_EXTENSIONS,
    CODE_EXTENSIONS,
    PROTECTED_PATTERNS,
    IMAGE_FUNCTION_SCHEMA,
    FILE_IMAGE_PROMPT,
    XAI_MODEL_VISION,
    DOCUMENT_FUNCTION_SCHEMA,
    FILE_DOCUMENT_PROMPT,
    XAI_MODEL_TEXT
)
from .utils import (
    get_file_hash,
    get_file_metadata,
    is_protected_file,
    normalize_path,
    save_rename_log,
    add_error_to_log,
    get_image_dimensions,
    convert_heic_to_jpeg,
    convert_webp_to_jpeg,
    embed_alt_text_into_image,
    read_text_file,
    strip_media_suffixes,
    ensure_metadata_dir,
    get_description_path
)
from .api import call_xai_api, timeout, TimeoutError

# Configure logging
logger = logging.getLogger(__name__)

# Timeout for image processing (in seconds)
process_timeout = 30

# Try to import optional dependencies
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.error("PIL/Pillow not installed. Install with: pip install Pillow")

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logging.error("python-docx not installed. Install with: pip install python-docx")

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.error("PyPDF2 not installed. Install with: pip install PyPDF2")

def clean_filename(filename: str) -> str:
    """
    Clean a filename by removing invalid characters and controlling spaces.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Replace invalid characters with underscores
    invalid_chars = r'[<>:"/\\|?*\x00-\x1F]'
    filename = re.sub(invalid_chars, '_', filename)
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Replace multiple underscores with a single one
    while '__' in filename:
        filename = filename.replace('__', '_')
        
    # Remove leading/trailing underscores, dots, commas
    chars_to_strip = ['_', '.', ',', '-']
    base_name, ext = os.path.splitext(filename)
    
    for char in chars_to_strip:
        while base_name.startswith(char):
            base_name = base_name[1:]
        while base_name.endswith(char):
            base_name = base_name[:-1]
            
    # Limit filename length (Windows max path is 260 chars, leave room for path)
    if len(base_name) > 200:
        base_name = base_name[:200]
        
    # If base name is empty, use a timestamp
    if not base_name:
        base_name = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    return base_name + ext

class FileProcessor:
    """
    Core file processor for CleanupX.
    Handles all file types and processing operations.
    """
    
    def __init__(
        self,
        base_directory: Optional[str] = None,
        supported_extensions: Optional[List[str]] = None,
        recursive: bool = True,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the file processor.
        
        Args:
            base_directory: Root directory to process
            supported_extensions: List of file extensions to process
            recursive: Whether to search subdirectories
            logger: Optional logger instance
        """
        self.processed_files: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.max_size_mb = 25.0
        
        # Initialize base directory if provided
        if base_directory:
            self.base_directory = Path(base_directory)
            if not self.base_directory.exists():
                raise FileNotFoundError(f"Directory not found: {base_directory}")
        else:
            self.base_directory = None
            
        # Set supported extensions
        self.supported_extensions = supported_extensions or {
            'image': set(IMAGE_EXTENSIONS),
            'document': set(DOCUMENT_EXTENSIONS),
            'archive': set(ARCHIVE_EXTENSIONS),
            'text': set(TEXT_EXTENSIONS),
            'media': set(MEDIA_EXTENSIONS)
        }
        
        self.recursive = recursive
        self.logger = logger or logging.getLogger(__name__)
        
    def check_file_size(self, file_path: Union[str, Path], max_size: Optional[int] = None) -> bool:
        """
        Check if a file's size is within limits.
        
        Args:
            file_path: Path to the file to check
            max_size: Maximum file size in MB (overrides instance max_size_mb)
            
        Returns:
            Whether the file size is within limits
        """
        try:
            path = Path(file_path)
            if not path.exists():
                self.logger.warning(f"File not found: {path}")
                return False
                
            size_mb = path.stat().st_size / (1024 * 1024)
            max_allowed = max_size if max_size is not None else self.max_size_mb
            
            if max_allowed > 0 and size_mb > max_allowed:
                self.logger.warning(f"File too large ({size_mb:.1f}MB): {path}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking file size for {file_path}: {e}")
            return False
            
    def can_process(self, file_path: Union[str, Path]) -> bool:
        """
        Check if a file can be processed based on its extension and size.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            Whether the file can be processed
        """
        try:
            path = Path(file_path)
            
            # Check if file exists
            if not path.exists():
                self.logger.warning(f"File not found: {path}")
                return False
                
            # Check if file is protected
            if is_protected_file(path, PROTECTED_PATTERNS):
                self.logger.info(f"Protected file: {path}")
                return False
                
            # Check file size
            if not self.check_file_size(path):
                return False
                
            # Check file extension
            ext = path.suffix.lower()
            for extensions in self.supported_extensions.values():
                if ext in extensions:
                    return True
                    
            self.logger.warning(f"Unsupported file type: {path}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking file {file_path}: {e}")
            return False
        
    def scan_directory(self) -> List[Path]:
        """
        Scans directory for supported files.
        
        Returns:
            List[Path]: List of paths to supported files
            
        Raises:
            FileNotFoundError: If directory scanning fails
        """
        try:
            if not self.base_directory:
                raise FileNotFoundError("No base directory specified")
                
            self.logger.info(f"Scanning directory: {self.base_directory}")
            pattern = '**/*' if self.recursive else '*'
            files = []
            
            # Flatten supported extensions list
            all_extensions = set()
            for ext_set in self.supported_extensions.values():
                all_extensions.update(ext_set)
                
            for ext in all_extensions:
                found = list(self.base_directory.glob(f'{pattern}{ext}'))
                self.logger.debug(f"Found {len(found)} files with extension {ext}")
                files.extend(found)
                
            self.logger.info(f"Total files found: {len(files)}")
            return files
            
        except Exception as e:
            self.logger.error(f"Error scanning directory: {str(e)}")
            raise FileNotFoundError(f"Error scanning directory: {str(e)}")
            
    def validate_file(self, file_path: Path) -> bool:
        """
        Validates if a file can be processed.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            bool: Whether the file is valid for processing
        """
        try:
            if not file_path.exists():
                self.logger.warning(f"File not found: {file_path}")
                return False
                
            if not file_path.is_file():
                self.logger.warning(f"Not a file: {file_path}")
                return False
                
            # Check if file extension is supported
            ext = file_path.suffix.lower()
            is_supported = any(ext in exts for exts in self.supported_extensions.values())
            if not is_supported:
                self.logger.warning(f"Unsupported file type: {file_path}")
                return False
                
            # Check if file is readable
            try:
                file_path.open('rb').close()
            except Exception as e:
                self.logger.warning(f"File not readable: {file_path} - {str(e)}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating file {file_path}: {str(e)}")
            return False
            
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Gets basic information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dict containing:
                - name: Original filename
                - extension: File extension
                - size: File size in bytes
                - created: Creation timestamp
                - modified: Last modified timestamp
        """
        try:
            stats = file_path.stat()
            return {
                'name': file_path.name,
                'extension': file_path.suffix.lower(),
                'size': stats.st_size,
                'created': stats.st_ctime,
                'modified': stats.st_mtime
            }
        except Exception as e:
            self.logger.error(f"Error getting file info: {str(e)}")
            raise FileProcessingError(f"Error getting file info: {str(e)}")
            
    def create_backup(self, file_path: Path) -> Path:
        """
        Creates a backup of a file before processing.
        
        Args:
            file_path: Path to the file to backup
            
        Returns:
            Path to the backup file
            
        Raises:
            FileProcessingError: If backup creation fails
        """
        try:
            backup_path = file_path.with_suffix(file_path.suffix + '.bak')
            self.logger.info(f"Creating backup: {backup_path}")
            
            import shutil
            shutil.copy2(file_path, backup_path)
            
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Error creating backup: {str(e)}")
            raise FileProcessingError(f"Error creating backup: {str(e)}")
            
    def restore_from_backup(self, backup_path: Path) -> bool:
        """
        Restores a file from its backup.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            bool: Whether restoration was successful
        """
        try:
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
                
            original_path = backup_path.with_suffix('')
            self.logger.info(f"Restoring from backup: {original_path}")
            
            import shutil
            shutil.move(backup_path, original_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error restoring from backup: {str(e)}")
            return False
        
    def process_directory(
        self,
        directory: Path,
        recursive: bool = False,
        max_size: Optional[int] = None,
        skip_images: bool = False,
        skip_documents: bool = False,
        skip_archives: bool = False,
        skip_text: bool = False,
        skip_media: bool = False,
        citation_styles: Optional[List[str]] = None,
        generate_dash: bool = False
    ) -> None:
        """
        Process all files in a directory.
        
        Args:
            directory: Path to the directory to process
            recursive: Whether to process subdirectories
            max_size: Maximum file size in MB to process
            skip_images: Whether to skip image files
            skip_documents: Whether to skip document files
            skip_archives: Whether to skip archive files
            skip_text: Whether to skip text files
            skip_media: Whether to skip media files
            citation_styles: Optional list of citation styles to extract
            generate_dash: Whether to generate a dashboard
        """
        try:
            if not directory.exists():
                raise FileNotFoundError(f"Directory not found: {directory}")
                
            for item in directory.iterdir():
                if item.is_file():
                    self._process_file(
                        item,
                        max_size=max_size,
                        skip_images=skip_images,
                        skip_documents=skip_documents,
                        skip_archives=skip_archives,
                        skip_text=skip_text,
                        skip_media=skip_media,
                        citation_styles=citation_styles,
                        generate_dash=generate_dash
                    )
                elif recursive and item.is_dir():
                    self.process_directory(
                        item,
                        recursive=recursive,
                        max_size=max_size,
                        skip_images=skip_images,
                        skip_documents=skip_documents,
                        skip_archives=skip_archives,
                        skip_text=skip_text,
                        skip_media=skip_media,
                        citation_styles=citation_styles,
                        generate_dash=generate_dash
                    )
                    
        except Exception as e:
            logger.error(f"Error processing directory {directory}: {e}")
            self.errors.append(str(e))
            
    def _process_file(
        self,
        file_path: Path,
        max_size: Optional[int] = None,
        skip_images: bool = False,
        skip_documents: bool = False,
        skip_archives: bool = False,
        skip_text: bool = False,
        skip_media: bool = False,
        citation_styles: Optional[List[str]] = None,
        generate_dash: bool = False
    ) -> None:
        """
        Process a single file.
        
        Args:
            file_path: Path to the file to process
            max_size: Maximum file size in MB to process
            skip_images: Whether to skip image files
            skip_documents: Whether to skip document files
            skip_archives: Whether to skip archive files
            skip_text: Whether to skip text files
            skip_media: Whether to skip media files
            citation_styles: Optional list of citation styles to extract
            generate_dash: Whether to generate a dashboard
        """
        try:
            # Check file size
            if max_size is not None:
                size_mb = file_path.stat().st_size / (1024 * 1024)
                if size_mb > max_size:
                    logger.info(f"Skipping large file: {file_path} ({size_mb:.2f} MB)")
                    return
                    
            # Determine file type
            file_type = self._get_file_type(file_path)
            
            # Check if we should skip this file type
            if (file_type == 'image' and skip_images) or \
               (file_type == 'document' and skip_documents) or \
               (file_type == 'archive' and skip_archives) or \
               (file_type == 'text' and skip_text) or \
               (file_type == 'media' and skip_media):
                logger.info(f"Skipping {file_type} file as requested: {file_path}")
                return
                
            # Process based on file type
            if file_type == 'image':
                self._process_image(file_path)
            elif file_type == 'document':
                self._process_document(file_path)
            elif file_type == 'archive':
                self._process_archive(file_path)
            elif file_type == 'text':
                self._process_text(file_path, citation_styles)
            elif file_type == 'media':
                self._process_media(file_path)
            else:
                logger.warning(f"Unsupported file type: {file_path}")
                
            # Update processed files tracking
            self.processed_files[str(file_path)] = {
                'type': file_type,
                'size': file_path.stat().st_size,
                'processed': True
            }
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            self.errors.append(str(e))
            
    def _get_file_type(self, file_path: Path) -> str:
        """
        Determine the file type based on its extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File type as a string
        """
        ext = file_path.suffix.lower()
        for file_type, extensions in self.supported_extensions.items():
            if ext in extensions:
                return file_type
        return 'other'
        
    def _process_image(self, file_path: Path) -> None:
        """
        Process an image file.
        
        Args:
            file_path: Path to the image file
        """
        try:
            # Check if we can process this file
            if not self.can_process(file_path):
                logger.warning(f"Unsupported file type: {file_path.suffix}")
                return
                
            # Check file size
            if not self.check_file_size(file_path):
                logger.warning(f"File size exceeds maximum ({self.max_size_mb}MB)")
                return
                
            # Analyze image
            description = self._analyze_image(file_path)
            if not description:
                logger.error(f"Failed to analyze image: {file_path}")
                return
                
            # Generate new filename
            new_name = self.generate_new_filename(file_path, description)
            if not new_name:
                logger.error(f"Failed to generate new filename for: {file_path}")
                return
                
            # Rename file
            new_path = self.rename_file(file_path, new_name)
            if new_path:
                logger.info(f"Renamed image: {file_path} -> {new_path}")
                
            # Update metadata
            if PIL_AVAILABLE:
                try:
                    embed_alt_text_into_image(new_path or file_path, description.get('alt_text', ''))
                except Exception as e:
                    logger.error(f"Error updating image metadata: {e}")
                    
            # Generate markdown
            self._generate_image_markdown(file_path, description)
            
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {e}")
            self.errors.append(str(e))
            
    def _analyze_image(self, image_path: Path) -> Optional[Dict[str, Any]]:
        """
        Analyze an image using X.AI Vision API.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with image analysis or None if analysis failed
        """
        original_path = image_path
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
                img = Image.open(analysis_path)
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
                img.close()
                gc.collect()
                    
            except Exception as e:
                logger.error(f"Error resizing large image: {e}")
                
        try:
            # Encode image
            image_data = self._encode_image(analysis_path)
            if not image_data:
                logger.error(f"Failed to encode image: {analysis_path}")
                self._cleanup_temp_files(temp_converted)
                gc.collect()
                return None
                
            # Call API with timeout
            result = None
            try:
                result = call_xai_api(XAI_MODEL_VISION, FILE_IMAGE_PROMPT, IMAGE_FUNCTION_SCHEMA, image_data)
            except Exception as e:
                logger.error(f"Error during image analysis: {e}")
                self._cleanup_temp_files(temp_converted)
                gc.collect()
                return None
                
            if result:
                logger.info(f"Successfully analyzed image: {original_path.name}")
            else:
                logger.error(f"Failed to analyze image: {original_path.name}")
                
        except Exception as e:
            logger.error(f"Error during image analysis: {e}")
            self._cleanup_temp_files(temp_converted)
            gc.collect()
            return None
            
        self._cleanup_temp_files(temp_converted)
        image_data = None
        gc.collect()
        
        return result
        
    def _encode_image(self, image_path: Path) -> Optional[str]:
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
                
    def _generate_image_markdown(self, file_path: Path, description: Dict[str, Any]):
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
                f"# {description.get('title', file_path.stem)}",
                "",
                f"**Description:** {description.get('description', 'No description available')}",
                "",
                "## Image Information",
                f"- **Original Filename:** {file_path.name}",
                f"- **File Size:** {description.get('file_size', 'Unknown')}",
                f"- **Dimensions:** {description.get('dimensions', 'Unknown')}",
                f"- **Format:** {description.get('format', 'Unknown')}",
                "",
                "## Content Analysis",
                f"- **Main Subject:** {description.get('main_subject', 'Unknown')}",
                f"- **Scene Type:** {description.get('scene_type', 'Unknown')}",
                f"- **Colors:** {description.get('colors', 'Unknown')}",
                "",
                "## Tags",
                "\n".join(f"- {tag}" for tag in description.get('tags', []))
            ]
            
            if 'alt_text' in description:
                content.extend([
                    "",
                    "## Accessibility",
                    f"**Alt Text:** {description['alt_text']}"
                ])
                
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
            logger.info(f"Generated markdown description: {md_path}")
        except Exception as e:
            logger.error(f"Error generating markdown for {file_path}: {e}")
            
    def _process_document(self, file_path: Path) -> None:
        """
        Process a document file.
        
        Args:
            file_path: Path to the document file
        """
        try:
            # Check if we can process this file
            if not self.can_process(file_path):
                logger.warning(f"Unsupported file type: {file_path.suffix}")
                return
                
            # Check file size
            if not self.check_file_size(file_path):
                logger.warning(f"File size exceeds maximum ({self.max_size_mb}MB)")
                return
                
            # Analyze document
            description = self._analyze_document(file_path)
            if not description:
                logger.error(f"Failed to analyze document: {file_path}")
                return
                
            # Generate new filename
            new_name = self.generate_new_filename(file_path, description, "document")
            if not new_name:
                logger.error(f"Failed to generate new filename for: {file_path}")
                return
                
            # Rename file
            new_path = self.rename_file(file_path, new_name)
            if new_path:
                logger.info(f"Renamed document: {file_path} -> {new_path}")
                
            # Generate markdown
            self._generate_document_markdown(file_path, description)
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            self.errors.append(str(e))
            
    def _analyze_document(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Analyze a document using AI.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with document analysis or None if analysis failed
        """
        try:
            # Extract text from document
            text = self._extract_document_text(file_path)
            if not text or not text.strip():
                logger.error(f"Failed to extract text from {file_path}")
                return None
                
            # Add file metadata to text
            file_stats = file_path.stat()
            file_size_mb = file_stats.st_size / (1024 * 1024)
            modified_time = datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            # Get page count for PDFs
            page_count = None
            if file_path.suffix.lower() == '.pdf':
                page_count = self._get_pdf_page_count(file_path)
                
            # Prepare analysis request
            prompt = FILE_DOCUMENT_PROMPT
            max_text_length = 15000  # Limit text to avoid token limits
            
            if len(text) > max_text_length:
                logger.info(f"Truncating document text from {len(text)} to {max_text_length} characters")
                text = text[:max_text_length] + "\n[... TRUNCATED ...]"
                
            # Call API for analysis
            result = call_xai_api(
                XAI_MODEL_TEXT,
                prompt,
                DOCUMENT_FUNCTION_SCHEMA,
                text,
                filename=file_path.name,
                file_size=f"{file_size_mb:.2f} MB",
                modified_date=modified_time,
                page_count=page_count
            )
            
            if not result:
                logger.error(f"Failed to analyze document: {file_path}")
                return None
                
            # Add metadata
            result['file_size'] = f"{file_size_mb:.2f} MB"
            result['modified_date'] = modified_time
            if page_count:
                result['page_count'] = page_count
                
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing document {file_path}: {e}")
            return None
            
    def _extract_document_text(self, file_path: Path, max_pages: int = 5) -> str:
        """
        Extract text from a document file.
        
        Args:
            file_path: Path to the document file
            max_pages: Maximum number of pages to extract (for PDFs)
            
        Returns:
            Extracted text or empty string if extraction failed
        """
        file_extension = file_path.suffix.lower()
        
        if file_extension == '.pdf':
            return self._extract_text_from_pdf(file_path, max_pages)
        elif file_extension == '.docx' and DOCX_AVAILABLE:
            return self._extract_text_from_docx(file_path)
        elif file_extension in ['.txt', '.md', '.py', '.js', '.html', '.css', '.csv', '.json', '.xml']:
            return self._extract_text_from_txt(file_path)
        else:
            logger.warning(f"No specific extraction method for {file_extension}, trying as text file")
            return self._extract_text_from_txt(file_path)
            
    def _get_pdf_page_count(self, file_path: Path) -> Optional[int]:
        """
        Get the number of pages in a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Number of pages or None if count failed
        """
        if not PDF_AVAILABLE:
            return None
            
        try:
            with open(file_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                return len(pdf.pages)
        except Exception as e:
            logger.error(f"Error getting PDF page count: {e}")
            return None
            
    def _extract_text_from_pdf(self, file_path: Path, max_pages: int = 5) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            max_pages: Maximum number of pages to extract
            
        Returns:
            Extracted text or empty string if extraction failed
        """
        if not PDF_AVAILABLE:
            return ""
            
        try:
            with open(file_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                text = []
                for page in pdf.pages[:max_pages]:
                    text.append(page.extract_text())
                return "\n".join(text)
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""
            
    def _extract_text_from_docx(self, file_path: Path) -> str:
        """
        Extract text from a DOCX file.
        
        Args:
            file_path: Path to the DOCX file
            
        Returns:
            Extracted text or empty string if extraction failed
        """
        if not DOCX_AVAILABLE:
            return ""
            
        try:
            doc = Document(file_path)
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            return ""
            
    def _extract_text_from_txt(self, file_path: Path) -> str:
        """
        Extract text from a text file.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Extracted text or empty string if extraction failed
        """
        try:
            return read_text_file(file_path)
        except Exception as e:
            logger.error(f"Error extracting text from text file: {e}")
            return ""
            
    def _generate_document_markdown(self, file_path: Path, description: Dict[str, Any]):
        """
        Generate markdown description for the document.
        
        Args:
            file_path: Path to the document file
            description: Dictionary with document description
        """
        try:
            ensure_metadata_dir(file_path.parent)
            md_path = get_description_path(file_path)
            
            content = [
                f"# {description.get('title', file_path.stem)}",
                "",
                f"**Summary:** {description.get('summary', 'No summary available')}",
                "",
                "## Document Information",
                f"- **Original Filename:** {file_path.name}",
                f"- **File Size:** {description.get('file_size', 'Unknown')}",
                f"- **Modified Date:** {description.get('modified_date', 'Unknown')}"
            ]
            
            if 'page_count' in description:
                content.append(f"- **Pages:** {description['page_count']}")
                
            content.extend([
                "",
                "## Content Analysis",
                f"- **Document Type:** {description.get('document_type', 'Unknown')}",
                f"- **Subject:** {description.get('subject', 'Unknown')}",
                f"- **Language:** {description.get('language', 'Unknown')}",
                "",
                "## Keywords",
                "\n".join(f"- {keyword}" for keyword in description.get('keywords', []))
            ])
            
            if 'citations' in description and description['citations']:
                content.extend([
                    "",
                    "## Citations",
                    "\n".join(f"- {citation}" for citation in description['citations'])
                ])
                
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
            logger.info(f"Generated markdown description: {md_path}")
        except Exception as e:
            logger.error(f"Error generating markdown for {file_path}: {e}")
            
    def _process_archive(self, file_path: Path) -> None:
        """
        Process an archive file.
        
        Args:
            file_path: Path to the archive file
        """
        try:
            # Check if we can process this file
            if not self.can_process(file_path):
                logger.warning(f"Unsupported file type: {file_path.suffix}")
                return
                
            # Check file size
            if not self.check_file_size(file_path):
                logger.warning(f"File size exceeds maximum ({self.max_size_mb}MB)")
                return
                
            # Get archive metadata
            metadata = self._get_archive_metadata(file_path)
            if not metadata:
                logger.error(f"Failed to get archive metadata: {file_path}")
                return
                
            # Generate new filename
            new_name = self.generate_new_filename(file_path, metadata, "archive")
            if not new_name:
                logger.error(f"Failed to generate new filename for: {file_path}")
                return
                
            # Rename file
            new_path = self.rename_file(file_path, new_name)
            if new_path:
                logger.info(f"Renamed archive: {file_path} -> {new_path}")
                
            # Generate markdown
            self._generate_archive_markdown(file_path, metadata)
            
        except Exception as e:
            logger.error(f"Error processing archive {file_path}: {e}")
            self.errors.append(str(e))
            
    def _get_archive_metadata(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get metadata from an archive file.
        
        Args:
            file_path: Path to the archive file
            
        Returns:
            Dictionary with archive metadata or None if metadata extraction failed
        """
        try:
            file_stats = file_path.stat()
            file_size_mb = file_stats.st_size / (1024 * 1024)
            modified_time = datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            # Get archive type and contents
            archive_type = file_path.suffix.lower()[1:]  # Remove the dot
            contents = self._list_archive_contents(file_path)
            
            return {
                'file_size': f"{file_size_mb:.2f} MB",
                'modified_date': modified_time,
                'archive_type': archive_type,
                'contents': contents,
                'file_count': len(contents) if contents else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting archive metadata: {e}")
            return None
            
    def _list_archive_contents(self, file_path: Path) -> List[str]:
        """
        List contents of an archive file.
        
        Args:
            file_path: Path to the archive file
            
        Returns:
            List of file paths in the archive
        """
        try:
            if file_path.suffix.lower() == '.zip':
                import zipfile
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    return zip_ref.namelist()
            elif file_path.suffix.lower() == '.tar':
                import tarfile
                with tarfile.open(file_path, 'r') as tar_ref:
                    return tar_ref.getnames()
            elif file_path.suffix.lower() in ['.gz', '.bz2']:
                import tarfile
                with tarfile.open(file_path, 'r:*') as tar_ref:
                    return tar_ref.getnames()
            else:
                logger.warning(f"Unsupported archive format: {file_path.suffix}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing archive contents: {e}")
            return []
            
    def _generate_archive_markdown(self, file_path: Path, metadata: Dict[str, Any]):
        """
        Generate markdown description for the archive.
        
        Args:
            file_path: Path to the archive file
            metadata: Dictionary with archive metadata
        """
        try:
            ensure_metadata_dir(file_path.parent)
            md_path = get_description_path(file_path)
            
            content = [
                f"# {file_path.stem}",
                "",
                "## Archive Information",
                f"- **Original Filename:** {file_path.name}",
                f"- **File Size:** {metadata.get('file_size', 'Unknown')}",
                f"- **Modified Date:** {metadata.get('modified_date', 'Unknown')}",
                f"- **Archive Type:** {metadata.get('archive_type', 'Unknown')}",
                f"- **File Count:** {metadata.get('file_count', 0)}",
                "",
                "## Contents"
            ]
            
            if metadata.get('contents'):
                content.extend(f"- {item}" for item in metadata['contents'])
            else:
                content.append("- No contents listed")
                
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
            logger.info(f"Generated markdown description: {md_path}")
        except Exception as e:
            logger.error(f"Error generating markdown for {file_path}: {e}")
            
    def _process_text(self, file_path: Path, citation_styles: Optional[List[str]] = None) -> None:
        """
        Process a text file.
        
        Args:
            file_path: Path to the text file
            citation_styles: Optional list of citation styles to extract
        """
        try:
            # Check if we can process this file
            if not self.can_process(file_path):
                logger.warning(f"Unsupported file type: {file_path.suffix}")
                return
                
            # Check file size
            if not self.check_file_size(file_path):
                logger.warning(f"File size exceeds maximum ({self.max_size_mb}MB)")
                return
                
            # Extract text and analyze
            text = self._extract_text_from_txt(file_path)
            if not text:
                logger.error(f"Failed to extract text from {file_path}")
                return
                
            # Analyze text
            description = self._analyze_text(file_path, text, citation_styles)
            if not description:
                logger.error(f"Failed to analyze text: {file_path}")
                return
                
            # Generate new filename
            new_name = self.generate_new_filename(file_path, description, "text")
            if not new_name:
                logger.error(f"Failed to generate new filename for: {file_path}")
                return
                
            # Rename file
            new_path = self.rename_file(file_path, new_name)
            if new_path:
                logger.info(f"Renamed text file: {file_path} -> {new_path}")
                
            # Generate markdown
            self._generate_text_markdown(file_path, description)
            
        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {e}")
            self.errors.append(str(e))
            
    def _analyze_text(self, file_path: Path, text: str, citation_styles: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze text content.
        
        Args:
            file_path: Path to the text file
            text: Extracted text content
            citation_styles: Optional list of citation styles to extract
            
        Returns:
            Dictionary with text analysis or None if analysis failed
        """
        try:
            # Get file metadata
            file_stats = file_path.stat()
            file_size_mb = file_stats.st_size / (1024 * 1024)
            modified_time = datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            # Prepare analysis request
            prompt = "Analyze the following text and extract key information:"
            max_text_length = 15000  # Limit text to avoid token limits
            
            if len(text) > max_text_length:
                logger.info(f"Truncating text from {len(text)} to {max_text_length} characters")
                text = text[:max_text_length] + "\n[... TRUNCATED ...]"
                
            # Call API for analysis
            result = call_xai_api(
                XAI_MODEL_TEXT,
                prompt,
                DOCUMENT_FUNCTION_SCHEMA,
                text,
                filename=file_path.name,
                file_size=f"{file_size_mb:.2f} MB",
                modified_date=modified_time
            )
            
            if not result:
                logger.error(f"Failed to analyze text: {file_path}")
                return None
                
            # Add metadata
            result['file_size'] = f"{file_size_mb:.2f} MB"
            result['modified_date'] = modified_time
            
            # Extract citations if requested
            if citation_styles:
                result['citations'] = self._extract_citations(text, citation_styles)
                
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            return None
            
    def _extract_citations(self, text: str, styles: List[str]) -> List[str]:
        """
        Extract citations from text using specified styles.
        
        Args:
            text: Text content to analyze
            styles: List of citation styles to look for
            
        Returns:
            List of extracted citations
        """
        citations = []
        try:
            # Common citation patterns
            patterns = {
                'apa': r'\([A-Za-z]+, \d{4}\)',
                'mla': r'\([A-Za-z]+ \d+\)',
                'chicago': r'\([A-Za-z]+ \d{4}, \d+\)',
                'ieee': r'\[\d+\]',
                'vancouver': r'\[\d+\]'
            }
            
            for style in styles:
                if style.lower() in patterns:
                    matches = re.findall(patterns[style.lower()], text)
                    citations.extend(matches)
                    
            return list(set(citations))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error extracting citations: {e}")
            return []
            
    def _generate_text_markdown(self, file_path: Path, description: Dict[str, Any]):
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
                "",
                "## Content Analysis",
                f"- **Document Type:** {description.get('document_type', 'Unknown')}",
                f"- **Subject:** {description.get('subject', 'Unknown')}",
                f"- **Language:** {description.get('language', 'Unknown')}",
                "",
                "## Keywords",
                "\n".join(f"- {keyword}" for keyword in description.get('keywords', []))
            ]
            
            if 'citations' in description and description['citations']:
                content.extend([
                    "",
                    "## Citations",
                    "\n".join(f"- {citation}" for citation in description['citations'])
                ])
                
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
            logger.info(f"Generated markdown description: {md_path}")
        except Exception as e:
            logger.error(f"Error generating markdown for {file_path}: {e}")
            
    def _process_media(self, file_path: Path) -> None:
        """
        Process a media file.
        
        Args:
            file_path: Path to the media file
        """
        try:
            # Check if we can process this file
            if not self.can_process(file_path):
                logger.warning(f"Unsupported file type: {file_path.suffix}")
                return
                
            # Check file size
            if not self.check_file_size(file_path):
                logger.warning(f"File size exceeds maximum ({self.max_size_mb}MB)")
                return
                
            # Get media metadata
            metadata = self._get_media_metadata(file_path)
            if not metadata:
                logger.error(f"Failed to get media metadata: {file_path}")
                return
                
            # Generate new filename
            new_name = self.generate_new_filename(file_path, metadata, "media")
            if not new_name:
                logger.error(f"Failed to generate new filename for: {file_path}")
                return
                
            # Rename file
            new_path = self.rename_file(file_path, new_name)
            if new_path:
                logger.info(f"Renamed media file: {file_path} -> {new_path}")
                
            # Generate markdown
            self._generate_media_markdown(file_path, metadata)
            
        except Exception as e:
            logger.error(f"Error processing media file {file_path}: {e}")
            self.errors.append(str(e))
            
    def _get_media_metadata(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get metadata from a media file.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            Dictionary with media metadata or None if metadata extraction failed
        """
        try:
            file_stats = file_path.stat()
            file_size_mb = file_stats.st_size / (1024 * 1024)
            modified_time = datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            # Get media type
            media_type = self._get_media_type(file_path)
            
            # Get duration and other metadata based on type
            metadata = {
                'file_size': f"{file_size_mb:.2f} MB",
                'modified_date': modified_time,
                'media_type': media_type
            }
            
            if media_type == 'audio':
                metadata.update(self._get_audio_metadata(file_path))
            elif media_type == 'video':
                metadata.update(self._get_video_metadata(file_path))
                
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting media metadata: {e}")
            return None
            
    def _get_media_type(self, file_path: Path) -> str:
        """
        Determine the type of media file.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            Media type ('audio' or 'video')
        """
        try:
            mime = magic.Magic(mime=True)
            mime_type = mime.from_file(str(file_path))
            
            if mime_type.startswith('audio/'):
                return 'audio'
            elif mime_type.startswith('video/'):
                return 'video'
            else:
                return 'unknown'
                
        except Exception as e:
            logger.error(f"Error determining media type: {e}")
            return 'unknown'
            
    def _get_audio_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Get metadata from an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary with audio metadata
        """
        try:
            import mutagen
            audio = mutagen.File(file_path)
            
            if audio is None:
                return {}
                
            metadata = {}
            
            # Get duration
            if hasattr(audio.info, 'length'):
                metadata['duration'] = f"{audio.info.length:.2f} seconds"
                
            # Get bitrate
            if hasattr(audio.info, 'bitrate'):
                metadata['bitrate'] = f"{audio.info.bitrate / 1000:.1f} kbps"
                
            # Get sample rate
            if hasattr(audio.info, 'sample_rate'):
                metadata['sample_rate'] = f"{audio.info.sample_rate} Hz"
                
            # Get channels
            if hasattr(audio.info, 'channels'):
                metadata['channels'] = audio.info.channels
                
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting audio metadata: {e}")
            return {}
            
    def _get_video_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Get metadata from a video file.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            Dictionary with video metadata
        """
        try:
            import cv2
            video = cv2.VideoCapture(str(file_path))
            
            if not video.isOpened():
                return {}
                
            metadata = {}
            
            # Get frame count and FPS
            frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = video.get(cv2.CAP_PROP_FPS)
            
            if frame_count > 0 and fps > 0:
                duration = frame_count / fps
                metadata['duration'] = f"{duration:.2f} seconds"
                metadata['frame_count'] = frame_count
                metadata['fps'] = f"{fps:.2f}"
                
            # Get resolution
            width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            metadata['resolution'] = f"{width}x{height}"
            
            video.release()
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting video metadata: {e}")
            return {}
            
    def _generate_media_markdown(self, file_path: Path, metadata: Dict[str, Any]):
        """
        Generate markdown description for the media file.
        
        Args:
            file_path: Path to the media file
            metadata: Dictionary with media metadata
        """
        try:
            ensure_metadata_dir(file_path.parent)
            md_path = get_description_path(file_path)
            
            content = [
                f"# {file_path.stem}",
                "",
                "## Media Information",
                f"- **Original Filename:** {file_path.name}",
                f"- **File Size:** {metadata.get('file_size', 'Unknown')}",
                f"- **Modified Date:** {metadata.get('modified_date', 'Unknown')}",
                f"- **Media Type:** {metadata.get('media_type', 'Unknown')}"
            ]
            
            # Add type-specific metadata
            if metadata.get('media_type') == 'audio':
                content.extend([
                    "",
                    "## Audio Properties",
                    f"- **Duration:** {metadata.get('duration', 'Unknown')}",
                    f"- **Bitrate:** {metadata.get('bitrate', 'Unknown')}",
                    f"- **Sample Rate:** {metadata.get('sample_rate', 'Unknown')}",
                    f"- **Channels:** {metadata.get('channels', 'Unknown')}"
                ])
            elif metadata.get('media_type') == 'video':
                content.extend([
                    "",
                    "## Video Properties",
                    f"- **Duration:** {metadata.get('duration', 'Unknown')}",
                    f"- **Frame Count:** {metadata.get('frame_count', 'Unknown')}",
                    f"- **FPS:** {metadata.get('fps', 'Unknown')}",
                    f"- **Resolution:** {metadata.get('resolution', 'Unknown')}"
                ])
                
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
            logger.info(f"Generated markdown description: {md_path}")
        except Exception as e:
            logger.error(f"Error generating markdown for {file_path}: {e}")
            
    def generate_new_filename(
        self,
        file_path: Path,
        description: Union[str, Dict],
        file_type: str = None
    ) -> str:
        """
        Generate a descriptive filename based on file description.
        
        Args:
            file_path: Path to the file
            description: Description of the file
            file_type: Optional file type
            
        Returns:
            New filename
        """
        extension = file_path.suffix
        
        # If description is a dict, try to extract suggested_filename
        if isinstance(description, dict):
            if 'suggested_filename' in description:
                suggested_name = description['suggested_filename']
            elif 'filename' in description:
                suggested_name = description['filename']
            else:
                suggested_name = description.get('description', file_path.stem)
        else:
            # Try to extract JSON data from the description string
            import json
            import re
            
            json_match = re.search(r'\{.*"suggested_filename":\s*"([^"]+)".*\}', description)
            if json_match:
                try:
                    json_str = re.search(r'\{.*\}', description, re.DOTALL).group(0)
                    json_data = json.loads(json_str)
                    suggested_name = json_data.get('suggested_filename', file_path.stem)
                except (json.JSONDecodeError, AttributeError):
                    suggested_name = clean_filename(description[:100])
            else:
                suggested_name = clean_filename(description[:100])
        
        # Clean up suggested name
        suggested_name = clean_filename(suggested_name)
        
        # Add prefix based on file type if not already present
        file_type_prefix = ""
        if file_type:
            if file_type == "document":
                file_type_prefix = "doc_"
            elif file_type == "image":
                file_type_prefix = "img_"
            elif file_type == "audio":
                file_type_prefix = "audio_"
            elif file_type == "video":
                file_type_prefix = "video_"
            elif file_type == "archive":
                file_type_prefix = "archive_"
        
        # Only add prefix if it's not already at the start of the name
        if file_type_prefix and not suggested_name.startswith(file_type_prefix):
            final_name = f"{file_type_prefix}{suggested_name}"
        else:
            final_name = suggested_name
        
        # Ensure file has extension
        if not "." in final_name:
            final_name = f"{final_name}{extension}"
            
        # Limit to a reasonable length
        if len(final_name) > 255:
            name_part, ext_part = os.path.splitext(final_name)
            final_name = f"{name_part[:250]}{ext_part}"
            
        return final_name
        
    def rename_file(self, original_path: Path, new_name: str, rename_log: Optional[Dict] = None) -> Optional[Path]:
        """
        Rename a file.
        
        Args:
            original_path: Path to the original file
            new_name: New filename
            rename_log: Optional rename log
            
        Returns:
            Path to the renamed file or None if rename failed
        """
        try:
            if not os.path.splitext(new_name)[1]:
                new_name = f"{new_name}{original_path.suffix}"
            new_path = original_path.parent / new_name
            counter = 1
            base_name, ext = os.path.splitext(new_name)
            
            while new_path.exists() and new_path != original_path:
                new_name = f"{base_name}_{counter}{ext}"
                new_path = original_path.parent / new_name
                counter += 1
                
            if new_path == original_path:
                logger.info(f"New filename matches original, skipping rename for {original_path}")
                if rename_log is not None:
                    rename_log["stats"]["skipped_files"] += 1
                    root = original_path.parent
                    save_rename_log(rename_log, root)
                return original_path
                
            try:
                os.replace(str(original_path), str(new_path))
                logger.info(f"Renamed: {original_path} -> {new_path}")
                if rename_log is not None:
                    rename_log["stats"]["successful_renames"] += 1
            except OSError as e:
                logger.warning(f"Atomic rename failed, falling back to copy + delete for {original_path}")
                try:
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(str(original_path), str(new_path))
                    if new_path.exists() and new_path.stat().st_size == original_path.stat().st_size:
                        os.remove(str(original_path))
                        if rename_log is not None:
                            rename_log["stats"]["successful_renames"] += 1
                    else:
                        raise OSError("File copy failed")
                except Exception as e:
                    logger.error(f"Failed to rename file: {e}")
                    if rename_log is not None:
                        rename_log["stats"]["failed_renames"] += 1
                        add_error_to_log(rename_log, str(original_path), str(e))
                    return None
                    
            return new_path
            
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            if rename_log is not None:
                rename_log["stats"]["failed_renames"] += 1
                add_error_to_log(rename_log, str(original_path), str(e))
            return None
            
    def get_processed_files(self) -> Dict[str, Any]:
        """
        Get information about processed files.
        
        Returns:
            Dictionary containing information about processed files
        """
        return self.processed_files
        
    def get_errors(self) -> List[str]:
        """
        Get list of errors encountered during processing.
        
        Returns:
            List of error messages
        """
        return self.errors 