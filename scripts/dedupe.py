#!/usr/bin/env python3
"""
dedupe_images.py

This script deduplicates images in a folder based on file size and resolution.
For each image in the folder (filtered by common image extensions), it computes:

  - File size (in bytes)
  - Image resolution (width and height)

Images that share the same file size and resolution are assumed to be duplicates.
The script then prompts the user to delete all but the first file in each duplicate group.

Usage:
    python dedupe_images.py /path/to/image/folder
"""

import os
import sys
from pathlib import Path
from PIL import Image

# Define common image file extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic"}

def get_image_info(file_path: Path):
    """
    Return the file size (in bytes) and resolution (width, height) for an image.

    Args:
        file_path (Path): Path to the image file.

    Returns:
        tuple: (file_size, (width, height)) if successful; otherwise (file_size, None).
    """
    try:
        file_size = file_path.stat().st_size
    except Exception as e:
        print(f"Error getting file size for {file_path}: {e}")
        return None, None

    try:
        with Image.open(file_path) as img:
            resolution = img.size  # (width, height)
    except Exception as e:
        print(f"Error opening image {file_path}: {e}")
        resolution = None

    return file_size, resolution

def dedupe_images(folder_path: str):
    """
    Scan the specified folder for duplicate images based on file size and resolution.
    For each set of duplicates, keep the first file and prompt to delete the others.

    Args:
        folder_path (str): Path to the image folder.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        print(f"{folder_path} is not a valid directory.")
        return

    # Collect all image files in the folder (non-recursively)
    images = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
    
    if not images:
        print("No images found in the folder.")
        return

    # Dictionary mapping (file_size, resolution) to list of files
    image_dict = {}
    for img in images:
        file_size, resolution = get_image_info(img)
        if file_size is None or resolution is None:
            continue
        key = (file_size, resolution)
        image_dict.setdefault(key, []).append(img)

    duplicates = []

    # Identify duplicate groups
    for key, file_list in image_dict.items():
        if len(file_list) > 1:
            original = file_list[0]
            dupes = file_list[1:]
            print(f"\nFound duplicates for '{original.name}' (size: {key[0]} bytes, resolution: {key[1][0]}x{key[1][1]}):")
            for dup in dupes:
                print(f"  - {dup.name}")
            duplicates.extend(dupes)

    # Confirm deletion
    if duplicates:
        confirm = input("\nDo you want to delete these duplicate files? [y/N]: ").strip().lower()
        if confirm == 'y':
            for dup in duplicates:
                try:
                    dup.unlink()
                    print(f"Deleted: {dup}")
                except Exception as e:
                    print(f"Error deleting {dup}: {e}")
        else:
            print("No files were deleted.")
    else:
        print("No duplicate images found based on size and resolution.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python dedupe_images.py /path/to/image/folder")
        sys.exit(1)
    dedupe_images(sys.argv[1])

if __name__ == "__main__":
    main()