from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_cors import CORS, cross_origin
import requests
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('llm', __name__)
CORS(bp)  # Enable CORS for all routes in this blueprint

# Constants
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'https://api.assisted.space')

@bp.route('/ollama/chat/completions', methods=['POST'])
@cross_origin()
def ollama_chat():
    """
    Forward chat completions to Ollama
    """
    try:
        # First verify Ollama is accessible
        try:
            requests.get(f"{OLLAMA_BASE_URL}/api/version", timeout=5)
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {OLLAMA_BASE_URL}")
            return jsonify({
                "error": "Ollama server is not accessible. Please ensure Ollama is running and OLLAMA_BASE_URL is correctly configured."
            }), 503  # Service Unavailable

        data = request.json
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=data,
            stream=True,
            timeout=30  # Add timeout
        )
        
        if response.status_code != 200:
            logger.error(f"Ollama returned status code {response.status_code}")
            return jsonify({"error": f"Ollama error: {response.text}"}), response.status_code
            
        return Response(
            stream_with_context(response.iter_content(chunk_size=8192)),
            content_type=response.headers.get('content-type'),
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            }
        )
    except requests.exceptions.Timeout:
        logger.error("Ollama request timed out")
        return jsonify({"error": "Request to Ollama timed out"}), 504
    except Exception as e:
        logger.error(f"Ollama chat error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/ollama/models', methods=['GET'])
def ollama_models():
    """
    List available Ollama models
    """
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Ollama models error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/openai/chat/completions', methods=['POST'])
@cross_origin()
def openai_chat():
    """
    Forward chat completions to OpenAI-compatible API
    """
    try:
        # Get API configuration from environment or request
        openai_api_url = os.getenv('OPENAI_API_URL', 'https://api.openai.com/v1')
        openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Allow overriding the API URL in the request
        data = request.json
        api_url = data.pop('api_url', openai_api_url)
        
        # Set up headers
        headers = {
            'Content-Type': 'application/json'
        }
        
        if openai_api_key:
            headers['Authorization'] = f"Bearer {openai_api_key}"
        
        # Make the API request
        response = requests.post(
            f"{api_url}/chat/completions",
            json=data,
            headers=headers,
            stream=data.get('stream', False)
        )
        
        if response.status_code != 200:
            return jsonify({"error": response.text}), response.status_code
            
        # Handle streaming response
        if data.get('stream', False):
            return Response(
                stream_with_context(response.iter_content(chunk_size=8192)),
                content_type=response.headers.get('content-type'),
                status=response.status_code
            )
        else:
            return response.json(), response.status_code
            
    except Exception as e:
        logger.error(f"OpenAI chat error: {str(e)}")
        return jsonify({"error": str(e)}), 500 