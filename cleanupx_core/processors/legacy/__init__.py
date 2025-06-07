"""
CleanupX Legacy Processors

Contains the original legacy functionality for backward compatibility.
These modules have been migrated from storage/legacy_methods.
"""

try:
    # Import the legacy processors that are now included in the package
    from . import deduper
    from . import xsnipper
    
    # Try to import additional legacy modules if they exist
    try:
        from . import scrambler
    except ImportError:
        scrambler = None
        
    try:
        from . import xnamer
    except ImportError:
        xnamer = None
        
    try:
        from . import xcitation
    except ImportError:
        xcitation = None
        
    try:
        from . import ximagenamer
    except ImportError:
        ximagenamer = None
    
    # Export available modules
    __all__ = ['deduper', 'xsnipper']
    
    # Add optional modules if they're available
    if scrambler:
        __all__.append('scrambler')
    if xnamer:
        __all__.append('xnamer')
    if xcitation:
        __all__.append('xcitation')
    if ximagenamer:
        __all__.append('ximagenamer')
    
except ImportError as e:
    print(f"Warning: Legacy processors not available: {e}")
    __all__ = [] 