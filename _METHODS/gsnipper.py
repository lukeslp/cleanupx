#!/usr/bin/env python3

import os
import sys
import argparse
import shutil
import time
import base64
import json
from dotenv import load_dotenv
from PIL import Image
import io
from typing import List, Dict, Any, Optional, Union
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

# Global client variable
gemini_client = None

class GeminiAPI:
    """
    A Python client for the Google Gemini API using the official Google Generative AI library.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini API client.
        
        Args:
            api_key: Your Gemini API key. If not provided, will look for GEMINI_API_KEY environment variable.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided either directly or via GEMINI_API_KEY environment variable")
        
        # Configure the API
        genai.configure(api_key=self.api_key)
        
        # Initialize models
        self.text_model = genai.GenerativeModel('gemini-1.5-pro')
        self.vision_model = genai.GenerativeModel('gemini-1.5-vision')
    
    def _prepare_image_part(self, image: Union[str, Image.Image, bytes]) -> "genai.types.Image":
        """
        Prepare image part for the API request.
        
        Args:
            image: Can be a file path, PIL Image, or bytes
            
        Returns:
            Image object for the API
        """
        if isinstance(image, str):
            # Assume it's a file path
            return genai.types.Image.load_from_file(image)
        elif isinstance(image, Image.Image):
            # PIL Image
            buffer = io.BytesIO()
            image.save(buffer, format=image.format or "PNG")
            return genai.types.Image.from_bytes(buffer.getvalue())
        elif isinstance(image, bytes):
            # Raw bytes
            return genai.types.Image.from_bytes(image)
        else:
            raise ValueError("Image must be a file path, PIL Image, or bytes")
    
    def generate_text(self, 
                     prompt: str, 
                     model: str = "gemini-1.5-pro",
                     temperature: float = 0.7,
                     max_tokens: Optional[int] = None,
                     top_p: Optional[float] = None,
                     top_k: Optional[int] = None) -> str:
        """
        Generate text using the Gemini model.
        
        Args:
            prompt: Text prompt
            model: Model to use (default: gemini-1.5-pro)
            temperature: Sampling temperature (default: 0.7)
            max_tokens: Maximum number of tokens to generate
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
            
        Returns:
            Generated text
        """
        try:
            # Configure generation parameters
            generation_config = {
                "temperature": temperature,
            }
            
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            if top_p:
                generation_config["top_p"] = top_p
            if top_k:
                generation_config["top_k"] = top_k
            
            # Generate content
            response = self.text_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return response.text
        except Exception as e:
            raise Exception(f"Failed to generate text: {e}")
    
    def generate_with_images(self, 
                           prompt: str, 
                           images: List[Union[str, Image.Image, bytes]],
                           model: str = "gemini-1.5-vision",
                           temperature: float = 0.7,
                           max_tokens: Optional[int] = None) -> str:
        """
        Generate text based on images and a prompt.
        
        Args:
            prompt: Text prompt
            images: List of images (file paths, PIL Images, or bytes)
            model: Model to use (default: gemini-1.5-vision)
            temperature: Sampling temperature (default: 0.7)
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Generated text
        """
        try:
            # Prepare images
            prepared_images = [self._prepare_image_part(image) for image in images]
            
            # Configure generation parameters
            generation_config = {
                "temperature": temperature,
            }
            
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            
            # Generate content
            response = self.vision_model.generate_content(
                [prompt] + prepared_images,
                generation_config=generation_config
            )
            
            return response.text
        except Exception as e:
            raise Exception(f"Failed to generate text with images: {e}")

def initialize_client():
    """Initialize the Gemini API client."""
    global gemini_client
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set in .env file.", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Create the Gemini API client
        gemini_client = GeminiAPI(api_key)
        
        # Test with a simple query
        test_response = gemini_client.generate_text("Hello", temperature=0.1)
        
        if test_response:
            print(f"Successfully connected to Gemini API.")
            return True
        else:
            print("Error: No response from Gemini API.", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error initializing Gemini API: {e}", file=sys.stderr)
        sys.exit(1)

def call_gemini(prompt, temperature=0.3):
    """Call Gemini API with a prompt."""
    global gemini_client
    
    # Initialize the client if not already done
    if not gemini_client:
        initialize_client()
    
    try:
        # Generate content
        response = gemini_client.generate_text(prompt, temperature=temperature)
        
        # Return the generated text
        return response
    except Exception as e:
        print(f"Error calling Gemini API: {e}", file=sys.stderr)
        return f"Error: {e}"

def analyze_image(image_path, prompt, verbose=False):
    """Analyze an image using Gemini Vision."""
    global gemini_client
    
    if verbose:
        print(f"Analyzing image: {image_path} with prompt: {prompt}")
    
    # Initialize the client if not already done
    if not gemini_client:
        initialize_client()
    
    try:
        # Generate content with the image and prompt
        response = gemini_client.generate_with_images(prompt, [image_path])
        
        return response
    except Exception as e:
        print(f"Error analyzing image: {e}", file=sys.stderr)
        return f"Error: {e}"

def generate_text_with_streaming(prompt, verbose=False):
    """Generate text with streaming response."""
    global gemini_client
    
    if verbose:
        print(f"Generating text with streaming for prompt: {prompt}")
    
    # Initialize the client if not already done
    if not gemini_client:
        initialize_client()
    
    try:
        # For streaming, we'll use the regular generate_text but print chunks of the response
        # Note: true streaming requires a different implementation that's not included in this simplified client
        response = gemini_client.generate_text(prompt, temperature=0.7)
        
        # Simulate streaming by printing chunks of the response
        chunk_size = max(len(response) // 10, 1)  # At least 1 character
        full_response = []
        
        for i in range(0, len(response), chunk_size):
            chunk = response[i:i+chunk_size]
            print(chunk, end="", flush=True)
            time.sleep(0.1)  # Small delay to simulate streaming
            full_response.append(chunk)
        
        return "".join(full_response)
    except Exception as e:
        print(f"Error generating text with streaming: {e}", file=sys.stderr)
        return f"Error: {e}"

def read_file(file_path):
    """Read content from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        sys.exit(1)

