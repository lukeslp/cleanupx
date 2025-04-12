# Final Combined Snippets

Below is the final consolidated document resulting from my evaluation of the provided batch results. As part of this final evaluation, I performed the following steps:

1. **Identified the most important and unique snippets**: I reviewed the content from Batch 1, which already represents a refined consolidation of prior batches. I confirmed that it prioritizes critical elements such as application setup, AI interactions, API routes, event handling, security, and data models. These were selected based on their foundational role, reusability, and uniqueness (e.g., the `create_app` function, abstract AI methods, and security decorators).

2. **Removed duplicated content or redundancies**: Batch 1 had already eliminated most redundancies (e.g., multiple versions of `create_app` or `admin_required`). I double-checked for any subtle overlaps and found none. For instance, similar utility functions (like file renaming) were consolidated into a single, representative version.

3. **Organized the content logically and coherently**: The existing structure in Batch 1 is logical, progressing from high-level setup to specific functionalities. I preserved this flow while ensuring smooth transitions between sections. Each section includes brief introductions for context, followed by code snippets with documentation.

4. **Preserved critically important code and documentation**: I ensured that all essential code (e.g., error handling, logging, and asynchronous methods) and accompanying documentation (e.g., docstrings and comments) were retained, as they provide clarity and maintainability.

The resulting document is a streamlined, non-redundant representation of the best subset of content across all batches. It focuses on core innovations like AI-driven features and robust API handling while emphasizing modularity and error resilience. No significant changes were needed, as Batch 1 was already comprehensive and well-optimized.

---

# Final Consolidated Code Document: Optimized Snippets from the Project

This document represents the definitive compilation of the most important and unique code snippets from the analyzed batches. It emphasizes key aspects of the application, including setup, AI interactions, API handling, utilities, security, and data models. The content has been refined for clarity, reusability, and efficiency, ensuring that only the most robust and essential elements are included.

## 1. Application Setup
This section covers the foundational function for creating and configuring the Flask application. It includes logging, configuration management, blueprint registration, and error handling, making it a critical entry point for the application.

```python
def create_app(config=None):
    """
    Create and configure the Flask application.
    
    Args:
        config (dict, optional): Configuration overrides.
        
    Returns:
        Flask: Application instance.
    """
    import logging
    from flask import Flask, jsonify
    from pathlib import Path
    import os
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Create Flask app
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Default configuration
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-key-change-in-production'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max upload
        UPLOAD_FOLDER=os.getenv('UPLOAD_FOLDER', 'uploads'),
        TEMP_FOLDER=os.getenv('TEMP_FOLDER', 'temp'),
        SERVER_NAME=os.getenv('SERVER_NAME', None),
        PREFERRED_URL_SCHEME=os.getenv('PREFERRED_URL_SCHEME', 'https'),
        DEBUG=os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    )
    
    # Apply custom configuration if provided
    if config:
        app.config.update(config)
    
    # Create necessary directories
    Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True, parents=True)
    Path(app.config['TEMP_FOLDER']).mkdir(exist_ok=True, parents=True)
    
    # Register blueprints with URL prefixes
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(proxy_bp, url_prefix='/api/v1/proxy')
    app.register_blueprint(llm_bp, url_prefix='/api/v1/llm')
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(chat_bp, url_prefix='/api/v1/chat')
    app.register_blueprint(file_bp, url_prefix='/api/v1/files')
    app.register_blueprint(admin_bp, url_prefix='/api/v1/admin')
    app.register_blueprint(tunnel_bp, url_prefix='/api/v1/tunnel')
    app.register_blueprint(health_bp, url_prefix='/api/v1/health')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"Server error: {error}")
        return jsonify({"error": "Internal server error"}), 500
    
    @app.errorhandler(413)
    def too_large(error):
        return jsonify({"error": "File too large"}), 413
    
    logger.info(f"Application created with config: {app.config}")
    return app
```

## 2. AI and Tool Functionalities
This section highlights essential AI-related components, including abstract interfaces for chat completions and tool management, which enable modular and extensible AI interactions.

- **Abstract method for AI chat completions**:
  
  ```python
  @abstractmethod
  async def chat_completion(
      self,
      messages: List[Dict[str, str]],
      stream: bool = True,
      **kwargs
  ) -> AsyncIterator[Dict[str, str]]:
      """Generate chat completions from the AI provider.
      
      Args:
          messages: List of message dictionaries with 'role' and 'content' keys
          stream: Whether to stream the response
          **kwargs: Additional provider-specific parameters
          
      Yields:
          Dict containing response chunks with 'type' and 'content' keys
      """
      pass
  ```

