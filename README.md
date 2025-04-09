# CleanupX

An intelligent file organization and cleanup tool that uses AI to analyze and rename files based on their content.

## Features

- Generate descriptive names for files based on content analysis
- Process images, text files, documents, and more
- Maintain a cache of processed files to avoid reprocessing
- Undo rename operations if needed
- Rich command-line interface with progress tracking
- Cross-platform support

## Installation

### Option 1: Install from source

```bash
# Clone the repository
git clone https://github.com/yourusername/cleanupx.git
cd cleanupx

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

### Option 2: Install with pip

```bash
pip install cleanupx
```

## Dependencies

CleanupX requires several dependencies to work properly:

- **Required**:
  - openai: For AI-powered file analysis
  - Pillow: For image processing
  - inquirer: For interactive command-line interface
  - rich: For enhanced terminal output

- **Optional but recommended**:
  - pyheif or pillow-heif: For HEIC/HEIF image support
  - PyPDF2: For PDF document parsing
  - ffmpeg: For media file metadata extraction

## Usage

### Basic Usage

Process a single file or directory:

```bash
cleanupx process path/to/file_or_directory
```

Process a directory recursively:

```bash
cleanupx process --recursive path/to/directory
```

### Advanced Options

Process files even if previously renamed:

```bash
cleanupx process --force path/to/directory
```

Clear cache before processing:

```bash
cleanupx process --clear-cache path/to/directory
```

Show what would be done without making changes:

```bash
cleanupx process --dry-run path/to/directory
```

### Managing Renames

Undo a specific rename:

```bash
cleanupx undo path/to/file
```

Undo all renames:

```bash
cleanupx undo-all
```

### Cache Management

View current status:

```bash
cleanupx status
```

Clear cache and rename log:

```bash
cleanupx clear-cache
```

### Global Options

Enable debug logging:

```bash
cleanupx --debug process path/to/directory
```

Specify custom cache directory:

```bash
cleanupx --cache-dir /path/to/cache process path/to/directory
```

## Configuration

Configuration can be set in `src/cleanupx/core/config.py` or using environment variables:

- `XAI_API_KEY`: Your X.AI API key
- `XAI_API_BASE`: API base URL (default: https://api.x.ai/v1)
- `XAI_MODEL_TEXT`: Model for text analysis (default: grok-2-latest)
- `XAI_MODEL_VISION`: Model for image analysis (default: grok-2-vision-latest)
- `CLEANUPX_CACHE_DIR`: Directory for cache and log files (default: current directory)
- `OPENAI_API_KEY`: Your OpenAI API key (required)

## Troubleshooting

### Common Issues

- **Missing OpenAI package**: Install with `pip install openai`
- **HEIC conversion failures**: Install HEIC support with `pip install pillow-heif` or `pip install pyheif`
- **Media metadata extraction errors**: Install ffmpeg on your system

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. # cleanupx
