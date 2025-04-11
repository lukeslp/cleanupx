# Alternatives for llm_routes.py

These are alternative snippets that are also noteworthy but less comprehensive than the best version. They highlight variations in functionality, such as listing models or handling OpenAI-compatible APIs, and include unique elements like environment variable configuration and streaming options.

1. **Alternative 1: OpenAI Chat Completions Route**  
   This snippet is unique for its flexibility in overriding API URLs via requests, handling API keys from environment variables, and conditionally managing streaming responses. It's similar to the best version but tailored for OpenAI compatibility.
   
   ```python
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
   ```

2. **Alternative 2: Ollama Models Route**  
   This is a simpler snippet, unique for its focus on retrieving and returning data (e.g., listing models) without streaming. It's important for its straightforward error handling and use of environment variables, making it a good example of a basic GET route.
   
   ```python
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
   ```