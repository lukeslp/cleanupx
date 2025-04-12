#!/usr/bin/env python3
"""
Ollama Chat Implementation

This module provides a simple interface to the Ollama API for streaming chat responses.
It supports model selection, multi-turn conversations, image analysis, and file handling with streaming responses.
This implementation is set up for a local Ollama instance (http://localhost:11434) by default.
"""
!!! TEMPLATE - EDIT THIS - KEEP THE HARD CODED CREDENTIALS

import requests
import sys
import base64
import json
import mimetypes
from typing import Generator, List, Dict, Optional, Union, Tuple
from datetime import datetime
from PIL import Image
import io
import os

class OllamaChat:
    # Define Ollama endpoints with local as default.
    ENDPOINTS = {
        'local': 'http://localhost:11434',
        'cloud': 'https://ai.assisted.space'
    }
    
    def __init__(self, endpoint_type: str = 'local'):
        """
        Initialize the Ollama client with the specified endpoint.

        Args:
            endpoint_type (str): Type of endpoint to use ('local' or 'cloud').
        """
        if endpoint_type not in self.ENDPOINTS:
            raise ValueError(f"Invalid endpoint type. Must be one of: {', '.join(self.ENDPOINTS.keys())}")
        
        self.endpoint_type = endpoint_type
        self.base_url = self.ENDPOINTS[endpoint_type]
        self.models = self._fetch_models()
        self.chat_history = [{
            "role": "system",
            "content": "You are a helpful AI assistant focused on providing accurate and detailed responses."
        }]
        
        # Define supported file types and image types
        self.supported_image_types = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        self.supported_file_types = {
            'txt', 'md', 'markdown', 'rst', 'csv', 'json', 'yaml', 'yml',
            'py', 'js', 'html', 'css', 'xml', 'sql', 'sh', 'bash',
            'pdf', 'doc', 'docx', 'rtf'
        }
        self.max_file_size = 10 * 1024 * 1024  # 10MB limit

    def _fetch_models(self) -> Dict:
        """
        Fetch available models from the Ollama API.

        Returns:
            Dict: Dictionary of available models with their details.
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            
            models = {}
            for model in response.json().get("models", []):
                model_id = model["name"]
                
                # Determine model capabilities
                capabilities = ["text"]
                if any(x in model_id.lower() for x in ["llava", "bakllava", "vision"]):
                    capabilities.append("vision")
                
                # Determine context length based on model hint from the name
                context_length = 4096  # Default context length
                if "13b" in model_id.lower():
                    context_length = 8192
                elif "70b" in model_id.lower():
                    context_length = 16384
                
                models[model_id] = {
                    "id": model_id,
                    "name": model_id,
                    "context_length": context_length,
                    "description": f"Ollama {model_id} model",
                    "capabilities": capabilities,
                    "capability_count": len(capabilities),
                    "created": datetime.now(),
                    "created_str": datetime.now().strftime("%Y-%m-%d"),
                    "owned_by": "cloud" if self.endpoint_type == "cloud" else "local"
                }
            
            return models
            
        except Exception as e:
            print(f"Error fetching models: {e}", file=sys.stderr)
            return {}

    def list_models(
        self,
        sort_by: str = "id",
        reverse: bool = False,
        page: int = 1,
        page_size: int = 5,
        capability_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Get available Ollama models with sorting and pagination.

        Args:
            sort_by (str): Field to sort by ('id', 'context_length', 'capabilities').
            reverse (bool): Whether to reverse sort order.
            page (int): Page number (1-based).
            page_size (int): Number of items per page.
            capability_filter (Optional[str]): Filter by capability ('text', 'vision').

        Returns:
            List[Dict]: List of available models with their details.
        """
        models_list = [
            model for model in self.models.values()
            if not capability_filter or capability_filter in model["capabilities"]
        ]
        
        if sort_by == "context_length":
            models_list.sort(key=lambda x: x["context_length"], reverse=reverse)
        elif sort_by == "capabilities":
            models_list.sort(key=lambda x: x["capability_count"], reverse=reverse)
        else:  # Default: sort by id
            models_list.sort(key=lambda x: x["id"], reverse=reverse)
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        return models_list[start_idx:end_idx]

    def create_test_image(self, color: str = 'red', size: Tuple[int, int] = (100, 100)) -> Optional[str]:
        """
        Create a test image and return its base64 encoding.

        Args:
            color (str): Color for the test image.
            size (Tuple[int, int]): Size (width, height) of the test image.

        Returns:
            Optional[str]: Base64 encoded PNG image data or None if an error occurs.
        """
        try:
            img = Image.new('RGB', size, color=color)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Error creating test image: {e}", file=sys.stderr)
            return None

    def encode_file(self, file_path: str) -> Optional[Tuple[str, str]]:
        """
        Encode a file to base64 and determine its mime type.

        Args:
            file_path (str): Path to the file.

        Returns:
            Optional[Tuple[str, str]]: Tuple of (base64 encoded data, mime type) or None if encoding fails.
        """
        try:
            if os.path.getsize(file_path) > self.max_file_size:
                raise ValueError(f"File size exceeds {self.max_file_size / 1024 / 1024}MB limit")
            
            ext = os.path.splitext(file_path)[1][1:].lower()
            if ext not in self.supported_file_types and ext not in self.supported_image_types:
                raise ValueError(f"Unsupported file type: {ext}")
            
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            with open(file_path, "rb") as file:
                file_data = file.read()
                return base64.b64encode(file_data).decode('utf-8'), mime_type
        except Exception as e:
            print(f"Error encoding file: {e}", file=sys.stderr)
            return None

    def encode_image(self, image_path: str) -> Optional[str]:
        """
        Encode an image file to base64 with proper preprocessing.

        Args:
            image_path (str): Path to the image file.

        Returns:
            Optional[str]: Base64 encoded image data or None if encoding fails.
        """
        try:
            with Image.open(image_path) as img:
                if img.format.lower() not in self.supported_image_types:
                    raise ValueError(f"Unsupported image format: {img.format}")
                
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                
                if img.size[0] > 2048 or img.size[1] > 2048:
                    ratio = min(2048 / img.size[0], 2048 / img.size[1])
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                img_byte_arr = io.BytesIO()
                save_format = 'JPEG' if img.format.lower() == 'jpeg' else 'PNG'
                img.save(img_byte_arr, format=save_format, quality=95)
                if len(img_byte_arr.getvalue()) > self.max_file_size:
                    raise ValueError(f"Image size exceeds {self.max_file_size / 1024 / 1024}MB limit")
                
                return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Error encoding image: {e}", file=sys.stderr)
            return None

    def format_message_with_attachments(
        self,
        message: str,
        image_data: Optional[str] = None,
        file_data: Optional[Tuple[str, str]] = None,
        is_url: bool = False
    ) -> Union[str, Dict]:
        """
        Format a message with optional image and file attachments.

        Args:
            message (str): The text message.
            image_data (Optional[str]): Base64 encoded image data or URL.
            file_data (Optional[Tuple[str, str]]): Tuple of (base64 data, mime type).
            is_url (bool): Whether the image_data is a URL.

        Returns:
            Union[str, Dict]: The formatted message.
        """
        if not image_data and not file_data:
            return message
        
        content = message
        
        if image_data:
            if is_url:
                content += f"\n[Image]({image_data})"
            else:
                content += f"\n<image>data:image/png;base64,{image_data}</image>"
        
        if file_data:
            base64_data, mime_type = file_data
            try:
                if 'text' in mime_type or mime_type in ('application/json', 'application/xml'):
                    decoded_content = base64.b64decode(base64_data).decode('utf-8', errors='ignore')
                    content += f"\n\nFile content:\n```\n{decoded_content}\n```"
                else:
                    content += f"\n[File attachment: {mime_type}]"
            except Exception as e:
                print(f"Error decoding file content: {e}", file=sys.stderr)
                content += f"\n[File attachment: {mime_type}]"
        
        return content

    def stream_chat_response(
        self,
        message: str,
        model: str,
        temperature: float = 0.7,
        image_data: Optional[str] = None,
        file_data: Optional[Tuple[str, str]] = None,
        is_url: bool = False
    ) -> Generator[str, None, None]:
        """
        Stream a chat response from Ollama.

        Args:
            message (str): The user's input message.
            model (str): The model to use.
            temperature (float): Response temperature (0.0 to 1.0).
            image_data (Optional[str]): Base64 encoded image data or URL.
            file_data (Optional[Tuple[str, str]]): Tuple of (base64 data, mime type).
            is_url (bool): Whether image_data is a URL.

        Yields:
            str: Chunks of the response text as they arrive.
        """
        try:
            content = self.format_message_with_attachments(
                message,
                image_data,
                file_data,
                is_url
            )
            
            if self.endpoint_type == 'cloud':
                endpoint = f"{self.base_url}/api/generate"
                payload = {
                    "model": model,
                    "prompt": content,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "top_p": 0.9
                    }
                }
            else:  # local endpoint
                endpoint = f"{self.base_url}/api/chat"
                payload = {
                    "model": model,
                    "messages": self.chat_history + [{"role": "user", "content": content}],
                    "stream": True,
                    "options": {
                        "temperature": temperature
                    }
                }
            
            response = requests.post(
                endpoint,
                json=payload,
                stream=True,
                timeout=60
            )
            response.raise_for_status()

            accumulated_message = ""
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = line.decode('utf-8')
                        if chunk.startswith('data: '):
                            chunk = chunk[6:]
                        chunk_data = json.loads(chunk)
                        if self.endpoint_type == 'cloud':
                            message_content = chunk_data.get('response', '')
                        else:
                            message_content = chunk_data.get('message', {}).get('content', '')
                        
                        if message_content:
                            yield message_content
                            accumulated_message += message_content
                    except json.JSONDecodeError as e:
                        print(f"Warning: Failed to parse chunk: {e}", file=sys.stderr)
                        continue
                    except Exception as e:
                        print(f"Warning: Error processing chunk: {e}", file=sys.stderr)
                        continue

            if accumulated_message:
                self.chat_history.append({
                    "role": "assistant",
                    "content": accumulated_message
                })

        except requests.exceptions.Timeout:
            error_msg = f"Error: Request timed out when connecting to {self.endpoint_type} Ollama instance"
            print(error_msg, file=sys.stderr)
            yield error_msg
        except requests.exceptions.ConnectionError:
            error_msg = f"Error: Could not connect to {self.endpoint_type} Ollama instance"
            print(error_msg, file=sys.stderr)
            yield error_msg
        except Exception as e:
            error_msg = f"Error in stream_chat_response: {str(e)}"
            print(error_msg, file=sys.stderr)
            yield error_msg

    def clear_conversation(self):
        """Clear the conversation history."""
        self.chat_history = [{
            "role": "system",
            "content": "You are a helpful AI assistant focused on providing accurate and detailed responses."
        }]

