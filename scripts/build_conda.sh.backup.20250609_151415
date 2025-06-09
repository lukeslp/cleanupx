#!/bin/bash
# CleanupX Conda Build Script
# MIT License by Luke Steuber

set -e

echo "🐍 Building CleanupX conda package..."

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ conda not found. Please install Miniconda or Anaconda"
    exit 1
fi

# Check if conda-build is installed
if ! conda list conda-build &> /dev/null; then
    echo "📦 Installing conda-build..."
    conda install conda-build conda-verify -y
fi

# Create conda-recipe directory if it doesn't exist
if [[ ! -d "conda-recipe" ]]; then
    echo "❌ conda-recipe directory not found"
    exit 1
fi

# Clean previous builds
echo "🧹 Cleaning previous conda builds..."
rm -rf conda-dist/

# Build the package
echo "🏗️  Building conda package..."
cd conda-recipe
conda build . --output-folder ../conda-dist

echo "✅ Conda package built successfully!"

# List built packages
echo "📦 Built packages:"
find ../conda-dist -name "*.tar.bz2" -o -name "*.conda"

echo ""
echo "🧪 To test the package:"
echo "conda install --use-local cleanupx"
echo ""
echo "🚀 To upload to conda-forge:"
echo "1. Fork conda-forge/staged-recipes"
echo "2. Add recipe to recipes/cleanupx/"
echo "3. Submit pull request" 