#!/usr/bin/env python3
"""
CleanupX - File organization and renaming tool.

This is a wrapper script that imports and runs the modular version of CleanupX.
"""

import sys
from cleanupx.main import main

if __name__ == "__main__":
    sys.exit(main())