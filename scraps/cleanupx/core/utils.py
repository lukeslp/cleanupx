"""
Utilities

Provides utility functions for file operations.
"""

import os
import random
import string
import hashlib
import logging
import json
import fnmatch
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional, Union, Any
from PIL import Image

logger = logging.getLogger(__name__)

def deduplicate_files(directory: str, recursive: bool = True, text_only: bool = False, 
                   similarity_threshold: float = 0.7, delete_duplicates: bool = False) -> Dict:
    """
    Deduplicate files in a directory.
    
    Args:
        directory: Directory to process
        recursive: Whether to process subdirectories
        text_only: Whether to only deduplicate text files
        similarity_threshold: Threshold for considering text files similar
        delete_duplicates: Whether to delete duplicate files
        
    Returns:
        Deduplication results
    """
    if text_only:
        from ..processors.text_dedupe import TextDedupeProcessor
        processor = TextDedupeProcessor()
        processor.similarity_threshold = similarity_threshold
    else:
        from ..processors.dedupe import DedupeProcessor
        processor = DedupeProcessor()
    
    # Process directory
    cache = {}  # Initialize an empty cache for file hashes
    result = processor.process_directory(directory, recursive)
    
    # Delete duplicates if requested
    if delete_duplicates and not text_only:
        delete_results = processor.delete_duplicates(result.get('duplicate_groups', []))
        result['deleted'] = delete_results
    
    # Add additional statistics
    result['directory'] = directory
    result['recursive'] = recursive
    result['text_only'] = text_only
    
    return result
    
def scramble_filenames(directory: str, recursive: bool = False) -> Dict:
    """
    Scramble filenames in a directory.
    
    Args:
        directory: Directory to process
        recursive: Whether to process subdirectories
        
    Returns:
        Scrambling results
    """
    results = {
        'renamed': [],
        'failed': []
    }
    
    for root, _, files in os.walk(directory):
        if not recursive and Path(root) != Path(directory):
            continue
            
        for file in files:
            file_path = Path(root) / file
            try:
                # Generate random filename while preserving extension
                ext = file_path.suffix
                new_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                new_path = file_path.parent / f"{new_name}{ext}"
                
                # Rename file
                file_path.rename(new_path)
                results['renamed'].append({
                    'old': str(file_path),
                    'new': str(new_path)
                })
            except Exception as e:
                logger.error(f"Error scrambling {file_path}: {str(e)}")
                results['failed'].append(str(file_path))
                
    return results
    
def generate_test_documents(directory: str, count: int = 10) -> Dict:
    """
    Generate test documents in a directory.
    
    Args:
        directory: Directory to generate documents in
        count: Number of documents to generate
        
    Returns:
        Generation results
    """
    results = {
        'created': [],
        'failed': []
    }
    
    doc_types = [
        ('txt', 'text/plain'),
        ('md', 'text/markdown'),
        ('py', 'text/x-python'),
        ('html', 'text/html'),
        ('css', 'text/css'),
        ('js', 'application/javascript'),
        ('json', 'application/json'),
        ('xml', 'application/xml'),
        ('csv', 'text/csv'),
        ('pdf', 'application/pdf')
    ]
    
    for i in range(count):
        try:
            # Select random document type
            ext, mime = random.choice(doc_types)
            
            # Generate random content based on type
            content = _generate_test_content(ext)
            
            # Create file with random name
            name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            file_path = Path(directory) / f"{name}.{ext}"
            
            # Write content to file
            with open(file_path, 'w') as f:
                f.write(content)
                
            results['created'].append({
                'path': str(file_path),
                'type': mime,
                'size': len(content)
            })
        except Exception as e:
            logger.error(f"Error generating test document: {str(e)}")
            results['failed'].append(str(e))
            
    return results
    
