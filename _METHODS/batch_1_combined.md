# Batch 1 Combined Snippets

Below is a cohesive document that combines the provided code snippets into a single, organized structure. I have focused on retaining only the most important and unique segments, eliminating redundancies (e.g., the duplicate `admin_required` decorator from `api_routes.py` is removed), and organizing the content logically. The structure follows a natural flow:

1. **Application Setup**: Starts with the core `create_app` function from `app.py`, as it forms the foundation of the Flask application.
2. **Blueprints and Modularity**: Includes the blueprint example from `README.md`, which demonstrates how to create and register blueprints for modular API design.
3. **Authentication and Security**: Covers the unique authentication utilities, including the `admin_required` decorator (from `admin_routes.py`) and the `_get_bearer_token` helper function (from `auth_routes.py`).

I've added minimal explanatory comments to tie the sections together, based on the original descriptions, while keeping the document concise and focused on the code. Only essential, non-redundant code is included.

---

# Combined Code Document: Flask Application Overview

This document consolidates the key components of the Flask application, emphasizing modularity, security, and initialization. It begins with the application factory for setup, followed by blueprint registration for API organization, and ends with authentication utilities for secure access.

## 1. Application Setup
The `create_app` function is the core of the application, implementing the Flask application factory pattern. It handles configuration, logging, directory creation, CORS setup, blueprint registration, and basic routes/error handlers. This modular approach makes it reusable and suitable for production.

```python
import os
import logging
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS

def create_app(config=None):
    """
    Create and configure the Flask application.
    
    Args:
        config (dict, optional): Configuration overrides.
        
    Returns:
        Flask: Application instance.
    """
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
    
    # Configure CORS
    CORS(app, resources={
        r"/*": {
            "origins": os.getenv('CORS_ORIGINS', '*').split(','),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"]
        }
    })
    
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
    
    # Root route
    @app.route('/')
    def index():
        return jsonify({
            "name": "Your API Service",
            "version": "1.0.0",
            "status": "operational",
            "documentation": "/api/v1/docs"
        })
    
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
    
    # Log startup information
    logger.info(f"Application created with config: {app.config}")
    
    return app
```

## 2. Blueprints and Modularity
This snippet demonstrates how to create and register a Flask blueprint, promoting modularity in API design. It's essential for organizing routes and allowing extensions to the API.

```python
from flask import Blueprint, jsonify

bp = Blueprint('my_feature', __name__)

@bp.route('/', methods=['GET'])
def my_endpoint():
    return jsonify({"message": "Hello from my_feature!"})

# To register the blueprint in the application (e.g., in create_app):
# from my_feature import bp as my_feature_bp
# app.register_blueprint(my_feature_bp, url_prefix='/api/v1/my-feature')
```

## 3. Authentication and Security Utilities
These functions handle secure authentication. The `admin_required` decorator ensures protection for sensitive endpoints by verifying the Authorization header. The `_get_bearer_token` function provides a reusable way to extract bearer tokens, supporting OAuth/JWT-based systems.

```python
from functools import wraps
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

def admin_required(f):
    """Decorator to require admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            logger.warning("No authorization header provided")
            return jsonify({"error": "No authorization header"}), 401
        
        try:
            token_type, token = auth_header.split(' ')
            if token_type.lower() != 'bearer':
                logger.warning("Invalid authorization type")
                return jsonify({"error": "Invalid authorization type"}), 401
            
            if token != ADMIN_TOKEN:  # Assuming ADMIN_TOKEN is defined elsewhere
                logger.warning("Invalid admin token provided")
                return jsonify({"error": "Unauthorized"}), 403
                
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Auth error: {str(e)}")
            return jsonify({"error": "Invalid authorization header"}), 401
            
    return decorated_function

def _get_bearer_token():
    """
    Helper function to extract access token from Authorization header: 'Bearer <token>'.
    This is a fundamental utility for secure token handling in authentication systems.
    """
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    return None
```

This combined document provides a complete, logical overview of the application's key elements, focusing on essentials while removing duplicates and redundancies. It can serve as a reference for development or documentation.