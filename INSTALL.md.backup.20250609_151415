# CleanupX Installation Guide

Complete installation instructions for CleanupX across different platforms and package managers.

## 🚀 Quick Install

### PyPI (Recommended)
```bash
# Basic installation
pip install cleanupx

# With all optional features
pip install cleanupx[all]

# Specific feature sets
pip install cleanupx[ai,documents,images]
```

### Conda/Mamba
```bash
# From conda-forge (when available)
conda install -c conda-forge cleanupx

# Or with mamba
mamba install -c conda-forge cleanupx
```

## 📦 Installation Options

### Feature-Specific Installations

#### Core Only (Minimal)
```bash
pip install cleanupx
```
**Includes**: Basic file processing, organization, deduplication

#### AI Features
```bash
pip install cleanupx[ai]
```
**Adds**: OpenAI API integration, AI-powered analysis

#### Document Processing
```bash
pip install cleanupx[documents]
```
**Adds**: PDF processing, Word document support

#### Enhanced Image Support
```bash
pip install cleanupx[images]
```
**Adds**: HEIC/HEIF support, advanced image formats

#### Archive Support
```bash
pip install cleanupx[archives]
```
**Adds**: RAR archive processing

#### Development Tools
```bash
pip install cleanupx[dev]
```
**Adds**: Testing, linting, formatting tools

#### Everything
```bash
pip install cleanupx[all]
```
**Includes**: All optional features combined

## 🛠️ Development Installation

### From Source
```bash
# Clone the repository
git clone https://github.com/lukeslp/cleanupx.git
cd cleanupx

# Install in development mode
pip install -e .[dev]

# Verify installation
cleanupx --help
cleanupx-status
```

### Pre-commit Hooks (Optional)
```bash
# Install pre-commit hooks for development
pip install pre-commit
pre-commit install
```

## 🔧 Platform-Specific Instructions

### Ubuntu/Debian
```bash
# Update package list
sudo apt update

# Install Python and pip (if not already installed)
sudo apt install python3 python3-pip

# Install CleanupX
pip3 install cleanupx[all]

# For system-wide installation
sudo pip3 install cleanupx[all]
```

### macOS
```bash
# Using Homebrew (recommended)
brew install python3
pip3 install cleanupx[all]

# Using MacPorts
sudo port install python311
pip3.11 install cleanupx[all]
```

### Windows
```powershell
# Using Python from python.org
python -m pip install cleanupx[all]

# Using Chocolatey
choco install python3
python -m pip install cleanupx[all]

# Using Windows Store Python
python3 -m pip install cleanupx[all]
```

### CentOS/RHEL/Fedora
```bash
# CentOS/RHEL
sudo yum install python3 python3-pip
pip3 install cleanupx[all]

# Fedora
sudo dnf install python3 python3-pip
pip3 install cleanupx[all]
```

### Arch Linux
```bash
# Install Python and pip
sudo pacman -S python python-pip

# Install CleanupX
pip install cleanupx[all]

# Or from AUR (when available)
yay -S cleanupx
```

## 🐍 Python Version Requirements

- **Python 3.8+** (recommended: Python 3.11+)
- **pip 21.0+** (for proper dependency resolution)

### Check Your Python Version
```bash
python --version
pip --version
```

### Upgrade pip if needed
```bash
python -m pip install --upgrade pip
```

## 🔑 Environment Configuration

### Required for AI Features
```bash
# Set your X.AI API key
export XAI_API_KEY="your-xai-api-key"

# Or create a .env file
echo "XAI_API_KEY=your-xai-api-key" > .env
```

### Optional Configuration
```bash
# Custom output directory
export CLEANUP_OUTPUT_DIR="/path/to/output"

# Log level
export CLEANUP_LOG_LEVEL="INFO"
```

## ✅ Verify Installation

### Basic Verification
```bash
# Check if CleanupX is installed
cleanupx --help

# Check module status
cleanupx-status

# Test core functionality
python -c "import cleanupx_core; cleanupx_core.print_status()"
```

