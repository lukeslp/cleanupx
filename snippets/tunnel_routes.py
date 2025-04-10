from flask import Blueprint, request, jsonify, Response, stream_with_context
import requests
import logging
import os
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('tunnel', __name__)

# Constants
TUNNEL_SERVICE_URL = os.getenv('TUNNEL_SERVICE_URL', 'https://api.yourdomain.com')

@bp.route('/chat/completions', methods=['POST'])
def chat_completions():
    """
    Forward chat completions to an OpenAI-compatible endpoint
    """
    try:
        data = request.json
        logger.info("Forwarding chat completion request")
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Forward the auth header if present
        auth_header = request.headers.get('Authorization')
        if auth_header:
            headers['Authorization'] = auth_header
        
        # Forward the request
        response = requests.post(
            f"{TUNNEL_SERVICE_URL}/v1/chat/completions",
            json=data,
            headers=headers,
            stream=data.get('stream', False)
        )
        
        # If streaming response
        if data.get('stream', False):
            def generate():
                for chunk in response.iter_lines():
                    if chunk:
                        yield f"{chunk.decode('utf-8')}\n"

            return Response(
                stream_with_context(generate()),
                content_type=response.headers.get('content-type', 'text/event-stream')
            )
        else:
            # Return regular response
            return response.json(), response.status_code
            
    except Exception as e:
        logger.error(f"Error in chat completions: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/completions', methods=['POST'])
def completions():
    """
    Forward text completions to an OpenAI-compatible endpoint
    """
    try:
        data = request.json
        logger.info("Forwarding text completion request")
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Forward the auth header if present
        auth_header = request.headers.get('Authorization')
        if auth_header:
            headers['Authorization'] = auth_header
        
        # Forward the request
        response = requests.post(
            f"{TUNNEL_SERVICE_URL}/v1/completions",
            json=data,
            headers=headers,
            stream=data.get('stream', False)
        )
        
        # If streaming response
        if data.get('stream', False):
            def generate():
                for chunk in response.iter_lines():
                    if chunk:
                        yield f"{chunk.decode('utf-8')}\n"

            return Response(
                stream_with_context(generate()),
                content_type=response.headers.get('content-type', 'text/event-stream')
            )
        else:
            # Return regular response
            return response.json(), response.status_code
            
    except Exception as e:
        logger.error(f"Error in completions: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/models', methods=['GET'])
def list_models():
    """
    Forward model list request
    """
    try:
        headers = {}
        
        # Forward the auth header if present
        auth_header = request.headers.get('Authorization')
        if auth_header:
            headers['Authorization'] = auth_header
            
        response = requests.get(
            f"{TUNNEL_SERVICE_URL}/v1/models",
            headers=headers
        )
        
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/embeddings', methods=['POST'])
def embeddings():
    """
    Forward embeddings request
    """
    try:
        data = request.json
        logger.info("Forwarding embeddings request")
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Forward the auth header if present
        auth_header = request.headers.get('Authorization')
        if auth_header:
            headers['Authorization'] = auth_header
        
        # Forward the request
        response = requests.post(
            f"{TUNNEL_SERVICE_URL}/v1/embeddings",
            json=data,
            headers=headers
        )
        
        return response.json(), response.status_code
            
    except Exception as e:
        logger.error(f"Error in embeddings: {str(e)}")
        return jsonify({"error": str(e)}), 500 