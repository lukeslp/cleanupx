#!/usr/bin/env python3
"""
Configuration settings for the CleanupX file organization tool.
"""

import os
from pathlib import Path
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# API Configuration
XAI_API_KEY = os.getenv('XAI_API_KEY')
XAI_MODEL_TEXT = os.getenv('XAI_MODEL_TEXT', 'grok-3-mini-latest')
XAI_MODEL_VISION = os.getenv('XAI_MODEL_VISION', 'grok-2-vision-latest')

# Validate API configuration
if not XAI_API_KEY:
    logger.warning("XAI_API_KEY not found in environment variables. API calls will fail.")

# File type constants
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.heif', '.ico'}
TEXT_EXTENSIONS = {'.txt', '.md', '.markdown', '.rst', '.text', '.log', '.csv', '.tsv', '.json', '.xml', '.yaml', '.yml', '.html', '.htm', '.py', '.db', '.sh', '.rtf', '.ics', '.icsv', '.icsx'}
MEDIA_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.m4v'}
DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.doc', '.ppt', '.pptx', 'xlsx', '.xls'}
ARCHIVE_EXTENSIONS = {'.zip', '.tar', '.tgz', '.tar.gz', '.rar', '.gz', '.pkg'}

# Cache and rename log files
CACHE_FILE = "generated_alts.json"
RENAME_LOG_FILE = "rename_log.json"

# Protected files that should not be processed
PROTECTED_PATTERNS = [
    "PROJECT_PLAN.md",
    ".git*",
    "*.exe",
    "*.dll",
    "requirements.txt",
    "package.json",
    "setup.py",
    "Makefile",
    "Dockerfile",
    "*.pyc",
    "__pycache__*",
    ".env*",
    "*.env",
    ".venv*",
    "venv*",
    "*.ini",
    "*.cfg",
    "*.config",
    "*.lock",
    "*.sh",
    "*.bat",
    "*.cmd",
    "*.ps1",
    "LICENSE*",
    "README*",
    ".cleanupx*",
    ".dir_summary.json",
    ".cleanupx-citations"
]

# Alias for backward compatibility
IGNORE_PATTERNS = PROTECTED_PATTERNS

# Function schemas for API calls
IMAGE_FUNCTION_SCHEMA = {
    "name": "analyze_image",
    "description": "Analyze an image file and return a short title and a detailed alt_text for accessibility.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "A short, descriptive title for the image."
            },
            "alt_text": {
                "type": "string",
                "description": "Provide a comprehensive, long-form description of the image content, detailing every visible element, color nuance, texture, embedded text, spatial arrangement, and contextual cues—as though explaining the scene to an engineer who has lost their vision and needs exhaustive detail for complete understanding. Search the internet for context on the image to enrich your description"
            },
            "suggested_filename": {
                "type": "string",
                "description": "A succinct, descriptive filename (without extension) using underscores."
            }
        },
        "required": ["title", "alt_text", "suggested_filename"]
    }
}

# Prompt constants for file analysis
FILE_IMAGE_PROMPT = """Analyze this image carefully and provide:
1. A clear, concise title capturing the main subject.
2. A detailed description covering all visible elements, colors, text, and context.
3. A suggested filename that is descriptive, consisting of 7-9 words, all lowercase with underscores."""

FILE_TEXT_PROMPT = """Analyze this {suffix} file and provide structured information.
File name: {name}
File type: {suffix}

Content:
```
{content}
```

Based on the above content, please provide:
1. A detailed description of what this document contains and its purpose.
2. The type of document (e.g., code, notes, configuration, data).
3. A suggested filename that reflects the content (7-9 words, lowercase with underscores, no extension)."""

FILE_DOCUMENT_PROMPT = """Analyze this document and provide structured information.
File name: {name}
File type: {suffix}

Content:
```
{text_content}
```

Provide:
1. A detailed description of the document's content.
2. The type of document (e.g., report, article, notes).
3. A suggested filename (7-9 words, lowercase with underscores, no extension)."""

# Duplicate prompt system for archives (initially the same as file prompts)
ARCHIVE_IMAGE_PROMPT = FILE_IMAGE_PROMPT
ARCHIVE_TEXT_PROMPT = FILE_TEXT_PROMPT
ARCHIVE_DOCUMENT_PROMPT = FILE_DOCUMENT_PROMPT

DOCUMENT_FUNCTION_SCHEMA = {
    "name": "analyze_document",
    "description": "Analyze a document and return a detailed content description, a document type, and a suggested filename.",
    "parameters": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "A detailed description of the file content."
            },
            "document_type": {
                "type": "string",
                "description": "A classification of the document (e.g., report, article, notes)."
            },
            "suggested_filename": {
                "type": "string",
                "description": "A descriptive filename (without extension, lowercase with underscores)."
            }
        },
        "required": ["description", "document_type", "suggested_filename"]
    }
}

# Add new Archive function schema
ARCHIVE_FUNCTION_SCHEMA = {
    "name": "analyze_archive",
    "description": "Analyze an archive file and return a suggested filename and a markdown summary of its contents.",
    "parameters": {
        "type": "object",
        "properties": {
            "suggested_filename": {
                "type": "string",
                "description": "A descriptive filename (7-9 words, lowercase with underscores, no extension) based on the archive contents."
            },
            "summary_md": {
                "type": "string",
                "description": "A markdown formatted summary of the archive contents."
            }
        },
        "required": ["suggested_filename", "summary_md"]
    }
}

# Add a schema for directory analysis
DIRECTORY_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": "Brief description of the directory's contents and purpose."
        },
        "topics": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of topics or subjects related to this directory's content."
        },
        "current_organization_scheme": {
            "type": "string",
            "description": "Description of how the directory is currently organized."
        },
        "organization_suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Type of suggestion (e.g., 'create_subdirectory', 'rename_files', etc.)."
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the suggestion."
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "normal", "low"],
                        "description": "Priority of the suggestion."
                    }
                },
                "required": ["type", "reason"]
            },
            "description": "Suggestions for improving the organization of this directory."
        }
    },
    "required": ["description", "topics", "organization_suggestions"]
}

# Code analysis configuration
CODE_FUNCTION_SCHEMA = {
    "name": "analyze_code",
    "description": "Analyze code content and provide structured information about its purpose, structure, and components.",
    "parameters": {
        "type": "object",
        "properties": {
            "code_type": {
                "type": "string",
                "description": "Type of code (e.g., Class, Function, Module, Script)"
            },
            "name": {
                "type": "string",
                "description": "Name of the code component (class name, function name, etc.)"
            },
            "description": {
                "type": "string",
                "description": "Detailed description of what the code does and its purpose"
            },
            "dependencies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of dependencies or imports used by this code"
            },
            "complexity": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Estimated complexity of the code"
            }
        },
        "required": ["code_type", "name", "description"]
    }
}

FILE_CODE_PROMPT = """Analyze this code file and provide structured information.
File name: {name}
File type: {suffix}

Content:
```
{content}
```

Based on the above code, please provide:
1. The type of code (Class, Function, Module, Script)
2. The name of the main component
3. A detailed description of what the code does and its purpose
4. Any dependencies or imports used
5. An estimate of the code's complexity (low, medium, high)"""
