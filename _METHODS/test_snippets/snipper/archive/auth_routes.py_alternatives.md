# Alternatives for auth_routes.py

```python
# CORS Configuration
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
```
This snippet is unique for its configuration of Cross-Origin Resource Sharing (CORS), tailored for development and production environments using environment variables. It's essential for handling cross-domain requests in web APIs but less central than token handling.

```python
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
This alternative snippet demonstrates the core OAuth token exchange logic, including error handling and integration with an external provider. It's a full route handler that's important for the authentication flow but more complex than the best version, making it a good secondary example.