### Expected Output
```
CleanupX Core v2.0.0
  Integrated Processors: ✓
  XAI API Support: ✓  
  Legacy Processors: ✓
  Module Path: /path/to/cleanupx_core
```

### Test Run
```bash
# Test with sample directory
mkdir test_files
echo "test content" > test_files/test.txt
cleanupx organize --dir test_files
```

## 🔄 Upgrading

### From PyPI
```bash
# Upgrade to latest version
pip install --upgrade cleanupx

# Upgrade with all features
pip install --upgrade cleanupx[all]
```

### From Development Source
```bash
cd cleanupx
git pull origin main
pip install -e .[dev]
```

## 🗑️ Uninstalling

```bash
# Remove CleanupX
pip uninstall cleanupx

# Clean up any remaining files
rm -rf ~/.cleanupx  # Config files (if any)
```

## 🐛 Troubleshooting

### Common Issues

#### ImportError: No module named 'cleanupx_core'
```bash
# Reinstall cleanupx
pip uninstall cleanupx
pip install cleanupx
```

#### Permission Denied on Linux/macOS
```bash
# Use user installation
pip install --user cleanupx[all]

# Add to PATH if needed
export PATH="$HOME/.local/bin:$PATH"
```

#### SSL Certificate Errors
```bash
# Upgrade certificates
pip install --upgrade certifi

# Or use trusted host
pip install --trusted-host pypi.org --trusted-host pypi.python.org cleanupx
```

#### Missing Dependencies
```bash
# Install with all dependencies
pip install cleanupx[all]

# Force reinstall dependencies
pip install --force-reinstall cleanupx[all]
```

### Platform-Specific Issues

#### Windows: 'cleanupx' is not recognized
```powershell
# Add Python Scripts to PATH
# Or use full path
python -m cleanupx --help
```

#### macOS: Permission denied
```bash
# Use user installation
pip3 install --user cleanupx[all]

# Update PATH in ~/.zshrc or ~/.bash_profile
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

#### Linux: Command not found
```bash
# Check if ~/.local/bin is in PATH
echo $PATH

# Add to PATH if missing
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## 🏗️ Building from Source

### Prerequisites
```bash
# Install build tools
pip install build twine

# Install development dependencies
pip install -e .[dev]
```

### Build Process
```bash
# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Build package
python -m build

# Check package
twine check dist/*
```

### Local Installation
```bash
# Install from local build
pip install dist/cleanupx-2.0.0-py3-none-any.whl
```

## 📊 Installation Verification Script

Create and run this verification script:

```python
#!/usr/bin/env python3
"""CleanupX Installation Verification Script"""

def verify_installation():
    """Verify CleanupX installation and report status."""
    print("🔍 Verifying CleanupX Installation...\n")
    
    # Test imports
    try:
        import cleanupx_core
        print("✅ Core module imported successfully")
        
        # Get status
        status = cleanupx_core.get_status()
        print(f"📦 Version: {status['version']}")
        print(f"🔧 Integrated Processors: {'✅' if status['integrated_available'] else '❌'}")
        print(f"🤖 XAI API Support: {'✅' if status['xai_api_available'] else '❌'}")
        print(f"📂 Legacy Processors: {'✅' if status['legacy_available'] else '❌'}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test CLI
    try:
        import subprocess
        result = subprocess.run(['cleanupx', '--help'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ CLI command working")
        else:
            print("❌ CLI command failed")
            return False
    except Exception as e:
        print(f"❌ CLI test error: {e}")
        return False
    
    print("\n🎉 Installation verified successfully!")
    return True

if __name__ == "__main__":
    verify_installation()
```

Save as `verify_install.py` and run:
```bash
python verify_install.py
```

## 📞 Getting Help

- **Documentation**: [README.md](README.md)
- **Issues**: [GitHub Issues](https://github.com/lukeslp/cleanupx/issues)
- **Installation Problems**: [GitHub Discussions](https://github.com/lukeslp/cleanupx/discussions)
- **Email Support**: luke@lukesteuber.com

---

**Happy Processing!** 🚀

The CleanupX team is here to help if you encounter any installation issues. 