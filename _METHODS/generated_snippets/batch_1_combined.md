# Batch 1 Combined Snippets

Below is a cohesive document that combines the provided code snippets into a single, organized structure. I have focused on retaining only the most important and unique segments, eliminating redundancies (e.g., the `admin_required` decorator appears in multiple files, so I've included it only once), and organizing the content logically.

The document is structured as follows:
1. **App Setup and Initialization**: Starts with the `create_app` function from `app.py`, as it's the core entry point for configuring the Flask application.
2. **Authentication Mechanisms**: Includes the unique `admin_required` decorator (from `admin_routes.py`) and the `oauth_token_exchange` function (from `auth_routes.py`), as these handle security and token exchange, which are critical for API authentication.
3. **Modular Features**: Ends with the Blueprint example from `README.md`, which demonstrates how to create and register blueprints, tying into the app's extensibility as referenced in `app.py`.

This results in a streamlined, logical flow: from app creation to authentication to modular extensions. I've added brief comments to explain the organization and transitions, but kept the content concise.

---

# Combined API Application Code Document

## 1. App Setup and Initialization
This section includes the `create_app` function, which is the central function for creating and configuring the Flask application. It handles logging, configuration, CORS, blueprint registration, and basic routes/error handlers. This is the foundation of the application.

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

## 2. Authentication Mechanisms
This section covers key authentication components. The `admin_required` decorator ensures admin-only access, while the `oauth_token_exchange` function handles OAuth 2.0 token exchanges. These are unique and essential for securing routes.

```python
from functools import wraps
from flask import request, jsonify
import logging
import requests
import os

# Admin authentication decorator
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
            
            if token != ADMIN_TOKEN:  # Assuming ADMIN_TOKEN is defined in your environment or config
                logger.warning("Invalid admin token provided")
                return jsonify({"error": "Unauthorized"}), 403
                
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Auth error: {str(e)}")
            return jsonify({"error": "Invalid authorization header"}), 401
            
    return decorated_function

# OAuth token exchange route
from flask import Blueprint as bp  # Assuming bp is imported for blueprint usage

auth_bp = bp('auth', __name__)

@auth_bp.route('/oauth/token', methods=['POST'])
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

## 3. Modular Features and Examples
This section includes an example of creating and registering a Blueprint, as shown in `README.md`. This is important for extending the application modularly, and it aligns with the blueprint registrations in `create_app`.

```python
from flask import Blueprint, jsonify

# Example: Create a new Blueprint
bp = Blueprint('my_feature', __name__)

@bp.route('/', methods=['GET'])
def my_endpoint():
    return jsonify({"message": "Hello from my feature!"})

# To register it in the main application (as referenced in create_app):
# from my_feature import bp as my_feature_bp
# app.register_blueprint(my_feature_bp, url_prefix='/api/v1/my-feature')
```

This document provides a complete, non-redundant overview of the key components from the snippets. If you need to run this as a single file, ensure dependencies like blueprints (e.g., `api_bp`) are imported or defined appropriately.