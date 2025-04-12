#!/usr/bin/env python3
"""
Anthropic API Chat Implementation

This module provides a simple interface to the Anthropic Claude API for streaming chat responses.
It supports text-based conversations and uses a hard-coded API key.
Requires the 'anthropic' package to be installed (pip install anthropic).

Hard-coded credentials:
    API_KEY: Anthropic API key (keep it secure in production!)
    BASE_URL: Base URL for Anthropic API requests (if different from the default)
"""
!!! TEMPLATE - EDIT THIS - KEEP THE HARD CODED CREDENTIALS

import os
import sys
import json
import time
import signal
import logging
from contextlib import contextmanager
from typing import Dict, Any, Optional, Generator

import anthropic

# Hard-coded credentials
API_KEY = "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"
BASE_URL = "https://api.anthropic.com"  # Change this if you use a custom base URL

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class TimeoutError(Exception):
    """Exception raised when an operation times out."""
    pass


@contextmanager
def timeout(seconds: int):
    """
    Context manager that raises a TimeoutError if execution takes longer than specified seconds.
    
    Example:
        with timeout(10):
            do_something()
    """
    def signal_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


class AnthropicChatAPI:
    """
    Simplified utility to interact with the Anthropic API for streaming chat responses.
    
    This class maintains conversation history and constructs a prompt for Anthropic's API.
    """
    def __init__(self, api_key: str = API_KEY, base_url: Optional[str] = BASE_URL):
        # Initialize the Anthropic client with hard-coded credentials
        self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        self.conversation_history = []

    def stream_chat_response(
        self,
        prompt: str,
        max_tokens: int = 1024,
        model: str = "claude-3-opus-20240229"
    ) -> Generator[str, None, None]:
        """
        Stream a chat response from the Anthropic API.
        
        Args:
            prompt: User's input message.
            max_tokens: Maximum tokens for the generated response.
            model: The Anthropic Claude model to use.
            
        Yields:
            Chunks of text as they arrive in real time.
        """
        # Append the user message to the conversation history
        self.conversation_history.append({"role": "user", "text": prompt})
        
        try:
            # Anthropic's API expects a single prompt with the conversation context.
            full_prompt = self._build_prompt()
            with self.client.completions.stream(
                model=model,
                prompt=full_prompt,
                max_tokens_to_sample=max_tokens,
            ) as stream:
                response_text = ""
                for chunk in stream:
                    # Each chunk is a dictionary; we extract the generated text.
                    text_chunk = chunk.get("completion", "")
                    response_text += text_chunk
                    yield text_chunk
                # Append the assistant's full response to conversation history
                self.conversation_history.append({"role": "assistant", "text": response_text})
        except anthropic.APIError as e:
            logger.error(f"API Error: {e}")
            yield f"\nAPI Error: {e}"
        except anthropic.APIConnectionError as e:
            logger.error(f"Connection Error: {e}")
            yield f"\nConnection Error: {e}"
        except anthropic.AuthenticationError as e:
            logger.error("Authentication Error: Please check your API key.")
            yield "\nAuthentication Error: Please check that your API key is valid."
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            yield f"\nUnexpected error: {e}"
    
    def _build_prompt(self) -> str:
        """
        Construct the conversation prompt for Anthropic API based on conversation history.
        
        Returns:
            A single prompt string that includes system instructions and conversation history.
        """
        system_prompt = "You are a helpful assistant.\n\n"
        conversation_text = ""
        for msg in self.conversation_history:
            if msg["role"] == "user":
                conversation_text += f"\n\nHuman: {msg['text']}\n\n"
            elif msg["role"] == "assistant":
                conversation_text += f"\n\nAssistant: {msg['text']}\n\n"
        return system_prompt + conversation_text

    def clear_conversation(self):
        """Clear the conversation history."""
        self.conversation_history = []


def call_anthropic_api(
    prompt: str,
    model: str = "claude-3-opus-20240229",
    max_tokens: int = 1024,
    timeout_seconds: int = 30
) -> str:
    """
    Call the Anthropic API to get a chat response using streaming.
    
    Args:
        prompt: The user's prompt.
        model: The Anthropic model to use.
        max_tokens: Maximum tokens to sample.
        timeout_seconds: Timeout for the API call.
        
    Returns:
        The full response text generated by the API.
    """
    chat_api = AnthropicChatAPI()
    full_response = ""
    try:
        with timeout(timeout_seconds):
            for chunk in chat_api.stream_chat_response(prompt, max_tokens, model):
                full_response += chunk
    except TimeoutError as te:
        logger.error(te)
        return f"Error: {te}"
    return full_response


if __name__ == "__main__":
    # Example usage of the Anthropic API chat utility with hard-coded credentials.
    prompt = "Explain the theory of relativity in simple terms."
    print("Anthropic API Response:")
    response = call_anthropic_api(prompt)
    print(response)