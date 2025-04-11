# Batch 14 Combined Snippets

Below is a cohesive document that combines the most important and unique segments from the provided code snippets. I focused on retaining only the essential, non-redundant parts based on their uniqueness, functionality, and rationale from the original files. Redundancies (e.g., multiple similar API error-handling patterns) were eliminated by selecting representative examples. The content is organized logically into sections for better readability:

1. **Configurations**: Centralized definitions like file extensions, which provide foundational setup.
2. **Data Structures**: Core classes or dataclasses that define key entities.
3. **API Interactions and Utilities**: Functions for API calls, data processing, and conversions, grouped by theme.
4. **Processing and Formatting Tools**: Specialized functions for content transformation.
5. **Testing and Package Setup**: Fixtures and imports for testing and modularization.

This organization ensures a logical flow, starting from foundational elements and moving toward application-specific logic and testing.

---

# Combined Code Document: Key Snippets from Various Files

## 1. Configurations
These segments define centralized configurations for file handling and extensions. They are unique as they promote modularity and are likely used across the application for file validation and classification.

```python
# File Extensions Configuration
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.heif'
}

MEDIA_EXTENSIONS = {
    '.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma',
    '.mp4', '.mov', '.avi', '.wmv', '.flv', '.mkv', '.webm'
}

ARCHIVE_EXTENSIONS = {
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.iso'
}

DOCUMENT_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.odt', '.ods', '.odp', '.rtf'
}

TEXT_EXTENSIONS = {
    '.txt'
}
```

## 2. Data Structures
This section includes key dataclasses that encapsulate core entities, such as API services. These are retained for their role in structuring data for analysis and interaction.

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class APIService:
    """Represents an API service"""
    name: str
    key: str
    category: str
    requires_payment: bool
    accessibility_features: List[str]
    documentation_url: Optional[str] = None
```

## 3. API Interactions and Utilities
These functions handle API requests, data conversions, and external interactions. I selected the most representative ones to avoid redundancy (e.g., only one proxy-like function is included, as others follow similar patterns). They are grouped by functionality for clarity.

### URL and Image Handling
```python
from flask import Blueprint, request, jsonify
import requests
import base64
import logging

bp = Blueprint('tools', __name__)
logger = logging.getLogger(__name__)

@bp.route('/url-to-base64', methods=['POST'])
def url_to_base64():
    """
    Convert an image URL to a base64-encoded data URL.
    Expects JSON payload with: { "url": "https://example.com/image.jpg" }
    """
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "URL is required"}), 400
            
        image_url = data['url']
        response = requests.get(image_url)
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch image from URL"}), 400
            
        content_type = response.headers.get('content-type', 'application/octet-stream')
        base64_data = base64.b64encode(response.content).decode('utf-8')
        data_url = f"data:{content_type};base64,{base64_data}"
        return jsonify({"base64": data_url}), 200
    except Exception as e:
        logger.error(f"Error converting URL to base64: {e}")
        return jsonify({"error": str(e)}), 500
```

### External API Fetching
```python
async def fetch_webcams(
    self,
    lat: float,
    lon: float,
) -> str:
    """
    Fetch live webcams for a given location.
    
    Args:
        lat (float): Latitude of the location.
        lon (float): Longitude of the location.
    
    Returns:
        str: Formatted response with webcam details and links.
    """
    # Implementation for API request and processing would follow here

def fetch_available_voices(self) -> str:
    """
    Fetches the list of available voices from the ElevenLabs API.
    
    :return: A formatted string containing the list of available voices.
    """
    # Implementation for API request would go here
```

### Proxy and DOI Handling
```python
from flask import Blueprint, jsonify
import requests
import logging

bp = Blueprint('proxy', __name__)
logger = logging.getLogger(__name__)

@bp.route('/doi/<path:doi>', methods=['GET'])
def proxy_doi(doi):
    """
    Proxy DOI requests to Crossref.
    """
    try:
        response = requests.get(
            f'https://api.crossref.org/works/{doi}',
            headers={
                'User-Agent': 'YourApp/1.0 (https://yourdomain.com; mailto:support@yourdomain.com)'
            }
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error(f"DOI proxy error: {str(e)}")
        return jsonify({'error': str(e)}), 500
```

## 4. Processing and Formatting Tools
These snippets focus on data transformation and formatting, including JSON handling and content processing. I extracted the most unique parts, such as the docstring for JSON features, to avoid repetition.

```python
"""
Module for JSON Conversion Tool
title: Convert to JSON
author: BrandXX/UserX
version: 1.0.4
license: MIT
description: Converts data to JSON format and returns it in a markdown code block.

Notes:
- Added 'COMPACT_PRINT' Valve:
  - OFF: Pretty-Printed JSON
  - ON: Compact JSON (one Array per line)
- Added 'SINGLE_LINE' Valve: Toggle ON for a single line of JSON
- Improved reliability of JSON output and LLM tool calls
- Refactored code for better dependability
"""

```javascript
/**
 * Process markdown content with syntax highlighting
 * @param {string} content - Raw markdown content
 * @returns {string} - Processed HTML
 */
processMessageContent(content) {
  const parsedContent = this.md.render(content);
  const container = document.createElement("div");
  container.className = "markdown-body message-content";
  container.innerHTML = parsedContent;
  // Apply syntax highlighting (implementation details omitted for brevity)
}
```

## 5. Testing and Package Setup
This includes essential setup for testing and package imports, which are unique for ensuring modularity and test reliability.

```python
"""
Tools package for the MoE system.
"""

from .location import LocationFinder

__all__ = ["LocationFinder"]

# Testing Fixture
import pytest

@pytest.fixture
def test_config():
    """Test configuration fixture"""
    return {
        'models': {
            'test_model': {
                'model_id': 'test_model',
                'model_type': 'belter',
                'base_model': 'mistral:7b',
                'endpoint': 'http://localhost:8001/test',
                'capabilities': {
                    'capabilities': ['test_capability'],
                    'max_tokens': 2048,
                    'temperature': 0.4,
                    'timeout': 30
                }
            }
        },
        'settings': {
            'retry_config': {
                'max_retries': 3,
                'backoff_factor': 1.5,
                'max_backoff': 30
            }
        }
    }
```

This document is streamlined and focused, with a total reduction in redundancy (e.g., similar error-handling code was consolidated into representative examples). If you need further adjustments, such as adding more context or expanding on any section, let me know!