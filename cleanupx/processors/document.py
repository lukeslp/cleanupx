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
from cleanupx.utils.cache import save_cache, _MEMORY_CACHE, get_cache_path
from cleanupx.api import call_xai_api
from cleanupx.processors.base import generate_new_filename, rename_file

# Configure logging
logger = logging.getLogger(__name__)

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
                        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                            text = f.read()
                        if text.strip():
                            logger.info(f"Successfully read file as text using {encoding} encoding")
                            break
                    except Exception as enc_error:
                        logger.debug(f"Failed to read with {encoding} encoding: {enc_error}")
            except Exception as txt_error:
                logger.warning(f"Failed to read as text: {txt_error}")
                
        # If still empty, use the filename as fallback text
        if not text.strip():
            text = str(file_path.stem).replace("_", " ").replace("-", " ")
            logger.info(f"All extraction methods including text scan failed. Using filename as fallback text for {file_path}")
            # We don't cache fallback text since it's just the filename
        else:
            # Cache the extracted text to avoid re-extraction
            # Skip caching if NO_CACHE is set
            if os.environ.get('CLEANUPX_NO_CACHE'):
                logger.debug(f"Skipping text cache creation for {file_path} due to NO_CACHE setting")
            else:
                # Cache to disk
                try:
                    # Create parent directories if they don't exist
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        f.write(text)
                    logger.debug(f"Cached text extraction to disk for {file_path} at {cache_file}")
                except Exception as e:
                    logger.warning(f"Failed to cache text extraction to disk: {e}")
                
                # Cache to memory
                _MEMORY_CACHE[cache_key] = text
                logger.debug(f"Cached text extraction in memory for {file_path}")
            
        return text
    except Exception as e:
        logger.error(f"Error in PDF extraction process for {file_path}: {e}")
        text = str(file_path.stem).replace("_", " ").replace("-", " ")
        return text

def extract_text_with_pypdf2(file_path: Union[str, Path], max_pages: int = 3) -> str:
    """Extract text using PyPDF2 with fallback options."""
    import PyPDF2
    text = ""
    
    # First try the normal PyPDF2 extraction
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            # Determine how many pages to process
            total_pages = len(reader.pages)
            pages_to_process = min(total_pages, max_pages) if max_pages is not None else total_pages
            
            for i in range(pages_to_process):
                extracted = reader.pages[i].extract_text()
                if extracted:
                    text += extracted
                    
            if max_pages is not None and total_pages > max_pages:
                logger.info(f"Only processed {pages_to_process} of {total_pages} pages in {file_path} with PyPDF2")
    except Exception as e:
        logger.warning(f"Standard PyPDF2 extraction failed for {file_path}: {e}")
        
    # If standard extraction failed, try more robust approach
    if not text.strip():
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f, strict=False)
                
                # Determine how many pages to process
                total_pages = len(reader.pages)
                pages_to_process = min(total_pages, max_pages) if max_pages is not None else total_pages
                
                for i in range(pages_to_process):
                    try:
                        page = reader.pages[i]
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted
                    except Exception as page_e:
                        logger.warning(f"Error extracting text from page {i}: {page_e}")
                        continue
                        
                if max_pages is not None and total_pages > max_pages:
                    logger.info(f"Only processed {pages_to_process} of {total_pages} pages in {file_path} with alternative PyPDF2")
        except Exception as alt_e:
            logger.warning(f"Alternative PyPDF2 extraction failed for {file_path}: {alt_e}")
    
    return text

def extract_text_with_pdftotext(file_path: Union[str, Path], max_pages: int = 3) -> str:
    """Extract text using pdftotext command line tool."""
    try:
        cmd = ['pdftotext']
        
        # Add page range if max_pages is specified
        if max_pages is not None:
            cmd.extend(['-f', '1', '-l', str(max_pages)])
            
        cmd.extend([str(file_path), '-'])
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if max_pages is not None:
            logger.info(f"Processed up to {max_pages} pages in {file_path} with pdftotext")
            
        return result.stdout
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning(f"pdftotext extraction failed: {e}")
        return ""

def extract_text_from_txt(file_path: Union[str, Path]) -> str:
    """Extract text from a plain text file with encoding detection."""
    file_path = Path(file_path)
    
    # Use in-memory cache for extracted text during this session
    cache_key = f"text_extraction_{str(file_path)}_{file_path.stat().st_mtime}"
    if cache_key in _MEMORY_CACHE:
        logger.info(f"Using in-memory cached text extraction for {file_path}")
        return _MEMORY_CACHE[cache_key]
    
    # Check for disk cache
    # Create a standardized cache filename using hash of the path
    cache_dir = file_path.parent
    file_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:8]
    cache_file = cache_dir / f"text_cache_{file_hash}_{file_path.stem}.txt"
    
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
        except Exception as e:
            logger.warning(f"Failed to read cache file for {file_path}: {e}")
    
    # Try to read the text with different encodings
    text = ""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']
    
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, errors='replace') as f:
                text = f.read()
            if text.strip():
                logger.info(f"Successfully read text file with {enc} encoding")
                break
        except Exception as e:
            logger.debug(f"Failed to read with {enc} encoding: {e}")
    
    # Cache the result if we got text
    if text.strip() and not os.environ.get('CLEANUPX_NO_CACHE'):
        try:
            # Create parent directories if they don't exist
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(text)
            logger.debug(f"Cached text extraction to disk for {file_path}")
            
            # Also cache in memory
            _MEMORY_CACHE[cache_key] = text
        except Exception as e:
            logger.warning(f"Failed to cache text extraction: {e}")
    
    return text

