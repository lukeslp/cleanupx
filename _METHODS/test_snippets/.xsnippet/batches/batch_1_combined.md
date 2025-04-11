# Batch 1 Combined Snippets

Below is a cohesive document that combines the most important and unique code snippets from the provided files. I have carefully selected segments based on their centrality to the application's functionality, such as application setup, modularity, security, and authentication. Redundancies were eliminated—for example, multiple versions of the `admin_required` decorator were consolidated into one, and repeated instances of the `create_app` function were reduced to a single, comprehensive version. The content is organized logically: starting with high-level application setup, followed by modular design, security mechanisms, and authentication flows.

This document focuses on reusability, uniqueness, and core features like Flask application configuration, blueprint registration, token validation, and OAuth handling, while omitting less critical or repetitive elements (e.g., log entries, minor alternatives like helper functions).

---

# Combined Code Snippets: Core Flask Application Components

This document compiles essential code from various files in the project, emphasizing a modular, secure, and extensible Flask API. The selected snippets include:

- **Application Factory**: The foundation for creating and configuring the Flask app.
- **Blueprint Example**: Demonstrates modularity for feature organization.
- **Security Decorator**: A custom decorator for admin authentication.
- **Authentication Handler**: Core logic for OAuth token exchange.

These elements highlight best practices in Flask development, such as configuration management, error handling, logging, and secure routing.

## 1. Application Factory
The `create_app` function is the most comprehensive and unique snippet, serving as the application's entry point. It handles configuration, logging, CORS, blueprint registration, and error handling, making it reusable for initializing the entire API.

```python
import logging
import os
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS

def create_app(config=None):
    """
    Create and configure Flask application
    
    Args:
        config (dict, optional): Configuration overrides
        
    Returns:
        Flask: Application instance
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

## 2. Blueprint Example
This snippet illustrates how to create and register a blueprint, promoting modularity and extensibility in the API design. It's a simple, reusable pattern for organizing routes.

```python
from flask import Blueprint, jsonify

bp = Blueprint('my_feature', __name__)

@bp.route('/', methods=['GET'])
def my_endpoint():
    return jsonify({"message": "Hello from my_feature!"})

# To register the blueprint in your application:
# from my_feature import bp as my_feature_bp
# app.register_blueprint(my_feature_bp, url_prefix='/api/v1/my-feature')
```

## 3. Security Decorator
The `admin_required` decorator is a unique and essential security mechanism. It enforces authentication for protected routes, handles token validation, and includes logging for error tracking. Only one version is included here to avoid redundancy.

```python
from functools import wraps
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '')  # Assume this is set in environment

def admin_required(f):
    """Decorator to require admin authentication"""
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

## 4. Authentication Handler
The `oauth_token_exchange` function is a critical snippet for handling OAuth flows. It's unique for its secure implementation, error handling, and integration with external providers.

```python
import requests
import logging
from flask import Blueprint, request, jsonify
import os

logger = logging.getLogger(__name__)
bp = Blueprint('auth', __name__)

@bp.route('/oauth/token', methods=['POST'])
def oauth_token_exchange():
    """Handle OAuth token exchange"""
    try:
        data = request.json
        code = data.get('code')
        if not code:
            return jsonify({'error': 'No authorization code provided'}), 400

        client_id = os.getenv('OAUTH_CLIENT_ID', '')
        client_secret = os.getenv('OAUTH_CLIENT_SECRET', '')
        redirect_uri = os.getenv('OAUTH_REDIRECT_URI', '')
        token_url = "https://oauth-provider.com/oauth/token"
        
        payload = {
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret
        }

        response = requests.post(token_url, data=payload)
        token_data = response.json()

        if response.status_code != 200:
            logger.error(f"OAuth token exchange failed: {token_data}")
            return jsonify({
                'error': 'Token exchange failed',
                'details': token_data.get('error_description', 'Unknown error')
            }), response.status_code

        return jsonify({
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token')
        })

    except Exception as e:
        logger.exception("Error during OAuth token exchange")
        return jsonify({'error': str(e)}), 500
```

This document provides a streamlined, logical overview of the project's core components. It eliminates unnecessary repetitions (e.g., multiple `admin_required` versions) and focuses on what makes the application unique and functional. If you need further customization or additional details, let me know!