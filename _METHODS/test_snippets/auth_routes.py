from flask import Blueprint, request, jsonify
from flask_cors import CORS
import requests
import logging
import random
import string
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bp = Blueprint('auth', __name__)

# Enable CORS for all routes in this blueprint
CORS(bp, resources={
    r"/*": {
        "origins": [
            os.getenv('ALLOWED_ORIGIN', 'https://yourdomain.com'),
            "http://localhost:*",   # local dev
            "https://*.ngrok.app"   # ngrok
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Utility function for random string generation
def generate_random_string(length=16):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

# Helper function to extract bearer token
def _get_bearer_token():
    """
    Helper function to extract access token from Authorization header: 'Bearer <token>'
    """
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    return None

# OAuth Integration Example - Customize for your specific provider
@bp.route('/oauth/authorize')
def oauth_authorize():
    """Redirect the user to the OAuth provider's authorization page"""
    client_id = os.getenv('OAUTH_CLIENT_ID', '')
    redirect_uri = os.getenv('OAUTH_REDIRECT_URI', '')
    scope = 'profile email'
    state = generate_random_string()

    auth_url = (
        f"https://oauth-provider.com/oauth/authorize?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"state={state}"
    )
    return jsonify({'authorization_url': auth_url})

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

@bp.route('/user', methods=['GET'])
def get_user():
    """Get user identity information"""
    access_token = _get_bearer_token()
    if not access_token:
        return jsonify({'error': 'Authorization token required'}), 401

    try:
        user_url = "https://oauth-provider.com/api/user"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(user_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to fetch user: {response.text}")
            return jsonify({'error': 'Failed to fetch user'}), response.status_code

        user_data = response.json()
        return jsonify({
            "id": user_data.get("id"),
            "email": user_data.get("email"),
            "name": user_data.get("name"),
            "profile_url": user_data.get("profile_url")
        })

    except Exception as e:
        logger.exception("Error fetching user data")
        return jsonify({'error': str(e)}), 500

@bp.route('/validate', methods=['POST'])
def validate_token():
    """Validate an existing access token"""
    try:
        data = request.json
        access_token = data.get('token')
        if not access_token:
            return jsonify({'error': 'No token provided'}), 400

        validate_url = "https://oauth-provider.com/api/validate"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(validate_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Invalid token: {response.text}")
            return jsonify({'error': 'Invalid token', 'valid': False}), 401

        return jsonify({'valid': True})

    except Exception as e:
        logger.exception("Error validating token")
        return jsonify({'error': str(e), 'valid': False}), 500 