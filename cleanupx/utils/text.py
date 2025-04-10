import logging
import os
import re
import string
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
import hashlib
import time

try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

try:
    import docx2txt
    DOCX2TXT_AVAILABLE = True
except ImportError:
    DOCX2TXT_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    
    # Initialize NLTK resources
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
    
    NLTK_AVAILABLE = True
    STOPWORDS = set(stopwords.words('english'))
except ImportError:
    NLTK_AVAILABLE = False
    STOPWORDS = set()

from cleanupx.utils.file import (
    get_file_extension, is_binary_file, is_image_file, is_text_file,
    is_document_file, is_pdf_file, get_file_metadata
)

logger = logging.getLogger(__name__)

# In-memory cache for extracted text
_TEXT_CACHE: Dict[str, str] = {}

def get_file_text(file_path: Union[str, Path], force_extract: bool = False) -> str:
    """
    Extract text from a file with in-memory caching.
    
    Args:
        file_path: Path to the file
        force_extract: Force extraction even if cached
        
    Returns:
        Extracted text or empty string if extraction fails
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.warning(f"File does not exist: {file_path}")
        return ""
    
    # Create a cache key from file path and modification time
    # This ensures the cache is invalidated if the file changes
    try:
        mod_time = os.path.getmtime(file_path)
        cache_key = f"{str(file_path)}_{mod_time}"
    except OSError:
        cache_key = str(file_path)
        
    # Check if text is in cache
    if not force_extract and cache_key in _TEXT_CACHE:
        logger.debug(f"Using cached text for {file_path}")
        return _TEXT_CACHE[cache_key]
    
    text = ""
    
    try:
        # Extract text based on file type
        if is_binary_file(file_path):
            logger.debug(f"Skipping binary file: {file_path}")
        elif is_text_file(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
        elif is_pdf_file(file_path) and PYPDF2_AVAILABLE:
            text = _extract_pdf_text(file_path)
        elif is_document_file(file_path) and DOCX2TXT_AVAILABLE:
            text = docx2txt.process(file_path)
        elif is_image_file(file_path) and PYTESSERACT_AVAILABLE:
            text = _extract_image_text(file_path)
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        text = ""
    
    # Cache the extracted text
    _TEXT_CACHE[cache_key] = text
    logger.debug(f"Cached text for {file_path} (length: {len(text)})")
    
    return text

def _extract_pdf_text(file_path: Path) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text
    """
    text = ""
    try:
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
    except Exception as e:
        logger.error(f"Error extracting text from PDF {file_path}: {e}")
    return text

def _extract_image_text(file_path: Path) -> str:
    """
    Extract text from an image using OCR.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        Extracted text
    """
    text = ""
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
    except Exception as e:
        logger.error(f"Error extracting text from image {file_path}: {e}")
    return text

