# Reference Renamer

Reference Renamer (FileLlama) is an intelligent, accessibility-focused command-line tool that standardizes academic article filenames by extracting and enriching metadata from documents. The tool leverages advanced technologies such as OCR, LLM-based metadata extraction, and academic API integrations (Semantic Scholar, arXiv) to ensure robust, reliable file management.

## Features

- **Intelligent Renaming**: Automatically rename academic articles to a standardized format, e.g., `Author_Year_FiveWordTitle.ext`, derived from extracted metadata.
- **Multi-Format Support**: Process PDF, TXT, DOC, DOCX, and other document formats.
- **Metadata Extraction & Enrichment**:
  - **Text & OCR Extraction**: Uses PyPDF2 for digital PDFs and Tesseract OCR for scanned pages.
  - **LLM Integration**: Enhances metadata extraction through Ollama with advanced LLM prompts.
  - **Academic APIs**: Optionally verify metadata via Semantic Scholar and arXiv.
- **Backup System**: Automatically creates backups in a designated directory before renaming files.
- **Comprehensive Logging**: Utilizes structured logging with structlog and rich output for detailed and accessible logs.
- **Robust CLI Interface**: Offers commands for processing files (`process`), managing citations (`citations`), extracting metadata (`extract`), and organizing files (`organize`).
- **Accessibility Focused**: Features high contrast output, screen reader friendly messages, and verbose mode for enhanced usability.
- **Configurable & Extensible**: YAML configuration support allows customization of processing options, filename formats, API settings, and logging.

## Installation

### Prerequisites

- **Python**: Version 3.8 or higher.
- **Tesseract OCR**: For extracting text from scanned documents.
  - **macOS**: `brew install tesseract`
  - **Linux**: `sudo apt-get install tesseract-ocr`
  - **Windows**: Download from [Tesseract OCR Releases](https://github.com/UB-Mannheim/tesseract/wiki)
- **Ollama**: For LLM-based metadata extraction. See [Ollama.ai](https://ollama.ai) for installation instructions.

### Quick Installation (pip)

```bash
# Install from the current directory
pip install .

# Or install in development mode
pip install -e .
```

### Development Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/lsteuber/reference-renamer.git
   cd reference-renamer
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. Install dependencies and the package:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

### Troubleshooting Installation

If you encounter issues during installation:

1. Ensure you're in the correct directory:
   ```bash
   pwd  # Should show the reference-renamer directory
   ```

2. Verify Python version:
   ```bash
   python --version  # Should be 3.8 or higher
   ```

3. Update pip and setuptools:
   ```bash
   pip install --upgrade pip setuptools wheel
   ```

4. If you get permission errors:
   ```bash
   pip install --user .  # Install for current user only
   ```

5. For development installation issues:
   ```bash
   pip install -e . -v  # Verbose output for debugging
   ```

## Usage

### Display Help

```bash
filellama --help
```

This command displays information about available commands and options.

### Processing Files

- **Process a Single File**:
  ```bash
  filellama process /path/to/paper.pdf
  ```
- **Process a Directory (Recursive)**:
  ```bash
  filellama process --recursive /path/to/papers
  ```
- **Dry Run Mode (Preview Changes)**:
  ```bash
  filellama process --recursive --dry-run /path/to/papers
  ```
- **Specify Backup Directory and Custom Config**:
  ```bash
  filellama process --backup-dir /path/to/backups --config /path/to/config.yaml /path/to/papers
  ```

### Other Commands

- **Citations**: Extract and manage citations from academic papers (coming soon).
  ```bash
  filellama citations /path/to/papers
  ```
- **Extract**: Extract metadata and content from academic papers (coming soon).
  ```bash
  filellama extract /path/to/paper.pdf
  ```
- **Organize**: Organize papers into a logical directory structure (coming soon).
  ```bash
  filellama organize /path/to/papers
  ```

## Configuration

The tool can be configured using a YAML file. Below is an example (`config.yaml`):

```yaml
processing:
  supported_extensions:
    - .pdf
    - .txt
    - .doc
    - .docx
  recursive: true
  max_title_words: 5
  backup: true
  backup_dir: ".backups"
  filename_template: "{authors}_{year}_{title}"
  max_filename_length: 255
  author_format: "lastname"
  title_case: "title"

apis:
  semantic_scholar:
    enabled: true
    timeout: 30
    max_retries: 3
    rate_limit: 100

  arxiv:
    enabled: true
    max_results: 3
    timeout: 30

  ollama:
    enabled: true
    model: "drummer-knowledge"
    timeout: 60

output:
  citations:
    format: "bibtex"
    file: "citations.bib"
    overwrite: false

logging:
  level: "INFO"
  file: "rename_log.csv"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

accessibility:
  high_contrast: true
  verbose_output: true
  progress_bar: true
  screen_reader_hints: true
```

## Output Files

- **Renamed Files**: Files are renamed to a unified format (e.g., `Smith_2023_NeuralNetworksInML.pdf`).
- **Operation Log**: Detailed logs of operations are recorded in `rename_log.csv`.
- **Citation Database**: A BibTeX file (`citations.bib`) is maintained for document citations.

## Error Handling & Troubleshooting

- **File Access Errors**: Verify file permissions and ownership.
- **API Timeouts/Rate Limits**: Adjust API configurations in your `config.yaml` if you encounter timeouts.
- **OCR/Extraction Issues**: Ensure Tesseract is installed and configured properly.
- **Filename Conflicts**: The tool checks for existing files to avoid overwrites; unique filenames are generated if conflicts occur.

## Accessibility Features

- **Screen Reader Support**: Enhanced logging and progress indicators facilitate screen reader usage.
- **High Contrast Mode**: Launch the tool with the `--high-contrast` flag for improved visibility.
- **Verbose Output**: Use the `-v` or `--verbose` option for detailed logging information.

## Development & Testing

### Setting Up the Development Environment

1. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
2. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
pytest
```

For test coverage:
```bash
pytest --cov=reference_renamer
```

### Code Quality Tools

- **Formatting**: `black .`
- **Import Sorting**: `isort .`
- **Type Checking**: `mypy .`
- **Linting**: `flake8`

## Contributing

1. Fork the repository.
2. Create and checkout a feature branch.
3. Make your changes and ensure all tests pass.
4. Update documentation as needed.
5. Submit a pull request with a clear description of your changes.

Please follow the project's coding style guidelines and include tests for new features.

## Project Roadmap

Future enhancements include:
- **Citation Database Integration**
- **Batch Processing Improvements**
- **Custom Naming Templates**
- **Interactive and GUI Modes**
- **Cloud-based Processing Support**

For detailed project planning, refer to the [Project Plan](docs/PROJECT_PLAN.md).

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgments

- Built with Python using libraries such as PyPDF2, structlog, and rich.
- OCR capabilities powered by Tesseract.
- Metadata enrichment via Semantic Scholar, arXiv, and Ollama integrations.
- Special thanks to all contributors and the open source community.

## Getting Help

For issues or inquiries, please:
- Consult the documentation.
- Check [GitHub Issues](https://github.com/lsteuber/reference-renamer/issues).
- Join our community on [Discord](https://discord.gg/reference-renamer). 