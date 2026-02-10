# Changelog

All notable changes to CleanupX will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-06-06

### Added
- **Complete Package Restructure**: Organized codebase into clean modular structure
- **PyPI Distribution**: Full setup.py and pyproject.toml configuration for package distribution
- **Conda Support**: Meta.yaml configuration for conda-forge distribution
- **AI-Powered Processing**: X.AI API integration for intelligent file analysis
- **Image Accessibility**: Automated alt text generation for images
- **Comprehensive CLI**: Rich command-line interface with progress bars
- **File Deduplication**: Advanced duplicate detection and organization
- **Privacy Tools**: Filename scrambling utilities with reversal logs
- **Multiple Output Formats**: Organized output management
- **Error Handling**: Robust error handling and retry logic
- **Extensive Documentation**: Complete README, PROJECT_PLAN, and API docs

### Changed
- **Architecture Overhaul**: Moved from scattered scripts to organized package structure
- **Import System**: Clean import paths with fallback handling
- **Output Management**: Centralized output instead of scattered files
- **Dependency Management**: Separated core vs. optional dependencies
- **CLI Interface**: Unified command structure with backward compatibility

### Fixed
- **Import Errors**: Resolved all import path issues
- **UTF-8 Handling**: Fixed file encoding issues with Word documents
- **SSL Configuration**: Proper HTTPS/HTTP server setup
- **Memory Management**: Improved memory usage for large file processing
- **Cross-Platform**: Enhanced compatibility across different operating systems

### Security
- **API Key Management**: Secure environment variable handling
- **File Privacy**: Filename scrambling for sensitive data
- **Input Validation**: Comprehensive input sanitization

## [1.x.x] - Historical Versions

### Legacy Development (Pre-2.0.0)
- Initial development of core functionality
- Basic file processing capabilities
- Early AI integration experiments
- SSL server implementation
- Storage-based architecture (now archived)

---

## Release Notes

### Version 2.0.0 - "Production Ready"

This major release represents a complete transformation of CleanupX from experimental scripts into a production-ready package suitable for PyPI and conda distribution.

#### Key Highlights:
- **Professional Package Structure**: Complete reorganization with proper Python packaging
- **AI Integration**: Seamless X.AI API integration for intelligent processing
- **Enhanced CLI**: Beautiful, interactive command-line experience
- **Accessibility Focus**: Automated image alt text generation
- **Privacy Tools**: Advanced filename scrambling with recovery options
- **Documentation**: Comprehensive documentation and examples

#### Breaking Changes:
- Module import paths have changed (legacy imports still supported)
- Output directory structure has been reorganized
- Some CLI argument names have been standardized

#### Migration Guide:
- Update import statements to use `cleanupx_core` module
- Review output directory structure for any automated scripts
- Set `XAI_API_KEY` environment variable for AI features

#### Installation:
```bash
# PyPI (when published)
pip install cleanupx

# With optional features
pip install cleanupx[ai,documents,images]

# Development installation
pip install -e .[dev]
```

---

## Contributors

**Luke Steuber** - *Author & Maintainer*
- Website: [lukesteuber.com](https://lukesteuber.com)
- Platform: [assisted.site](https://assisted.site)
- Email: luke@lukesteuber.com
- LinkedIn: [lukesteuber](https://www.linkedin.com/in/lukesteuber/)
- Bluesky: [@lukesteuber.com](https://bsky.app/profile/lukesteuber.com)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [GitHub README](https://github.com/lukeslp/cleanupx#readme)
- **Issues**: [GitHub Issues](https://github.com/lukeslp/cleanupx/issues)
- **Newsletter**: [Substack](https://lukesteuber.substack.com/)
- **Support Development**: [Tip Jar](https://usefulai.lemonsqueezy.com/buy/bf6ce1bd-85f5-4a09-ba10-191a670f74af) 