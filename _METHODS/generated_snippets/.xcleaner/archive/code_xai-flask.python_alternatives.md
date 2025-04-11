# Alternatives for code_xai-flask.python

** This includes the alternative implementation of the `XAIChat` class, which is similar but slightly more streamlined (e.g., fewer imports in the original context). It provides a variant for comparison, emphasizing the same core structure but potentially for different use cases like a CLI interface.

  ```
  class XAIChat:
      def __init__(self, api_key: str):
          """Initialize the X.AI client with the provided API key."""
          self.client = OpenAI(
              api_key=api_key,
              base_url="https://api.x.ai/v1"
          )
          self.conversation_history = [
              {
                  "role": "system",
                  "content": "You are Grok, a chatbot inspired by the Hitchhiker's Guide to the Galaxy."
              }
          ]
      
      def clear_conversation(self):
          """Clear the conversation history, keeping only the system message."""
          self.conversation_history = [
  ```