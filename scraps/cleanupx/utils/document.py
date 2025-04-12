#!/usr/bin/env python3
"""
Document analysis utilities.
This module provides functionality for extracting information from documents
and analyzing their content.
"""

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Union, Dict, Any, Tuple
import time

import docx2txt
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

from cleanupx.utils.common import is_image_file, get_file_extension
from cleanupx.utils.config import DEFAULT_OCR_LANGUAGE
from cleanupx.utils.cache import is_cached, save_to_cache, get_from_cache
from cleanupx.utils.text import get_file_text, extract_keywords, get_language
from cleanupx.utils.file import get_file_metadata, get_file_info, is_document

logger = logging.getLogger(__name__)

def analyze_document(file_path: Union[str, Path], force: bool = False) -> Dict[str, Any]:
    """
    Analyze a document and extract its content and metadata.
    Results are cached in memory for future use.
    
    Args:
        file_path: Path to the document
        force: Force reanalysis even if cached result exists
        
    Returns:
        Dictionary containing document analysis results
    """
    file_path = Path(file_path)
    
    # Generate a cache key based on the file path and modification time
    file_stat = file_path.stat()
    mod_time = file_stat.st_mtime
    cache_key = f"doc_analysis_{str(file_path)}_{mod_time}"
    
    # Check if analysis is already cached and not forced to reanalyze
    if not force and is_cached(cache_key):
        cached_result = get_from_cache(cache_key)
        logger.debug(f"Using cached document analysis for {file_path}")
        return cached_result
    
    logger.info(f"Analyzing document: {file_path}")
    
    # Start timing
    start_time = time.time()
    
    # Get basic file info
    file_info = get_file_info(file_path)
    
    # Initialize result dictionary
    result = {
        "file_info": file_info,
        "content": {},
        "metadata": {},
        "analysis": {}
    }
    
    # Only process if it's a document
    if is_document(file_path):
        try:
            # Extract text content
            content = get_file_text(file_path)
            result["content"]["text"] = content
            
            # Extract keywords
            if content:
                keywords = extract_keywords(content)
                result["analysis"]["keywords"] = keywords
                
                # Add keyword count
                result["analysis"]["keyword_count"] = len(keywords)
                
                # Add approximate word count
                words = content.split()
                result["analysis"]["word_count"] = len(words)
            
        except Exception as e:
            logger.error(f"Error analyzing document {file_path}: {e}")
            result["error"] = str(e)
    
    # Calculate processing time
    processing_time = time.time() - start_time
    result["processing_time"] = processing_time
    
    # Cache the result in memory
    save_to_cache(cache_key, result)
    
    logger.info(f"Document analysis completed in {processing_time:.2f}s: {file_path}")
    return result

def analyze_documents(
    directory: Union[str, Path], 
    recursive: bool = True,
    force: bool = False
) -> Dict[str, Dict[str, Any]]:
    """
    Analyze all documents in a directory.
    
    Args:
        directory: Directory containing documents
        recursive: Whether to recursively scan subdirectories
        force: Force reanalysis even if cached result exists
        
    Returns:
        Dictionary mapping file paths to analysis results
    """
    directory = Path(directory)
    logger.info(f"Analyzing documents in {directory} (recursive={recursive})")
    
    results = {}
    
    # Function to process a single directory
    def process_directory(dir_path):
        for item in dir_path.iterdir():
            if item.is_file() and is_document(item):
                try:
                    results[str(item)] = analyze_document(item, force=force)
                except Exception as e:
                    logger.error(f"Error analyzing {item}: {e}")
                    results[str(item)] = {"error": str(e)}
            elif recursive and item.is_dir():
                process_directory(item)
    
    # Start processing
    process_directory(directory)
    
    logger.info(f"Completed analysis of {len(results)} documents in {directory}")
    return results

def clear_document_cache(file_path: Optional[Union[str, Path]] = None) -> None:
    """
    Clear document analysis cache for a specific file or all files.
    This function is a placeholder since actual cache management is handled
    by the cache module. The cache key pattern for document analysis is
    'doc_analysis_{file_path}_{mod_time}'.
    
    Args:
        file_path: Path to the document to clear cache for, or None for all documents
    """
    logger.info(f"Document cache clearing functionality is handled by the cache module")
    logger.info(f"Use the cache module's clear_cache() or remove_from_cache() functions")

def generate_document_summary(
    directory: Union[str, Path], 
    recursive: bool = True,
    force: bool = False
) -> Dict[str, Any]:
    """
    Generate a summary of all documents in a directory.
    
    Args:
        directory: Directory containing documents
        recursive: Whether to recursively scan subdirectories
        force: Force reanalysis even if cached result exists
        
    Returns:
        Summary dictionary with statistics and top keywords
    """
    directory = Path(directory)
    logger.info(f"Generating document summary for {directory}")
    
    # Analyze all documents
    analysis_results = analyze_documents(directory, recursive=recursive, force=force)
    
    # Initialize summary
    summary = {
        "directory": str(directory),
        "document_count": len(analysis_results),
        "total_word_count": 0,
        "keywords": {},
        "document_types": {},
        "errors": []
    }
    
    # Process each document's analysis
    for file_path, result in analysis_results.items():
        # Check for errors
        if "error" in result:
            summary["errors"].append({
                "file": file_path,
                "error": result["error"]
            })
            continue
        
        # Add file type statistics
        file_type = result["file_info"].get("extension", "unknown").lower()
        summary["document_types"][file_type] = summary["document_types"].get(file_type, 0) + 1
        
        # Add word count
        word_count = result.get("analysis", {}).get("word_count", 0)
        summary["total_word_count"] += word_count
        
        # Add keywords
        for keyword in result.get("analysis", {}).get("keywords", []):
            summary["keywords"][keyword] = summary["keywords"].get(keyword, 0) + 1
    
    # Sort keywords by frequency
    sorted_keywords = sorted(summary["keywords"].items(), key=lambda x: x[1], reverse=True)
    summary["top_keywords"] = dict(sorted_keywords[:20])  # Top 20 keywords
    
    logger.info(f"Generated document summary for {directory}: {len(analysis_results)} documents")
    return summary

def export_document_summary(file_path: Union[str, Path], output_path: Optional[Path] = None) -> Path:
    """
    Generate and export a document summary to a markdown file.
    
    Args:
        file_path: Path to the document to analyze
        output_path: Optional custom output path
        
    Returns:
        Path to the created summary file
    """
    file_path = Path(file_path)
    
    # Generate summary
    summary = generate_document_summary(file_path)
    
    # Determine output path
    if output_path is None:
        output_path = file_path.parent / f"{file_path.stem}_summary.md"
    
    # Write summary to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    logger.info(f"Document summary exported to {output_path}")
    return output_path

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