# X.AI API Usage Examples

This snippet demonstrates how CleanupX interacts with the X.AI API for both text and vision tasks.

```python
from storage.xai_unified import XAIClient

client = XAIClient()  # API key taken from XAI_API_KEY env var
messages = [{"role": "system", "content": "Hello!"}]

# Simple chat completion
response = client.chat(messages)
print(response["choices"][0]["message"]["content"])
```

Image alt text generation with streaming:

```python
from storage.xai_alt import generate_alt_text

result = generate_alt_text("image.jpg")
print(result["alt_text"])
```
