# API Building Blocks

This directory contains a collection of Flask blueprint modules that can be used to quickly build a robust API service. Each module is designed to be modular, reusable, and easily customizable for your specific needs.

## Overview

The API components include:

- **API Routes** (`api_routes.py`): Core API endpoints and health checks
- **Proxy Routes** (`proxy_routes.py`): Proxy endpoints for academic APIs (DOI, arXiv, PubMed)
- **LLM Routes** (`llm_routes.py`): Routes for interacting with Large Language Models
- **Auth Routes** (`auth_routes.py`): Authentication and OAuth integration
- **Chat Routes** (`chat_routes.py`): Chat completions with various AI providers
- **File Routes** (`file_routes.py`): File upload, serving, and manipulation
- **Admin Routes** (`admin_routes.py`): Administrative dashboard and system tools
- **Tunnel Routes** (`tunnel_routes.py`): Routes for tunneling to OpenAI-compatible APIs
- **Health Routes** (`health_routes.py`): Health check and system status endpoints

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Flask and other dependencies (see `requirements.txt`)

### Installation

1. Install the required packages:

```bash
pip install -r requirements.txt
```

2. Create a directory structure for your project:

```bash
mkdir -p myproject/{templates,static,uploads,temp,logs}
```

3. Copy the blueprint files to your project structure:

```bash
cp snippets/*.py myproject/
```

4. Create an `.env` file with your configuration values:

```
# Server configuration
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=False
PORT=5000

# Directory paths
UPLOAD_FOLDER=uploads
TEMP_FOLDER=temp
LOG_DIR=logs

# API credentials
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
ADMIN_TOKEN=your-admin-token
```

5. Create a main application file (or use the provided `app.py`):

```python
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
```

### Running the API

```bash
python app.py
```

Or with gunicorn:

```bash
gunicorn --bind 0.0.0.0:5000 'app:create_app()'
```

## Customizing the API

Each blueprint module is designed to be self-contained and easily customizable. You can modify the routes, add new endpoints, or change the behavior to suit your needs.

### Adding New Routes

1. Create a new blueprint file with your routes:

```python
from flask import Blueprint, jsonify

bp = Blueprint('my_feature', __name__)

@bp.route('/', methods=['GET'])
def my_endpoint():
    return jsonify({"message": "Hello from my feature!"})
```

2. Register the blueprint in your application:

```python
from my_feature import bp as my_feature_bp

app.register_blueprint(my_feature_bp, url_prefix='/api/v1/my-feature')
```

## Security Considerations

- Update the `SECRET_KEY` to a strong, random value in production
- Use HTTPS in production (set up with a reverse proxy like Nginx)
- Consider implementing rate limiting for public-facing APIs
- Review the admin authentication to ensure it's sufficiently secure
- Keep API keys and credentials in environment variables, not in code

## Testing

To test the API endpoints:

```bash
curl http://localhost:5000/api/v1/health
```

## License

This code is provided under the MIT License. Feel free to use, modify, and distribute it as needed. 