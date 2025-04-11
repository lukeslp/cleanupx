# Batch 1 Combined Snippets

Below is a cohesive document that combines the most important and unique segments from the provided code snippets. I have eliminated redundancies (e.g., keeping only one version of the `admin_required` decorator from `admin_routes.py`, as it's explicitly marked as the best and most unique), retained only the core, non-redundant code, and organized the content logically. The structure follows a logical flow:

1. **Application Setup**: Starts with the high-level Flask app creation, as it's the foundation.
2. **Modularization with Blueprints**: Covers how to create and register blueprints, which is key for extending the API.
3. **Authentication and Security**: Includes the admin authentication decorator and the OAuth token exchange function, as these handle security features.

This results in a streamlined, self-contained document that focuses on the essential elements without repetition.

---

# Combined Code Document: Flask Application Overview

This document consolidates the key code segments from your project files into a single, organized structure. It emphasizes core functionality like app initialization, blueprint registration, and authentication mechanisms, which are critical for building a secure and modular Flask API.

## 1. Application Setup
The `create_app` function from `app.py` serves as the entry point for the Flask application. It handles configuration, sets up the app instance, and registers blueprints for modular routing. This is the most foundational piece, ensuring the app is configurable and extensible.

```python
def create_app(config=None):
    """
    Create and configure Flask application
    
    Args:
        config (dict, optional): Configuration overrides
        
    Returns:
        Flask: Application instance
    """
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
    
    return app
```

## 2. Modularization with Blueprints
Blueprints allow for modular API extension, as demonstrated in the README.md snippet. This is a key feature for organizing routes and making the application customizable without cluttering the main app file.

```python
from flask import Blueprint, jsonify

bp = Blueprint('my_feature', __name__)

@bp.route('/', methods=['GET'])
def my_endpoint():
    return jsonify({"message": "Hello from my feature!"})

# To register the blueprint in your application:
# from my_feature import bp as my_feature_bp
# app.register_blueprint(my_feature_bp, url_prefix='/api/v1/my-feature')
```

## 3. Authentication and Security Mechanisms
Authentication is handled through custom decorators and OAuth flows. The following sections include the unique admin authentication decorator (from `admin_routes.py`) and the OAuth token exchange function (from `auth_routes.py`), which together provide robust security for protected routes.

### Admin Authentication Decorator
This decorator ensures that only authorized admins can access certain routes. It's a custom implementation with token-based auth, logging, and error handling.

```python
from functools import wraps
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)
ADMIN_TOKEN = "your_admin_token_here"  # Assume this is defined elsewhere

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
            if token_type.lower() != 'bearer':
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

### OAuth Token Exchange
This function handles the OAuth authorization code flow, securely exchanging codes for tokens while incorporating error handling and logging.

```python
import os
import requests
from flask import request, jsonify, Blueprint

bp = Blueprint('auth', __name__)  # Assuming this is part of an auth blueprint

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

This document provides a complete, logical overview of the key components while keeping it concise and focused. If you need further customization or additional context, let me know!