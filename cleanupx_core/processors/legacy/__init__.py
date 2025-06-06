"""
CleanupX Legacy Processors

Contains the original _METHODS functionality for backward compatibility.
Now imports from storage/legacy_methods.
"""

try:
    import sys
    import os
    # Add storage/legacy_methods to path
    current_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    storage_path = os.path.join(project_root, 'storage', 'legacy_methods')
    
    if storage_path not in sys.path:
        sys.path.append(storage_path)
    
    # Import the legacy methods
    import deduper
    import xsnipper  
    import scrambler
    import xnamer
    import xcitation
    import ximagenamer
    
    __all__ = ['deduper', 'xsnipper', 'scrambler', 'xnamer', 'xcitation', 'ximagenamer']
    
except ImportError as e:
    print(f"Warning: Legacy processors not available: {e}")
    __all__ = [] 