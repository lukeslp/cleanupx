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

from cleanupx.config import DOCUMENT_EXTENSIONS, DOCUMENT_FUNCTION_SCHEMA, FILE_DOCUMENT_PROMPT, XAI_MODEL_TEXT
from cleanupx.utils.common import read_text_file, strip_media_suffixes, clean_filename
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
        # Check for specific "No /Root object" error that indicates a corrupted PDF
        if "No /Root object" in str(e):
            logger.error(f"pdfminer.six extraction failed for {file_path}: {e} - File appears to be corrupted or not a valid PDF")
            # For these specific corrupted files, we should immediately try OCR
            try:
                if 'pdf2image' in sys.modules and 'pytesseract' in sys.modules:
                    logger.info(f"Attempting OCR as fallback for corrupted PDF: {file_path}")
                    from pdf2image import convert_from_path
                    import pytesseract
                    
                    try:
                        images = convert_from_path(str(file_path))
                        text = ""
                        
                        for i, image in enumerate(images[:3]):  # Process up to 3 pages
                            logger.info(f"OCR processing page {i+1} of corrupted PDF")
                            text += pytesseract.image_to_string(image)
                            text += "\n\n"
                            
                        if text.strip():
                            logger.info(f"Successfully extracted text from corrupted PDF using OCR")
                            return text
                    except Exception as ocr_e:
                        logger.error(f"OCR fallback for corrupted PDF failed: {ocr_e}")
            except ImportError:
                logger.warning("OCR fallback unavailable for corrupted PDF")
        
        logger.error(f"pdfminer.six extraction failed for {file_path}: {e}")
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
    
    # Check if we have a text extraction cache - used to avoid re-extracting the same PDF
    cache_file = file_path.parent / f".{file_path.stem}_text_cache.txt"
    if cache_file.exists() and cache_file.stat().st_mtime > file_path.stat().st_mtime:
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_text = f.read()
            if cached_text.strip():
                logger.info(f"Using cached text extraction for {file_path}")
                return cached_text
        except Exception as e:
            logger.warning(f"Failed to read text extraction cache: {e}")
    
    # Try different extraction methods in order
    try:
        # 1. First try PyPDF2 extraction
        import PyPDF2
        extraction_methods.append(("PyPDF2 standard", lambda: extract_text_with_pypdf2(file_path, max_pages)))
        
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
        else:
            # Cache the extracted text to avoid re-extraction
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                logger.debug(f"Cached text extraction for {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cache text extraction: {e}")
            
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

def process_document_file(file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Dict, 
                    citation_style_pdfs: bool = False) -> Tuple[Path, Optional[Path], Optional[Dict]]:
    """
    Process a document file (PDF, DOCX, etc.) - extract text, analyze content, and rename.
    
    Args:
        file_path: Path to the document file
        cache: Cache dictionary for storing/retrieving document descriptions
        rename_log: Log for tracking renames
        citation_style_pdfs: Whether to use citation-style naming for PDFs
        
    Returns:
        Tuple of (original_path, new_path, description)
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    cache_key = str(file_path)
    
    # Check if we already have processed this file in this session
    # This prevents redundant processing of the same file multiple times
    if cache.get(f"{cache_key}_processed") == True:
        logger.info(f"Skipping already processed file in this session: {file_path}")
        description = cache.get(cache_key)
        return file_path, None, description
    
    # Extract content for analysis
    if ext == ".docx":
        text_content = extract_text_from_docx(file_path)
    elif ext == ".pdf":
        # Limit PDF processing to first few pages for efficiency
        text_content = extract_text_from_pdf(file_path, max_pages=3)
    else:
        text_content = read_text_file(file_path)
    
    if not text_content.strip():
        logger.error(f"No text could be extracted from {file_path}")
        return file_path, None, None
    
    # Get page count for PDFs early (we'll need it for the filename)
    page_count = None
    if ext == ".pdf":
        page_count = get_pdf_page_count(file_path)
        
    # Analyze content and create description
    prompt = FILE_DOCUMENT_PROMPT.format(name=file_path.name, suffix=ext, text_content=text_content[:10000])
    result = call_xai_api(XAI_MODEL_TEXT, prompt, DOCUMENT_FUNCTION_SCHEMA)
    description = result
    
    if description:
        cache[cache_key] = description
        # Mark file as processed in this session to avoid redundant processing
        cache[f"{cache_key}_processed"] = True
        save_cache(cache)
        
        # Also process for citations if there's content
        try:
            from cleanupx.processors.citation import process_file_for_citations
            process_file_for_citations(file_path)
        except Exception as e:
            logger.error(f"Error processing citations for {file_path}: {e}")
    
    # Generate new name
    new_name = None
    new_path = None
    
    if description:
        # For PDFs, use citation style naming if requested
        if ext == ".pdf" and citation_style_pdfs and isinstance(description, dict) and description.get("document_type") == "research article":
            # Extract author, title, year for citation style
            author = description.get("author", "unknown")
            title = description.get("title", "")
            if not title:
                title = description.get("suggested_filename", "document")
            year = description.get("year", "")
            
            # Clean up author - extract last name of first author
            if "," in author:
                author = author.split(",")[0].strip()
            elif " " in author:
                author = author.split(" ")[-1].strip()
            
            # Format the citation style name with page count
            if page_count:
                if year:
                    new_name = f"{author}_{year}_{title}_{page_count}p{ext}"
                else:
                    new_name = f"{author}_{title}_{page_count}p{ext}"
            else:
                if year:
                    new_name = f"{author}_{year}_{title}{ext}"
                else:
                    new_name = f"{author}_{title}{ext}"
        else:
            # Normal content-based naming
            new_name = generate_new_filename(file_path, description)
            
            # Add page count for PDFs
            if ext == ".pdf" and page_count and new_name:
                # Add page count as a suffix with underscore format
                new_name = new_name.replace(ext, f"_{page_count}p{ext}")
    
    # Rename the file if we have a new name
    if new_name:
        # First clean the name to ensure it's valid
        new_name = clean_filename(new_name)
        
        new_path = rename_file(file_path, new_name, rename_log)
        if new_path and new_path != file_path and cache_key in cache:
            cache[str(new_path)] = cache[cache_key]
            del cache[cache_key]
            save_cache(cache)
    
    return file_path, new_path, description