def split_into_chunks(text, max_chunk_size=6000):
    """Split text into chunks by lines."""
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_size = 0
    for line in lines:
        line_size = len(line)
        if current_size + line_size > max_chunk_size and current_chunk:
            chunks.append('\n'.join(current_chunk))
            current_chunk = []
            current_size = 0
        current_chunk.append(line)
        current_size += line_size
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    return chunks

def explain_code(code, verbose=False):
    """Generate explanation for a code snippet."""
    global gemini_client
    
    # Initialize the client if not already done
    if not gemini_client:
        initialize_client()
    
    if verbose:
        print("Sending code to Gemini for explanation...")
        print(f"Code length: {len(code)} characters")
    
    try:
        # Prepare the prompt with the code
        prompt = f"""
You are a helpful coding assistant specializing in explaining code.
When presented with code, provide clear, detailed explanations that include:
1. Overall purpose of the code
2. Key functions/classes and their roles
3. Flow of execution
4. Important design patterns or techniques used
5. Potential issues or improvements

Here is the code to explain:

```
{code}
```

Please provide a thorough yet concise explanation of this code.
"""
        
        # Generate content
        response = gemini_client.generate_text(prompt, temperature=0.3)
        
        return response
    except Exception as e:
        print(f"Error explaining code: {e}", file=sys.stderr)
        return f"Error: {e}"