def process_document_file(file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Tuple[Path, Optional[Path], Optional[Dict[str, Any]]]:
    """
    Process a document file - extract text, analyze content, and rename.
    
    Args:
        file_path: Path to the document file
        cache: Cache dictionary for storing/retrieving document descriptions
        rename_log: Optional log for tracking renames
        
    Returns:
        Tuple of (original_path, new_path, description)
    """
    try:
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        
        # Check if already processed
        cache_key = str(file_path)
        if cache_key in cache:
            logger.info(f"Using cached description for {file_path.name}")
            data = cache[cache_key]
        else:
            # Extract text based on file type
            if ext == '.docx':
                text_content = extract_text_from_docx(file_path)
            elif ext == '.pdf':
                text_content = extract_text_from_pdf(file_path)
            else:
                text_content = read_text_file(file_path)
            
            if not text_content.strip():
                logger.warning(f"No text content extracted from {file_path.name}")
                return file_path, None, None
            
            # Analyze content
            prompt = FILE_DOCUMENT_PROMPT.format(
                name=file_path.name,
                suffix=ext,
                text_content=text_content[:10000]  # Limit content length
            )
            
            data = call_xai_api(XAI_MODEL_TEXT, prompt, DOCUMENT_FUNCTION_SCHEMA)
            if not data:
                logger.warning(f"Failed to analyze document: {file_path.name}")
                return file_path, None, None
            
            # Cache the result
            cache[cache_key] = data
            save_cache(cache)
        
        # Generate new filename
        new_filename = generate_new_filename(file_path, data)
        if not new_filename:
            logger.warning(f"Failed to generate new filename for {file_path.name}")
            return file_path, None, data
        
        try:
            new_path = file_path.parent / new_filename
            if new_path != file_path:
                file_path.rename(new_path)
                logger.info(f"Renamed {file_path.name} to {new_filename}")
                if cache_key in cache:
                    cache[str(new_path)] = cache.pop(cache_key)
                    save_cache(cache)
            
            # Create markdown file with the document description
            md_base_name = os.path.splitext(new_filename)[0] if new_path != file_path else os.path.splitext(file_path.name)[0]
            md_filename = f"{md_base_name}.md"
            md_path = (new_path if new_path != file_path else file_path).parent / md_filename
            
            with open(md_path, 'w', encoding='utf-8') as md_file:
                title = data.get("title", "Document Description")
                md_file.write(f"# {title}\n\n")
                
                # Add document type and description
                doc_type = data.get("document_type", "unknown")
                md_file.write(f"**Type:** {doc_type}\n\n")
                
                description = data.get("description", "")
                if description:
                    md_file.write(f"## Description\n\n{description}\n\n")
                
                # Add file information
                md_file.write("## File Information\n\n")
                md_file.write(f"- **Original Name:** {file_path.name}\n")
                md_file.write(f"- **Current Name:** {new_filename if new_path != file_path else file_path.name}\n")
                md_file.write(f"- **File Size:** {file_path.stat().st_size / 1024:.1f} KB\n")
                md_file.write(f"- **Last Modified:** {datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            logger.info(f"Created markdown description file: {md_path}")
            
            return file_path, new_path, data
            
        except Exception as e:
            logger.warning(f"Failed to rename file {file_path.name}: {e}")
            return file_path, None, data
            
    except Exception as e:
        logger.warning(f"Error processing document {file_path.name}: {e}")
        return file_path, None, None

def clear_document_cache(file_path: Optional[Union[str, Path]] = None) -> None:
    """
    Clear document analysis cache for a specific file or all files.
    
    Args:
        file_path: Path to the document to clear cache for, or None for all documents
    """
    cache_dir = ensure_cache_dir()
    documents_cache_dir = cache_dir / "documents"
    
    if file_path is not None:
        # Clear cache for specific file
        cache_file = get_cache_path(file_path, "documents")
        if cache_file.exists():
            try:
                os.remove(cache_file)
                logger.info(f"Cleared document cache for {file_path}")
            except Exception as e:
                logger.error(f"Failed to clear document cache for {file_path}: {e}")
    else:
        # Clear all document caches
        if documents_cache_dir.exists():
            for cache_file in documents_cache_dir.glob("*.cache"):
                try:
                    os.remove(cache_file)
                except Exception as e:
                    logger.error(f"Failed to remove document cache file {cache_file}: {e}")
            logger.info("Cleared all document caches")
