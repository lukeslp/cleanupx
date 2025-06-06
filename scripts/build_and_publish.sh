#!/bin/bash
# CleanupX Build and Publish Script
# MIT License by Luke Steuber, lukesteuber.com

set -e  # Exit on any error

echo "🏗️  CleanupX Build and Publish Script"
echo "======================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Check if we're in the right directory
if [[ ! -f "setup.py" ]] || [[ ! -f "pyproject.toml" ]]; then
    print_error "Must be run from CleanupX root directory (setup.py and pyproject.toml not found)"
fi

# Check for required tools
print_step "Checking required tools..."

if ! command -v python &> /dev/null; then
    print_error "Python not found. Please install Python 3.8+"
fi

if ! command -v pip &> /dev/null; then
    print_error "pip not found. Please install pip"
fi

print_success "Required tools found"

# Install/upgrade build tools
print_step "Installing/upgrading build tools..."
pip install --upgrade pip build twine

# Clean previous builds
print_step "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info/
print_success "Build directories cleaned"

# Run tests and checks
print_step "Running pre-build checks..."

# Check imports
python -c "import cleanupx_core; cleanupx_core.print_status()" || print_error "Core module import failed"
python cleanupx.py --help > /dev/null || print_error "CLI help command failed"

print_success "Pre-build checks passed"

# Build the package
print_step "Building package..."
python -m build

if [[ ! -d "dist" ]] || [[ -z "$(ls -A dist)" ]]; then
    print_error "Build failed - no distribution files created"
fi

print_success "Package built successfully"

# Check the package
print_step "Checking package integrity..."
twine check dist/*

print_success "Package integrity check passed"

# List built files
print_step "Built files:"
ls -la dist/

# Get package info
WHEEL_FILE=$(ls dist/*.whl | head -1)
TAR_FILE=$(ls dist/*.tar.gz | head -1)

echo
echo "📦 Package Information:"
echo "   Wheel: $(basename "$WHEEL_FILE")"
echo "   Source: $(basename "$TAR_FILE")"

# Ask for confirmation before publishing
echo
read -p "🚀 Do you want to publish to PyPI? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_step "Publishing to PyPI..."
    
    # Check if we have API token
    if [[ -z "$TWINE_PASSWORD" ]] && [[ -z "$PYPI_API_TOKEN" ]]; then
        print_warning "No API token found in environment variables"
        print_warning "You may need to enter credentials manually"
    fi
    
    # Upload to PyPI
    if [[ -n "$PYPI_API_TOKEN" ]]; then
        # Use API token
        twine upload dist/* --username __token__ --password "$PYPI_API_TOKEN"
    else
        # Use interactive upload
        twine upload dist/*
    fi
    
    print_success "Package published to PyPI!"
    echo
    echo "📢 Package is now available:"
    echo "   pip install cleanupx"
    echo
else
    print_warning "Skipping PyPI publication"
    echo
    echo "To publish later, run:"
    echo "   twine upload dist/*"
fi

# Optional: Test installation from PyPI
echo
read -p "🧪 Do you want to test installation from PyPI? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_step "Testing installation from PyPI..."
    
    # Create a temporary virtual environment
    python -m venv /tmp/cleanupx_test_env
    source /tmp/cleanupx_test_env/bin/activate
    
    # Install from PyPI
    pip install cleanupx
    
    # Test basic functionality
    cleanupx --help > /dev/null || print_error "Installed package CLI test failed"
    python -c "import cleanupx_core; cleanupx_core.print_status()" || print_error "Installed package import test failed"
    
    # Cleanup
    deactivate
    rm -rf /tmp/cleanupx_test_env
    
    print_success "PyPI installation test passed"
else
    print_warning "Skipping PyPI installation test"
fi

echo
print_success "Build and publish process completed!"
echo
echo "🎉 Next steps:"
echo "   1. Create a GitHub release: https://github.com/lukeslp/cleanupx/releases/new"
echo "   2. Update conda-forge recipe if needed"
echo "   3. Announce the release on social media"
echo "   4. Update documentation if needed"
echo
echo "📚 Resources:"
echo "   PyPI: https://pypi.org/project/cleanupx/"
echo "   Documentation: https://github.com/lukeslp/cleanupx#readme"
echo "   Issues: https://github.com/lukeslp/cleanupx/issues" 