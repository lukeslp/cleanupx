"""
Configuration settings for CleanupX.
"""

import os
from pathlib import Path
from typing import Set

# API Keys and Authentication
XAI_API_KEY = "xai-8zAk5VIaL3Vxpu3fO3r2aiWqqeVAZ173X04VK2R1m425uYpWOIOQJM3puq1Q38xJ2sHfbq3mX4PBxJXC"

# File type constants
IMAGE_EXTENSIONS: Set[str] = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.heif', '.ico'}
TEXT_EXTENSIONS: Set[str] = {'.txt', '.md', '.markdown', '.rst', '.text', '.log', '.csv', '.tsv', '.json', '.xml', '.yaml', '.yml', '.html', '.htm', '.py', '.db', '.sh', '.rtf', '.ics', '.icsv', '.icsx'}
MEDIA_EXTENSIONS: Set[str] = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.m4v'}
DOCUMENT_EXTENSIONS: Set[str] = {'.pdf', '.docx', '.doc', '.ppt', '.pptx', '.xlsx', '.xls'}
ARCHIVE_EXTENSIONS: Set[str] = {'.zip', '.tar', '.tgz', '.tar.gz', '.rar', '.gz', '.pkg'}
CODE_EXTENSIONS: Set[str] = {'.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss', '.less', '.php', '.rb', '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.go', '.rs', '.swift', '.kt', '.scala', '.r', '.m', '.sql', '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd'}

# Combination of all extension types
DEFAULT_EXTENSIONS: Set[str] = (IMAGE_EXTENSIONS.union(TEXT_EXTENSIONS)
                              .union(MEDIA_EXTENSIONS)
                              .union(DOCUMENT_EXTENSIONS)
                              .union(ARCHIVE_EXTENSIONS)
                              .union(CODE_EXTENSIONS))

# Cache and rename log files
CACHE_FILE: str = "generated_alts.json"
RENAME_LOG_FILE: str = "rename_log.json"

# Protected files that should not be processed
PROTECTED_PATTERNS: list = [
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
]

# XAI Model Constants
XAI_MODEL_VISION = "gpt-4-vision-preview"
XAI_MODEL_TEXT = "gpt-4-turbo-preview"

# API Configuration
API_BASE_URL = "https://api.assisted.space/v2"
API_TIMEOUT = 30  # seconds

# Image Processing
IMAGE_FUNCTION_SCHEMA = {
    "name": "analyze_image",
    "description": "Analyze an image and provide a detailed description",
    "parameters": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "A detailed description of the image content"
            },
            "alt_text": {
                "type": "string",
                "description": "Accessible alt text for the image"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Relevant tags for the image"
            }
        },
        "required": ["description", "alt_text", "tags"]
    }
}

# Document Processing
DOCUMENT_FUNCTION_SCHEMA = {
    "name": "analyze_document",
    "description": "Analyze a document and extract key information",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Document title or main subject"
            },
            "summary": {
                "type": "string",
                "description": "Brief summary of the document content"
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key terms and concepts from the document"
            },
            "citations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Citations found in the document"
            }
        },
        "required": ["title", "summary", "keywords"]
    }
}

# File Processing Prompts
FILE_IMAGE_PROMPT = """Analyze this image and provide:
1. A detailed description of the content
2. Accessible alt text
3. Relevant tags for organization

Focus on:
- Main subjects and objects
- Colors and visual elements
- Context and setting
- Any text or symbols present"""

FILE_DOCUMENT_PROMPT = """Analyze this document and provide:
1. A clear title or main subject
2. A concise summary
3. Key terms and concepts
4. Any citations found

Focus on:
- Main topic and purpose
- Key points and arguments
- Technical terms and concepts
- References and citations"""

# Alias for backward compatibility
IGNORE_PATTERNS = PROTECTED_PATTERNS

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