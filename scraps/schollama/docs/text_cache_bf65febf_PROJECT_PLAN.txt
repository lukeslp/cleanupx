# FileLlama Project Plan

## 1. Metadata Extraction Pipeline

### 1.1 PDF Text Extraction Layer
- Implement PyPDF2 for initial text extraction
- Add Tesseract OCR fallback for scanned documents
- Extract text from:
  - Title pages
  - Headers
  - First few pages
  - References section
  - Full document if needed

### 1.2 Metadata Enrichment Services
1. **Academic APIs**
   - Semantic Scholar API for paper lookup
   - arXiv API for preprints
   - DOI resolution for published papers
   - CrossRef for citation data

2. **LLM Processing**
   - Primary: Ollama with drummer-knowledge model
   - Backup: Local embeddings for offline processing
   - Prompts for:
     ```
     - Author extraction (handling various formats)
     - Year identification
     - Title parsing
     - Key topic identification
     - Summary generation
     ```

### 1.3 Verification System
- Cross-reference multiple sources
- Confidence scoring for extracted metadata
- Human-readable validation reports
- Interactive confirmation for low-confidence cases

## 2. Filename Generation System

### 2.1 Author Name Processing
```python
Format: "LastName1_LastName2_et_al"
Rules:
- Use first author's full last name
- Include second author if only two
- Use "et_al" for three or more
- Handle hyphenated names
- Preserve non-English characters
- Remove special characters
```

### 2.2 Year Extraction
```python
Format: "YYYY"
Rules:
- Prefer publication year
- Fall back to submission/preprint year
- Handle date ranges (use earliest)
- Validate year format
```

### 2.3 Title Processing
```python
Format: "FiveWordSummary"
Rules:
- Extract key concepts
- Maintain semantic meaning
- Remove stop words
- CamelCase formatting
- Handle technical terms
- Maximum length control
```

## 3. Implementation Phases

### Phase 1: Core Infrastructure
- [x] Basic CLI setup
- [x] File scanning
- [x] Backup system
- [ ] Logging and error handling
- [ ] Configuration management

### Phase 2: Metadata Extraction
- [ ] PDF text extraction
- [ ] OCR integration
- [ ] API integrations
- [ ] LLM prompt engineering
- [ ] Metadata validation

### Phase 3: Filename Generation
- [ ] Author name processor
- [ ] Year validator
- [ ] Title summarizer
- [ ] Filename formatter
- [ ] Collision handler

### Phase 4: User Interface
- [ ] Interactive mode
- [ ] Batch processing
- [ ] Progress visualization
- [ ] Error recovery
- [ ] Configuration UI

## 4. LLM Prompt Templates

### 4.1 Author Extraction
```yaml
task: author_extraction
prompt: |
  Analyze the following academic text and extract the authors.
  Focus on:
  1. Author names in the header/title
  2. Author affiliations
  3. Corresponding author information
  4. Author order
  
  Return in format:
  {
    "primary_author": "LastName, FirstName",
    "all_authors": ["Author1", "Author2", ...],
    "confidence": 0.95
  }
```

### 4.2 Title Analysis
```yaml
task: title_processing
prompt: |
  Given this academic article title and abstract:
  [TEXT]
  
  1. Extract the 5 most important words that capture the core topic
  2. Ensure words are specific and meaningful
  3. Maintain proper technical terminology
  4. Avoid generic terms
  
  Return in format:
  {
    "key_words": ["Word1", "Word2", "Word3", "Word4", "Word5"],
    "confidence": 0.90
  }
```

### 4.3 Content Verification
```yaml
task: content_verification
prompt: |
  Compare the extracted metadata with the document content:
  
  Extracted:
  [METADATA]
  
  Document Text:
  [TEXT]
  
  Verify:
  1. Author names and order
  2. Publication year
  3. Title accuracy
  4. Subject matter
  
  Return confidence scores and any discrepancies found.
```

## 5. Error Handling

### 5.1 Common Failure Modes
- Missing or corrupt PDF data
- OCR failures
- API rate limits/failures
- LLM processing errors
- Filename collisions
- Invalid characters in paths

### 5.2 Recovery Strategies
- Automatic retries with backoff
- Alternative source fallbacks
- Manual intervention prompts
- Backup restoration
- Detailed error reporting

## 6. Testing Strategy

### 6.1 Test Datasets
- Create corpus of academic PDFs
- Include various formats:
  - Single/multiple authors
  - Different publication types
  - Multiple languages
  - Scanned documents
  - Born-digital PDFs

### 6.2 Validation Metrics
- Metadata extraction accuracy
- Filename compliance
- Processing speed
- Error recovery rate
- API efficiency

## 7. Documentation

### 7.1 User Documentation
- Installation guide
- Configuration options
- Command reference
- Best practices
- Troubleshooting

### 7.2 Technical Documentation
- Architecture overview
- API integrations
- LLM prompt design
- Error handling
- Testing procedures

## 8. Future Enhancements

### 8.1 Planned Features
- Citation database integration
- Batch processing optimization
- Custom naming templates
- GUI interface
- Cloud processing support

### 8.2 Performance Optimizations
- Parallel processing
- Caching system
- API request batching
- LLM context optimization
- Memory management

## Latest Updates

- Updated README.md with comprehensive documentation covering installation steps, usage instructions (including new CLI commands for process, citations, extract, and organize), configuration examples (YAML), troubleshooting tips, and accessibility features.
- Enhanced the CLI to better integrate intelligent renaming, metadata extraction, backup creation, and robust logging using structlog and rich.
- Improved error handling throughout the codebase, standardizing exception classes in `utils/exceptions.py`.
- Strengthened the backup mechanism in the FileProcessor class with unique timestamped backups.
- Refined the filename generation logic to ensure filesystem-safe and standardized names based on metadata.
- Overall codebase enhancements have been documented in this project plan to reflect improved functionality and maintainability. 