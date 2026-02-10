#!/bin/bash
# CleanupX Build Script
# MIT License by Luke Steuber

set -e

echo "🏗️  Building CleanupX package..."

# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Install build tools
pip install --upgrade build twine

# Build package
python -m build

# Check package
twine check dist/*

echo "✅ Package built successfully!"
echo "Files created:"
ls -la dist/

echo ""
echo "To publish to PyPI:"
echo "twine upload dist/*" 