# cleanupx

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Active](https://img.shields.io/badge/status-active-success.svg)]()

File organization and processing tool with optional LLM features for image alt-text and content analysis.

## Install

```bash
pip install cleanupx
```

Set `XAI_API_KEY` in your environment to enable LLM features like alt text generation (optional).

## Usage

```bash
# Organize files by type
cleanupx organize --dir ~/Downloads

# Find and handle duplicates
cleanupx deduplicate --dir ~/Projects

# Generate alt text for images (requires XAI_API_KEY)
cleanupx images --dir ./photos

# Run all processing steps
cleanupx comprehensive --dir ./documents

# Scramble filenames for privacy (reversible)
cleanupx scramble --dir ./sensitive_data
```

## What It Does

- **Deduplication** — SHA256 hash-based duplicate detection
- **File Organization** — Categorize by type: images, code, documents, archives
- **Image Alt Text** — Generate accessibility descriptions via vision models
- **Code Extraction** — Pull and analyze code snippets from files
- **Filename Scrambling** — Randomize names for privacy, with undo log
- **PDF/DOCX Support** — Process documents alongside plain text

## Supported File Types

Images (jpg, png, gif, webp, bmp, tiff), code (py, js, html, css, md, json, yaml), documents (pdf, doc, docx, rtf, pptx), archives (zip, tar, gz, rar).

## Structure

```
cleanupx/
├── cleanupx.py           # CLI entry point
├── cleanupx_core/        # Core processing modules
│   ├── api/              # XAI integration
│   ├── processors/       # File type handlers
│   └── utils/            # Common utilities
└── storage/              # Experimental/archived code
```

## Configuration

```bash
XAI_API_KEY=your-key      # Required for LLM features
CLEANUP_OUTPUT_DIR=./out  # Custom output directory
CLEANUP_LOG_LEVEL=INFO    # Logging verbosity
```

## Dependencies

Core: requests, rich, inquirer, pillow, PyPDF2, python-docx. Optional: openai, PyHEIF, rarfile.

## License

MIT — Luke Steuber (luke@dr.eamer.dev)