- **OllamaAPI client**:
  
  ```python
  class OllamaAPI:
      """Client for interacting with Ollama LLM service."""
      
      def __init__(
          self,
          base_url: str = "http://localhost:11434/api",
          model: str = "drummer-knowledge",
          logger: Optional[logging.Logger] = None
      ):
          """
          Initialize Ollama API client.
          
          Args:
              base_url: Base URL for Ollama API
              model: Model to use for inference
              logger: Optional logger instance
          """
          self.base_url = base_url
          self.model = model
          self.logger = logger or get_logger(__name__)
  ```

- **Base tool class**:
  
  ```python
  class BaseTool:
      """Base class for all tools in the MoE system."""
      
      class UserValves(BaseModel):
          """Base class for tool credentials."""
          pass  # Subclasses can extend this for specific credentials
      
      def __init__(self, credentials: Dict[str, str] = None):
          """
          Initialize the tool.
          
          Args:
              credentials: Optional dictionary of credentials.
          """
          self.credentials = credentials or {}
          self.validate_credentials()
      
      def validate_credentials(self) -> None:
          """
          Validate that all required credentials are present.
          
          Raises:
              ValueError: If required credentials are missing.
          """
          if not self.credentials:
              raise ValueError("Required credentials are missing.")
  ```

## 3. API Interactions and Routes
This includes robust API handlers for external interactions, with a focus on error handling and streaming responses.

- **Flask route for Ollama chat completions**:
  
  ```python
  from flask import Blueprint, request, Response, jsonify
  import requests
  from flask_cors import cross_origin
  import logging
  
  bp = Blueprint('llm', __name__)
  OLLAMA_BASE_URL = "http://localhost:11434"
  
  @bp.route('/ollama/chat/completions', methods=['POST'])
  @cross_origin()
  def ollama_chat():
      """
      Forward chat completions to Ollama
      """
      try:
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

- **URL to base64 conversion**:
  
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

## 4. Event Handling and Utilities
This section includes mechanisms for event emission and practical utilities, ensuring observability and safe operations.

- **EventEmitter class**:
  
  ```python
  class EventEmitter:
      def __init__(self, event_emitter: Callable[[dict], Any] = None):
          self.event_emitter = event_emitter
      
      async def progress_update(self, description):
          await self.emit(description)
      
      async def error_update(self, description):
          await self.emit(description, "error", True)
      
      async def success_update(self, description):
          await self.emit(description, "success", True)
      
      async def emit(self, description="Unknown State", status="in_progress", done=False):
          if self.event_emitter:
              await self.event_emitter({
                  "type": "status",
                  "data": {"status": status, "description": description, "done": done}
              })
  ```

- **File renaming function**:
  
  ```python
  def rename_files(file_pairs: List[Tuple[Path, Path]], backup: bool = False) -> List[Tuple[Path, Path, bool]]:
      """
      Safely rename multiple files with optional backups.
      
      Args:
          file_pairs: List of (source, destination) path tuples
          backup: Whether to create backups before renaming
          
      Returns:
          List of (source, destination, success) tuples
      """
      results = []
      for src, dst in file_pairs:
          try:
              success, _ = safe_rename(src, dst, backup=backup)
              results.append((src, dst, success))
          except OSError as e:
              logger.error(f"Failed to rename {src} to {dst}: {str(e)}")
              results.append((src, dst, False))
      return results
  ```

## 5. Security Mechanisms
This focuses on authentication and protection for sensitive routes.

- **Admin authentication decorator**:
  
  ```python
  from functools import wraps
  from flask import request, jsonify
  import logging
  
  logger = logging.getLogger(__name__)
  ADMIN_TOKEN = "your_admin_token"  # Replace with actual token
  
  def admin_required(f):
      @wraps(f)
      def decorated_function(*args, **kwargs):
          auth_header = request.headers.get('Authorization')
          if not auth_header:
              logger.warning("No authorization header provided")
              return jsonify({"error": "No authorization header"}), 401
          
          try:
              token_type, token = auth_header.split(' ')
              if token_type.lower() != 'Bearer':
                  logger.warning("Invalid authorization type")
                  return jsonify({"error": "Invalid authorization type"}), 401
              
              if token != ADMIN_TOKEN:
                  logger.warning("Invalid admin token provided")
                  return jsonify({"error": "Unauthorized"}), 403
                  
              return f(*args, **kwargs)
          except Exception as e:
              logger.error(f"Auth error: {str(e)}")
              return jsonify({"error": "Invalid authorization header"}), 401
              
      return decorated_function
  ```

## 6. Data Models
This section provides structured data representations for key entities.

- **Article metadata dataclass**:
  
  ```python
  @dataclass
  class ArticleMetadata:
      """Structured container for article metadata."""
      authors: List[str]
      year: Optional[int]
      title: str
      doi: Optional[str]
      abstract: Optional[str]
      keywords: List[str]
      source: Optional[str] = None
      confidence: float = 0.0
  ```

This final document is comprehensive, efficient, and ready for use. It captures the essence of the project while eliminating any unnecessary elements, ensuring a high level of maintainability and focus on core functionalities. If additional context or adjustments are required, please provide further details.