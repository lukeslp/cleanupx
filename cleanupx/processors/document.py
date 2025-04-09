#!/usr/bin/env python3
"""
Document file processor for CleanupX (PDF, DOCX, etc.).
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any

from cleanupx.config import DOCUMENT_EXTENSIONS, DOCUMENT_FUNCTION_SCHEMA, FILE_DOCUMENT_PROMPT, XAI_MODEL_TEXT
from cleanupx.utils.common import read_text_file
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

def extract_text_from_pdf(file_path: Union[str, Path]) -> str:
    """Extract text content from a PDF file."""
    try:
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
            logger.warning(f"Standard PDF extraction failed for {file_path}: {e}")
            
        # If standard extraction failed, try more robust approach
        if not text:
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
                logger.warning(f"Alternative PDF extraction failed for {file_path}: {alt_e}")
                
        # If both methods failed, try using the filename as fallback text
        if not text:
            text = str(Path(file_path).stem).replace("_", " ").replace("-", " ")
            logger.info(f"Using filename as fallback text for {file_path}")
            
        return text
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
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
    new_name = generate_new_filename(file_path, description)
    new_path = None
    if new_name:
        new_path = rename_file(file_path, new_name, rename_log)
        if new_path and new_path != file_path and cache_key in cache:
            cache[str(new_path)] = cache[cache_key]
            del cache[cache_key]
            save_cache(cache)
    return file_path, new_path, description
