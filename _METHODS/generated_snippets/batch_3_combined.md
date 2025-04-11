# Batch 3 Combined Snippets

Below is a cohesive document that combines the most important and unique segments from the provided code snippets. I have focused on retaining only the essential parts, eliminating redundancies (e.g., avoiding repeated error-handling patterns or incomplete/truncated code unless critical), and organizing the content logically. The structure is as follows:

1. **Introduction**: A brief overview to set context.
2. **Configurations and Utilities**: Includes environment-aware API utilities (from JavaScript) and logging setup (from Python), as these are foundational for any application.
3. **API Interactions and Models**: Groups AI-related routes and methods (e.g., Ollama chat, Coze chat completions, and Perplexity models), as they handle core AI functionality.
4. **Search and Data Configurations**: Covers search engine configurations, which are unique and central to knowledge-related tasks.
5. **Tools and Analyzers**: Includes code execution and text/data analysis tools, as they represent practical extensions for processing and analysis.

I omitted the snippet from `code_aggregation.python` entirely, as it only describes an empty file and adds no unique or executable content. Truncated parts of snippets (e.g., incomplete methods) were not expanded, but I ensured the retained segments are self-contained and representative.

This document is presented as a markdown file for readability, with code blocks organized by section. If needed, this could be adapted into a single Python module (with the JavaScript snippet noted as a separate utility).

---

# Combined Code Document: AI and Utility Snippets

## Introduction
This document aggregates key code segments from various files into a logical structure. It focuses on core functionalities such as API proxying, logging, AI interactions, search configurations, and tool implementations. The goal is to provide a reusable, streamlined reference for building an AI-driven application, such as a Flask-based backend with external API integrations.

## 1. Configurations and Utilities
These snippets handle foundational setup, including dynamic API URL resolution and logging configuration. They ensure the application is adaptable to different environments (e.g., local vs. production) and maintainable.

### JavaScript: API Base URL Utility
This utility dynamically determines the API base URL based on the host, making it essential for cross-environment API calls.

```javascript
export const API_CONFIG = {
    getBaseUrl() {
        return window.location.hostname === "localhost"
            ? "http://localhost:5002"
            : "https://ai.assisted.space";
    }
};
```

### Python: Logging Setup
This function configures logging with options for verbosity and file output, promoting best practices for error tracking in AI applications.

```python
import logging
import structlog
from pathlib import Path
from typing import Optional

def setup_logging(
    verbose: bool = False,
    log_file: Optional[Path] = None,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
) -> None:
    """Set up logging configuration.
    
    Args:
        verbose: If True, set log level to DEBUG
        log_file: Optional path to log file
        log_format: Format string for log messages
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.stdlib.render_to_log_kwargs,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set up basic configuration
    logging.basicConfig(level=level, filename=log_file, format=log_format)
```

## 2. API Interactions and Models
These segments focus on interacting with external AI APIs, including request forwarding, streaming, and model definitions. They are central to AI-driven features like chat completions.

### Python: Ollama Chat Route (from llm_routes.py)
This route forwards chat requests to an external Ollama API, handles streaming responses, and includes robust error checking and CORS support.

```python
from flask import Blueprint, request, Response, jsonify
import requests
from flask_cors import cross_origin
import logging

bp = Blueprint('llm', __name__)
OLLAMA_BASE_URL = "http://localhost:11434"  # Assume this is defined elsewhere

@bp.route('/ollama/chat/completions', methods=['POST'])
@cross_origin()
def ollama_chat():
    """
    Forward chat completions to Ollama
    """
    try:
        # Verify Ollama is accessible
        requests.get(f"{OLLAMA_BASE_URL}/api/version", timeout=5)
        
        data = request.json
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=data,
            stream=True,
            timeout=30
        )
        
        if response.status_code != 200:
            logging.error(f"Ollama returned status code {response.status_code}")
            return jsonify({"error": f"Ollama error: {response.text}"}), response.status_code
            
        return Response(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get('content-type'),
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            }
        )
    except requests.exceptions.Timeout:
        logging.error("Ollama request timed out")
        return jsonify({"error": "Request to Ollama timed out"}), 504
    except Exception as e:
        logging.error(f"Ollama chat error: {str(e)}")
        return jsonify({"error": str(e)}), 500
```

