# Contributing to CleanupX

Thank you for your interest in contributing to CleanupX! This document provides guidelines and instructions for contributing to the project.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/cleanupx.git
   cd cleanupx
   ```
3. **Install in development mode**:
   ```bash
   pip install -e .[dev]
   ```
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 📁 Project Structure

```
cleanupx/
├── cleanupx.py                 # Main CLI interface
├── cleanupx_core/              # Core functionality
│   ├── api/                    # API integrations
│   ├── processors/
│   │   ├── integrated/         # New processing modules
│   │   └── legacy/             # Backward compatibility
│   └── utils/                  # Common utilities
├── storage/                    # Non-core archived functionality
├── test/                       # Test files and data
├── .github/workflows/          # CI/CD pipelines
└── [config files]             # Package configuration
```

## 🛠️ Development Guidelines

### Code Style
- **Python**: Follow PEP 8 with 88-character line limit
- **Formatting**: Use `black` for automatic formatting
- **Linting**: Use `flake8` for code quality checks
- **Type Hints**: Add type hints for new functions
- **Docstrings**: Use Google-style docstrings

### Example:
```python
def process_file(file_path: str, options: dict) -> bool:
    """Process a single file with given options.
    
    Args:
        file_path: Path to the file to process
        options: Processing configuration options
        
    Returns:
        True if processing succeeded, False otherwise
        
    Raises:
        FileNotFoundError: If file_path doesn't exist
    """
    # Implementation here
    pass
```

### Code Quality Tools
```bash
# Format code
black cleanupx_core/ cleanupx.py

# Check linting
flake8 cleanupx_core/ cleanupx.py

# Run tests
python -c "import cleanupx_core; cleanupx_core.print_status()"
```

## 📦 Module Organization

### Core Modules (`cleanupx_core/`)
- **API integrations** go in `api/`
- **File processors** go in `processors/integrated/`
- **Utilities** go in `utils/`
- **Configuration** in `config.py`

### Legacy Support (`cleanupx_core/processors/legacy/`)
- Maintain backward compatibility
- Import from `storage/legacy_methods/` when needed

### Storage (`storage/`)
- Non-core functionality
- Experimental features
- Development utilities

## 🧪 Testing

### Basic Tests
```bash
# Test core functionality
python -c "import cleanupx_core; cleanupx_core.print_status()"

# Test CLI
python cleanupx.py --help

# Test specific modules
python -c "from cleanupx_core import get_status; print(get_status())"
```

### Adding New Tests
1. Create test files in `test/` directory
2. Use descriptive test data
3. Test both success and failure cases
4. Include edge cases

## 🆕 Adding New Features

### File Processors
1. Create new processor in `cleanupx_core/processors/integrated/`
2. Follow the existing pattern:
   ```python
   class NewProcessor:
       def __init__(self, config):
           self.config = config
           
       def process(self, file_path):
           # Implementation
           pass
   ```
3. Add to `cleanupx_core/__init__.py` exports
4. Update CLI in `cleanupx.py` if needed

### API Integrations
1. Add new API client to `cleanupx_core/api/`
2. Include proper error handling and retry logic
3. Add environment variable configuration
4. Update documentation

### CLI Commands
1. Add new command in `cleanupx.py`
2. Follow existing argument patterns
3. Include help text and examples
4. Maintain backward compatibility

## 📝 Documentation

### Required Documentation
- **Docstrings**: All public functions and classes
- **README updates**: For new features
- **CHANGELOG**: For all changes
- **Type hints**: For new code

### Banner Comments
All new Python files must include banner comments:
```python
"""
CleanupX - [File Purpose]

[Brief description of what this file does]

Primary Functions/Classes:
- [List main components]

Inputs and Outputs:
- Input: [Description]
- Output: [Description]

MIT License by Luke Steuber
Website: lukesteuber.com, assisted.site
Email: luke@lukesteuber.com
"""
```

## 🔄 Pull Request Process

1. **Update documentation** for any new features
2. **Add tests** for new functionality
3. **Run quality checks**:
   ```bash
   black cleanupx_core/ cleanupx.py
   flake8 cleanupx_core/ cleanupx.py
   python -c "import cleanupx_core; cleanupx_core.print_status()"
   ```
4. **Update CHANGELOG.md** with your changes
5. **Submit pull request** with descriptive title and description

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added new tests for new functionality
- [ ] Verified backward compatibility

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

## 🐛 Bug Reports

### Before Reporting
1. Check existing issues
2. Test with latest version
3. Verify it's not a configuration issue

### Bug Report Template
```markdown
**Describe the bug**
Clear description of the problem

**To Reproduce**
1. Command/steps to reproduce
2. Expected behavior
3. Actual behavior

**Environment**
- OS: [e.g. Ubuntu 22.04]
- Python version: [e.g. 3.11]
- CleanupX version: [e.g. 2.0.0]

**Additional context**
Any other relevant information
```

## 🌟 Feature Requests

### Feature Request Template
```markdown
**Is your feature request related to a problem?**
Description of the problem

**Describe the solution you'd like**
Clear description of desired feature

**Describe alternatives you've considered**
Other approaches you've thought about

**Additional context**
Any other relevant information
```

## 📜 License

By contributing to CleanupX, you agree that your contributions will be licensed under the MIT License.

## 🤝 Code of Conduct

### Our Standards
- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Acknowledge different perspectives

### Unacceptable Behavior
- Harassment or discrimination
- Trolling or inflammatory comments
- Publishing private information
- Unprofessional conduct

## 📞 Getting Help

- **Documentation**: [README.md](README.md)
- **Issues**: [GitHub Issues](https://github.com/lukeslp/cleanupx/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lukeslp/cleanupx/discussions)
- **Email**: luke@lukesteuber.com

## 🎯 Development Roadmap

### High Priority
- Performance optimization
- Enhanced test coverage
- Web interface development
- Plugin system architecture

### Medium Priority
- Additional AI integrations
- Extended file format support
- Batch processing improvements
- Configuration management

### Long Term
- API server implementation
- Cloud storage integration
- Machine learning enhancements
- Enterprise features

---

**Thank you for contributing to CleanupX!** 🚀

Your contributions help make file processing more accessible and powerful for everyone. 