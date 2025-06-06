# CleanupX

A unified code organization, deduplication, and documentation tool that uses the X.AI API to help manage code repositories and snippet collections.
This project is released under the MIT License by [Luke Steuber](https://lukesteuber.com) and is part of the [Assisted.site](https://assisted.site/) family of tools.
If you find it useful feel free to toss a coin in the [tip&nbsp;jar](https://usefulai.lemonsqueezy.com/buy/bf6ce1bd-85f5-4a09-ba10-191a670f74af) or follow along on [Substack](https://lukesteuber.substack.com/).

## Features

- **Deduplication**: Find and consolidate duplicate code files or snippets
- **Snippet Extraction**: Extract important parts of code files to create documentation
- **Organization**: Organize and rename files based on content analysis
- **API Integration**: Uses X.AI API for intelligent code analysis

## Requirements

- Python 3.7+
- X.AI API key (set as environment variable `XAI_API_KEY`)
- Required Python packages (see Installation section)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/cleanupx.git
   cd cleanupx
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set your X.AI API key:
   ```bash
   # Create a .env file
   echo "XAI_API_KEY=your_api_key_here" > .env
   ```

   Alternatively, you can set the environment variable directly:
   ```bash
   # For Linux/Mac
   export XAI_API_KEY=your_api_key_here
   
   # For Windows
   set XAI_API_KEY=your_api_key_here
   ```

## X.AI API Requirements

CleanupX uses the X.AI API for intelligent code analysis. To obtain an API key:

1. Visit the [X.AI website](https://x.ai/)
2. Create an account or log in
3. Navigate to the API section and create a new API key
4. Use this key in the `.env` file or set it as an environment variable

The API is used for:
- Finding duplicate files and creating consolidated versions
- Extracting the most important parts of code files
- Generating summaries and documentation from code

The default models used are:
- `grok-3-mini-latest` for text processing
- `grok-2-vision-latest` for image processing (if enabled)

You can customize these models by setting the appropriate environment variables (see Configuration section).

## Usage

If you just want to see how the API calls work, peek at the examples in
[`snippets/xai_api_usage.md`](snippets/xai_api_usage.md).

CleanupX provides a unified command-line interface for all its functions. Here are the main commands:

### Find and Process Duplicates

```bash
python cleanupx.py deduplicate --dir /path/to/directory [--output /path/to/output]
```

This command:
1. Identifies potential duplicate files using similarity analysis
2. Groups similar files into batches
3. Uses X.AI to analyze duplicates and create consolidated versions
4. Saves results in the output directory (default: `<dir>/deduplicated`)

### Extract Important Code Snippets

```bash
python cleanupx.py extract --dir /path/to/directory [--output output_file.md] [--mode code|snippet]
```

This command:
1. Processes all files in the directory
2. Uses X.AI to extract the most important code snippets
3. Combines them into a final document
4. Generates a project summary
5. Saves everything to the specified output file (default: `<dir>/final_combined.md`)

### Organize Files

```bash
python cleanupx.py organize --dir /path/to/directory
```

This command:
1. Analyzes files in the directory
2. Renames and organizes them based on content analysis
3. Updates file metadata

### Run All Processes

```bash
python cleanupx.py all --dir /path/to/directory [--output /path/to/output]
```

This command runs all the above processes in sequence and saves results to the specified output directory (default: `<dir>/cleanupx_output`).

## Individual Scripts

CleanupX consists of several interconnected scripts that can also be used independently:

### find_duplicates.py

Identifies potential duplicate files and prepares them for processing:

```bash
python find_duplicates.py /path/to/snippets [/path/to/output]
```

### process_duplicates.py

Processes batches of duplicate files using the X.AI API:

```bash
python process_duplicates.py /path/to/batches [--output-dir /path/to/output]
```

### xsnipper.py

Extracts important code snippets from files using the X.AI API:

```bash
python xsnipper.py --directory /path/to/code --mode code|snippet [--output output_file.md]
```

### organize.py

Organizes and renames files based on content analysis:

```bash
python organize.py /path/to/directory
```

## Configuration

CleanupX uses environment variables for configuration. You can set these in a `.env` file:

- `XAI_API_KEY`: Your X.AI API key (required)
- `XAI_MODEL_TEXT`: Model to use for text processing (default: "grok-3-mini-latest")
- `XAI_MODEL_VISION`: Model to use for image processing (default: "grok-2-vision-latest")

### Example .env file

```
XAI_API_KEY=your_api_key_here
XAI_MODEL_TEXT=grok-3-mini-latest
XAI_MODEL_VISION=grok-2-vision-latest
```

## Customizing Behavior

You can customize the behavior of CleanupX by modifying these parameters:

- In `find_duplicates.py`:
  - `SIMILARITY_THRESHOLD`: Adjust the threshold for considering files as duplicates (default: 0.25)
  - `MAX_BATCH_SIZE`: Maximum number of files to include in a single batch (default: 8)
  - `MAX_BATCH_TOKENS`: Maximum tokens to send in a single batch (default: 12000)
  - `VALID_EXTENSIONS`: File extensions to process

- In `xai_unified.py`:
  - `MAX_RETRIES`: Maximum number of API retries (default: 3)
  - `RETRY_DELAY`: Delay between retries in seconds (default: 2)

## Output Files

CleanupX creates various output files:

- **Deduplication**: 
  - `deduplicated/` directory with consolidated files
  - `deduplication_results.json` with detailed results

- **Snippet Extraction**:
  - `final_combined.md` with extracted snippets
  - `.xcleaner/summary.txt` with project summary
  - `.xcleaner/snippets.txt` with ongoing collection of snippets
  - `.xcleaner/log.txt` with processing logs

- **Complete Processing**:
  - `processing_results.json` with overall results
  - All files from individual processes

## Troubleshooting

### API Connection Issues
If you encounter API connection issues:
1. Verify your API key is correct
2. Check your internet connection
3. Ensure you're not exceeding API rate limits
4. Try increasing `MAX_RETRIES` in `xai_unified.py`

### File Processing Issues
If files aren't being processed correctly:
1. Check the file extensions against `VALID_EXTENSIONS`
2. Verify the files are text-based and not binary
3. For large files, try increasing `MAX_BATCH_TOKENS`

## License

[MIT License](LICENSE)

## Credits

- X.AI for providing the API for code analysis
- All contributors to this project
- Project lead and maintainer: [Luke Steuber](https://github.com/lukeslp)
- Licensed under the [MIT License](LICENSE)
