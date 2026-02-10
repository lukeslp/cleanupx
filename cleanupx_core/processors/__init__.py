"""
CleanupX Processors Module

Contains both legacy and integrated file processing functionality.
"""

# Try to import integrated processors first
try:
    from .integrated.cleanup import (
        cleanup_directory,
        CleanupProcessor,
        XAIIntegration,
        ImageProcessor,
        FilenameScrambler
    )
    INTEGRATED_AVAILABLE = True
except ImportError:
    INTEGRATED_AVAILABLE = False

# Export based on what's available
if INTEGRATED_AVAILABLE:
    __all__ = [
        'cleanup_directory',
        'CleanupProcessor',
        'XAIIntegration',
        'ImageProcessor',
        'FilenameScrambler',
        'INTEGRATED_AVAILABLE'
    ]
else:
    __all__ = ['INTEGRATED_AVAILABLE'] 