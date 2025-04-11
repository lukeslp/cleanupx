from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
from pathlib import Path

# Import blueprints
from snippets.api_routes import bp as api_bp
from snippets.proxy_routes import bp as proxy_bp
from snippets.llm_routes import bp as llm_bp
from snippets.auth_routes import bp as auth_bp
from snippets.chat_routes import bp as chat_bp
from snippets.file_routes import bp as file_bp
from snippets.admin_routes import bp as admin_bp
from snippets.tunnel_routes import bp as tunnel_bp
from snippets.health_routes import bp as health_bp

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

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG']) 