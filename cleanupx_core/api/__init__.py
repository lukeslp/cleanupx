"""
CleanupX API Module

Provides unified API access for external services including X.AI integration.
"""

from .xai_unified import get_xai_client, analyze_code_snippet, find_duplicates

__all__ = ['get_xai_client', 'analyze_code_snippet', 'find_duplicates'] 