def explain_file(file_path, verbose=False, output=None):
    """Generate explanation for a code file."""
    global gemini_client
    
    if verbose:
        print(f"Reading file: {file_path}")
    
    code = read_file(file_path)
    
    if len(code) > 6000:
        if verbose:
            print(f"Code is large ({len(code)} characters). Splitting into chunks for analysis.")
        
        chunks = split_into_chunks(code)
        explanations = []
        
        for i, chunk in enumerate(chunks):
            if verbose:
                print(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
            
            exp = explain_code(chunk, verbose)
            explanations.append(exp)
        
        # Initialize the client if not already done
        if not gemini_client:
            initialize_client()
        
        try:
            # Prepare the prompt for synthesizing explanations
            combined_text = "\n\n===== CHUNK DIVIDER =====\n\n".join(explanations)
            synthesis_prompt = f"""
You are a coding expert who can synthesize multiple code explanations into a single cohesive explanation.
The following text contains explanations of different chunks of the same code file: {file_path}
Please synthesize these explanations into one comprehensive explanation:

{combined_text}

Eliminate redundancies while retaining the most important details.
"""
            
            if verbose:
                print("Synthesizing chunk explanations...")
            
            # Generate content
            response = gemini_client.generate_text(synthesis_prompt, temperature=0.3)
            
            final_explanation = response
        except Exception as e:
            print(f"Error synthesizing explanations: {e}", file=sys.stderr)
            final_explanation = "Error synthesizing explanations. Here are the individual chunk explanations:\n\n" + combined_text
    else:
        final_explanation = explain_code(code, verbose)
    
    file_name = os.path.basename(file_path)
    formatted_output = f"# Code Explanation: {file_name}\n\n{final_explanation}"
    
    if output:
        try:
            with open(output, "w", encoding="utf-8") as f:
                f.write(formatted_output)
            if verbose:
                print(f"Explanation written to {output}")
        except Exception as e:
            print(f"Error writing output: {e}", file=sys.stderr)
    else:
        print("\n" + "=" * 80)
        print(f"CODE EXPLANATION: {file_name}")
        print("=" * 80 + "\n")
        print(formatted_output)
    
    return formatted_output

def process_file_for_snippet(file_path, mode, verbose=False):
    """Process a file to extract code snippets."""
    global gemini_client
    
    # Initialize the client if not already done
    if not gemini_client:
        initialize_client()
    
    content = read_file(file_path)
    
    if verbose:
        print(f"Processing file for snippet extraction: {file_path}")
    
    chunks = [content] if len(content) <= 6000 else split_into_chunks(content)
    responses = []
    
    try:
        for i, chunk in enumerate(chunks):
            if verbose:
                print(f"Sending chunk {i+1}/{len(chunks)} to Gemini for snippet extraction...")
            
            if mode == "code":
                prompt = f"""
You are a helpful coding assistant. Extract the most important and unique code snippets
or documentation segments from the following code. Return your answer formatted as follows:

Best Version:
<best snippet>

Alternatives:
<alternative snippet(s)>

Code:
{chunk}
"""
            else:
                prompt = f"""
You are a helpful coding assistant. Evaluate the following code snippet for its uniqueness and importance.
If it is significant, return it as the Best Version; otherwise, indicate that it is not significant.
Format your answer as follows (if significant):

Best Version:
<best snippet>

Alternatives:
<alternative snippet(s)>

Snippet:
{chunk}
"""
            
            try:
                # Generate content
                response = gemini_client.generate_text(prompt, temperature=0.3)
                responses.append(response)
            except Exception as e:
                print(f"Error processing chunk {i+1}: {e}", file=sys.stderr)
                responses.append(f"Error processing chunk: {e}")
        
        if len(responses) > 1:
            combined_responses = "\n\n===== CHUNK RESPONSE DIVIDER =====\n\n".join(responses)
            synthesis_prompt = f"""
You are a coding expert who can synthesize multiple extracted snippet responses into one cohesive output.
Combine the following responses into a unified result, ensuring only the most important and unique snippets are retained,
and preserve the formatting with 'Best Version:' and 'Alternatives:' as in the individual responses.

Responses:
{combined_responses}
"""
            
            try:
                # Generate content
                response = gemini_client.generate_text(synthesis_prompt, temperature=0.3)
                final_response = response
            except Exception as e:
                print(f"Error synthesizing responses: {e}", file=sys.stderr)
                final_response = combined_responses
        else:
            final_response = responses[0] if responses else ""
        
        # Extract the best and alternatives from the response
        best = ""
        alternatives = ""
        
        if "Best Version:" in final_response:
            parts = final_response.split("Best Version:")
            remainder = parts[1]
            
            if "Alternatives:" in remainder:
                best, alt_part = remainder.split("Alternatives:", 1)
                best = best.strip()
                alternatives = alt_part.strip()
            else:
                best = remainder.strip()
        else:
            best = final_response.strip()
        
        return {"best": best, "alternatives": alternatives}
    
    except Exception as e:
        print(f"Error in process_file_for_snippet: {e}", file=sys.stderr)
        return {"best": f"Error: {e}", "alternatives": ""}

def synthesize_overall_snippets(best_snippets, verbose=False):
    """Synthesize snippets from multiple files into one document."""
    global gemini_client
    
    # Initialize the client if not already done
    if not gemini_client:
        initialize_client()
    
    combined_text = ""
    for file_name, snippet in best_snippets.items():
        combined_text += f"\n\nFile: {file_name}\nBest Version:\n{snippet}\n"
    
    try:
        # Prepare the prompt for synthesizing snippets
        synthesis_prompt = f"""
You are an expert coding assistant. Combine the following best code/documentation snippets from various files
into a cohesive final document that retains only the most important and unique segments.
Eliminate redundancies and format the output clearly.

Snippets:{combined_text}
"""
        
        # Generate content
        response = gemini_client.generate_text(synthesis_prompt, temperature=0.3)
        
        return response
    except Exception as e:
        print(f"Error synthesizing overall snippets: {e}", file=sys.stderr)
        return combined_text

def generate_alt_text(file_path, verbose=False):
    """Generate alternative text for multimedia files."""
    global gemini_client
    
    # Initialize the client if not already done
    if not gemini_client:
        initialize_client()
    
    file_name = os.path.basename(file_path)
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    image_types = [".jpg", ".jpeg", ".png", ".gif"]
    video_types = [".mp4", ".mov", ".avi"]
    
    if ext in image_types:
        if verbose:
            print(f"Using Gemini vision API to analyze image: {file_path}")
        
        prompt = f"Generate a detailed, descriptive alternative text for this image that would be suitable for accessibility purposes. The filename is: {file_name}"
        return analyze_image(file_path, prompt, verbose)
    elif ext in video_types:
        try:
            # Prepare the prompt for video metadata
            prompt = f"""
You are a visual assistant that specializes in creating alternative text descriptions for multimedia content.
Given the metadata about a multimedia file, provide a concise, clear, and descriptive alternative text suitable for accessibility purposes.

File name: {file_name}
File extension: {ext}

Please generate a concise alternative text description for this file.
"""
            
            if verbose:
                print(f"Generating alt text for video {file_path} using metadata...")
            
            # Generate content
            response = gemini_client.generate_text(prompt, temperature=0.3)
            
            return response
        except Exception as e:
            print(f"Error generating alt text: {e}", file=sys.stderr)
            return f"Error: {e}"
    else:
        print(f"File {file_path} is not a supported multimedia type for alt text.", file=sys.stderr)
        return None

def process_directory(directory, mode, verbose=False, output_file="final_combined_snippets.md", archive_dir=None):
    """Process all files in a directory."""
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory.", file=sys.stderr)
        sys.exit(1)
    
    # Initialize the client once at the beginning
    if gemini_client:
        initialize_client()
    
    if mode == "alt":
        # Process multimedia files for alt text
        alt_texts = {}
        multimedia_types = [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov", ".avi"]
        
        for file in os.listdir(directory):
            if file.startswith('.') or file == "gsnipper.py":
                continue
            
            file_path = os.path.join(directory, file)
            
            if os.path.isfile(file_path):
                ext = os.path.splitext(file)[1].lower()
                
                if ext in multimedia_types:
                    if verbose:
                        print(f"Processing multimedia file for alt text: {file}")
                    
                    alt_text = generate_alt_text(file_path, verbose)
                    
                    if alt_text:
                        alt_texts[file] = alt_text
        
        if not alt_texts:
            print("No multimedia alt texts were generated.", file=sys.stderr)
            sys.exit(1)
        
        final_document = "# Alternative Text Descriptions\n\n"
        
        for filename, alt in alt_texts.items():
            final_document += f"## {filename}\n\n{alt}\n\n"
        
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(final_document)
            
            if verbose:
                print(f"Final alt text markdown written to {output_file}")
        except Exception as e:
            print(f"Error writing final output: {e}", file=sys.stderr)
        
        return final_document
    else:
        # Process code files
        if not archive_dir:
            archive_dir = os.path.join(directory, "archive")
        
        os.makedirs(archive_dir, exist_ok=True)
        
        best_snippets = {}
        alternatives_dict = {}
        
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f)) and not f.startswith('.') and f != "gsnipper.py"]
        
        # Process files in batches
        for i in range(0, len(files), 25):
            batch_files = files[i:i+25]
            batch_snippets = {}
            
            for file in batch_files:
                file_path = os.path.join(directory, file)
                
                if verbose:
                    print(f"Reading file: {file}")
                
                result = process_file_for_snippet(file_path, mode, verbose)
                
                batch_snippets[file] = result.get("best", "")
                alt_text = result.get("alternatives", "")
                
                if alt_text:
                    alternatives_dict[file] = alt_text
            
            if verbose:
                print("Synthesizing batch best snippets...")
            
            batch_document = synthesize_overall_snippets(batch_snippets, verbose)
            
            for file, snippet in batch_snippets.items():
                best_snippets[file] = snippet
            
            try:
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(batch_document)
                
                if verbose:
                    print(f"Batch document appended to {output_file}")
            except Exception as e:
                print(f"Error writing batch output: {e}", file=sys.stderr)
        
        if verbose:
            print("Synthesizing overall best snippets from all batches...")
        
        final_document = synthesize_overall_snippets(best_snippets, verbose)
        
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                if mode in ["explain"]:
                    f.write("# Code Explanation\n\n")
                else:
                    f.write("# Final Combined Snippets\n\n")
                
                f.write(final_document)
            
            if verbose:
                print(f"Final combined document written to {output_file}")
        except Exception as e:
            print(f"Error writing final output: {e}", file=sys.stderr)
        
        for filename, alt_text in alternatives_dict.items():
            archive_file = os.path.join(archive_dir, f"{filename}_alternatives.md")
            
            try:
                with open(archive_file, "w", encoding="utf-8") as f:
                    f.write(f"# Alternatives for {filename}\n\n")
                    f.write(alt_text)
                
                if verbose:
                    print(f"Archived alternative snippets for {filename} in {archive_file}")
            except Exception as e:
                print(f"Error writing archive file for {filename}: {e}", file=sys.stderr)
        
        return final_document

