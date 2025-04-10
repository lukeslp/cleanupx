import logging
import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Union, Dict, Any, Tuple

import docx2txt
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

from cleanupx.utils.common import is_image_file, get_file_extension
from cleanupx.utils.config import DEFAULT_OCR_LANGUAGE
from cleanupx.utils.cache import _MEMORY_CACHE, save_to_cache, get_from_cache

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path: Union[str, Path], force_reextract: bool = False) -> str:
    """
    Extract text from a PDF file using various methods.
    First tries pdftotext, then OCR if needed.
    
    Args:
        file_path: Path to the PDF file
        force_reextract: If True, ignore any cached results and re-extract
        
    Returns:
        Extracted text string
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.error(f"PDF file does not exist: {file_path}")
        return ""
    
    # Generate cache key based on file path and modification time for versioning
    file_stat = file_path.stat()
    cache_key = f"pdf_text_{file_path}_{file_stat.st_mtime}"
    
    # Check if text is in memory cache
    if not force_reextract:
        cached_text = get_from_cache(cache_key)
        if cached_text:
            logger.info(f"Using in-memory cached text extraction for {file_path.name}")
            return cached_text
    
    logger.info(f"Extracting text from PDF: {file_path.name}")
    
    # Try pdftotext first (much faster)
    text = _extract_with_pdftotext(file_path)
    
    # If pdftotext fails or extracts very little text, try OCR
    if not text or len(text.strip()) < 100:
        logger.info(f"pdftotext extracted little or no text from {file_path.name}, trying OCR")
        text = _extract_with_ocr(file_path)
    
    # Cache the extracted text in memory
    if text and len(text) > 0:
        save_to_cache(cache_key, text)
        logger.debug(f"Saved text in memory cache for {file_path.name}")
    
    return text

def extract_text_from_docx(file_path: Union[str, Path], force_reextract: bool = False) -> str:
    """
    Extract text from a DOCX file using python-docx.
    
    Args:
        file_path: Path to the DOCX file
        force_reextract: If True, ignore any cached results and re-extract
        
    Returns:
        Extracted text string
    """
    try:
        import docx
    except ImportError:
        logger.error("python-docx library not installed. Install with 'pip install python-docx'")
        return ""
    
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.error(f"DOCX file does not exist: {file_path}")
        return ""
    
    # Generate cache key based on file path and modification time for versioning
    file_stat = file_path.stat()
    cache_key = f"docx_text_{file_path}_{file_stat.st_mtime}"
    
    # Check if text is in memory cache
    if not force_reextract:
        cached_text = get_from_cache(cache_key)
        if cached_text:
            logger.info(f"Using in-memory cached text extraction for {file_path.name}")
            return cached_text
    
    logger.info(f"Extracting text from DOCX: {file_path.name}")
    
    try:
        doc = docx.Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        
        # Cache the extracted text in memory
        if text and len(text) > 0:
            save_to_cache(cache_key, text)
            logger.debug(f"Saved text in memory cache for {file_path.name}")
        
        return text
    except Exception as e:
        logger.error(f"Error extracting text from DOCX {file_path.name}: {e}")
        return ""

def extract_text_from_image(image_path: Union[str, Path], lang: str = DEFAULT_OCR_LANGUAGE, force_reextract: bool = False) -> str:
    """
    Extract text from an image file using OCR.
    
    Args:
        image_path: Path to the image file
        lang: OCR language code
        force_reextract: If True, ignore any cached results and re-extract
        
    Returns:
        Extracted text string
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        logger.error(f"Image file does not exist: {image_path}")
        return ""
    
    # Generate cache key based on file path and modification time for versioning
    file_stat = image_path.stat()
    cache_key = f"image_text_{image_path}_{file_stat.st_mtime}"
    
    # Check if text is in memory cache
    if not force_reextract:
        cached_text = get_from_cache(cache_key)
        if cached_text:
            logger.info(f"Using in-memory cached text extraction for {image_path.name}")
            return cached_text
    
    logger.info(f"Extracting text from image: {image_path.name}")
    
    try:
        # Open the image
        img = Image.open(image_path)
        
        # Perform OCR
        text = pytesseract.image_to_string(img, lang=lang)
        
        # Cache the extracted text in memory
        if text and len(text) > 0:
            save_to_cache(cache_key, text)
            logger.debug(f"Saved text in memory cache for {image_path.name}")
        
        return text
    except Exception as e:
        logger.error(f"Error extracting text from image {image_path.name}: {e}")
        return ""

# Private helper functions
def _extract_with_pdftotext(file_path: Path) -> str:
    """
    Extract text from PDF using pdftotext command-line tool.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text string, empty string if failed
    """
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(file_path), "-"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            logger.warning(f"pdftotext failed with return code {result.returncode}: {result.stderr}")
            return ""
    except FileNotFoundError:
        logger.warning("pdftotext not found. Install poppler-utils package.")
        return ""
    except Exception as e:
        logger.error(f"Error using pdftotext: {e}")
        return ""

def _extract_with_ocr(file_path: Path, lang: str = DEFAULT_OCR_LANGUAGE) -> str:
    """
    Extract text from PDF using OCR.
    
    Args:
        file_path: Path to the PDF file
        lang: OCR language code
        
    Returns:
        Extracted text string
    """
    try:
        # Convert PDF to images
        logger.info(f"Converting PDF to images: {file_path.name}")
        images = convert_from_path(file_path)
        
        # Process each page
        extracted_text = []
        for i, img in enumerate(images):
            logger.info(f"OCR processing page {i+1}/{len(images)} of {file_path.name}")
            # Perform OCR on the image
            page_text = pytesseract.image_to_string(img, lang=lang)
            extracted_text.append(page_text)
        
        # Combine text from all pages
        full_text = "\n\n".join(extracted_text)
        return full_text
    except Exception as e:
        logger.error(f"Error performing OCR on PDF {file_path.name}: {e}")
        return "" 