# cleanupx v0.8.0 - Prerelease 🚧

**A prerelease version of cleanupx is now live on PyPI for testing and feedback!**

This prerelease features consistent branding, integrated legacy processors, and GitHub sponsor links while maintaining all the comprehensive file processing capabilities.

## 🎉 Major Features

### AI-Powered Processing
- **X.AI API integration** for intelligent file analysis and content understanding
- **Automated image alt text generation** for accessibility compliance
- **Smart duplicate detection** using advanced algorithms beyond simple hashing
- **Content-aware file organization** with AI assistance

### Professional CLI Interface
- **Rich terminal output** with beautiful progress bars and colored text
- **Interactive prompts** for better user experience
- **Comprehensive help system** with detailed command documentation
- **Status monitoring** with `cleanupx-status` command

### Privacy & Organization Tools
- **Filename scrambling** for sensitive data with reversal logs
- **Advanced file categorization** by type and content
- **Citation extraction** from documents and research papers
- **Batch processing** with progress tracking

### Production-Grade Package
- **PyPI distribution** - Install with `pip install cleanupx`
- **Cross-platform compatibility** (Windows, macOS, Linux)
- **Python 3.8+ support** with proper version constraints
- **Optional dependencies** for feature-specific installations
- **Comprehensive documentation** and guides

## 📦 Installation

### Quick Start
```bash
# Basic installation
pip install cleanupx

# With all optional features
pip install cleanupx[all]

# Feature-specific installations
pip install cleanupx[ai,documents,images]
```

### Verify Installation
```bash
# Check status
cleanupx-status

# View available commands
cleanupx --help
```

## 🚀 Usage Examples

### Comprehensive Processing
```bash
# Process directory with all features
cleanupx comprehensive --dir ./my_files

# Process images only
cleanupx images --dir ./photos

# Privacy: scramble filenames
cleanupx scramble --dir ./sensitive_data
```

### Legacy Commands (Backward Compatible)
```bash
# File deduplication
cleanupx deduplicate --dir ./downloads

# Extract code snippets
cleanupx extract --dir ./projects

# Organize files
cleanupx organize --dir ./documents
```

## 🔧 Configuration

### Required for AI Features
```bash
# Set your X.AI API key
export XAI_API_KEY="your-xai-api-key"

# Or create a .env file
echo "XAI_API_KEY=your-xai-api-key" > .env
```

### Optional Settings
```bash
# Custom output directory
export CLEANUP_OUTPUT_DIR="/path/to/output"

# Adjust log level
export CLEANUP_LOG_LEVEL="INFO"
```

## 🆕 What's New in v0.8.0

### Branding & Consistency
- **Consistent lowercase "cleanupx" branding** throughout all documentation and code
- **Updated CLI commands** to use `cleanupx` instead of `python cleanupx.py`
- **GitHub sponsor integration** with funding links and connect table
- **Professional README** with improved installation instructions

### Legacy Processor Integration
- **Migrated deduper.py** from storage to cleanupx_core/processors/legacy/
- **Migrated xsnipper.py** from storage to cleanupx_core/processors/legacy/
- **Fixed import issues** that were causing legacy processor warnings
- **Maintained backward compatibility** for all existing functionality

### Package Improvements
- **Prerelease versioning** (0.8.0) for testing and feedback
- **Simplified conda dependencies** to avoid conda-forge conflicts
- **Enhanced error handling** for missing optional dependencies
- **Updated documentation** to reflect current state and usage

## 🔄 Breaking Changes

### Import Paths
- Module imports now use `cleanupx_core` package structure
- Legacy imports are still supported but may show warnings

### CLI Arguments
- Some command arguments have been standardized for consistency
- All existing functionality remains available

### Output Structure
- Output files are now organized in structured directories
- Naming conventions have been improved for clarity

## 🐛 Bug Fixes

- **Fixed UTF-8 encoding issues** with Word document processing
- **Resolved import path problems** across different environments
- **Improved error handling** for missing dependencies
- **Enhanced cross-platform compatibility**

## 📊 Supported File Types

- **Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.tiff`
- **Documents**: `.pdf`, `.doc`, `.docx`, `.rtf`, `.pptx`
- **Code**: `.py`, `.js`, `.html`, `.css`, `.md`, `.txt`, `.json`, `.yaml`
- **Archives**: `.zip`, `.tar`, `.gz` (with optional RAR support)

## 🔗 Resources

- **📚 Documentation**: [README.md](README.md)
- **🛠️ Installation Guide**: [INSTALL.md](INSTALL.md)
- **🤝 Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **📋 Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **🏠 Homepage**: https://lukesteuber.com
- **🎮 Platform**: https://assisted.site

## 🙏 Support

- **Issues**: [GitHub Issues](https://github.com/lukeslp/cleanupx/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lukeslp/cleanupx/discussions)
- **Email**: luke@lukesteuber.com
- **Newsletter**: https://lukesteuber.substack.com/

## 💝 Acknowledgments

Special thanks to the Python packaging community and all the open-source libraries that make CleanupX possible. This project represents months of development focused on accessibility, usability, and professional software distribution practices.

---

**Download**: Available on [PyPI](https://pypi.org/project/cleanupx/)  
**License**: MIT  
**Author**: Luke Steuber ([lukesteuber.com](https://lukesteuber.com))  
**Support**: [Tip Jar](https://usefulai.lemonsqueezy.com/buy/bf6ce1bd-85f5-4a09-ba10-191a670f74af)  

**Install now**: `pip install cleanupx` 🚀 