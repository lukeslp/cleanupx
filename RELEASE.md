# cleanupx v0.8.0 Release Guide

**Prerelease Package Release**

This document outlines the complete release process for cleanupx v0.8.0, a prerelease version for testing and feedback before the stable 1.0.0 release.

## 🎯 Release Overview

**Version**: 0.8.0  
**Release Date**: 2025-06-07  
**Release Type**: Prerelease - "Testing & Feedback"  
**Stability**: Prerelease/Beta  

### Key Highlights
- **Complete package restructure** for professional distribution
- **PyPI and conda compatibility** with proper packaging
- **AI-powered file processing** with X.AI integration
- **Comprehensive CLI interface** with rich output
- **GitHub sponsor integration** with funding links
- **Consistent branding** with lowercase "cleanupx" throughout
- **Legacy processor integration** from storage directory

## 📋 Pre-Release Checklist

### Code Quality
- [x] All imports working correctly
- [x] CLI commands functional
- [x] Core module status verification
- [x] Error handling implemented
- [x] Code formatted with black
- [x] Linting passed with flake8

### Documentation
- [x] README.md updated
- [x] CHANGELOG.md created
- [x] INSTALL.md comprehensive guide
- [x] CONTRIBUTING.md for developers
- [x] PROJECT_PLAN.md current
- [x] API documentation in docstrings

### Packaging
- [x] setup.py configured
- [x] pyproject.toml modern configuration
- [x] MANIFEST.in distribution control
- [x] requirements.txt dependencies
- [x] conda meta.yaml recipe

### Testing
- [x] Basic functionality tests
- [x] Import tests across modules
- [x] CLI help commands
- [x] Cross-platform compatibility
- [x] Installation verification

## 🚀 Release Process

### 1. PyPI Release

#### Build and Test Package
```bash
# Clean and build
rm -rf dist/ build/ *.egg-info/
python -m build

# Verify package
python -m twine check dist/*

# Test local installation
pip install dist/cleanupx-0.8.0-py3-none-any.whl
cleanupx --help
```

#### Upload to PyPI
```bash
# Upload to TestPyPI first (recommended)
twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install -i https://test.pypi.org/simple/ cleanupx

# Upload to production PyPI
twine upload dist/*
```

### 2. Conda Package

#### Build Conda Package
```bash
# Build conda package
conda-build conda-recipe/ --output-folder conda-dist/ --no-test

# Test installation
conda install --use-local cleanupx
cleanupx-status
```

#### Submit to conda-forge
1. Fork `conda-forge/staged-recipes`
2. Copy `conda-recipe/meta.yaml` to `recipes/cleanupx/meta.yaml`
3. Update source URL to point to PyPI release
4. Submit pull request

### 3. GitHub Release

#### Create Release
1. Go to https://github.com/lukeslp/cleanupx/releases/new
2. Tag version: `v0.8.0`
3. Release title: `cleanupx v0.8.0 - Prerelease`
4. Description: Use template below

#### Release Description Template
```markdown
# cleanupx v0.8.0 - Prerelease 🚧

A prerelease version of cleanupx for testing and feedback, featuring consistent branding and integrated legacy processors.

## 🎉 Major Features

### AI-Powered Processing
- X.AI API integration for intelligent file analysis
- Automated image alt text generation for accessibility
- Smart duplicate detection beyond simple hashing

### Professional CLI Interface
- Rich terminal output with progress bars
- Interactive prompts for better UX
- Comprehensive help and documentation

### Privacy & Organization
- Filename scrambling for sensitive data
- Advanced file organization and categorization
- Citation extraction from documents

## 📦 Installation

### PyPI (Recommended)
```bash
# Basic installation
pip install cleanupx

# With all features
pip install cleanupx[all]
```

### Conda (Coming Soon)
```bash
conda install -c conda-forge cleanupx
```

## 🔗 Quick Links

- **Documentation**: [README.md](README.md)
- **Installation Guide**: [INSTALL.md](INSTALL.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

## 🙏 Support

- **Issues**: [GitHub Issues](https://github.com/lukeslp/cleanupx/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lukeslp/cleanupx/discussions)
- **Email**: luke@lukesteuber.com

---

**Full Changelog**: https://github.com/lukeslp/cleanupx/compare/v1.0.0...v2.0.0
```

### 4. Social Media Announcement

#### Twitter/X
```
🚀 CleanupX v2.0.0 is here! 

✨ AI-powered file processing
📂 Smart organization & deduplication  
🖼️ Accessibility features (alt text)
🔒 Privacy tools
🐍 Now on PyPI!

pip install cleanupx

#Python #AI #FileManagement #Accessibility #OpenSource
```

#### LinkedIn
```
Excited to announce CleanupX v2.0.0 - Production Ready! 🚀

After months of development, CleanupX is now a professional-grade package available on PyPI. This comprehensive file processing tool combines AI capabilities with accessibility features and privacy tools.

Key highlights:
✅ AI-powered file analysis and deduplication
✅ Automated image alt text generation
✅ Privacy-focused filename scrambling
✅ Rich CLI interface with progress tracking
✅ Cross-platform compatibility
✅ Extensive documentation

Perfect for developers, content creators, and anyone dealing with large file collections.

Get started: pip install cleanupx

#SoftwareDevelopment #AI #Accessibility #Python #OpenSource #ProductLaunch
```

## 📊 Post-Release Monitoring

### Metrics to Track
- **PyPI downloads** and install statistics
- **GitHub stars, forks, and issues**
- **User feedback** and feature requests
- **Documentation usage** and gaps
- **Platform compatibility** reports

### Response Plan
- **Issues**: Respond within 24-48 hours
- **Security vulnerabilities**: Immediate response
- **Feature requests**: Evaluate and roadmap
- **Documentation gaps**: Address promptly

## 🔄 Maintenance Schedule

### Patch Releases (2.0.x)
- **Bug fixes** and minor improvements
- **Documentation** updates
- **Dependency** updates
- **Performance** optimizations

### Minor Releases (2.x.0)
- **New features** that maintain compatibility
- **Enhanced AI** capabilities
- **Additional integrations**
- **UI/UX improvements**

### Major Releases (x.0.0)
- **Breaking changes** (rare)
- **Architecture overhauls**
- **Major new capabilities**

## 📞 Support Contacts

**Primary Maintainer**: Luke Steuber
- **Email**: luke@lukesteuber.com
- **Website**: https://lukesteuber.com
- **Platform**: https://assisted.site
- **LinkedIn**: https://www.linkedin.com/in/lukesteuber/
- **Bluesky**: @lukesteuber.com

**Project Resources**:
- **Repository**: https://github.com/lukeslp/cleanupx
- **PyPI**: https://pypi.org/project/cleanupx/
- **Documentation**: https://github.com/lukeslp/cleanupx#readme
- **Issue Tracker**: https://github.com/lukeslp/cleanupx/issues

---

**License**: MIT  
**Status**: Production Ready ✅  
**Support**: Community + Maintainer Response 