#!/usr/bin/env python3
"""
Image analysis and processing utilities for cleanupx.

This module provides functionality for analyzing images, generating summaries,
and finding similar images. All caching is now done in-memory instead of
writing cache files to disk.
"""

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any, Set

import imagehash
import numpy as np
from PIL import Image, UnidentifiedImageError, ExifTags

from cleanupx.utils.cache import is_cached, save_to_cache, get_from_cache, clear_cache
from cleanupx.utils.file import get_file_metadata, format_timestamp
from cleanupx.utils.string import truncate_string
from cleanupx.utils.text import get_most_similar_strings, generate_caption

# Configure logging
logger = logging.getLogger(__name__)

# Cache constants
IMAGE_ANALYSIS_CACHE_PREFIX = "image_analysis:"
IMAGE_SIMILARITY_CACHE_PREFIX = "image_similarity:"
SIMILAR_IMAGES_CACHE_PREFIX = "similar_images:"
IMAGE_SUMMARY_CACHE_PREFIX = "image_summary:"

def analyze_image(image_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Analyze an image file and return metadata and analysis results.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary containing image metadata and analysis results
    """
    image_path = Path(image_path)
    
    # Generate a cache key based on the file path and modification time
    # This ensures the cache is invalidated if the file changes
    mtime = os.path.getmtime(image_path)
    cache_key = f"{IMAGE_ANALYSIS_CACHE_PREFIX}{image_path}:{mtime}"
    
    # Check if result is cached
    if is_cached(cache_key):
        logger.debug(f"Using cached analysis for {image_path}")
        return get_from_cache(cache_key)
    
    logger.info(f"Analyzing image: {image_path}")
    
    # Get basic file metadata
    file_metadata = get_file_metadata(image_path)
    
    # Initialize analysis result with basic metadata
    analysis = {
        "path": str(image_path),
        "filename": image_path.name,
        "size_bytes": file_metadata["size_bytes"],
        "size_human": file_metadata["size_human"],
        "created": file_metadata["created"],
        "modified": file_metadata["modified"],
        "format": None,
        "mode": None,
        "width": None,
        "height": None,
        "aspect_ratio": None,
        "exif": {},
        "hashes": {},
        "error": None
    }
    
    try:
        # Open the image
        with Image.open(image_path) as img:
            # Basic image properties
            analysis["format"] = img.format
            analysis["mode"] = img.mode
            analysis["width"], analysis["height"] = img.size
            analysis["aspect_ratio"] = analysis["width"] / analysis["height"] if analysis["height"] > 0 else 0
            
            # Extract EXIF data if available
            if hasattr(img, "_getexif") and img._getexif():
                exif = {
                    ExifTags.TAGS.get(tag, tag): value
                    for tag, value in img._getexif().items()
                    if tag in ExifTags.TAGS
                }
                
                # Process EXIF data to ensure it's serializable
                clean_exif = {}
                for key, value in exif.items():
                    if isinstance(value, (str, int, float, bool, list, dict)):
                        clean_exif[key] = value
                    elif isinstance(value, bytes):
                        clean_exif[key] = f"<{len(value)} bytes>"
                    elif isinstance(value, datetime):
                        clean_exif[key] = value.isoformat()
                    else:
                        clean_exif[key] = str(value)
                
                analysis["exif"] = clean_exif
            
            # Calculate image hashes for later comparison
            try:
                analysis["hashes"] = {
                    "md5": hashlib.md5(img.tobytes()).hexdigest(),
                    "phash": str(imagehash.phash(img)),
                    "dhash": str(imagehash.dhash(img)),
                    "average_hash": str(imagehash.average_hash(img))
                }
            except Exception as e:
                logger.warning(f"Failed to calculate hashes for {image_path}: {e}")
                analysis["hashes"] = {}
    
    except UnidentifiedImageError:
        analysis["error"] = f"Not a valid image file: {image_path}"
        logger.warning(analysis["error"])
    except Exception as e:
        analysis["error"] = f"Error analyzing image {image_path}: {str(e)}"
        logger.error(analysis["error"])
    
    # Cache the result
    save_to_cache(cache_key, analysis)
    
    return analysis

def calculate_image_similarity(
    image1_path: Union[str, Path], 
    image2_path: Union[str, Path]
) -> Dict[str, float]:
    """
    Calculate similarity between two images using various methods.
    
    Args:
        image1_path: Path to the first image
        image2_path: Path to the second image
        
    Returns:
        Dictionary with similarity scores
    """
    image1_path = Path(image1_path)
    image2_path = Path(image2_path)
    
    # Create cache key (use sorted paths to ensure same key regardless of argument order)
    sorted_paths = sorted([str(image1_path), str(image2_path)])
    mtime1 = os.path.getmtime(image1_path)
    mtime2 = os.path.getmtime(image2_path)
    cache_key = f"{IMAGE_SIMILARITY_CACHE_PREFIX}{sorted_paths[0]}:{mtime1}_{sorted_paths[1]}:{mtime2}"
    
    # Check cache
    if is_cached(cache_key):
        return get_from_cache(cache_key)
    
    logger.info(f"Calculating similarity between {image1_path} and {image2_path}")
    
    # Analyze both images
    image1_analysis = analyze_image(image1_path)
    image2_analysis = analyze_image(image2_path)
    
    # Initialize similarity result
    similarity = {
        "size_ratio": 0.0,
        "dimension_ratio": 0.0,
        "aspect_ratio_similarity": 0.0,
        "phash_similarity": 0.0,
        "dhash_similarity": 0.0,
        "average_hash_similarity": 0.0,
        "overall_similarity": 0.0
    }
    
    # If either image had an error, return zero similarity
    if image1_analysis.get("error") or image2_analysis.get("error"):
        save_to_cache(cache_key, similarity)
        return similarity
    
    try:
        # Calculate size ratio
        size1 = image1_analysis["size_bytes"]
        size2 = image2_analysis["size_bytes"]
        size_ratio = min(size1, size2) / max(size1, size2)
        similarity["size_ratio"] = size_ratio
        
        # Calculate dimension similarity
        width1, height1 = image1_analysis["width"], image1_analysis["height"]
        width2, height2 = image2_analysis["width"], image2_analysis["height"]
        
        area1 = width1 * height1
        area2 = width2 * height2
        dimension_ratio = min(area1, area2) / max(area1, area2)
        similarity["dimension_ratio"] = dimension_ratio
        
        # Calculate aspect ratio similarity
        aspect1 = image1_analysis["aspect_ratio"]
        aspect2 = image2_analysis["aspect_ratio"]
        aspect_similarity = 1.0 - min(abs(aspect1 - aspect2) / max(aspect1, aspect2), 1.0)
        similarity["aspect_ratio_similarity"] = aspect_similarity
        
        # Hash similarities
        if image1_analysis["hashes"] and image2_analysis["hashes"]:
            # For phash, dhash, and average_hash: lower hamming distance = more similar
            try:
                hash1 = imagehash.hex_to_hash(image1_analysis["hashes"]["phash"])
                hash2 = imagehash.hex_to_hash(image2_analysis["hashes"]["phash"])
                phash_distance = hash1 - hash2
                phash_similarity = 1.0 - min(phash_distance / 64.0, 1.0)  # 64-bit hash
                similarity["phash_similarity"] = phash_similarity
            except Exception:
                similarity["phash_similarity"] = 0.0
            
            try:
                hash1 = imagehash.hex_to_hash(image1_analysis["hashes"]["dhash"])
                hash2 = imagehash.hex_to_hash(image2_analysis["hashes"]["dhash"])
                dhash_distance = hash1 - hash2
                dhash_similarity = 1.0 - min(dhash_distance / 64.0, 1.0)  # 64-bit hash
                similarity["dhash_similarity"] = dhash_similarity
            except Exception:
                similarity["dhash_similarity"] = 0.0
            
            try:
                hash1 = imagehash.hex_to_hash(image1_analysis["hashes"]["average_hash"])
                hash2 = imagehash.hex_to_hash(image2_analysis["hashes"]["average_hash"])
                avg_hash_distance = hash1 - hash2
                avg_hash_similarity = 1.0 - min(avg_hash_distance / 64.0, 1.0)  # 64-bit hash
                similarity["average_hash_similarity"] = avg_hash_similarity
            except Exception:
                similarity["average_hash_similarity"] = 0.0
        
        # Calculate overall similarity (weighted average)
        weights = {
            "size_ratio": 0.1,
            "dimension_ratio": 0.2,
            "aspect_ratio_similarity": 0.1,
            "phash_similarity": 0.3,
            "dhash_similarity": 0.2,
            "average_hash_similarity": 0.1
        }
        
        overall = sum(similarity[k] * weights[k] for k in weights)
        similarity["overall_similarity"] = overall
    
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        similarity["error"] = str(e)
    
    # Cache the result
    save_to_cache(cache_key, similarity)
    
    return similarity

def find_similar_images(
    directory: Union[str, Path], 
    target_image: Optional[Union[str, Path]] = None,
    extensions: Optional[List[str]] = None,
    threshold: float = 0.85,
    max_results: int = 10,
    recursive: bool = True
) -> List[Dict[str, Any]]:
    """
    Find images similar to a target image or find all similar image pairs.
    
    Args:
        directory: Directory to search for images
        target_image: Target image to compare against (optional)
        extensions: List of image file extensions to consider
        threshold: Similarity threshold (0.0 to 1.0)
        max_results: Maximum number of results to return
        recursive: Whether to search subdirectories
        
    Returns:
        List of dictionaries with similar image information
    """
    directory = Path(directory)
    target_image = Path(target_image) if target_image else None
    
    if not extensions:
        extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"]
    
    # Create a unique cache key
    cache_components = [
        str(directory),
        str(target_image) if target_image else "all",
        "_".join(extensions),
        str(threshold),
        str(max_results),
        "recursive" if recursive else "nonrecursive"
    ]
    
    # Add mtime of target image if specified
    if target_image and target_image.exists():
        cache_components.append(str(os.path.getmtime(target_image)))
    
    # Add directory mtime to invalidate cache when directory changes
    if directory.exists():
        cache_components.append(str(os.path.getmtime(directory)))
    
    cache_key = f"{SIMILAR_IMAGES_CACHE_PREFIX}{hashlib.md5('_'.join(cache_components).encode()).hexdigest()}"
    
    # Check if result is cached
    if is_cached(cache_key):
        logger.info(f"Using cached similar images result for {directory}")
        return get_from_cache(cache_key)
    
    logger.info(f"Finding similar images in {directory}")
    
    # Find all image files
    image_files = []
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext) for ext in extensions):
                    image_files.append(Path(root) / file)
    else:
        image_files = [
            directory / file for file in os.listdir(directory)
            if any(file.lower().endswith(ext) for ext in extensions)
        ]
    
    # If no image files found, return empty list
    if not image_files:
        empty_result = []
        save_to_cache(cache_key, empty_result)
        return empty_result
    
    results = []
    
    # Single target image mode
    if target_image:
        for image_file in image_files:
            if image_file == target_image:
                continue
            
            similarity = calculate_image_similarity(target_image, image_file)
            if similarity["overall_similarity"] >= threshold:
                results.append({
                    "image1": str(target_image),
                    "image2": str(image_file),
                    "similarity": similarity["overall_similarity"],
                    "details": similarity
                })
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Limit results
        if max_results > 0:
            results = results[:max_results]
    
    # Find all similar pairs mode
    else:
        # Compare all pairs
        for i, image1 in enumerate(image_files):
            for image2 in image_files[i+1:]:
                similarity = calculate_image_similarity(image1, image2)
                if similarity["overall_similarity"] >= threshold:
                    results.append({
                        "image1": str(image1),
                        "image2": str(image2),
                        "similarity": similarity["overall_similarity"],
                        "details": similarity
                    })
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Limit results
        if max_results > 0:
            results = results[:max_results]
    
    # Cache the result
    save_to_cache(cache_key, results)
    
    return results

def analyze_images(
    directory: Union[str, Path],
    extensions: Optional[List[str]] = None,
    recursive: bool = True
) -> Dict[str, Dict]:
    """
    Analyze all images in a directory.
    
    Args:
        directory: Directory containing images
        extensions: List of image file extensions to consider
        recursive: Whether to search subdirectories
        
    Returns:
        Dictionary mapping image paths to analysis results
    """
    directory = Path(directory)
    
    if not extensions:
        extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"]
    
    # Create cache key
    dir_mtime = os.path.getmtime(directory) if directory.exists() else 0
    cache_key = f"image_analysis:{directory}:{dir_mtime}:{'_'.join(extensions)}:{recursive}"
    
    # Check cache
    if is_cached(cache_key):
        logger.info(f"Using cached image analysis for {directory}")
        return get_from_cache(cache_key)
    
    logger.info(f"Analyzing images in {directory}")
    
    # Find all image files
    image_files = []
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext) for ext in extensions):
                    image_files.append(Path(root) / file)
    else:
        image_files = [
            directory / file for file in os.listdir(directory)
            if any(file.lower().endswith(ext) for ext in extensions)
        ]
    
    # Analyze each image
    results = {}
    for image_file in image_files:
        analysis = analyze_image(image_file)
        results[str(image_file)] = analysis
    
    # Cache results
    save_to_cache(cache_key, results)
    
    return results

def generate_image_summary(
    directory: Union[str, Path],
    extensions: Optional[List[str]] = None,
    recursive: bool = True,
    max_image_count: int = 100
) -> Dict[str, Any]:
    """
    Generate a summary of images in a directory.
    
    Args:
        directory: Directory containing images
        extensions: List of image file extensions to consider
        recursive: Whether to search subdirectories
        max_image_count: Maximum number of images to analyze
        
    Returns:
        Dictionary with image summary information
    """
    directory = Path(directory)
    
    if not extensions:
        extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"]
    
    # Create cache key
    dir_mtime = os.path.getmtime(directory) if directory.exists() else 0
    cache_key = f"{IMAGE_SUMMARY_CACHE_PREFIX}{directory}:{dir_mtime}:{'_'.join(extensions)}:{recursive}:{max_image_count}"
    
    # Check cache
    if is_cached(cache_key):
        logger.info(f"Using cached image summary for {directory}")
        return get_from_cache(cache_key)
    
    logger.info(f"Generating image summary for {directory}")
    
    # Find all image files
    image_files = []
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext) for ext in extensions):
                    image_files.append(Path(root) / file)
    else:
        image_files = [
            directory / file for file in os.listdir(directory)
            if any(file.lower().endswith(ext) for ext in extensions)
        ]
    
    # Limit the number of images to analyze
    if max_image_count and len(image_files) > max_image_count:
        logger.info(f"Limiting analysis to {max_image_count} images out of {len(image_files)}")
        image_files = image_files[:max_image_count]
    
    # Initialize summary
    summary = {
        "directory": str(directory),
        "image_count": len(image_files),
        "total_size_bytes": 0,
        "formats": {},
        "resolutions": {},
        "aspect_ratios": {},
        "cameras": {},
        "creation_dates": {},
        "similar_images": [],
        "largest_images": [],
        "smallest_images": []
    }
    
    # Analyze each image
    analyses = {}
    for image_file in image_files:
        analysis = analyze_image(image_file)
        analyses[str(image_file)] = analysis
        
        # Skip images with errors
        if analysis.get("error"):
            continue
        
        # Update total size
        summary["total_size_bytes"] += analysis["size_bytes"]
        
        # Update formats
        format_key = analysis["format"] or "Unknown"
        summary["formats"][format_key] = summary["formats"].get(format_key, 0) + 1
        
        # Update resolutions
        if analysis["width"] and analysis["height"]:
            resolution = f"{analysis['width']}x{analysis['height']}"
            summary["resolutions"][resolution] = summary["resolutions"].get(resolution, 0) + 1
        
        # Update aspect ratios
        if analysis["aspect_ratio"]:
            # Round to 2 decimal places
            aspect_key = round(analysis["aspect_ratio"], 2)
            summary["aspect_ratios"][str(aspect_key)] = summary["aspect_ratios"].get(str(aspect_key), 0) + 1
        
        # Update cameras
        camera_model = analysis["exif"].get("Model", "Unknown")
        summary["cameras"][camera_model] = summary["cameras"].get(camera_model, 0) + 1
        
        # Update creation dates
        if "DateTime" in analysis["exif"]:
            try:
                date_str = analysis["exif"]["DateTime"].split()[0].replace(":", "-")
                summary["creation_dates"][date_str] = summary["creation_dates"].get(date_str, 0) + 1
            except Exception:
                pass
    
    # Find similar images (if more than one image)
    if len(image_files) > 1:
        similar_pairs = find_similar_images(
            directory, 
            extensions=extensions, 
            threshold=0.95,  # High threshold for summary
            max_results=10,
            recursive=recursive
        )
        summary["similar_images"] = similar_pairs
    
    # Find largest and smallest images
    sorted_by_size = sorted(
        [a for a in analyses.values() if not a.get("error")],
        key=lambda x: x["size_bytes"]
    )
    
    if sorted_by_size:
        summary["smallest_images"] = [
            {
                "path": img["path"],
                "size": img["size_human"],
                "dimensions": f"{img['width']}x{img['height']}"
            }
            for img in sorted_by_size[:5]
        ]
        
        summary["largest_images"] = [
            {
                "path": img["path"],
                "size": img["size_human"],
                "dimensions": f"{img['width']}x{img['height']}"
            }
            for img in sorted_by_size[-5:]
        ]
        summary["largest_images"].reverse()  # Largest first
    
    # Format total size
    if summary["total_size_bytes"] < 1024:
        summary["total_size_human"] = f"{summary['total_size_bytes']} bytes"
    elif summary["total_size_bytes"] < 1024 * 1024:
        summary["total_size_human"] = f"{summary['total_size_bytes'] / 1024:.1f} KB"
    elif summary["total_size_bytes"] < 1024 * 1024 * 1024:
        summary["total_size_human"] = f"{summary['total_size_bytes'] / (1024 * 1024):.1f} MB"
    else:
        summary["total_size_human"] = f"{summary['total_size_bytes'] / (1024 * 1024 * 1024):.1f} GB"
    
    # Calculate average size
    if summary["image_count"] > 0:
        avg_size = summary["total_size_bytes"] / summary["image_count"]
        if avg_size < 1024:
            summary["average_size_human"] = f"{avg_size:.1f} bytes"
        elif avg_size < 1024 * 1024:
            summary["average_size_human"] = f"{avg_size / 1024:.1f} KB"
        elif avg_size < 1024 * 1024 * 1024:
            summary["average_size_human"] = f"{avg_size / (1024 * 1024):.1f} MB"
        else:
            summary["average_size_human"] = f"{avg_size / (1024 * 1024 * 1024):.1f} GB"
    
    # Cache summary
    save_to_cache(cache_key, summary)
    
    return summary

def clear_image_cache() -> None:
    """
    Clear the image analysis cache.
    This is now just a placeholder, as cache management is handled by the cache module.
    """
    # Clear all caches with our prefixes
    clear_cache(IMAGE_ANALYSIS_CACHE_PREFIX)
    clear_cache(IMAGE_SIMILARITY_CACHE_PREFIX)
    clear_cache(SIMILAR_IMAGES_CACHE_PREFIX)
    clear_cache(IMAGE_SUMMARY_CACHE_PREFIX)
    logger.info("Image cache cleared") 