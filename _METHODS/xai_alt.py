#!/usr/bin/env python3
"""
xai_alt.py - Process image-data.js interactively to generate comprehensive alt text and update each image's description and alt_text.
This script uses an OpenAI API (grok-2-vision-latest) to generate detailed alt text for each image.
It maintains a cache file (generated_alts.json) so that already processed images are not re-queried.
After each key step, the user is prompted to confirm, and changes are displayed in terminal for full observability.
"""

import os
import json
import re
import time
import openai

# --- Configuration and Setup ---
# NOTE: In production, do not hardcode your API key; use environment variables instead.
XAI_API_KEY = "xai-8zAk5VIaL3Vxpu3fO3r2aiWqqeVAZ173X04VK2R1m425uYpWOIOQJM3puq1Q38xJ2sHfbq3mX4PBxJXC"
client = openai.Client(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

# File names
IMAGE_DATA_JS = "image-data.js"
UPDATED_IMAGE_DATA_JS = "image-data.updated.js"
BACKUP_IMAGE_DATA_JS = "image-data.backup.js"
CACHE_FILE = "generated_alts.json"

# Prompt text used for alt text generation
PROMPT_TEXT = (
    "Write comprehensive alt text for this image, as though for a blind engineer who needs "
    "to understand every detail of the information including text. Write at maximum length. "
    "Do not include prepended or appended content like Alt Text, just resopnd with the description "
    "verbatim and nothing else?"
)

# --- Helper Functions ---

def load_cache():
    """Load the generated alt texts cache if it exists."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as fp:
            return json.load(fp)
    return {}

def save_cache(cache):
    """Save the generated alt texts cache to file."""
    with open(CACHE_FILE, "w", encoding="utf-8") as fp:
        json.dump(cache, fp, indent=4, ensure_ascii=False)

def backup_file(src, backup):
    """Create a backup of the file if it does not already exist."""
    if not os.path.exists(backup):
        with open(src, "r", encoding="utf-8") as fin, open(backup, "w", encoding="utf-8") as fout:
            fout.write(fin.read())
        print(f"Backup created: {backup}")
    else:
        print(f"Backup already exists: {backup}")

def extract_gallery_images(js_content):
    """
    Extract the galleryImages array from image-data.js.
    Assumes the file contains a line starting with "const galleryImages =" and ending with "];".
    """
    pattern = re.compile(r"const\s+galleryImages\s*=\s*(\[\s*{.*?}\s*\]);", re.DOTALL)
    match = pattern.search(js_content)
    if match:
        json_text = match.group(1)
        try:
            gallery = json.loads(json_text)
            return gallery
        except json.JSONDecodeError as e:
            print("Error parsing galleryImages JSON:", e)
            raise
    else:
        raise RuntimeError("Could not extract galleryImages from image-data.js")

def update_js_file(gallery_images):
    """
    Writes the updated galleryImages array to UPDATED_IMAGE_DATA_JS.
    The file output will be in the format:
       const galleryImages = <JSON dump>;
    """
    with open(UPDATED_IMAGE_DATA_JS, "w", encoding="utf-8") as fp:
        fp.write("const galleryImages = ")
        fp.write(json.dumps(gallery_images, indent=4, ensure_ascii=False))
        fp.write(";\n")
    print(f"Updated image data written to {UPDATED_IMAGE_DATA_JS}")

def generate_alt_text(image_url):
    """
    Call the OpenAI API with the image URL and prompt.
    Returns the generated alt text (string) if successful; otherwise, returns None.
    """
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
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
    try:
        completion = client.chat.completions.create(
            model="grok-2-vision-latest",
            messages=messages,
            temperature=0.01,
        )
        generated_text = completion.choices[0].message.content.strip()
        return generated_text
    except Exception as e:
        print(f"Error generating alt text for {image_url}: {e}")
        return None

def apply_alt_text_from_cache(gallery_images, cache):
    """
    Apply alt text from the cache to gallery images.
    This is useful for integrating with generate_viewers.py
    
    Args:
        gallery_images: List of image objects
        cache: Dictionary with image IDs as keys and alt text as values
        
    Returns:
        Tuple of (number of images updated, number of images skipped)
    """
    updated_count = 0
    skipped_count = 0
    
    for image in gallery_images:
        image_id = image.get("id")
        if not image_id:
            skipped_count += 1
            continue
            
        if image_id in cache:
            generated_text = cache[image_id]
            # Update the image object with generated text
            image["description"] = generated_text
            image["alt_text"] = generated_text
            updated_count += 1
        else:
            skipped_count += 1
            
    return updated_count, skipped_count

def create_alt_text_enriched_js(input_js_file, output_js_file=None):
    """
    Creates a new version of the image-data.js file with alt text from the cache.
    
    Args:
        input_js_file: Path to the input image-data.js file
        output_js_file: Path to the output file (defaults to "image-data.with-alts.js")
        
    Returns:
        Tuple of (total images, updated images, skipped images)
    """
    if output_js_file is None:
        output_js_file = "image-data.with-alts.js"
        
    # Load the cache
    cache = load_cache()
    print(f"Cache loaded with {len(cache)} entries")
    
    # Read and extract galleryImages from input JS file
    with open(input_js_file, "r", encoding="utf-8") as fp:
        js_content = fp.read()
        
    # Backup the input file
    backup_file(input_js_file, f"{input_js_file}.bak")
    
    # Extract the gallery images
    gallery_images = extract_gallery_images(js_content)
    print(f"Found {len(gallery_images)} images in {input_js_file}")
    
    # Apply alt text from cache
    updated_count, skipped_count = apply_alt_text_from_cache(gallery_images, cache)
    
    # Find the contents before and after the galleryImages array
    start_pattern = re.compile(r"(.*?const\s+galleryImages\s*=\s*)\[", re.DOTALL)
    end_pattern = re.compile(r"\];(.*)", re.DOTALL)
    
    start_match = start_pattern.search(js_content)
    end_match = end_pattern.search(js_content)
    
    if start_match and end_match:
        js_prefix = start_match.group(1)
        js_suffix = end_match.group(1)
    else:
        js_prefix = "const galleryImages = "
        js_suffix = ";\n"
    
    # Write the enriched JS file
    with open(output_js_file, "w", encoding="utf-8") as fp:
        fp.write(js_prefix)
        fp.write(json.dumps(gallery_images, indent=4, ensure_ascii=False))
        fp.write("]")
        fp.write(js_suffix)
    
    print(f"Alt text enriched JS file written to {output_js_file}")
    print(f"Total images: {len(gallery_images)}")
    print(f"Images updated with alt text: {updated_count}")
    print(f"Images without alt text: {skipped_count}")
    
    return len(gallery_images), updated_count, skipped_count

# --- Main Interactive Processing Function ---

def process_images():
    # Step 1: Back up the original image-data.js
    backup_file(IMAGE_DATA_JS, BACKUP_IMAGE_DATA_JS)
    confirm = input("Step 1: Backup complete. Press Enter to continue or 'n' to exit: ")
    if confirm.lower() == 'n':
        print("Exiting as per user request.")
        return

    # Step 2: Load the cache file
    cache = load_cache()
    print(f"Cache loaded with {len(cache)} entries.")

    # Step 3: Read and extract galleryImages from image-data.js
    with open(IMAGE_DATA_JS, "r", encoding="utf-8") as fp:
        js_content = fp.read()
    gallery_images = extract_gallery_images(js_content)
    print(f"Found {len(gallery_images)} images in galleryImages.")
    confirm = input("Press Enter to start processing all images or 'n' to exit: ")
    if confirm.lower() == 'n':
        print("Exiting.")
        return

    # Step 4: Process all images without individual confirmations
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"\nProcessing all {len(gallery_images)} images...")
    for idx, image in enumerate(gallery_images):
        image_id = image.get("id")
        if not image_id:
            print(f"Image at index {idx} is missing an 'id' field. Skipping.")
            skipped_count += 1
            continue

        print(f"\n[{idx+1}/{len(gallery_images)}] Processing image ID: {image_id}")
        
        # Check cache first
        if image_id in cache:
            generated_text = cache[image_id]
            print(f"[{image_id}] Using cached alt text.")
            processed_count += 1
        else:
            print(f"[{image_id}] Generating new alt text...")
            generated_text = generate_alt_text(image.get("url"))
            if not generated_text:
                print(f"[{image_id}] Failed to generate alt text. Skipping update for this image.")
                error_count += 1
                continue
                
            # Save to cache
            cache[image_id] = generated_text
            save_cache(cache)
            processed_count += 1
            
            # Sleep briefly to avoid rate limits
            time.sleep(1)

        # Update the image object with generated text
        image["description"] = generated_text
        image["alt_text"] = generated_text
        print(f"[{image_id}] Updated description and alt_text fields.")

    # Summary of processing
    print("\n======= Processing Complete =======")
    print(f"Total images: {len(gallery_images)}")
    print(f"Successfully processed: {processed_count}")
    print(f"Skipped (missing ID): {skipped_count}")
    print(f"Errors during generation: {error_count}")

    # Final confirmation before writing file
    confirm_write = input(f"\nDo you want to write the updated image-data to {UPDATED_IMAGE_DATA_JS}? [Y/n]: ")
    if confirm_write.lower() == 'n':
        print("Exiting without writing updated file.")
        return

    # Write the updated galleryImages to the new JS file
    update_js_file(gallery_images)
    print("Processing complete. Please review the updated file and the cache for observability.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "enrich":
        # Run in enrichment mode
        if len(sys.argv) > 2:
            input_file = sys.argv[2]
        else:
            input_file = IMAGE_DATA_JS
            
        if len(sys.argv) > 3:
            output_file = sys.argv[3]
        else:
            output_file = "image-data.with-alts.js"
            
        create_alt_text_enriched_js(input_file, output_file)
    else:
        # Run in interactive mode
        process_images()