"""
CleanupX Integrated Processors

Contains the new comprehensive processing functionality that integrates
all features from storage and _METHODS.
"""

try:
    from .cleanup import (
        cleanup_directory,
        CleanupProcessor,
        XAIIntegration,
        ImageProcessor,
        FilenameScrambler
    )
    __all__ = [
        'cleanup_directory',
        'CleanupProcessor',
        'XAIIntegration',
        'ImageProcessor',
        'FilenameScrambler'
    ]
except ImportError as e:
    print(f"Warning: Integrated processors not available: {e}")
    __all__ = [] 