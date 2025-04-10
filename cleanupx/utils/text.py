import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from cleanupx.utils.cache import save_to_cache, get_from_cache, is_cached
from cleanupx.utils.common import is_text_file, is_supported_document, get_file_extension
from cleanupx.utils.config import MAX_TEXT_LENGTH
from cleanupx.utils.document import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_image
)

logger = logging.getLogger(__name__)

def get_file_text(file_path: Union[str, Path], force_reextract: bool = False, max_length: int = MAX_TEXT_LENGTH) -> str:
    """
    Get text content from a file. For binary files like PDFs, DOCXs, and images,
    it will extract text using appropriate methods.
    
    Args:
        file_path: Path to the file
        force_reextract: If True, ignore any cached results
        max_length: Maximum text length to return
        
    Returns:
        Text content of the file
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.error(f"File does not exist: {file_path}")
        return ""
    
    # Generate cache key based on file path and modification time
    file_stat = file_path.stat()
    cache_key = f"file_text_{file_path}_{file_stat.st_mtime}"
    
    # Check if text is in memory cache
    if not force_reextract and is_cached(cache_key):
        text = get_from_cache(cache_key)
        if text:
            logger.info(f"Using cached text for {file_path.name}")
            return text[:max_length] if max_length > 0 else text
    
    # Extract text based on file type
    logger.info(f"Extracting text from {file_path.name}")
    
    ext = get_file_extension(file_path).lower()
    text = ""
    
    try:
        if is_text_file(file_path):
            # For text files, read directly
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
        
        elif ext == '.pdf':
            # For PDFs, use PDF extraction
            text = extract_text_from_pdf(file_path, force_reextract)
        
        elif ext == '.docx':
            # For DOCX files, use DOCX extraction
            text = extract_text_from_docx(file_path, force_reextract)
        
        elif is_supported_document(file_path):
            # For images and other supported documents, try OCR
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif']:
                text = extract_text_from_image(file_path, force_reextract=force_reextract)
            else:
                logger.warning(f"Unsupported document type: {ext}")
        
        # Cache the extracted text in memory
        if text:
            save_to_cache(cache_key, text)
            logger.debug(f"Saved text to cache for {file_path.name}")
        
        return text[:max_length] if max_length > 0 else text
    
    except Exception as e:
        logger.error(f"Error extracting text from {file_path.name}: {e}")
        return ""

def extract_keywords(text: str, min_length: int = 3, max_keywords: int = 20) -> List[str]:
    """
    Extract potential keywords from text.
    
    Args:
        text: Input text
        min_length: Minimum keyword length
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of keywords
    """
    if not text:
        return []
    
    # Remove common punctuation and convert to lowercase
    cleaned_text = re.sub(r'[^\w\s]', ' ', text.lower())
    
    # Split into words
    words = cleaned_text.split()
    
    # Filter words by length and remove duplicates
    words = [w for w in words if len(w) >= min_length]
    
    # Count word frequencies
    word_count = {}
    for word in words:
        if word in word_count:
            word_count[word] += 1
        else:
            word_count[word] = 1
    
    # Sort by frequency and take top keywords
    keywords = sorted(word_count.keys(), key=lambda k: word_count[k], reverse=True)
    return keywords[:max_keywords]

def get_language(text: str) -> str:
    """
    Detect the language of a text.
    
    Args:
        text: Input text
        
    Returns:
        ISO language code (e.g., 'en', 'fr', 'de')
    """
    try:
        from langdetect import detect
        
        if not text or len(text.strip()) < 10:
            return "unknown"
        
        return detect(text[:1000])  # Use first 1000 chars for efficiency
    except ImportError:
        logger.warning("langdetect library not installed. Install with 'pip install langdetect'")
        return "unknown"
    except Exception as e:
        logger.error(f"Error detecting language: {e}")
        return "unknown"

def contains_sensitive_information(text: str) -> bool:
    """
    Check if text contains potentially sensitive information.
    
    Args:
        text: Input text
        
    Returns:
        True if sensitive information is detected
    """
    if not text:
        return False
    
    # Check for potential credit card numbers
    cc_pattern = r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
    if re.search(cc_pattern, text):
        return True
    
    # Check for potential SSNs
    ssn_pattern = r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'
    if re.search(ssn_pattern, text):
        return True
    
    # Check for potential passwords or keys
    password_patterns = [
        r'\bpassword\s*[:=]\s*\S+',
        r'\bpasswd\s*[:=]\s*\S+',
        r'\bsecret\s*[:=]\s*\S+',
        r'\bapi[-_]?key\s*[:=]\s*\S+',
    ]
    
    for pattern in password_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False

def calculate_information_density(text: str) -> float:
    """
    Calculate approximate information density of text.
    Higher values indicate more information-rich content.
    
    Args:
        text: Input text
        
    Returns:
        Information density score (0.0-1.0)
    """
    if not text or len(text.strip()) < 10:
        return 0.0
    
    # Remove spaces and punctuation
    cleaned_text = re.sub(r'\s+', '', text)
    cleaned_text = re.sub(r'[^\w]', '', cleaned_text)
    
    if not cleaned_text:
        return 0.0
    
    # Calculate unique character ratio
    unique_chars = len(set(cleaned_text))
    total_chars = len(cleaned_text)
    
    # Calculate word variety
    words = text.lower().split()
    unique_words = len(set(words))
    total_words = len(words)
    
    # Combine metrics
    char_ratio = unique_chars / total_chars if total_chars > 0 else 0
    word_ratio = unique_words / total_words if total_words > 0 else 0
    
    # Weight and combine
    density = (0.4 * char_ratio) + (0.6 * word_ratio)
    
    return min(1.0, density) 