def display_models(
    models: List[Dict],
    current_page: int,
    total_pages: int,
    sort_by: str,
    capability_filter: Optional[str] = None
) -> None:
    """Display available models in a formatted way."""
    print(f"\nAvailable Ollama Models (Page {current_page}/{total_pages}):")
    print(f"Sorting by: {sort_by}")
    if capability_filter:
        print(f"Filtering by capability: {capability_filter}")
    print("-" * 50)
    
    for idx, model in enumerate(models, 1):
        print(f"{idx}. {model['name']}")
        print(f"   Context Length: {model['context_length']} tokens")
        print(f"   Description: {model['description']}")
        print(f"   Capabilities: {', '.join(model['capabilities'])}")
        print()

def get_user_input(prompt: str, default: str = None) -> str:
    """Get user input with an optional default value."""
    prompt_str = f"{prompt} [{default}]: " if default else f"{prompt}: "
    response = input(prompt_str).strip()
    return response if response else (default or "")

def main():
    """Main CLI interface."""
    print("\nChoose Ollama endpoint:")
    print("1. Local (http://localhost:11434)")
    print("2. Cloud (https://ai.assisted.space)")
    
    while True:
        choice = get_user_input("Select endpoint", "1")
        if choice == "1":
            endpoint_type = "local"
            break
        elif choice == "2":
            endpoint_type = "cloud"
            break
        else:
            print("Invalid choice. Please select 1 or 2.")
    
    try:
        chat = OllamaChat(endpoint_type)
    except Exception as e:
        print(f"Error initializing {endpoint_type} Ollama instance: {e}")
        sys.exit(1)
    
    print(f"\nConnected to {endpoint_type.title()} Ollama instance at {chat.base_url}")
    
    # Model browsing loop
    page = 1
    page_size = 5
    sort_by = "id"
    capability_filter = None
    
    while True:
        models = chat.list_models(
            sort_by=sort_by,
            page=page,
            page_size=page_size,
            capability_filter=capability_filter
        )
        
        if not models:
            print(f"\nError: No models found on {endpoint_type} instance. Please check your connection and try again.")
            sys.exit(1)
        
        all_models = chat.list_models(
            sort_by=sort_by,
            capability_filter=capability_filter,
            page=1,
            page_size=1000
        )
        total_pages = (len(all_models) + page_size - 1) // page_size
        
        display_models(models, page, total_pages, sort_by, capability_filter)
        
        print("\nOptions:")
        print("1. Select model")
        print("2. Next page")
        print("3. Previous page")
        print("4. Sort by (id/context_length/capabilities)")
        print("5. Filter by capability (text/vision/none)")
        print("6. Change page size")
        print("7. Switch endpoint")
        print("8. Quit")
        
        option = get_user_input("Select option", "1")
        
        if option == "1":
            try:
                selection = int(get_user_input("Select a model number", "1")) - 1
                if 0 <= selection < len(models):
                    selected_model = models[selection]["id"]
                    break
                print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
        elif option == "2" and page < total_pages:
            page += 1
        elif option == "3" and page > 1:
            page -= 1
        elif option == "4":
            sort_by = get_user_input("Sort by (id/context_length/capabilities)", "id")
        elif option == "5":
            cap_choice = get_user_input("Filter by capability (text/vision/none)", "none").lower()
            capability_filter = None if cap_choice == "none" else cap_choice
        elif option == "6":
            try:
                new_size = int(get_user_input("Enter page size", str(page_size)))
                if new_size > 0:
                    page_size = new_size
            except ValueError:
                print("Please enter a valid number.")
        elif option == "7":
            print("\nRestarting to switch endpoint...")
            python = sys.executable
            os.execl(python, python, *sys.argv)
        elif option == "8":
            print("Exiting...")
            sys.exit(0)
        
        print()

    # Conversation loop
    while True:
        supports_images = "vision" in chat.models[selected_model]["capabilities"]
        
        print("\nInput options:")
        if not supports_images:
            print("[Note: Selected model does not support image understanding]")
        
        print("\nAttachment options:")
        print("1. Text only")
        print("2. Test image (colored square)")
        print("3. Load image from file")
        print("4. Image from URL")
        print("5. Load file")
        print("6. Switch endpoint")
        print("7. Quit")
        
        input_choice = get_user_input("Select input option", "1")
        image_data = None
        file_data = None
        is_url = False
        
        if input_choice == "2" and supports_images:
            color = get_user_input("Enter color (e.g., red, blue, green)", "red")
            size_str = get_user_input("Enter size (width,height)", "100,100")
            try:
                width, height = map(int, size_str.split(","))
                image_data = chat.create_test_image(color=color, size=(width, height))
                if not image_data:
                    print("Failed to create test image. Continuing without image...")
            except ValueError:
                print("Invalid size format. Using default 100x100...")
                image_data = chat.create_test_image(color=color)
        elif input_choice == "3" and supports_images:
            file_path = get_user_input("Enter image file path")
            image_data = chat.encode_image(file_path)
            if not image_data:
                print("Failed to load image. Continuing without image...")
        elif input_choice == "4" and supports_images:
            url = get_user_input("Enter image URL")
            if url:
                image_data = url
                is_url = True
        elif input_choice == "5":
            file_path = get_user_input("Enter file path")
            if os.path.exists(file_path):
                file_data = chat.encode_file(file_path)
                if not file_data:
                    print("Failed to load file. Continuing without file...")
            else:
                print("File not found. Continuing without file...")
        elif input_choice == "6":
            print("\nRestarting to switch endpoint...")
            python = sys.executable
            os.execl(python, python, *sys.argv)
        elif input_choice == "7":
            print("Exiting...")
            sys.exit(0)
        
        default_prompt = "What do you see in this image?" if image_data else \
                         "Please analyze this file." if file_data else "Hello! How can I help you today?"
        message = get_user_input("Enter your message", default_prompt)
        
        print("\nStreaming response:")
        print("-" * 50)
        
        try:
            for chunk in chat.stream_chat_response(
                message,
                selected_model,
                image_data=image_data,
                file_data=file_data,
                is_url=is_url
            ):
                if chunk:
                    print(chunk, end='', flush=True)
            print("\n" + "-" * 50)
        except KeyboardInterrupt:
            print("\nResponse streaming interrupted by user.")
            print("-" * 50)
        
        if get_user_input("\nContinue conversation? (y/n)", "y").lower() != 'y':
            print("\nClearing conversation history and exiting...")
            chat.clear_conversation()
            break
        print("\nContinuing conversation...\n")

if __name__ == "__main__":
    main()