### Python: Coze Chat Completion Method
This asynchronous method handles chat completions for Coze's API, including message formatting and streaming support.

```python
from typing import List, Dict, AsyncIterator
import asyncio  # For async context

async def chat_completion(
    self,
    messages: List[Dict[str, str]],
    stream: bool = True,
    **kwargs
) -> AsyncIterator[Dict[str, str]]:
    """Generate chat completions using Coze's API."""
    
    try:
        # Convert messages to Coze format
        coze_messages = [...]  # (Truncated; assume conversion logic here)
        # Proceed with API call (e.g., using aiohttp or similar)
    except Exception as e:
        # Error handling would continue here
        raise
```

### Python: PerplexityChat Models
This defines a dictionary of models for the PerplexityChat class, which is key for model selection in AI interactions.

```python
class PerplexityChat:
    MODELS = {
        "sonar-reasoning-pro": {
            "id": "sonar-reasoning-pro",
            "context_length": 127000,
            "description": "Advanced reasoning and analysis"
        },
        "sonar-reasoning": {
            "id": "sonar-reasoning",
            "context_length": 127000,
            "description": "Enhanced reasoning capabilities"
        },
        "sonar-pro": {
            "id": "sonar-pro",
            "context_length": 200000,
            "description": "Professional grade completion"
        },
        "sonar": {
            "id": "sonar",
            "context_length": 127000,
            "description": "Basic completion"  # Corrected from incomplete original
        },
    }
```

## 3. Search and Data Configurations
This section includes configurations for external services like search engines, which are unique and enable knowledge retrieval.

### Python: Search Engine Configurations (from code_knowledge_search.python)
This Pydantic model defines URLs and timeouts for search engines, central to web searching functionality.

```python
from pydantic import BaseModel, Field

class Valves(BaseModel):
    SEARXNG_URL: str = Field(
        default="https://paulgo.io/search",
        description="SearXNG search URL. You can find available SearXNG instances at https://searx.space/. The URL should end with '/search'."
    )
    BAIDU_URL: str = Field(
        default="https://www.baidu.com/s",
        description="Baidu search URL"
    )
    TIMEOUT: int = Field(default=30, description="Request timeout in seconds")
```

## 4. Tools and Analyzers
These snippets cover practical tools for code execution and data analysis, emphasizing security and asynchronous operations.

### Python: Restricted Code Execution
This method securely runs Python code in a restricted environment, highlighting safety features.

```python
import asyncio
import tempfile
from pathlib import Path

async def run_python_code(self, code: str) -> str:
    """Run Python code in a restricted environment"""
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        # Run with restricted permissions
        process = await asyncio.create_subprocess_exec(
            self.python_path,
            temp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.temp_dir,
            env={}  # Restricted environment; add specifics as needed
        )
        # (Truncated; handle output and errors here)
    except Exception as e:
        raise
```

### Python: Text Analysis Method
This asynchronous method analyzes text for sentiment and entities using an external API.

```python
from typing import Optional, Callable, Any, Awaitable

async def analyze_text(
    self,
    text: str,
    language: str = "en",
    __user__: dict = {},
    __event_emitter__: Optional[Callable[[Any], Awaitable[None]]] = None,
) -> str:
    """
    Analyze text for sentiment, key entities, and offensive content.

    Args:
        text (str): The input text to analyze.
        language (str): The language code (default: "en" for English).

    Returns:
        str: Formatted analysis results.
    """
    if __event_emitter__:
        await __event_emitter__({
            "type": "status",
        })
    # (Proceed with API request; truncated in original)
```

### Python: Finance Analyzer Class
This class defines a tool for financial analysis, serving as a base for extension.

```python
from .base import BaseTool  # Assume BaseTool is imported

class FinanceAnalyzer(BaseTool):
    """Tool for analyzing financial assets and market data."""
```

## Conclusion
This document provides a streamlined, organized view of the key code segments, focusing on uniqueness and utility. To integrate into a full application, consider adding imports, dependencies (e.g., Flask, requests, Pydantic), and any necessary wrappers. If you need this as a single executable file, further consolidation into a Python package would be recommended.