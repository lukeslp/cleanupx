from flask_cors import CORS
from flask import Blueprint, request, jsonify
from pathlib import Path
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import logging

# Set up logging
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
BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "temp"
IMAGE_COUNTER_FILE = BASE_DIR / "data" / "image_counter.json"

# Create necessary directories
TEMP_DIR.mkdir(exist_ok=True, parents=True)
IMAGE_COUNTER_FILE.parent.mkdir(exist_ok=True, parents=True)

# Initialize Coze client
coze_api_token = 'pat_Uk4Z075Oo8RE5Po13rBUoEQNzr3dcKTNmBuf5Qtj1V6QZLiwAeZDaNzfNSLMIca8'
# Initialize image counter if it doesn't exist
if not IMAGE_COUNTER_FILE.exists():
    with open(IMAGE_COUNTER_FILE, 'w') as f:
        json.dump({"count": 0}, f)

def increment_image_counter():
    """
    Increment the image counter
    """
    try:
        with open(IMAGE_COUNTER_FILE, 'r') as f:
            data = json.load(f)
        data["count"] += 1
        with open(IMAGE_COUNTER_FILE, 'w') as f:
            json.dump(data, f)
        logger.info(f"Image counter incremented. New count: {data['count']}")
    except Exception as e:
        logger.error(f"Error updating image counter: {e}")

def cleanup_temp_files():
    """
    Delete files older than 1 hour from the temp directory
    """
    try:
        current_time = datetime.now()
        for file_path in TEMP_DIR.glob('*'):
            if file_path.is_file():
                file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_age > timedelta(hours=1):
                    file_path.unlink()
                    logger.info(f"Deleted old temp file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {str(e)}")

# Schedule cleanup task
scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_temp_files, 'interval', hours=1)
scheduler.start()

@bp.route('/upload', methods=['POST'])
def upload_file():
    logger.info("File upload endpoint hit")
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if not file:
            return jsonify({"error": "Empty file"}), 400

        # Upload file using direct API call
        files = {'file': (file.filename, file.stream, file.content_type)}
        headers = {'Authorization': f'Bearer {coze_api_token}'}
        
        logger.info(f"Uploading file {file.filename} to Coze")
        upload_response = requests.post(
            'https://api.coze.com/v1/files/upload',
            files=files,
            headers=headers
        )
        
        logger.info(f"Upload response: {upload_response.text}")
        
        if not upload_response.ok:
            raise Exception(f"Upload failed: {upload_response.text}")
            
        upload_data = upload_response.json()
        logger.info(f"Upload data: {upload_data}")
        
        # Extract file ID according to documented response format
        # Response format: {"code": 0, "data": {"id": "xxx", ...}, "msg": ""}
        file_id = None
        if upload_data.get('code') == 0:
            file_id = upload_data.get('data', {}).get('id')
        
        if not file_id:
            raise Exception("No file_id in response")
        
        logger.info(f"File uploaded successfully, ID: {file_id}")
        return jsonify({
            "success": True,
            "file_id": file_id
        })

    except Exception as e:
        error_msg = str(e)
        logger.error(f"File upload error: {error_msg}")
        return jsonify({"error": error_msg}), 500

@bp.route('/counter', methods=['GET'])
def get_image_count():
    """
    Get the current image counter value
    """
    try:
        logger.debug(f"Accessing image counter file at: {IMAGE_COUNTER_FILE}")
        
        if not os.access(IMAGE_COUNTER_FILE, os.R_OK | os.W_OK):
            logger.error(f"Permission denied for file: {IMAGE_COUNTER_FILE}")
            return jsonify({
                "success": False,
                "error": "Permission denied",
                "count": 0
            }), 500
                
        with open(IMAGE_COUNTER_FILE, 'r') as f:
            data = json.load(f)
            count = data.get("count", 0)
            logger.debug(f"Successfully read count: {count}")
            
        return jsonify({
            "success": True,
            "count": count
        }), 200
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        with open(IMAGE_COUNTER_FILE, 'w') as f:
            json.dump({"count": 0}, f)
        return jsonify({
            "success": False,
            "error": "Counter reset due to file corruption",
            "count": 0
        }), 500
    except Exception as e:
        logger.error(f"Error in get_image_count: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "count": 0
        }), 500

@bp.route('/nuke', methods=['POST'])
def clear_conversation():
    """
    Clear all temporary files and conversations
    """
    try:
        # Clear temp directory
        for file_path in TEMP_DIR.glob('*'):
            if file_path.is_file():
                file_path.unlink()
        
        return jsonify({'success': True, 'message': 'All temporary files cleared'}), 200
    except Exception as e:
        logger.error(f"Error clearing files: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
    
    
@bp.route('/url-to-base64', methods=['POST'])
def url_to_base64():
    """
    Convert an image URL to base64 encoding
    
    Expects JSON payload with:
    {
        "url": "https://example.com/image.jpg"
    }
    
    Returns:
    {
        "base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
    }
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
        import base64
        base64_data = base64.b64encode(response.content).decode('utf-8')
        
        # Format as data URL
        data_url = f"data:{content_type};base64,{base64_data}"
        
        return jsonify({
            "base64": data_url
        }), 200
        
    except Exception as e:
        logger.error(f"Error converting URL to base64: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/ocr', methods=['POST'])
def perform_ocr():
    """
    Extract text from an image using Tesseract OCR
    
    Accepts either:
    - Multipart form data with an image file
    - JSON with base64 encoded image
    - JSON with image URL
    
    Returns:
    {
        "text": "Extracted text from image",
        "confidence": 95.5
    }
    """
    try:
        import pytesseract
        from PIL import Image
        import io
        import base64

        image = None
        
        # Handle different input types
        if request.files and 'image' in request.files:
            # Handle direct file upload
            file = request.files['image']
            image = Image.open(file.stream)
            
        elif request.is_json:
            data = request.json
            if 'base64' in data:
                # Handle base64 encoded image
                base64_data = data['base64']
                if 'base64,' in base64_data:
                    base64_data = base64_data.split('base64,')[1]
                image_data = base64.b64decode(base64_data)
                image = Image.open(io.BytesIO(image_data))
                
            elif 'url' in data:
                # Handle image URL
                response = requests.get(data['url'])
                if response.status_code != 200:
                    return jsonify({"error": "Failed to fetch image from URL"}), 400
                image = Image.open(io.BytesIO(response.content))
        
        if not image:
            return jsonify({"error": "No image provided"}), 400

        # Perform OCR
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        # Extract text and confidence
        text = " ".join(ocr_data['text'])
        # Calculate average confidence excluding empty text
        confidences = [conf for conf, txt in zip(ocr_data['conf'], ocr_data['text']) 
                      if txt.strip() and conf != -1]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return jsonify({
            "text": text,
            "confidence": round(avg_confidence, 2)
        }), 200

    except Exception as e:
        logger.error(f"Error performing OCR: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