def interactive_cli():
    """Run the interactive CLI mode."""
    print("\nWelcome to Gemini Snipper Interactive CLI!")
    print("Make sure your GEMINI_API_KEY environment variable is set in your .env file.")
    
    # Initialize the client once at the beginning
    if gemini_client:
        initialize_client()
    
    while True:
        print("\nPlease choose an option:")
        print("  1. Explain a single code file")
        print("  2. Process a directory of code files / snippets")
        print("  3. Generate alternative text for a multimedia file")
        print("  4. Process a directory of multimedia files for alt text")
        print("  5. Interactive chat with streaming responses")
        print("  6. Exit")
        
        choice = input("Enter your choice (1/2/3/4/5/6): ").strip()
        
        if choice == "1":
            file_path = input("Enter the full path to the code file: ").strip()
            verbose_input = input("Enable verbose output? (y/n): ").strip().lower()
            verbose = verbose_input == "y"
            output = input("Enter an output file path (or leave blank to print to terminal): ").strip()
            output = output if output else None
            explain_file(file_path, verbose, output)
        
        elif choice == "2":
            directory = input("Enter the full path to the directory of code files: ").strip()
            mode = input("Enter the mode ('explain' for explanation, 'code' for code snippets, 'snippet' for snippet evaluation): ").strip().lower()
            verbose_input = input("Enable verbose output? (y/n): ").strip().lower()
            verbose = verbose_input == "y"
            output_file = input("Enter an output file name for the final combined snippets (default: final_combined_snippets.md): ").strip()
            if not output_file:
                output_file = "final_combined_snippets.md"
            archive_dir = input("Enter a directory to archive alternative snippets (or leave blank to use 'archive' inside the input directory): ").strip()
            if not archive_dir:
                archive_dir = None
            process_directory(directory, mode, verbose, output_file, archive_dir)
        
        elif choice == "3":
            file_path = input("Enter the full path to the multimedia file: ").strip()
            verbose_input = input("Enable verbose output? (y/n): ").strip().lower()
            verbose = verbose_input == "y"
            output_file = input("Enter an output file name for the alt text (default: alt_text.md): ").strip()
            if not output_file:
                output_file = "alt_text.md"
            alt_text = generate_alt_text(file_path, verbose)
            if alt_text:
                formatted_output = f"## {os.path.basename(file_path)}\n\n{alt_text}\n"
                try:
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(formatted_output)
                    print(f"Alt text written to {output_file}")
                except Exception as e:
                    print(f"Error writing alt text output: {e}", file=sys.stderr)
                else:
                    print(formatted_output)
        
        elif choice == "4":
            directory = input("Enter the full path to the directory of multimedia files: ").strip()
            verbose_input = input("Enable verbose output? (y/n): ").strip().lower()
            verbose = verbose_input == "y"
            output_file = input("Enter an output file name for the final alt text markdown (default: alt_text.md): ").strip()
            if not output_file:
                output_file = "alt_text.md"
            process_directory(directory, "alt", verbose, output_file)
        
        elif choice == "5":
            print("\nInteractive Chat with Streaming Responses")
            print("Type 'exit' to return to the main menu.")
            while True:
                user_input = input("\nYou: ").strip()
                if user_input.lower() == 'exit':
                    break
                print("\nGemini: ", end="")
                generate_text_with_streaming(user_input, verbose=False)
                print()
        
        elif choice == "6":
            print("Exiting Gemini Snipper. Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Gemini Snipper Interactive CLI and Batch Processor\nIf no arguments are provided, the interactive CLI is launched."
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--file", help="Path to a file to process (code or multimedia)")
    group.add_argument("--directory", help="Path to a directory to process")
    
    parser.add_argument("--mode", choices=["explain", "code", "snippet", "alt"], default="explain",
                         help="Operation mode. Use 'explain' for code explanation, 'code' or 'snippet' for code snippet extraction, or 'alt' for multimedia alt text generation.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--archive", "-a", help="Archive directory for alternative snippets (used with code modes)")
    
    args = parser.parse_args()
    
    # Initialize the client once at the beginning
    if gemini_client:
        initialize_client()
    
    if not args.file and not args.directory:
        interactive_cli()
    elif args.file:
        if args.mode == "alt":
            alt_text = generate_alt_text(args.file, args.verbose)
            if args.output:
                try:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(f"## {os.path.basename(args.file)}\n\n{alt_text}\n")
                    print(f"Alt text written to {args.output}")
                except Exception as e:
                    print(f"Error writing output: {e}", file=sys.stderr)
            else:
                print(alt_text)
        elif args.mode == "explain":
            explain_file(args.file, args.verbose, args.output)
        elif args.mode in ["code", "snippet"]:
            result = process_file_for_snippet(args.file, args.mode, args.verbose)
            output_text = f"Best Version:\n{result.get('best', '')}\n\nAlternatives:\n{result.get('alternatives', '')}"
            if args.output:
                try:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(output_text)
                    print(f"Output written to {args.output}")
                except Exception as e:
                    print(f"Error writing output: {e}", file=sys.stderr)
            else:
                print(output_text)
    elif args.directory:
        process_directory(args.directory, args.mode, args.verbose, args.output, args.archive)
    else:
        print("Invalid combination of arguments. Use --help for usage details.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()