#!/usr/bin/env python3
"""
Document file processor for CleanupX (PDF, DOCX, etc.).
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any
import io
import subprocess

from cleanupx.config import DOCUMENT_EXTENSIONS, DOCUMENT_FUNCTION_SCHEMA, FILE_DOCUMENT_PROMPT, XAI_MODEL_TEXT
from cleanupx.utils.common import read_text_file, strip_media_suffixes
from cleanupx.utils.cache import save_cache
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

def extract_text_from_pdf_with_pdfminer(file_path: Union[str, Path]) -> str:
    """Extract text content from a PDF file using pdfminer.six."""
    try:
        from pdfminer.high_level import extract_text
        return extract_text(str(file_path))
    except ImportError:
        logger.warning("pdfminer.six not installed, can't use alternative PDF extraction")
        return ""
    except Exception as e:
        logger.error(f"pdfminer.six extraction failed for {file_path}: {e}")
        return ""

def extract_text_from_pdf_with_ocr(file_path: Union[str, Path]) -> str:
    """Extract text content from a PDF file using OCR via pdf2image and pytesseract."""
    try:
        from pdf2image import convert_from_path
        import pytesseract
        
        images = convert_from_path(str(file_path))
        text = ""
        
        for i, image in enumerate(images):
            logger.info(f"OCR processing page {i+1} of {file_path}")
            text += pytesseract.image_to_string(image)
            text += "\n\n"
            
        return text
    except ImportError:
        logger.warning("pdf2image or pytesseract not installed, can't use OCR extraction")
        return ""
    except Exception as e:
        logger.error(f"OCR extraction failed for {file_path}: {e}")
        return ""

def extract_text_from_pdf(file_path: Union[str, Path]) -> str:
    """Extract text content from a PDF file."""
    file_path = Path(file_path)
    text = ""
    extraction_methods = []
    
    # Try different extraction methods in order
    try:
        # 1. First try PyPDF2 extraction
        import PyPDF2
        extraction_methods.append(("PyPDF2 standard", lambda: extract_text_with_pypdf2(file_path)))
        
        # 2. Then try pdfminer.six if available
        try:
            import importlib.util
            if importlib.util.find_spec("pdfminer"):
                extraction_methods.append(("pdfminer.six", lambda: extract_text_from_pdf_with_pdfminer(file_path)))
        except ImportError:
            pass
        
        # 3. Then try OCR if available
        try:
            import importlib.util
            if (importlib.util.find_spec("pdf2image") and 
                importlib.util.find_spec("pytesseract")):
                extraction_methods.append(("OCR", lambda: extract_text_from_pdf_with_ocr(file_path)))
        except ImportError:
            pass
        
        # 4. Fallback to using pdftotext command line if available
        extraction_methods.append(("pdftotext", lambda: extract_text_with_pdftotext(file_path)))
        
        # Try each method until we get some text
        for method_name, method_func in extraction_methods:
            logger.info(f"Trying {method_name} extraction for {file_path}")
            try:
                text = method_func()
                if text.strip():
                    logger.info(f"Successfully extracted text using {method_name}")
                    break
            except Exception as e:
                logger.warning(f"{method_name} extraction failed: {e}")
                continue
                
        # If all methods failed, use the filename as fallback text
        if not text.strip():
            text = str(file_path.stem).replace("_", " ").replace("-", " ")
            logger.info(f"All extraction methods failed. Using filename as fallback text for {file_path}")
            
        return text
    except Exception as e:
        logger.error(f"Error in PDF extraction process for {file_path}: {e}")
        text = str(file_path.stem).replace("_", " ").replace("-", " ")
        return text

def extract_text_with_pypdf2(file_path: Union[str, Path]) -> str:
    """Extract text using PyPDF2 with fallback options."""
    import PyPDF2
    text = ""
    
    # First try the normal PyPDF2 extraction
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted
    except Exception as e:
        logger.warning(f"Standard PyPDF2 extraction failed for {file_path}: {e}")
        
    # If standard extraction failed, try more robust approach
    if not text.strip():
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f, strict=False)
                for i in range(len(reader.pages)):
                    try:
                        page = reader.pages[i]
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted
                    except Exception as page_e:
                        logger.warning(f"Error extracting text from page {i}: {page_e}")
                        continue
        except Exception as alt_e:
            logger.warning(f"Alternative PyPDF2 extraction failed for {file_path}: {alt_e}")
    
    return text

def extract_text_with_pdftotext(file_path: Union[str, Path]) -> str:
    """Extract text using pdftotext command line tool."""
    try:
        result = subprocess.run(['pdftotext', str(file_path), '-'],
                              capture_output=True, text=True, check=True)
        return result.stdout
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning(f"pdftotext extraction failed: {e}")
        return ""

def process_document_file(file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Dict) -> Tuple[Path, Optional[Path], Optional[Dict]]:
    """
    Process a document file (PDF, DOCX, etc.) - extract text, analyze content, and rename.
    
    Args:
        file_path: Path to the document file
        cache: Cache dictionary for storing/retrieving document descriptions
        rename_log: Log for tracking renames
        
    Returns:
        Tuple of (original_path, new_path, description)
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    
    # For PDFs, we need to add page count to filename
    if ext == ".pdf":
        # First clean the stem to remove any existing metadata
        clean_stem = strip_media_suffixes(file_path.stem)
        
        # Get the page count
        page_count = get_pdf_page_count(file_path)
        if page_count is not None:
            # Create new name with page count
            new_name = f"{clean_stem}_PAGES{page_count}{ext}"
            new_path = rename_file(file_path, new_name, rename_log)
            
            # After renaming with page count, we can still extract text and process further
            file_path = new_path or file_path  # Use new path if renaming succeeded
    
    # Continue with normal processing
    if ext == ".docx":
        text_content = extract_text_from_docx(file_path)
    elif ext == ".pdf":
        text_content = extract_text_from_pdf(file_path)
    else:
        text_content = read_text_file(file_path)
    
    if not text_content.strip():
        logger.error(f"No text could be extracted from {file_path}")
        return file_path, None, None
        
    prompt = FILE_DOCUMENT_PROMPT.format(name=file_path.name, suffix=ext, text_content=text_content[:10000])
    result = call_xai_api(XAI_MODEL_TEXT, prompt, DOCUMENT_FUNCTION_SCHEMA)
    description = result
    cache_key = str(file_path)
    
    if description:
        cache[cache_key] = description
        save_cache(cache)
        
        # Also process for citations if there's content
        try:
            from cleanupx.processors.citation import process_file_for_citations
            process_file_for_citations(file_path)
        except Exception as e:
            logger.error(f"Error processing citations for {file_path}: {e}")
    
    # For PDFs, we've already renamed with page count, so only rename if not PDF
    if ext != ".pdf":
        new_name = generate_new_filename(file_path, description)
        new_path = None
        if new_name:
            new_path = rename_file(file_path, new_name, rename_log)
            if new_path and new_path != file_path and cache_key in cache:
                cache[str(new_path)] = cache[cache_key]
                del cache[cache_key]
                save_cache(cache)
        return file_path, new_path, description
    
    # For PDFs, return the already renamed file
    return file_path, file_path if ext == ".pdf" else None, description
