# Alternatives for auth_routes.py

1. **Helper function for token extraction**:
   ```
   def _get_bearer_token():
       """
       Helper function to extract access token from Authorization header: 'Bearer <token>'
       """
       auth_header = request.headers.get('Authorization')
       if auth_header and auth_header.startswith('Bearer '):
           return auth_header.split(' ')[1]
       return None
   ```
   *This is a concise, custom utility for securely extracting bearer tokens, which is unique for its simplicity and direct application in authentication routes.*

2. **CORS configuration for the blueprint**:
   ```
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
   *This snippet is unique for its detailed CORS setup, tailored for development and production environments, ensuring secure cross-origin requests in an OAuth context.*