def clear_text_cache() -> None:
    """Clear the in-memory text cache and text cache files."""
    global _TEXT_CACHE
    _TEXT_CACHE = {}
    
    # Clear text cache files from centralized cache
    cache_dir = ensure_cache_dir()
    text_cache_dir = cache_dir / "text"
    if text_cache_dir.exists():
        for cache_file in text_cache_dir.glob("*.cache"):
            try:
                os.remove(cache_file)
            except Exception as e:
                logger.error(f"Failed to remove text cache file {cache_file}: {e}")
    
    logger.info("Text cache cleared")

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract important keywords from text.
    
    Args:
        text: Input text
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of keywords
    """
    if not text or not NLTK_AVAILABLE:
        return []
    
    try:
        # Tokenize and clean text
        words = word_tokenize(text.lower())
        
        # Remove punctuation and stopwords
        words = [word for word in words 
                if word not in STOPWORDS 
                and word not in string.punctuation
                and len(word) > 2
                and not word.isdigit()]
        
        # Count word frequency
        word_freq = {}
        for word in words:
            if word in word_freq:
                word_freq[word] += 1
            else:
                word_freq[word] = 1
        
        # Sort by frequency
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # Return top keywords
        return [word for word, _ in sorted_keywords[:max_keywords]]
    except Exception as e:
        logger.error(f"Error extracting keywords: {e}")
        return []

def get_language(text: str) -> Optional[str]:
    """
    Attempt to detect the language of a text.
    
    Args:
        text: Input text
        
    Returns:
        Detected language code or None if detection fails
    """
    try:
        from langdetect import detect
        if not text or len(text.strip()) < 10:
            return None
        return detect(text)
    except ImportError:
        logger.warning("langdetect not installed, language detection unavailable")
        return None
    except Exception as e:
        logger.error(f"Error detecting language: {e}")
        return None

def contains_sensitive_information(text: str) -> bool:
    """
    Check if the text contains potentially sensitive information.
    
    Args:
        text: Input text
        
    Returns:
        True if sensitive information is detected, False otherwise
    """
    if not text:
        return False
    
    try:
        # Define patterns for sensitive information
        patterns = [
            # Email addresses
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            # Phone numbers
            r'\b(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b',
            # SSNs
            r'\b\d{3}-\d{2}-\d{4}\b',
            # Credit card numbers
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            # Passwords (common password field identifiers)
            r'\b(password|passwd|pwd|secret|api[\s_-]?key)\s*[:=]\s*\w+',
            # API keys (common formats)
            r'\b[A-Za-z0-9]{20,}\b'
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
                
        return False
    except Exception as e:
        logger.error(f"Error checking for sensitive information: {e}")
        return False

def calculate_information_density(text: str) -> float:
    """
    Calculate information density of text (0-1 scale).
    Higher values indicate more meaningful content.
    
    Args:
        text: Input text
        
    Returns:
        Information density score (0-1)
    """
    if not text or not NLTK_AVAILABLE:
        return 0.0
    
    try:
        # Tokenize text
        tokens = word_tokenize(text.lower())
        
        if not tokens:
            return 0.0
        
        # Count meaningful tokens (not stopwords or punctuation)
        meaningful_tokens = [token for token in tokens 
                             if token not in STOPWORDS 
                             and token not in string.punctuation
                             and len(token) > 1]
        
        # Calculate ratio of meaningful tokens to total tokens
        return len(meaningful_tokens) / len(tokens) if tokens else 0.0
    except Exception as e:
        logger.error(f"Error calculating information density: {e}")
        return 0.0

def read_text_file(file_path: Union[str, Path], max_chars: int = 10000) -> str:
    """
    Read content from a text file with caching support.
    
    Args:
        file_path: Path to the text file
        max_chars: Maximum number of characters to read
        
    Returns:
        Text content of the file, or empty string if reading fails
    """
    file_path = Path(file_path)
    
    # Create a memory cache key
    try:
        cache_key = f"text_read_{str(file_path)}_{file_path.stat().st_mtime}"
        
        # Check for in-memory cache first (faster)
        if cache_key in _MEMORY_CACHE:
            return _MEMORY_CACHE[cache_key][:max_chars]
        
        # Get cache file path from centralized cache system
        cache_file = get_cache_path(file_path, "text")
        
        # Try to load from disk cache if file hasn't changed
        if not os.environ.get('CLEANUPX_NO_CACHE') and cache_file.exists():
            try:
                if cache_file.stat().st_mtime >= file_path.stat().st_mtime:
                    with open(cache_file, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    
                    # Store in memory cache
                    _MEMORY_CACHE[cache_key] = content
                    
                    return content[:max_chars]
            except Exception as e:
                logger.debug(f"Failed to read from cache file {cache_file}: {e}")
        
        # Read from the actual file
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(max_chars)
        
        # Cache the content if caching is enabled
        if not os.environ.get('CLEANUPX_NO_CACHE'):
            try:
                # Write to disk cache
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Store in memory cache
                _MEMORY_CACHE[cache_key] = content
            except Exception as e:
                logger.debug(f"Failed to cache text file content: {e}")
        
        return content
    except Exception as e:
        logger.error(f"Error reading text file {file_path}: {e}")
        return "" 