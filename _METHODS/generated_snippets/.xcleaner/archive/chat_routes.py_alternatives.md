# Alternatives for chat_routes.py

These are alternative snippets that are also important and unique but are more specialized. They include provider-specific implementations and a utility decorator, providing context to the best version.

1. **openai_chat_completion Function (Provider-Specific API Handling)**:  
   This snippet is unique for its direct integration with the OpenAI API, including streaming response generation and error logging. It shows how the code forwards requests and formats responses as Server-Sent Events (SSE) for streaming.
   
   ```
   def openai_chat_completion(data, stream=True):
       """
       Forward chat completions to OpenAI compatible API
       """
       try:
           data_copy = data.copy()
           api_key = data_copy.pop('api_key', OPENAI_API_KEY)
           if not api_key:
               return jsonify({"error": "OpenAI API key not configured"}), 401
           
           headers = {
               'Authorization': f'Bearer {api_key}',
               'Content-Type': 'application/json'
           }
           
           timeout = data_copy.pop('timeout', 60)
           
           response = requests.post(
               f"{OPENAI_API_URL}/chat/completions",
               json=data_copy,
               headers=headers,
               stream=stream,
               timeout=timeout
           )
           
           if response.status_code != 200:
               error_info = response.json() if response.text else {"raw_text": response.text[:500]}
               logger.error(f"OpenAI API error: {error_info}")
               return jsonify({"error": "OpenAI API error", "details": error_info}), response.status_code
           
           if stream:
               def generate():
                   for chunk in response.iter_lines():
                       if chunk:
                           chunk_text = chunk.decode('utf-8')
                           yield f"data: {chunk_text}\n\n"  # Proper SSE formatting
               return Response(
                   stream_with_context(generate()),
                   content_type='text/event-stream',
                   headers={'Cache-Control': 'no-cache'}
               )
           else:
               return jsonify(response.json())
       except requests.RequestException as e:
           logger.error(f"OpenAI request error: {str(e)}")
           return jsonify({"error": f"OpenAI request error: {str(e)}"}), 502
   ```

2. **anthropic_chat_completion Function (Format Conversion and Streaming)**:  
   This is unique for converting OpenAI-style requests to Anthropic's format (e.g., handling 'system' messages) and managing streaming. It highlights adaptability between APIs, which is a key feature of this code.
   
   ```
   def anthropic_chat_completion(data, stream=True):
       """
       Forward chat completions to Anthropic API
       """
       try:
           data_copy = data.copy()
           api_key = data_copy.pop('api_key', ANTHROPIC_API_KEY)
           if not api_key:
               return jsonify({"error": "Anthropic API key not configured"}), 401
           
           if 'messages' in data_copy:
               messages = data_copy.pop('messages', [])
               system_message = next((m['content'] for m in messages if m['role'] == 'system'), None)
               anthropic_data = {
                   "model": data_copy.get('model', 'claude-3-opus-20240229'),
                   "max_tokens": data_copy.get('max_tokens', 1024),
                   "temperature": data_copy.get('temperature', 0.7),
                   "stream": stream,
                   "messages": [m for m in messages if m['role'] != 'system']
               }
               if system_message:
                   anthropic_data["system"] = system_message
               data_copy = anthropic_data
           
           headers = {
               'x-api-key': api_key,
               'anthropic-version': '2023-06-01',
               'Content-Type': 'application/json'
           }
           
           timeout = data_copy.pop('timeout', 60)
           
           response = requests.post(
               f"{ANTHROPIC_API_URL}/messages",
               json=data_copy,
               headers=headers,
               stream=stream,
               timeout=timeout
           )
           
           if response.status_code != 200:
               error_info = response.json() if response.text else {"raw_text": response.text[:500]}
               logger.error(f"Anthropic API error: {error_info}")
               return jsonify({"error": "Anthropic API error", "details": error_info}), response.status_code
           
           if stream:
               def generate():
                   for chunk in response.iter_lines():
                       if chunk:
                           chunk_text = chunk.decode('utf-8')
                           yield f"data: {chunk_text}\n\n"  # Proper SSE formatting
               return Response(
                   stream_with_context(generate()),
                   content_type='text/event-stream',
                   headers={'Cache-Control': 'no-cache'}
               )
           else:
               return jsonify(response.json())
       except requests.RequestException as e:
           logger.error(f"Anthropic request error: {str(e)}")
           return jsonify({"error": f"Anthropic request error: {str(e)}"}), 502
   ```

3. **require_json Decorator (Utility for Input Validation)**:  
   This is a simple yet unique helper that ensures all routes expect JSON, with error handling. It's important for maintaining consistency across endpoints.
   
   ```
   def require_json(f):
       @wraps(f)
       def decorated_function(*args, **kwargs):
           if not request.is_json:
               return jsonify({"error": "Request must be JSON"}), 415
           return f(*args, **kwargs)
       return decorated_function
   ```