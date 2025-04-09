#!/usr/bin/env python3
"""
CleanupX - File organization and renaming tool.

This is a wrapper script that imports and runs the modular version of CleanupX.
"""

import sys
import logging
from cleanupx.ui.cli import run_cli

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    sys.exit(run_cli())