# CleanupX

An intelligent file organization and renaming tool with AI-powered content analysis.

## Features

- **Smart File Renaming**: Analyzes file content and suggests descriptive names
- **Alt Text Generation**: Creates accessibility-friendly alt text for images
- **Content Extraction**: Processes text, documents, images, media, and archives
- **Batch Processing**: Processes entire directories of files recursively
- **Privacy Mode**: Scrambles filenames with random strings for privacy
- **Comprehensive Logging**: Maintains detailed logs of all rename operations
- **Interactive CLI**: User-friendly command-line interface with progress indicators

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/cleanupx.git
cd cleanupx

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Command Line Interface

```bash
python cleanupx.py [directory] [options]
```

### Interactive Mode

```bash
python cleanupx.py
```

### Available Options

- `--recursive, -r`: Process subdirectories recursively
- `--force, -f`: Process all files, including previously renamed ones
- `--clear-cache`: Clear cache before processing
- `--interactive, -i`: Run in interactive mode
- `--scramble, -s`: Scramble filenames with random strings
- `--max-size`: Skip files larger than this size in MB (default: 25MB)
- `--images-only`: Process only image files
- `--text-only`: Process only text files
- `--documents-only`: Process only document files
- `--archives-only`: Process only archive files
- `--skip-images`: Skip processing of image files
- `--skip-text`: Skip processing of text files
- `--skip-documents`: Skip processing of document files
- `--skip-archives`: Skip processing of archive files

## Examples

Process all files in the current directory:
```bash
python cleanupx.py .
```

Process all files recursively in a specific directory:
```bash
python cleanupx.py ~/Documents/unsorted -r
```

Scramble filenames in a directory for privacy:
```bash
python cleanupx.py ~/Pictures/private -s
```

## Dependencies

- OpenAI/X.AI API for content analysis
- Python 3.7+
- See requirements.txt for full list of dependencies

## Project Structure

```
cleanupx/
├── __init__.py
├── main.py              # Entry point
├── config.py            # Configuration settings
├── api.py               # API interaction
├── utils/
│   ├── __init__.py
│   ├── common.py        # Shared utilities
│   ├── logging.py       # Logging utilities
│   ├── cache.py         # Cache management
│   ├── reporting.py     # Report generation
├── processors/
│   ├── __init__.py
│   ├── base.py          # Base processor
│   ├── file.py          # File processing
│   ├── image.py         # Image processor
│   ├── text.py          # Text processor
│   ├── document.py      # Document processor
│   ├── archive.py       # Archive processor
│   ├── media.py         # Media processor
├── ui/
│   ├── __init__.py
│   ├── cli.py           # Command-line interface
│   ├── interactive.py   # Interactive UI
```

## Accessibility

This tool enhances file accessibility by:
1. Generating detailed alt text for images
2. Creating separate markdown files with content descriptions
3. Embedding metadata in files when possible
4. Using descriptive, content-based filenames

## License

MIT License
