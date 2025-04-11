from flask import Blueprint, jsonify, render_template, request, send_file, make_response
import logging
import os
from pathlib import Path
from functools import wraps
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
BASE_DIR = Path(os.getenv('BASE_DIR', '/app'))
MONITORED_PORTS = [80, 5000, 5001, 5002, 5003, 5004, 5005, 8000]
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'default_token')

bp = Blueprint('api', __name__,
              template_folder='../templates',
              static_folder='../static')

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

def format_datetime(timestamp):
    """Format timestamp for display"""
    if timestamp is None:
        return "Never"
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

# Register the filter when the blueprint is registered
@bp.record_once
def register_filters(state):
    state.app.jinja_env.filters['datetime'] = format_datetime

# Health Routes
@bp.route('/health')
def health_check():
    """Basic health check endpoint"""
    try:
        # Basic system health check
        import psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        result = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_usage": f"{cpu_percent}%",
                "memory": {
                    "total": memory.total,
                    "used": memory.used,
                    "free": memory.available,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
            }
        }
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@bp.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    return render_template('admin/dashboard.html')

@bp.route('/admin/docs')
@admin_required
def api_docs():
    """Serve API documentation"""
    try:
        docs_path = BASE_DIR / 'API_DOCUMENTATION.md'
        if docs_path.exists():
            return send_file(str(docs_path), mimetype='text/markdown')
        else:
            return jsonify({"error": "Documentation not found"}), 404
    except Exception as e:
        logger.error(f"Error serving documentation: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/dashboard/api/status')
def api_status():
    """Get API status"""
    try:
        # Basic system health check
        import psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        status = {
            "status": "healthy",
            "system": {
                "cpu_usage": f"{cpu_percent}%",
                "memory": {
                    "total": memory.total,
                    "used": memory.used,
                    "free": memory.available,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
            }
        }
        return jsonify(status)
    except Exception as e:
        logger.error(f"API status error: {str(e)}")
        return make_response(jsonify({'error': str(e), 'status': 500}), 500) 