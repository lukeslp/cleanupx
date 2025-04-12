#!/usr/bin/env python3
"""
xai_alt.py - Process image files in a directory to generate comprehensive alt text.

This script:
1. Scans a directory for image files (optionally recursively)
2. Uses X.AI Vision API (grok-2-vision-latest) to generate detailed alt text for each image
3. Creates a markdown file with the same name as each image containing the alt text
4. Maintains a cache file (alt_text_cache.json) to avoid re-processing images
5. Optionally renames image files based on their content
6. Provides an interactive CLI for directory selection and processing options

Usage:
  python xai_alt.py                      # Run in interactive CLI mode
  python xai_alt.py --dir PATH [--recursive] [--force] [--rename]  # Process directory with options
"""

import os
import sys
import json
import argparse
import time
import base64
import gc
from pathlib import Path
import openai

# --- Configuration and Setup ---
# NOTE: In production, do not hardcode your API key; use environment variables instead.
XAI_API_KEY = "xai-8zAk5VIaL3Vxpu3fO3r2aiWqqeVAZ173X04VK2R1m425uYpWOIOQJM3puq1Q38xJ2sHfbq3mX4PBxJXC"
client = openai.Client(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

# Cache file for storing generated alt texts
CACHE_FILE = "alt_text_cache.json"

# Image file extensions to process
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif'}

# Maximum file size to process in MB
MAX_FILE_SIZE_MB = 20

# Prompt text used for alt text generation
PROMPT_TEXT = (
    "You are an AI specializing in describing images for accessibility purposes. "
    "Write comprehensive alt text for this image, as though for a blind engineer who needs "
    "to understand every detail of the information including text. "
    "Also suggest a descriptive filename based on the content of the image. "
    "Format your response in this exact JSON structure:\n"
    "{\n"
    "  \"description\": \"Detailed description of the image\",\n"
    "  \"alt_text\": \"Concise alt text for the image\",\n"
    "  \"suggested_filename\": \"descriptive_filename_without_extension\",\n"
    "  \"tags\": [\"tag1\", \"tag2\", ...]\n"
    "}"
)

# --- Helper Functions ---

def load_cache():
    """Load the alt text cache if it exists."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as fp:
            return json.load(fp)
    return {}

def save_cache(cache):
    """Save the alt text cache to file."""
    with open(CACHE_FILE, "w", encoding="utf-8") as fp:
        json.dump(cache, fp, indent=4, ensure_ascii=False)

def encode_image(image_path):
    """
    Encode an image file as base64 for API transmission.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded image or None if encoding failed
    """
    try:
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
            return base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None

def generate_alt_text(image_path):
    """
    Call the X.AI API with the image and prompt.
    Returns the generated alt text (dictionary) if successful; otherwise, returns None.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Generated description dictionary or None if an error occurred
    """
    try:
        # Check file size
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            print(f"Image too large ({file_size_mb:.1f} MB > {MAX_FILE_SIZE_MB} MB): {image_path}")
            return None
        
        # Encode the image to base64
        base64_image = encode_image(image_path)
        if not base64_image:
            print(f"Failed to encode image: {image_path}")
            return None
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    },
                    {
                        "type": "text",
                        "text": PROMPT_TEXT
                    }
                ]
            }
        ]
        
        completion = client.chat.completions.create(
            model="grok-2-vision-latest",
            messages=messages,
            temperature=0.01,
            response_format={"type": "json_object"}
        )
        
        generated_text = completion.choices[0].message.content.strip()
        
        # Parse JSON
        try:
            result = json.loads(generated_text)
            return result
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Raw response: {generated_text}")
            # Try to extract JSON if it's embedded in the response
            import re
            json_match = re.search(r'{[\s\S]*}', generated_text)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                    return result
                except:
                    pass
            return None
        
    except Exception as e:
        print(f"Error generating alt text for {image_path}: {e}")
        return None
    finally:
        # Force garbage collection to prevent memory issues with large images
        gc.collect()

def get_cache_key(file_path):
    """
    Create a unique cache key for an image file based on its path and modification time.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        String cache key
    """
    stats = os.stat(file_path)
    mod_time = stats.st_mtime
    return f"{file_path}:{mod_time}"

def scan_directory(directory, recursive=False):
    """
    Scan a directory for image files.
    
    Args:
        directory: Path to directory to scan
        recursive: Whether to scan subdirectories recursively
        
    Returns:
        List of image file paths
    """
    image_files = []
    
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path) and os.path.splitext(file_path)[1].lower() in IMAGE_EXTENSIONS:
                    image_files.append(file_path)
    else:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and os.path.splitext(file_path)[1].lower() in IMAGE_EXTENSIONS:
                image_files.append(file_path)
    
    return image_files

def clean_filename(filename):
    """
    Clean a filename to be safe for file systems.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Replace characters that are not allowed in filenames
    import re
    forbidden_chars = r'[<>:"/\\|?*]'
    cleaned = re.sub(forbidden_chars, '_', filename)
    
    # Replace multiple spaces or underscores with a single underscore
    cleaned = re.sub(r'[\s_]+', '_', cleaned)
    
    # Remove leading/trailing spaces and dots
    cleaned = cleaned.strip('. ')
    
    # Ensure the filename isn't too long (max 255 chars for most file systems)
    if len(cleaned) > 255:
        cleaned = cleaned[:255]
    
    return cleaned

def generate_new_filename(file_path, description):
    """
    Generate a new filename based on image description.
    
    Args:
        file_path: Path to the image file
        description: Dictionary with image description
        
    Returns:
        New filename with extension
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    
    # Get suggested name from description
    if description and isinstance(description, dict):
        suggested_name = description.get("suggested_filename")
        if suggested_name and isinstance(suggested_name, str):
            base_name = clean_filename(suggested_name)
        else:
            base_name = clean_filename(file_path.stem)
    else:
        base_name = clean_filename(file_path.stem)
    
    return f"{base_name}{ext}"

def rename_file(original_path, new_name):
    """
    Rename a file with a new name.
    
    Args:
        original_path: Original file path
        new_name: New filename (with extension)
        
    Returns:
        Path to renamed file or None if rename failed
    """
    original_path = Path(original_path)
    new_path = original_path.parent / new_name
    
    # Don't rename if the new name is the same as the old one
    if original_path.name == new_name:
        return original_path
    
    # Don't overwrite existing files
    if new_path.exists():
        base_name = new_path.stem
        ext = new_path.suffix
        counter = 1
        while new_path.exists():
            new_path = original_path.parent / f"{base_name}_{counter}{ext}"
            counter += 1
    
    try:
        os.rename(original_path, new_path)
        print(f"Renamed: {original_path} -> {new_path}")
        return new_path
    except Exception as e:
        print(f"Error renaming file {original_path}: {e}")
        return None

def create_markdown_file(image_path, description):
    """
    Create a markdown file with the same base name as the image containing the alt text.
    
    Args:
        image_path: Path to the image file
        description: Dictionary with image description
        
    Returns:
        Path to created markdown file
    """
    # Get the base name without extension
    image_path = Path(image_path)
    base_name = image_path.stem
    # Get the directory of the image
    directory = image_path.parent
    # Create markdown file path
    md_file_path = directory / f"{base_name}.md"
    
    # Create markdown content
    content = [
        f"# {base_name}",
        "",
        f"**Description:** {description.get('description', 'No description available')}",
        "",
        f"**Alt Text:** {description.get('alt_text', 'No alt text available')}",
        "",
        "## Metadata",
        f"- **Original Filename:** {image_path.name}",
        "",
        "## Tags",
    ]
    
    # Add tags if available
    tags = description.get('tags', [])
    if tags and isinstance(tags, list):
        for tag in tags:
            content.append(f"- {tag}")
    else:
        content.append("- No tags available")
    
    # Write markdown file
    with open(md_file_path, "w", encoding="utf-8") as fp:
        fp.write('\n'.join(content))
    
    return md_file_path

def process_image_file(image_path, cache, force=False, rename=False):
    """
    Process a single image file: generate alt text, create markdown file, and optionally rename.
    
    Args:
        image_path: Path to the image file
        cache: Alt text cache dictionary
        force: Whether to force regeneration of alt text even if in cache
        rename: Whether to rename the image file based on description
        
    Returns:
        Tuple of (success, message, new_image_path)
    """
    # Convert to Path object
    image_path = Path(image_path)
    
    # Get cache key for this image
    cache_key = get_cache_key(str(image_path))
    
    # Check if already in cache and not forcing regeneration
    if cache_key in cache and not force:
        print(f"Found cached alt text for {image_path}")
        description = cache[cache_key]
    else:
        print(f"Generating alt text for {image_path}...")
        description = generate_alt_text(image_path)
        
        if not description:
            return False, f"Failed to generate alt text for {image_path}", image_path
        
        # Store in cache (using the original path as key)
        cache[cache_key] = description
        save_cache(cache)
    
    # Track the current path of the image (may change if renamed)
    current_image_path = image_path
    
    # Rename the file if requested
    if rename and description:
        new_filename = generate_new_filename(image_path, description)
        renamed_path = rename_file(image_path, new_filename)
        if renamed_path:
            current_image_path = renamed_path
    
    # Create markdown file
    md_file_path = create_markdown_file(current_image_path, description)
    
    return True, f"Created {md_file_path}", current_image_path

def process_directory(directory, recursive=False, force=False, rename=False):
    """
    Process all image files in a directory.
    
    Args:
        directory: Path to directory to process
        recursive: Whether to scan subdirectories recursively
        force: Whether to force regeneration of alt text even if in cache
        rename: Whether to rename image files based on description
        
    Returns:
        Dictionary with processing statistics
    """
    # Load cache
    cache = load_cache()
    print(f"Cache loaded with {len(cache)} entries")
    
    # Scan directory for image files
    image_files = scan_directory(directory, recursive)
    print(f"Found {len(image_files)} image files in {directory}")
    
    # Initialize statistics
    stats = {
        "total": len(image_files),
        "success": 0,
        "error": 0,
        "renamed": 0
    }
    
    # Process each image
    for i, image_path in enumerate(image_files, 1):
        print(f"\n[{i}/{stats['total']}] Processing {image_path}")
        
        success, message, new_path = process_image_file(image_path, cache, force, rename)
        print(message)
        
        if success:
            stats["success"] += 1
            if new_path != image_path:
                stats["renamed"] += 1
        else:
            stats["error"] += 1
        
        # Sleep briefly to avoid rate limits
        time.sleep(0.5)
    
    # Print summary
    print("\n======= Processing Complete =======")
    print(f"Total images: {stats['total']}")
    print(f"Successfully processed: {stats['success']}")
    print(f"Files renamed: {stats['renamed']}")
    print(f"Errors during processing: {stats['error']}")
    
    return stats

def interactive_cli():
    """Run the interactive CLI mode."""
    print("\nWelcome to X.AI Alt Text Generator!")
    print("This script generates alt text for images and creates markdown files.")
    
    while True:
        print("\nPlease choose an option:")
        print("  1. Process a directory of images")
        print("  2. Exit")
        
        choice = input("Enter your choice (1/2): ").strip()
        
        if choice == "1":
            directory = input("Enter the directory path: ").strip()
            if not os.path.isdir(directory):
                print(f"Error: {directory} is not a valid directory.")
                continue
            
            recursive_input = input("Process subdirectories recursively? (y/n): ").strip().lower()
            recursive = recursive_input == "y"
            
            force_input = input("Force regeneration of alt text even if cached? (y/n): ").strip().lower()
            force = force_input == "y"
            
            rename_input = input("Rename files based on image content? (y/n): ").strip().lower()
            rename = rename_input == "y"
            
            process_directory(directory, recursive, force, rename)
            
        elif choice == "2":
            print("Exiting. Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Process image files to generate alt text and create markdown files."
    )
    parser.add_argument("--dir", help="Directory containing images to process")
    parser.add_argument("--recursive", "-r", action="store_true", help="Process subdirectories recursively")
    parser.add_argument("--force", "-f", action="store_true", help="Force regeneration of alt text even if cached")
    parser.add_argument("--rename", "-n", action="store_true", help="Rename files based on image content")
    
    args = parser.parse_args()
    
    if args.dir:
        # Command-line mode
        if not os.path.isdir(args.dir):
            print(f"Error: {args.dir} is not a valid directory.", file=sys.stderr)
            sys.exit(1)
        
        process_directory(args.dir, args.recursive, args.force, args.rename)
    else:
        # Interactive mode
        interactive_cli()

if __name__ == "__main__":
    main()
