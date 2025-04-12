#!/usr/bin/env python3
"""
Document file processor for CleanupX (PDF, DOCX, etc.).
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any
import io
import subprocess
import sys
import os
import hashlib
from datetime import datetime

from cleanupx.config import DOCUMENT_EXTENSIONS, DOCUMENT_FUNCTION_SCHEMA, FILE_DOCUMENT_PROMPT, XAI_MODEL_TEXT
from cleanupx.utils.common import read_text_file, strip_media_suffixes, clean_filename
from cleanupx.utils.cache import save_cache, _MEMORY_CACHE, get_cache_path, ensure_metadata_dir, get_description_path
from cleanupx.api import call_xai_api
from cleanupx.processors.base import BaseProcessor

# Configure logging
logger = logging.getLogger(__name__)

class DocumentProcessor(BaseProcessor):
    """Processor for document files (PDF, DOCX, etc.)."""
    
    def __init__(self):
        """Initialize the document processor."""
        super().__init__()
        self.supported_extensions = DOCUMENT_EXTENSIONS
        self.max_size_mb = 25.0
        
    def process(self, file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Dict) -> Dict:
        """
        Process a document file.
        
        Args:
            file_path: Path to the document file
            cache: Cache dictionary for storing processing results
            rename_log: Dictionary for tracking file renames
            
        Returns:
            Dictionary with processing results
        """
        file_path = Path(file_path)
        result = {
            "success": False,
            "error": None,
            "new_path": None
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
                
            # Get file description from cache or generate new one
            description = cache.get(str(file_path))
            if not description:
                logger.warning(f"No description found in cache for {file_path}")
                return result
                
            # Generate new filename
            new_name = self.generate_new_filename(file_path, description, "document")
            
            # Rename the file
            success, new_path = self.rename_file(file_path, new_name)
            
            if success:
                result.update({
                    "success": True,
                    "new_path": str(new_path)
                })
                # Update rename log
                rename_log[str(file_path)] = str(new_path)
            else:
                result["error"] = "Failed to rename file"
                
            # Generate markdown
            self._generate_markdown(file_path, description)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            result["error"] = str(e)
            
        return result
            
    def _analyze_document(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
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
            file_stats = Path(file_path).stat()
            file_size_mb = file_stats.st_size / (1024 * 1024)
            modified_time = datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            # Get page count for PDFs
            page_count = None
            if file_path.suffix.lower() == '.pdf':
                page_count = get_pdf_page_count(file_path)
                
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
            
    def _extract_document_text(self, file_path: Union[str, Path], max_pages: int = 5) -> str:
        """
        Extract text from a document file.
        
        Args:
            file_path: Path to the document file
            max_pages: Maximum number of pages to extract (for PDFs)
            
        Returns:
            Extracted text or empty string if extraction failed
        """
        file_path = Path(file_path)
        file_extension = file_path.suffix.lower()
        
        if file_extension == '.pdf':
            return extract_text_from_pdf(file_path, max_pages)
        elif file_extension == '.docx':
            return extract_text_from_docx(file_path)
        elif file_extension in ['.txt', '.md', '.py', '.js', '.html', '.css', '.csv', '.json', '.xml']:
            return extract_text_from_txt(file_path)
        else:
            logger.warning(f"No specific extraction method for {file_extension}, trying as text file")
            return extract_text_from_txt(file_path)
            
    def _generate_markdown(self, file_path: Path, description: Dict[str, Any]):
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

# Keep existing utility functions

def extract_text_from_docx(file_path: Union[str, Path]) -> str:
    """Extract text content from a DOCX file."""
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ""

def get_pdf_page_count(file_path: Union[str, Path]) -> Optional[int]:
    """Get the number of pages in a PDF file."""
    try:
        import PyPDF2
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return len(reader.pages)
    except Exception as e:
        logger.error(f"Error getting page count from {file_path}: {e}")
        
        # Fallback to using pdfinfo if available
        try:
            result = subprocess.run(['pdfinfo', str(file_path)], 
                                   capture_output=True, text=True, check=True)
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        except (subprocess.SubprocessError, ValueError, FileNotFoundError) as e:
            logger.error(f"Fallback page count extraction failed: {e}")
        
        return None

def extract_text_from_pdf_with_pdfminer(file_path: Union[str, Path], max_pages: int = 3) -> str:
    """Extract text using pdfminer.six."""
    try:
        from pdfminer.high_level import extract_text as pm_extract_text
        text = pm_extract_text(file_path)
        
        if max_pages is not None:
            # Since pdfminer doesn't support page limiting directly,
            # we'll extract the text and then try to limit it to approximately
            # the number of pages requested by looking for page breaks
            page_breaks = text.count('\f')  # Form feed character typically separates pages
            
            if page_breaks > max_pages:
                # Roughly split by form feeds to get number of pages
                pages = text.split('\f')
                limited_text = '\f'.join(pages[:max_pages])
                logger.info(f"Only processed {max_pages} of approximately {page_breaks+1} pages in {file_path} with pdfminer")
                return limited_text
        
        return text
    except ImportError:
        logger.warning("pdfminer.six not installed, skipping this extraction method")
        return ""
    except Exception as e:
        logger.warning(f"pdfminer.six extraction failed for {file_path}: {e}")
        return ""

def extract_text_from_pdf_with_ocr(file_path: Union[str, Path], max_pages: int = 3) -> str:
    """Extract text content from a PDF file using OCR via pdf2image and pytesseract."""
    try:
        from pdf2image import convert_from_path
        import pytesseract
        
        images = convert_from_path(str(file_path))
        text = ""
        
        # Limit processing to max_pages if specified
        pages_to_process = images[:max_pages] if max_pages is not None else images
        
        for i, image in enumerate(pages_to_process):
            logger.info(f"OCR processing page {i+1} of {file_path}")
            text += pytesseract.image_to_string(image)
            text += "\n\n"
            
        if max_pages is not None and len(images) > max_pages:
            logger.info(f"Only processed {max_pages} of {len(images)} pages in {file_path}")
            
        return text
    except ImportError:
        logger.warning("pdf2image or pytesseract not installed, can't use OCR extraction")
        return ""
    except Exception as e:
        logger.error(f"OCR extraction failed for {file_path}: {e}")
        return ""

def extract_text_from_pdf(file_path: Union[str, Path], max_pages: int = 3) -> str:
    """
    Extract text content from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        max_pages: Maximum number of pages to process. Default is 3.
                  Set to None to process all pages.
    
    Returns:
        Extracted text content
    """
    file_path = Path(file_path)
    text = ""
    extraction_methods = []
    
    # Use in-memory cache for extracted text during this session
    cache_key = f"text_extraction_{str(file_path)}_{file_path.stat().st_mtime}"
    if cache_key in _MEMORY_CACHE:
        logger.info(f"Using in-memory cached text extraction for {file_path}")
        return _MEMORY_CACHE[cache_key]
    
    # Get cache file path from centralized cache system
    cache_file = get_cache_path(file_path, "documents")
    
    # Try to load from disk cache if it exists
    if not os.environ.get('CLEANUPX_NO_CACHE') and cache_file.exists():
        try:
            # Check if cache file is newer than the actual file
            if cache_file.stat().st_mtime >= file_path.stat().st_mtime:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    text = f.read()
                if text.strip():
                    logger.info(f"Using disk cached text extraction for {file_path}")
                    # Also store in memory cache
                    _MEMORY_CACHE[cache_key] = text
                    return text
                else:
                    logger.debug(f"Disk cache for {file_path} exists but is empty, re-extracting")
            else:
                logger.debug(f"Disk cache for {file_path} is outdated, re-extracting")
        except Exception as e:
            logger.warning(f"Failed to read cache file for {file_path}: {e}")
    
    # Try different extraction methods in order
    try:
        # 1. First try PyPDF2 extraction
        import PyPDF2
        extraction_methods.append(("PyPDF2 standard", lambda: extract_text_with_pypdf2(file_path, max_pages)))
        
        # 2. Then try pdfminer.six if available
        try:
            import importlib.util
            if importlib.util.find_spec("pdfminer"):
                extraction_methods.append(("pdfminer.six", lambda: extract_text_from_pdf_with_pdfminer(file_path, max_pages)))
        except ImportError:
            pass
        
        # 3. Then try OCR if available
        try:
            import importlib.util
            if (importlib.util.find_spec("pdf2image") and 
                importlib.util.find_spec("pytesseract")):
                extraction_methods.append(("OCR", lambda: extract_text_from_pdf_with_ocr(file_path, max_pages)))
        except ImportError:
            pass
        
        # 4. Fallback to using pdftotext command line if available
        extraction_methods.append(("pdftotext", lambda: extract_text_with_pdftotext(file_path, max_pages)))
        
        # Try each method until we get some text
        for method_name, method_func in extraction_methods:
            logger.info(f"Trying {method_name} extraction for {file_path}")
            try:
                text = method_func()
                if text and text.strip():
                    logger.info(f"Successfully extracted text using {method_name}")
                    break
            except Exception as e:
                logger.warning(f"{method_name} extraction failed: {e}")
                continue
                
        # If all methods failed, try scanning as text file as a last resort
        if not text.strip():
            logger.info(f"All extraction methods failed. Trying to read as text file for {file_path}")
            try:
                # Try reading as plain text with multiple encodings
                for encoding in ['utf-8', 'latin-1', 'cp1252', 'ascii']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            text = f.read()
                        if text.strip():
                            logger.info(f"Successfully read {file_path} as text file with {encoding} encoding")
                            break
                    except UnicodeDecodeError:
                        continue
            except Exception as e:
                logger.warning(f"Text file reading failed: {e}")
                
        # Cache results to avoid repeated extraction
        if text.strip():
            # Cache to memory
            _MEMORY_CACHE[cache_key] = text
            
            # Cache to disk
            try:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                logger.info(f"Cached text extraction to {cache_file}")
            except Exception as e:
                logger.warning(f"Failed to save text extraction cache: {e}")
        else:
            logger.warning(f"No text extracted from {file_path}")
            
        return text
        
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ""

def extract_text_with_pypdf2(file_path: Union[str, Path], max_pages: int = 3) -> str:
    """Extract text content from a PDF file using PyPDF2."""
    try:
        import PyPDF2
        text = ""
        
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            pages_to_extract = min(len(reader.pages), max_pages) if max_pages is not None else len(reader.pages)
            
            if pages_to_extract < len(reader.pages) and max_pages is not None:
                logger.info(f"Only extracting {pages_to_extract} of {len(reader.pages)} pages from {file_path}")
                
            for i in range(pages_to_extract):
                try:
                    page = reader.pages[i]
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
                except Exception as e:
                    logger.warning(f"Error extracting text from page {i} in {file_path}: {e}")
                    continue
                    
        return text
    except Exception as e:
        logger.warning(f"PyPDF2 extraction failed for {file_path}: {e}")
        return ""

def extract_text_with_pdftotext(file_path: Union[str, Path], max_pages: int = 3) -> str:
    """Extract text content from a PDF file using pdftotext command line tool."""
    try:
        page_option = []
        if max_pages is not None:
            page_option = ["-l", str(max_pages)]  # -l specifies the last page to extract
            
        result = subprocess.run(
            ["pdftotext"] + page_option + ["-layout", str(file_path), "-"],
            capture_output=True, text=True, check=True
        )
        if result.stdout.strip():
            return result.stdout
        else:
            logger.warning(f"pdftotext produced empty output for {file_path}")
            return ""
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning(f"pdftotext extraction failed for {file_path}: {e}")
        return ""

def extract_text_from_txt(file_path: Union[str, Path]) -> str:
    """Extract text content from a text file."""
    file_path = Path(file_path)
    text = ""
    
    # List of encodings to try
    encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()
            logger.info(f"Successfully read {file_path} with {encoding} encoding")
            break
        except UnicodeDecodeError:
            logger.debug(f"Encoding {encoding} failed for {file_path}")
            continue
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return ""
            
    # If all encodings failed, try binary read as a last resort
    if not text:
        try:
            with open(file_path, 'rb') as f:
                binary_data = f.read()
            try:
                # Try to decode with errors='replace'
                text = binary_data.decode('utf-8', errors='replace')
                logger.info(f"Read {file_path} with binary fallback")
            except Exception as e:
                logger.error(f"Binary fallback failed for {file_path}: {e}")
                return ""
        except Exception as e:
            logger.error(f"Binary read failed for {file_path}: {e}")
            return ""
            
    return text

def clear_document_cache(file_path: Optional[Union[str, Path]] = None) -> None:
    """
    Clear document text extraction cache.
    
    Args:
        file_path: If provided, only clear cache for this file.
                  If None, clear all document cache.
    """
    if file_path:
        # Clear cache for a specific file
        file_path = Path(file_path)
        cache_file = get_cache_path(file_path, "documents")
        if cache_file.exists():
            try:
                cache_file.unlink()
                logger.info(f"Cleared document cache for {file_path}")
            except Exception as e:
                logger.error(f"Failed to clear document cache for {file_path}: {e}")
                
        # Clear memory cache
        cache_key = f"text_extraction_{str(file_path)}_{file_path.stat().st_mtime}"
        if cache_key in _MEMORY_CACHE:
            del _MEMORY_CACHE[cache_key]
    else:
        # Clear all document cache
        cache_dir = Path(os.path.expanduser("~/.cache/cleanupx/documents"))
        if cache_dir.exists():
            try:
                import shutil
                shutil.rmtree(cache_dir)
                logger.info(f"Cleared all document cache at {cache_dir}")
            except Exception as e:
                logger.error(f"Failed to clear document cache: {e}")
                
        # Clear all document-related memory cache
        for key in list(_MEMORY_CACHE.keys()):
            if key.startswith("text_extraction_"):
                del _MEMORY_CACHE[key]
