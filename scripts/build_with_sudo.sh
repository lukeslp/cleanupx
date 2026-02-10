#!/bin/bash
# CleanupX Build Script - Sudo Enabled Version
# MIT License by Luke Steuber

set -e

echo "🏗️  Building CleanupX package with sudo privileges..."

# Clean previous builds
sudo rm -rf build/ dist/ *.egg-info/

# Install build tools with sudo
sudo pip install --upgrade build twine

# Build package
python -m build

# Check package
twine check dist/*

echo "✅ Package built successfully with sudo!"
echo "Files created:"
ls -la dist/

echo ""
echo "To publish to PyPI:"
echo "twine upload dist/*"
