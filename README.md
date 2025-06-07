# cleanupx - Comprehensive File Processing Tool

**Version 0.8.2** - Near Production Ready

A powerful, AI-enhanced file organization and processing framework with comprehensive capabilities for code analysis, image processing, file deduplication, and privacy utilities.

## 🎯 What's New in v0.8.2 (Near Production Ready)

- **🏗️ Complete Reorganization**: Clean modular structure with core functionality separated from storage
- **🚀 Enhanced Performance**: Streamlined imports and optimized processing
- **🔄 Backward Compatibility**: All existing commands continue to work
- **📦 Unified Architecture**: Consolidated scattered functionality into organized modules
- **🔒 SSL Ready**: Full HTTPS support with proper certificate configuration
- **🎯 Consistent Branding**: Unified "cleanupx" naming throughout the project
- **🔧 Legacy Integration**: All storage functionality migrated and working
- **⚡ Production Ready**: Comprehensive testing and workflow optimization

## 📁 Project Structure

```
cleanupx/
├── cleanupx.py                 # Main CLI interface
├── cleanupx_core/              # Core functionality
│   ├── api/                    # XAI API integration  
│   ├── processors/
│   │   ├── integrated/         # New comprehensive processing
│   │   └── legacy/             # Backward compatibility
│   └── utils/                  # Common utilities
├── storage/                    # Non-core functionality archive
│   ├── legacy_methods/         # Original processing methods
│   ├── dev_tools/              # Development utilities
│   └── documentation/          # Archive documentation
└── test/                       # Test files
```

## 🚀 Quick Start

### Installation

```bash
# Install from PyPI (recommended)
pip install cleanupx

# Or install prerelease version
pip install --pre cleanupx

# Or clone from source
git clone https://github.com/lukeslp/cleanupx.git
cd cleanupx
pip install -r requirements.txt

# Set up environment (optional for AI features)
echo "XAI_API_KEY=your-xai-api-key" > .env
```

### Basic Usage

```bash
# Check system status
cleanupx --help

# Run file deduplication
cleanupx deduplicate --dir test

# Process images for accessibility
cleanupx images --dir test  

# Comprehensive processing with all features
cleanupx comprehensive --dir test

# Privacy: scramble filenames
cleanupx scramble --dir test
```

## 🛠️ Features

### Core Processing
- **File Deduplication**: Smart duplicate detection and organization
- **Code Analysis**: Extract and analyze code snippets
- **File Organization**: Categorize and organize files by type and content
- **Citation Processing**: Extract and format citations from documents

### AI-Powered Features
- **X.AI Integration**: Advanced AI processing with retry logic
- **Image Alt Text**: Generate accessibility descriptions for images
- **Content Analysis**: AI-powered content understanding and categorization
- **Smart Deduplication**: Intelligent duplicate detection beyond simple hashing

### Privacy & Utility
- **Filename Scrambling**: Randomize filenames for privacy/testing
- **Rename Logging**: Track and reverse filename changes
- **Rich CLI Interface**: Beautiful terminal output with progress bars
- **Comprehensive Logging**: Detailed operation logs

## 📋 Available Commands

### Primary Commands
```bash
comprehensive    # Full processing with all features
images          # AI-powered image processing and alt text generation  
scramble        # Privacy-focused filename scrambling
```

### Legacy Commands (Backward Compatible)
```bash
deduplicate     # Find and process duplicate files
extract         # Extract important code snippets  
organize        # Organize and rename files
all             # Run all legacy processing steps
```

## 🔧 Configuration

### Environment Variables
```bash
# Required for AI features
XAI_API_KEY=your-xai-api-key

# Optional configurations
CLEANUP_OUTPUT_DIR=custom_output_directory
CLEANUP_LOG_LEVEL=INFO
```

### Dependencies

#### Core Requirements
```
requests>=2.31.0        # HTTP requests
rich>=13.7.0           # Beautiful console output  
inquirer>=3.4.0        # Interactive prompts
pillow>=10.0.0         # Image processing
PyPDF2>=3.0.1          # PDF processing
python-docx>=1.1.2     # Word document processing
```

