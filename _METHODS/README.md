# CleanupX Methods Documentation

This directory contains the core processing modules for the CleanupX project. Each module is designed to handle specific aspects of file management, organization, and metadata enhancement.

## Core Modules

### 🔍 deduper.py
File deduplication and similarity detection module.

**Key Features:**
- Identifies and manages duplicate files using hash-based comparison
- Implements similarity detection for near-duplicate files
- Supports various file types including images, documents, and media files
- Maintains file integrity during deduplication process
- Generates detailed reports of duplicate findings

### 📝 xcitation.py
Academic citation extraction and management module.

**Key Features:**
- Extracts citations from PDF documents and text files
- Supports DOI resolution and validation
- Integrates with academic APIs for citation metadata
- Generates standardized citation formats
- Caches citation data for improved performance

### 🖼️ ximagenamer.py
Intelligent image naming and organization module.

**Key Features:**
- Analyzes image content for automatic naming
- Extracts and processes image metadata
- Implements AI-based image classification
- Supports batch processing of image files
- Maintains naming consistency across collections

### ✂️ xsnipper.py
File content extraction and snippet management module.

**Key Features:**
- Extracts relevant content snippets from documents
- Supports multiple file formats (PDF, text, code)
- Implements context-aware content selection
- Maintains snippet organization and indexing
- Provides search functionality for stored snippets

### 📛 xnamer.py
Advanced file naming and organization module.

**Key Features:**
- Implements intelligent file naming conventions
- Processes metadata for naming decisions
- Supports batch renaming operations
- Maintains file type consistency
- Handles special characters and formatting

### 🔀 scrambler.py
File randomization and anonymization module.

**Key Features:**
- Randomizes file names while maintaining extensions
- Implements secure anonymization techniques
- Maintains file mapping for recovery
- Supports batch processing
- Preserves file metadata when required

## Supporting Files

### alt_text_cache.json
Cache file for storing alternative text descriptions for images and media files.

### .env
Environment configuration file containing API keys and system settings.

## Directory Structure

```
_METHODS/
├── alt_text_cache.json    # Alternative text cache
├── deduper.py            # Deduplication module
├── xnamer.py             # File naming module
├── xsnipper.py           # Content extraction module
├── xcitation.py          # Citation processing module
├── scrambler.py          # File randomization module
├── ximagenamer.py        # Image naming module
└── snippets/             # Stored content snippets
```

## Usage Guidelines

1. **Module Dependencies**
   - Ensure all required Python packages are installed
   - Configure API keys in `.env` file
   - Initialize cache files before first use

2. **Best Practices**
   - Process files in manageable batch sizes
   - Regularly backup important data
   - Monitor cache sizes and clean as needed
   - Use appropriate error handling

3. **Performance Considerations**
   - Large file processing may require additional memory
   - Consider using batch processing for large directories
   - Monitor system resources during heavy operations

## API Integration

The modules integrate with various external APIs:
- Academic citation services
- Image recognition services
- Metadata enhancement services
- File type detection services

API base URL: api.assisted.space/v2

## Error Handling

All modules implement comprehensive error handling:
- File access errors
- API connection issues
- Processing failures
- Resource limitations

## Cache Management

Cache files are used to improve performance:
- `alt_text_cache.json` for image descriptions
- Citation data caching
- Snippet indexing
- Processing results

## Contributing

When contributing to these modules:
1. Follow existing code style
2. Add appropriate documentation
3. Implement error handling
4. Include unit tests
5. Update this README as needed

## Testing

Each module includes comprehensive test suites:
- Unit tests for core functionality
- Integration tests for API interactions
- Performance tests for optimization
- Error case handling tests

## Accessibility Features

All modules are designed with accessibility in mind:
- Alternative text generation
- Semantic file naming
- Accessible content extraction
- Screen reader compatibility

## License

Copyright © 2024 Lucas Steuber. All rights reserved. 