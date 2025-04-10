# Snippet Deduplication Tool

This tool helps identify and consolidate duplicate code snippets using a combination of text similarity detection and LLM-powered analysis.

## Overview

The deduplication process works in three steps:

1. **Finding potential duplicates**: Using a low similarity threshold (25% by default) to identify groups of potentially similar files
2. **Generating batch prompts**: Creating batches of similar files to send to an LLM for analysis
3. **Processing with LLM**: Having an LLM analyze each batch to identify true duplicates and create consolidated versions

## Features

- Uses text similarity metrics to identify potential duplicates
- Groups similar files into manageable batches
- Leverages LLMs to intelligently analyze and consolidate duplicates
- Maintains detailed metadata about the deduplication process
- Supports a wide range of file types (Python, JavaScript, HTML, CSS, etc.)
- Handles token limits and batch sizes automatically

## Requirements

- Python 3.6+
- Access to the cleanupx API and LLM models (optional, will work in simulation mode without them)

## Installation

1. Place these scripts in your project directory
2. Make them executable:
   ```bash
   chmod +x find_duplicates.py process_duplicates.py deduplicate_snippets.py
   ```

## Usage

### Complete Workflow

To run the complete deduplication workflow:

```bash
./deduplicate_snippets.py /path/to/snippets
```

This will:
1. Find all potential duplicates in the snippets directory
2. Generate batch prompts for LLM analysis
3. Process these batches with an LLM
4. Create consolidated files

### Options

```
usage: deduplicate_snippets.py [-h] [--output-dir OUTPUT_DIR] [--threshold THRESHOLD] [--skip-processing] snippets_dir

Run the complete snippet deduplication workflow

positional arguments:
  snippets_dir          Directory containing snippets to deduplicate

optional arguments:
  -h, --help            show this help message and exit
  --output-dir OUTPUT_DIR, -o OUTPUT_DIR
                        Base directory for all outputs (default: snippets_dir/deduplication_TIMESTAMP)
  --threshold THRESHOLD, -t THRESHOLD
                        Similarity threshold (0.0-1.0, default: 0.25)
  --skip-processing, -s
                        Skip LLM processing of batches (only generate batch files)
```

### Two-Step Process

If you want more control, you can run the steps separately:

#### 1. Find Potential Duplicates

```bash
./find_duplicates.py /path/to/snippets /path/to/output/batches
```

This will analyze the snippets directory and generate batch prompt files in the output directory.

#### 2. Process Batches with LLM

```bash
./process_duplicates.py /path/to/batches --output-dir /path/to/consolidated
```

This will process the generated batch files using an LLM and create consolidated files.

## Output Structure

The tool creates the following directory structure:

```
output_dir/
├── batches/
│   ├── batch_20230515_120145.txt       # LLM prompt for batch 1
│   ├── batch_20230515_120145.response.json  # LLM response for batch 1
│   ├── batch_20230515_120146.txt       # LLM prompt for batch 2
│   ├── batch_20230515_120146.response.json  # LLM response for batch 2
│   └── deduplication_results.json      # Overall batch generation results
├── consolidated/
│   ├── consolidated_file1.py           # Consolidated version of duplicate files
│   ├── consolidated_file1.py.meta.json # Metadata about the consolidation
│   ├── consolidated_file2.js           # Another consolidated file
│   ├── consolidated_file2.js.meta.json # Metadata about the consolidation
│   └── processing_results.json         # Overall processing results
```

## Metadata

Each consolidated file has an accompanying `.meta.json` file containing:
- The group ID that was consolidated
- Analysis of the duplicates by the LLM
- List of original files that were identified as duplicates
- Path to the consolidated file

## Example Workflow

1. You have a directory with many code snippets, some of which are duplicates
2. Run `./deduplicate_snippets.py /path/to/snippets`
3. Review the consolidated files in the output directory
4. For each consolidated file, check its metadata to see which original files it replaces
5. Delete or archive the duplicate files as needed

## Advanced Usage

### Adjusting Similarity Threshold

To catch more potential duplicates (with more false positives):
```bash
./deduplicate_snippets.py /path/to/snippets --threshold 0.15
```

To be more selective (with more false negatives):
```bash
./deduplicate_snippets.py /path/to/snippets --threshold 0.40
```

### Generating Batches Without Processing

If you want to manually review the batch prompts before processing:
```bash
./deduplicate_snippets.py /path/to/snippets --skip-processing
```

This will generate the batch files but not send them to the LLM. You can then review the batch files and run the processing step separately.

## Troubleshooting

### API Not Available

If the cleanupx API is not available, the script will run in simulation mode and generate placeholder consolidated files. To use the full functionality, ensure the API is properly configured.

### Large Batches

If you have a very large number of similar files, the batching algorithm will automatically split them into manageable chunks. You can adjust the `MAX_BATCH_SIZE` and `MAX_BATCH_TOKENS` constants in the script if needed.

### File Encoding Issues

The script attempts to handle different file encodings, but if you encounter issues, try setting the `errors='replace'` parameter in the file reading functions to a different value. 