from typing import Dict, Optional, List, Union
import requests
import json
import os
from datetime import datetime

class LLMTools:
    """Collection of utility tools for LLM interactions."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("API_KEY")
        
    async def fetch_citation(self, doi: str) -> Dict:
        """
        Fetch citation data from CrossRef API.
        Referenced from from_markdown.js lines 96-105
        """
        try:
            response = await requests.get(f"https://api.crossref.org/works/{doi}")
            return response.json()["message"]
        except Exception as e:
            print(f"Citation fetch failed: {e}")
            return None

    def process_file_embed(self, file: Dict, file_url: str) -> str:
        """
        Generate appropriate embed HTML based on file type.
        Referenced from from_utils.js lines 1388-1415
        """
        file_ext = file["name"].split(".")[-1].lower()
        
        # Code files
        code_extensions = {
            'js', 'jsx', 'ts', 'tsx', 'py', 'java', 'cpp', 'c', 'cs', 
            'php', 'rb', 'go', 'rs', 'swift', 'kt', 'dart', 'sql',
            'html', 'css', 'scss', 'less', 'json', 'xml', 'yaml', 'yml', 'toml'
        }
        
        if file_ext in code_extensions:
            return f"```{file_ext}\n{file['name']}\n```"
            
        # Markdown files
        if file_ext in ['md', 'markdown']:
            return f"[View Markdown: {file['name']}]({file_url})"
            
        # Text files
        if file["type"] == "text/plain" or file_ext in ['txt', 'log', 'csv', 'tsv']:
            return f'<div class="text-embed-container" data-file-url="{file_url}">\n' \
                   f'    <pre class="text-content">Loading text content...</pre>\n' \
                   f'</div>'
                   
        # Default fallback
        return f'<div class="file-embed-container">\n' \
               f'    <a href="{file_url}" target="_blank" rel="noopener noreferrer">\n' \
               f'        <i class="fas fa-file"></i> {file["name"]}\n' \
               f'    </a>\n' \
               f'</div>'

    def get_supported_mime_types(self) -> List[str]:
        """
        Get list of supported MIME types for file processing.
        Referenced from from_simple_alt_text.js lines 140-185
        """
        return [
            # Image Formats
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
            'image/webp', 'image/heic', 'image/heif', 'image/avif',
            'image/tiff', 'image/bmp', 'image/x-icon',
            'image/vnd.microsoft.icon', 'image/svg+xml',
            'image/vnd.adobe.photoshop', 'image/x-adobe-dng',
            'image/x-canon-cr2', 'image/x-nikon-nef',
            'image/x-sony-arw', 'image/x-fuji-raf',
            'image/x-olympus-orf', 'image/x-panasonic-rw2',
            'image/x-rgb', 'image/x-portable-pixmap',
            'image/x-portable-graymap', 'image/x-portable-bitmap',
            # Video Formats
            'video/mp4', 'video/quicktime', 'video/webm',
            'video/x-msvideo', 'video/x-flv', 'video/x-ms-wmv',
            'video/x-matroska', 'video/3gpp', 'video/x-m4v',
            'video/x-ms-asf', 'video/x-mpegURL', 'video/x-ms-vob',
            'video/x-ms-tmp', 'video/x-mpeg', 'video/mp2t',
            'application/octet-stream'
        ]

    def initialize_markdown(self, html: bool = True, breaks: bool = True) -> Dict:
        """
        Initialize markdown parser configuration.
        Referenced from from_markdown.js lines 2-43
        """
        return {
            "html": html,
            "breaks": breaks,
            "linkify": True,
            "typographer": True,
            "highlight": True,
            "plugins": [
                "markdownit-task-lists",
                "markdownit-footnote",
                "markdownit-sub",
                "markdownit-sup",
                "markdownit-deflist",
                "markdownit-abbr",
                "markdownit-mark",
                "markdownit-multimd-table",
                "markdownit-katex"
            ]
        } 