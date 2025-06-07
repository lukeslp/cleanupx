"""
cleanupx Core Module - Unified File Processing Framework

This module provides comprehensive file processing capabilities including:
- AI-powered code analysis and deduplication
- Image processing with accessibility features
- File organization and metadata management
- Privacy utilities like filename scrambling

MIT License by Luke Steuber, lukesteuber.com, assisted.site
luke@lukesteuber.com; bluesky @lukesteuber.com
linkedin https://www.linkedin.com/in/lukesteuber/
"""

import logging
import sys
from pathlib import Path

# Configure logging for the module
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Module version
__version__ = "0.8.2"
__author__ = "Luke Steuber"
__email__ = "luke@lukesteuber.com"
__license__ = "MIT"

# Add current directory to Python path for imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import main functionality with fallback handling
try:
    from .processors.integrated.cleanup import (
        cleanup_directory,
        CleanupProcessor,
        XAIIntegration,
        ImageProcessor,
        FilenameScrambler
    )
    INTEGRATED_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Integrated processors not available: {e}")
    INTEGRATED_AVAILABLE = False

try:
    from .api.xai_unified import get_xai_client, analyze_code_snippet, find_duplicates
    XAI_API_AVAILABLE = True
except ImportError as e:
    logger.warning(f"XAI API not available: {e}")
    XAI_API_AVAILABLE = False

try:
    from .processors.legacy import deduper, xsnipper, scrambler
    LEGACY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Legacy processors not available: {e}")
    LEGACY_AVAILABLE = False

# Export main functionality
if INTEGRATED_AVAILABLE:
    # Primary exports - integrated functionality
    __all__ = [
        'cleanup_directory',
        'CleanupProcessor',
        'XAIIntegration', 
        'ImageProcessor',
        'FilenameScrambler',
        'get_xai_client',
        'analyze_code_snippet',
        'find_duplicates',
        'INTEGRATED_AVAILABLE',
        'XAI_API_AVAILABLE',
        'LEGACY_AVAILABLE'
    ]
else:
    # Fallback exports
    __all__ = [
        'XAI_API_AVAILABLE',
        'LEGACY_AVAILABLE',
        'INTEGRATED_AVAILABLE'
    ]

# Module status
def get_status():
    """Get module availability status."""
    return {
        'version': __version__,
        'integrated_available': INTEGRATED_AVAILABLE,
        'xai_api_available': XAI_API_AVAILABLE,
        'legacy_available': LEGACY_AVAILABLE,
        'module_path': str(current_dir)
    }

def print_status():
    """Print module status for debugging."""
    status = get_status()
    print(f"cleanupx Core v{status['version']}")
    print(f"  Integrated Processors: {'✓' if status['integrated_available'] else '✗'}")
    print(f"  XAI API Support: {'✓' if status['xai_api_available'] else '✗'}")
    print(f"  Legacy Processors: {'✓' if status['legacy_available'] else '✗'}")
    print(f"  Module Path: {status['module_path']}")

if __name__ == "__main__":
    print_status() 