def _generate_test_content(ext: str) -> str:
    """Generate test content based on file extension."""
    if ext == 'txt':
        return "This is a sample text file.\n" * 10
    elif ext == 'md':
        return "# Sample Markdown\n\nThis is a sample markdown file.\n\n## Features\n\n- Item 1\n- Item 2\n"
    elif ext == 'py':
        return "def sample_function():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    sample_function()\n"
    elif ext == 'html':
        return "<!DOCTYPE html>\n<html>\n<head>\n<title>Sample</title>\n</head>\n<body>\n<h1>Hello</h1>\n</body>\n</html>"
    elif ext == 'css':
        return "body {\n    margin: 0;\n    padding: 0;\n    font-family: sans-serif;\n}\n"
    elif ext == 'js':
        return "function hello() {\n    console.log('Hello, World!');\n}\n\nhello();\n"
    elif ext == 'json':
        return '{"name": "Sample", "value": 42, "items": [1, 2, 3]}\n'
    elif ext == 'xml':
        return '<?xml version="1.0"?>\n<root>\n<item>Sample</item>\n</root>\n'
    elif ext == 'csv':
        return "id,name,value\n1,Sample,42\n2,Test,24\n"
    elif ext == 'pdf':
        # PDF generation would require additional libraries
        return ""
    else:
        return "Sample content\n" * 10

def get_file_hash(file_path: Union[str, Path], block_size: int = 65536) -> str:
    """
    Calculate SHA-256 hash of a file.
    
    Args:
        file_path: Path to the file
        block_size: Size of blocks to read
        
    Returns:
        File hash as hex string
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(block_size), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return ""

def get_file_metadata(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get metadata for a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file metadata
    """
    try:
        path = Path(file_path)
        stats = path.stat()
        
        metadata = {
            'name': path.name,
            'extension': path.suffix.lower(),
            'size': stats.st_size,
            'created': stats.st_ctime,
            'modified': stats.st_mtime,
            'mime_type': mimetypes.guess_type(str(path))[0]
        }
        
        # Get image dimensions if applicable
        if path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}:
            try:
                with Image.open(path) as img:
                    metadata['dimensions'] = img.size
            except Exception as e:
                logger.warning(f"Could not get image dimensions for {path}: {e}")
                
        return metadata
    except Exception as e:
        logger.error(f"Error getting metadata for {file_path}: {e}")
        return {}

def is_protected_file(file_path: Union[str, Path], patterns: List[str]) -> bool:
    """
    Check if a file matches protected patterns.
    
    Args:
        file_path: Path to check
        patterns: List of glob patterns
        
    Returns:
        Whether the file is protected
    """
    try:
        path = Path(file_path)
        name = path.name
        
        for pattern in patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False
    except Exception as e:
        logger.error(f"Error checking protected status for {file_path}: {e}")
        return True

def normalize_path(path: Union[str, Path]) -> Path:
    """
    Normalize a file path.
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized Path object
    """
    try:
        return Path(path).resolve()
    except Exception as e:
        logger.error(f"Error normalizing path {path}: {e}")
        return Path(path)