#### Optional Dependencies
```
openai                 # OpenAI API fallback
PyHEIF                # HEIC/HEIF image support
rarfile               # RAR archive processing
```

## 🏗️ Architecture

### Modular Design
cleanupx is built with a clean, modular architecture:

- **`cleanupx_core/`**: Core functionality with stable APIs
- **`storage/`**: Non-essential functionality for experimentation
- **Processors**: Specialized processing modules for different file types
- **API Layer**: Unified interface for AI service integration

### Key Benefits
1. **Clean Separation**: Core vs. experimental functionality
2. **Backward Compatibility**: Legacy commands continue to work
3. **Extensible**: Easy to add new processors and features
4. **Production Ready**: Robust error handling and logging
5. **Organized Output**: Centralized output management

## 📊 Supported File Types

- **Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.tiff`
- **Code**: `.py`, `.js`, `.html`, `.css`, `.md`, `.txt`, `.json`, `.yaml`
- **Documents**: `.pdf`, `.doc`, `.docx`, `.rtf`, `.pptx`
- **Archives**: `.zip`, `.tar`, `.gz` (with optional RAR support)
- **All Others**: Categorized and processed appropriately

## 🚦 Status Check

```bash
# Verify module status
python3 -c "import cleanupx_core; cleanupx_core.print_status()"
```

Expected output:
```
cleanupx Core v0.8.2
  Integrated Processors: ✓
  XAI API Support: ✓  
  Legacy Processors: ✓
  Module Path: /path/to/cleanupx_core
```

## 🔍 Examples

### Basic File Organization
```bash
# Organize a downloads directory
cleanupx organize --dir ~/Downloads

# Find duplicates in a project
cleanupx deduplicate --dir ~/Projects/MyProject
```

### AI-Enhanced Processing
```bash
# Generate alt text for all images
cleanupx images --dir ./photos

# Comprehensive AI analysis
cleanupx comprehensive --dir ./documents
```

### Privacy & Testing
```bash
# Scramble filenames for privacy
cleanupx scramble --dir ./sensitive_data

# Note: Scrambling creates a log file to reverse changes
```

## 🛠️ Development

### Module Status
The reorganized architecture provides:
- **Stable Core**: `cleanupx_core/` for production functionality
- **Experimental Storage**: `storage/` for development and testing
- **Clear APIs**: Well-defined interfaces between modules
- **Easy Testing**: Modular design enables easy unit testing

### Contributing
1. Core functionality goes in `cleanupx_core/`
2. Experimental features start in `storage/dev_tools/`
3. All changes must maintain backward compatibility
4. Add comprehensive tests for new features

## 📝 License & Credits

**MIT License** by Luke Steuber  

### 🔗 Connect & Support

| Platform | Link |
|----------|------|
| 🌐 **Website** | [lukesteuber.com](https://lukesteuber.com) |
| 🛠️ **Playground** | [assisted.site](https://assisted.site/) |
| 📧 **Email** | [luke@lukesteuber.com](mailto:luke@lukesteuber.com) |
| 🐦 **Bluesky** | [@lukesteuber.com](https://bsky.app/profile/lukesteuber.com) |
| 💼 **LinkedIn** | [lukesteuber](https://www.linkedin.com/in/lukesteuber/) |
| 💻 **GitHub** | [lukeslp](https://github.com/lukeslp) |
| 🧠 **LlamaLine** | [AI CLI Tool](https://github.com/lukeslp/llamaline) |
| ✉️ **Newsletter** | [Substack](https://lukesteuber.substack.com/) |
| ☕ **Support** | [Tip Jar](https://usefulai.lemonsqueezy.com/buy/bf6ce1bd-85f5-4a09-ba10-191a670f74af) |  

## 🎯 What's Next

1. **Performance Optimization**: Profile and optimize processing speeds
2. **Enhanced AI Features**: More sophisticated content analysis
3. **Web Interface**: Browser-based processing dashboard
4. **API Server**: REST API for remote processing
5. **Plugin System**: Custom processor plugins

---

**Version**: 0.8.2 - Near Production Ready  
**Last Updated**: June 7, 2025  
**Status**: 🚀 Near Production Ready - Legacy Integration Complete
