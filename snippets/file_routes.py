from flask import Blueprint, request, jsonify, send_file, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pathlib import Path
import json
import os
import logging
from datetime import datetime, timedelta
import requests
import shutil
import mimetypes
import uuid
import base64
from io import BytesIO

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bp = Blueprint('files', __name__)
# Configure CORS to allow requests from any origin
CORS(bp, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"]
    }
})

# Constants
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
TEMP_FOLDER = os.getenv('TEMP_FOLDER', 'temp')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'txt', 'csv', 'json', 'md'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# Create necessary directories
Path(UPLOAD_FOLDER).mkdir(exist_ok=True, parents=True)
Path(TEMP_FOLDER).mkdir(exist_ok=True, parents=True)

def allowed_file(filename):
    """Check if file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_temp_files():
    """
    Delete files older than 1 hour from the temp directory
    """
    try:
        current_time = datetime.now()
        temp_dir = Path(TEMP_FOLDER)
        for file_path in temp_dir.glob('*'):
            if file_path.is_file():
                file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_age > timedelta(hours=1):
                    file_path.unlink()
                    logger.info(f"Deleted old temp file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {str(e)}")

# Setup scheduler for cleanup (if needed, using your scheduler implementation)
# Example with APScheduler:
# from apscheduler.schedulers.background import BackgroundScheduler
# scheduler = BackgroundScheduler()
# scheduler.add_job(cleanup_temp_files, 'interval', hours=1)
# scheduler.start()

@bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Handle file uploads
    """
    logger.info("File upload endpoint hit")
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if file and allowed_file(file.filename):
            # Generate secure filename with UUID to avoid collisions
            filename = secure_filename(file.filename)
            file_uuid = str(uuid.uuid4())
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            secure_name = f"{file_uuid}.{ext}" if ext else file_uuid
            
            file_path = Path(UPLOAD_FOLDER) / secure_name
            file.save(file_path)
            
            # Return file details
            file_url = f"/api/files/{secure_name}"
            file_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            
            return jsonify({
                "success": True,
                "file_id": secure_name,
                "file_name": filename,
                "file_type": file_type,
                "file_url": file_url,
                "file_size": file_path.stat().st_size
            }), 201
        else:
            return jsonify({"error": f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/<file_id>', methods=['GET'])
def serve_file(file_id):
    """
    Serve a file by its ID
    """
    try:
        # Clean the file_id to prevent path traversal
        secure_id = secure_filename(file_id)
        file_path = Path(UPLOAD_FOLDER) / secure_id
        
        if not file_path.exists() or not file_path.is_file():
            return jsonify({'error': 'File not found'}), 404
            
        # Guess the mime type based on file extension
        mimetype = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        
        # Get original filename from database if available
        # For this example, we'll just use the file_id
        filename = secure_id
        
        return send_file(
            file_path, 
            mimetype=mimetype,
            as_attachment=request.args.get('download') == 'true',
            download_name=filename if request.args.get('download') == 'true' else None
        )
    except Exception as e:
        logger.error(f"Error serving file: {str(e)}")
        return jsonify({'error': 'Error serving file'}), 500

@bp.route('/delete/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    """
    Delete a file by its ID
    """
    try:
        # Clean the file_id to prevent path traversal
        secure_id = secure_filename(file_id)
        file_path = Path(UPLOAD_FOLDER) / secure_id
        
        if not file_path.exists() or not file_path.is_file():
            return jsonify({'error': 'File not found'}), 404
            
        # Delete the file
        file_path.unlink()
        
        return jsonify({'success': True, 'message': 'File deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return jsonify({'error': 'Error deleting file'}), 500

@bp.route('/url-to-base64', methods=['POST'])
def url_to_base64():
    """
    Convert an image URL to base64 encoding
    """
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "URL is required"}), 400
            
        image_url = data['url']
        
        # Download image from URL
        response = requests.get(image_url)
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch image from URL"}), 400
            
        # Get content type
        content_type = response.headers.get('content-type', 'application/octet-stream')
        
        # Convert to base64
        base64_data = base64.b64encode(response.content).decode('utf-8')
        
        # Format as data URL
        data_url = f"data:{content_type};base64,{base64_data}"
        
        return jsonify({
            "base64": data_url
        }), 200
        
    except Exception as e:
        logger.error(f"Error converting URL to base64: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/base64-to-file', methods=['POST'])
def base64_to_file():
    """
    Convert base64 data to a file and save it
    """
    try:
        data = request.json
        if not data or 'base64' not in data:
            return jsonify({"error": "Base64 data is required"}), 400
            
        base64_data = data['base64']
        filename = data.get('filename', 'file')
        
        # Strip prefix if present (e.g., "data:image/jpeg;base64,")
        if ';base64,' in base64_data:
            # Get content type from the data URL
            content_type = base64_data.split(';')[0].split(':')[1]
            base64_data = base64_data.split(';base64,')[1]
        else:
            content_type = data.get('content_type', 'application/octet-stream')
        
        # Decode base64 data
        file_data = base64.b64decode(base64_data)
        
        # Create a unique filename
        file_uuid = str(uuid.uuid4())
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        if not ext and '/' in content_type:
            ext = content_type.split('/')[1]
        secure_name = f"{file_uuid}.{ext}" if ext else file_uuid
        
        # Save the file
        file_path = Path(UPLOAD_FOLDER) / secure_name
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # Return file details
        file_url = f"/api/files/{secure_name}"
        
        return jsonify({
            "success": True,
            "file_id": secure_name,
            "file_name": filename,
            "file_type": content_type,
            "file_url": file_url,
            "file_size": file_path.stat().st_size
        }), 201
        
    except Exception as e:
        logger.error(f"Error converting base64 to file: {str(e)}")
        return jsonify({"error": str(e)}), 500 