def save_rename_log(log: Dict[str, Any], directory: Union[str, Path]) -> None:
    """
    Save rename operation log to file.
    
    Args:
        log: Log data to save
        directory: Directory to save log in
    """
    try:
        path = Path(directory) / "rename_log.json"
        with open(path, 'w') as f:
            json.dump(log, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving rename log: {e}")

def add_error_to_log(log: Dict[str, Any], file_path: str, error: str) -> None:
    """
    Add an error to the rename log.
    
    Args:
        log: Log dictionary to update
        file_path: Path of file with error
        error: Error message
    """
    try:
        if 'errors' not in log:
            log['errors'] = []
        log['errors'].append({
            'file': file_path,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error adding to error log: {e}")

def get_image_dimensions(file_path: Union[str, Path]) -> Optional[tuple]:
    """
    Get dimensions of an image file.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        Tuple of (width, height) or None if not available
    """
    try:
        with Image.open(file_path) as img:
            return img.size
    except Exception as e:
        logger.error(f"Error getting image dimensions for {file_path}: {e}")
        return None

def convert_heic_to_jpeg(file_path: Union[str, Path]) -> Optional[Path]:
    """
    Convert HEIC image to JPEG format.
    
    Args:
        file_path: Path to HEIC file
        
    Returns:
        Path to converted JPEG file or None if conversion failed
    """
    try:
        from PIL import Image
        import pillow_heif
        
        heif_file = pillow_heif.read_heif(str(file_path))
        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride,
        )
        
        jpeg_path = Path(file_path).with_suffix('.jpg')
        image.save(jpeg_path, 'JPEG')
        return jpeg_path
    except Exception as e:
        logger.error(f"Error converting HEIC to JPEG for {file_path}: {e}")
        return None

def convert_webp_to_jpeg(file_path: Union[str, Path]) -> Optional[Path]:
    """
    Convert WebP image to JPEG format.
    
    Args:
        file_path: Path to WebP file
        
    Returns:
        Path to converted JPEG file or None if conversion failed
    """
    try:
        with Image.open(file_path) as img:
            jpeg_path = Path(file_path).with_suffix('.jpg')
            img.convert('RGB').save(jpeg_path, 'JPEG')
            return jpeg_path
    except Exception as e:
        logger.error(f"Error converting WebP to JPEG for {file_path}: {e}")
        return None

def embed_alt_text_into_image(file_path: Union[str, Path], alt_text: str) -> bool:
    """
    Embed alt text into image metadata.
    
    Args:
        file_path: Path to image file
        alt_text: Alt text to embed
        
    Returns:
        Whether embedding was successful
    """
    try:
        with Image.open(file_path) as img:
            img.info['alt'] = alt_text
            img.save(file_path)
        return True
    except Exception as e:
        logger.error(f"Error embedding alt text for {file_path}: {e}")
        return False

def read_text_file(file_path: Union[str, Path]) -> str:
    """
    Read text from a file with encoding detection.
    
    Args:
        file_path: Path to text file
        
    Returns:
        File contents as string
    """
    try:
        import chardet
        
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            
        if not raw_data:
            return ""
            
        result = chardet.detect(raw_data)
        encoding = result['encoding'] or 'utf-8'
        
        try:
            return raw_data.decode(encoding)
        except UnicodeDecodeError:
            return raw_data.decode('utf-8', errors='ignore')
    except Exception as e:
        logger.error(f"Error reading text file {file_path}: {e}")
        return ""

def strip_media_suffixes(filename: str) -> str:
    """
    Remove common media suffixes from filename.
    
    Args:
        filename: Original filename
        
    Returns:
        Filename with suffixes removed
    """
    suffixes = [
        r'\[1080p\]', r'\[720p\]', r'\[480p\]',
        r'\[HD\]', r'\[SD\]', r'\[HQ\]', r'\[LQ\]',
        r'\[MP3\]', r'\[FLAC\]', r'\[WAV\]',
        r'\[MP4\]', r'\[AVI\]', r'\[MKV\]',
        r'\(Official Video\)', r'\(Lyric Video\)',
        r'\(Audio\)', r'\(Official Audio\)',
        r'\[.*?\]', r'\(.*?\)'
    ]
    
    import re
    clean_name = filename
    for suffix in suffixes:
        clean_name = re.sub(suffix, '', clean_name, flags=re.IGNORECASE)
    return clean_name.strip()

def ensure_metadata_dir(directory: Union[str, Path]) -> Path:
    """
    Ensure metadata directory exists.
    
    Args:
        directory: Base directory
        
    Returns:
        Path to metadata directory
    """
    try:
        metadata_dir = Path(directory) / '.cleanupx'
        metadata_dir.mkdir(parents=True, exist_ok=True)
        return metadata_dir
    except Exception as e:
        logger.error(f"Error creating metadata directory: {e}")
        return Path(directory)

def get_description_path(file_path: Union[str, Path]) -> Path:
    """
    Get path for file description markdown.
    
    Args:
        file_path: Path to original file
        
    Returns:
        Path for description file
    """
    try:
        path = Path(file_path)
        metadata_dir = ensure_metadata_dir(path.parent)
        return metadata_dir / f"{path.stem}_description.md"
    except Exception as e:
        logger.error(f"Error getting description path: {e}")
        return Path(file_path).with_suffix('.md') 