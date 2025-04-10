# Reference Renamer - Product Requirements Document

## Overview
Reference Renamer is a command-line interface (CLI) tool designed to standardize the naming of academic articles and research papers. It processes PDF, TXT, and other document formats, extracting metadata through content analysis and external API queries, then renames files to a consistent format based on APA-style conventions.

### Core Features
- Automated file renaming using the format: `Author_Year_FiveWordGeneratedTitle.ext`
- Content extraction from multiple file formats
- Metadata enrichment through arXiv, Semantic Scholar, and other academic APIs
- Intelligent title generation using LLM integration
- Comprehensive logging and citation tracking
- Accessibility-focused design

## Technical Architecture

### 1. Core Components

#### 1.1 File Processing System
```python
from pathlib import Path
from typing import List, Dict, Optional
import os
import logging

class FileProcessor:
    """Handles file discovery and initial processing."""
    
    def __init__(self, 
                 base_directory: str,
                 supported_extensions: List[str] = ['.pdf', '.txt'],
                 recursive: bool = True):
        self.base_directory = Path(base_directory)
        self.supported_extensions = supported_extensions
        self.recursive = recursive
        self.logger = logging.getLogger(__name__)
        
    def scan_directory(self) -> List[Path]:
        """
        Scans directory for supported files.
        
        Returns:
            List[Path]: List of paths to supported files
        """
        pattern = '**/*' if self.recursive else '*'
        files = []
        for ext in self.supported_extensions:
            files.extend(self.base_directory.glob(f'{pattern}{ext}'))
        return files
```

#### 1.2 Content Extraction Module
```python
from typing import Optional, Dict, Any
import PyPDF2
import pytesseract
from PIL import Image
import io

class ContentExtractor:
    """Extracts text content from various file formats."""
    
    def extract_content(self, file_path: Path) -> Dict[str, Any]:
        """
        Extracts content from a file based on its type.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dict containing:
                - text: Extracted text content
                - metadata: Any metadata found during extraction
                - format: The format of the original file
        """
        suffix = file_path.suffix.lower()
        
        if suffix == '.pdf':
            return self._extract_pdf(file_path)
        elif suffix == '.txt':
            return self._extract_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
            
    def _extract_pdf(self, file_path: Path) -> Dict[str, Any]:
        """PDF extraction with OCR fallback."""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                metadata = reader.metadata
                
                for page in reader.pages:
                    page_text = page.extract_text()
                    if not page_text.strip():
                        # If no text extracted, try OCR
                        page_text = self._ocr_pdf_page(page)
                    text += page_text
                    
                return {
                    'text': text,
                    'metadata': metadata,
                    'format': 'pdf'
                }
        except Exception as e:
            self.logger.error(f"Error extracting PDF content: {str(e)}")
            raise
```

#### 1.3 Metadata Extraction & Enrichment
```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ArticleMetadata:
    """Structured container for article metadata."""
    authors: List[str]
    year: Optional[int]
    title: str
    doi: Optional[str]
    abstract: Optional[str]
    keywords: List[str]
    
class MetadataEnricher:
    """Enriches document metadata using multiple sources."""
    
    def __init__(self,
                 semantic_scholar_api: SemanticScholarTool,
                 arxiv_api: Tools,
                 ollama_client: OllamaKnowledgeUser):
        self.semantic_scholar = semantic_scholar_api
        self.arxiv = arxiv_api
        self.ollama = ollama_client
        
    async def enrich_metadata(self, 
                            initial_metadata: Dict[str, Any],
                            content: str) -> ArticleMetadata:
        """
        Enriches metadata using multiple sources.
        
        1. Extracts basic metadata from content using LLM
        2. Searches academic APIs for additional information
        3. Combines and validates all sources
        """
        # Initial LLM extraction
        llm_metadata = await self._extract_with_llm(content)
        
        # Search academic APIs
        arxiv_data = await self._search_arxiv(llm_metadata)
        scholar_data = await self._search_semantic_scholar(llm_metadata)
        
        # Combine and validate
        return self._combine_metadata(llm_metadata, arxiv_data, scholar_data)
```

#### 1.4 Filename Generation
```python
import re
from typing import List

class FilenameGenerator:
    """Generates standardized filenames from metadata."""
    
    def __init__(self, max_title_words: int = 5):
        self.max_title_words = max_title_words
        
    def generate_filename(self,
                         metadata: ArticleMetadata,
                         original_extension: str) -> str:
        """
        Generates filename in format: Author_Year_FiveWordTitle.ext
        
        Args:
            metadata: ArticleMetadata object
            original_extension: Original file extension
            
        Returns:
            Standardized filename
        """
        # Get primary author (first author)
        author = self._format_author(metadata.authors[0])
        
        # Format year
        year = str(metadata.year) if metadata.year else "XXXX"
        
        # Generate title fragment
        title = self._generate_title_fragment(metadata.title)
        
        # Combine and sanitize
        filename = f"{author}_{year}_{title}{original_extension}"
        return self._sanitize_filename(filename)
        
    def _format_author(self, author: str) -> str:
        """Formats author name (Last, First -> Last)."""
        parts = author.split(',')
        return re.sub(r'\W+', '', parts[0].strip())
        
    def _generate_title_fragment(self, title: str) -> str:
        """Generates a five-word title fragment."""
        words = title.split()
        selected_words = words[:self.max_title_words]
        return '_'.join(word.capitalize() for word in selected_words)
```

#### 1.5 Logging and Citation Management
```python
import csv
from datetime import datetime
from pathlib import Path
import json

class ChangeLogger:
    """Logs file changes and maintains citation records."""
    
    def __init__(self, log_directory: Path):
        self.log_directory = log_directory
        self.log_directory.mkdir(parents=True, exist_ok=True)
        self.rename_log = self.log_directory / 'rename_log.csv'
        self.citation_log = self.log_directory / 'citations.bib'
        
    def log_change(self,
                   original_path: Path,
                   new_path: Path,
                   metadata: ArticleMetadata):
        """Logs a file rename operation."""
        # Log to CSV
        self._log_to_csv(original_path, new_path, metadata)
        
        # Add to citation database
        self._add_citation(metadata)
        
    def _log_to_csv(self,
                    original_path: Path,
                    new_path: Path,
                    metadata: ArticleMetadata):
        """Logs change to CSV file."""
        with open(self.rename_log, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                'timestamp',
                'original_path',
                'new_path',
                'authors',
                'year',
                'title',
                'doi'
            ])
            
            if csvfile.tell() == 0:
                writer.writeheader()
                
            writer.writerow({
                'timestamp': datetime.now().isoformat(),
                'original_path': str(original_path),
                'new_path': str(new_path),
                'authors': '; '.join(metadata.authors),
                'year': metadata.year,
                'title': metadata.title,
                'doi': metadata.doi
            })
```

### 2. Integration Points

#### 2.1 Ollama Integration
```python
class OllamaIntegration:
    """Handles interaction with Ollama LLM service."""
    
    def __init__(self, base_url: str = "http://localhost:11434/api/chat"):
        self.base_url = base_url
        
    async def extract_metadata(self, content: str) -> Dict[str, Any]:
        """
        Extracts metadata from content using Ollama.
        
        Args:
            content: Document content to analyze
            
        Returns:
            Dictionary containing extracted metadata
        """
        prompt = self._construct_metadata_prompt(content)
        response = await self._call_ollama(prompt)
        return self._parse_ollama_response(response)
        
    def _construct_metadata_prompt(self, content: str) -> str:
        """Constructs a prompt for metadata extraction."""
        return f"""
        Extract the following metadata from this academic article:
        - Author names (in order listed)
        - Publication year
        - Title
        - DOI (if present)
        - Keywords or key phrases
        
        Format the response as JSON.
        
        Content:
        {content[:2000]}  # First 2000 chars for context
        """
```

#### 2.2 Academic API Integration
```python
class AcademicAPIManager:
    """Manages interactions with academic APIs."""
    
    def __init__(self,
                 semantic_scholar: SemanticScholarTool,
                 arxiv: Tools):
        self.semantic_scholar = semantic_scholar
        self.arxiv = arxiv
        
    async def search_all_sources(self,
                               query: str,
                               max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Searches multiple academic sources for paper metadata.
        
        Args:
            query: Search query
            max_results: Maximum results to return per source
            
        Returns:
            Combined results from all sources
        """
        # Search both sources concurrently
        arxiv_results = await self.arxiv.search_papers(query)
        scholar_results = await self.semantic_scholar.execute(query)
        
        # Combine and deduplicate results
        return self._combine_results(arxiv_results, scholar_results)
```

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1-2)
1. Set up project structure
2. Implement file processing system
3. Build content extraction module
4. Create basic logging system

### Phase 2: Metadata Processing (Week 3-4)
1. Implement Ollama integration
2. Build academic API integrations
3. Create metadata enrichment system
4. Develop filename generation logic

### Phase 3: CLI & Integration (Week 5-6)
1. Build command-line interface
2. Implement configuration system
3. Create comprehensive logging
4. Add citation management

### Phase 4: Testing & Refinement (Week 7-8)
1. Write unit tests
2. Perform integration testing
3. Add error handling
4. Optimize performance

## Accessibility Considerations

### 1. Output Formats
- All logs and citations will be in plain text formats
- Support for screen readers through clear formatting
- High contrast CLI output

### 2. Error Handling
- Clear, descriptive error messages
- Graceful fallbacks for API failures
- Detailed logging for troubleshooting

### 3. Configuration
- Easy-to-edit configuration files
- Support for different naming conventions
- Customizable logging formats

## Testing Strategy

### 1. Unit Tests
```python
import pytest
from pathlib import Path

def test_file_processor():
    """Test file discovery and processing."""
    processor = FileProcessor("test_data")
    files = processor.scan_directory()
    assert len(files) > 0
    assert all(f.suffix in ['.pdf', '.txt'] for f in files)

def test_content_extraction():
    """Test content extraction from different formats."""
    extractor = ContentExtractor()
    
    # Test PDF extraction
    pdf_content = extractor.extract_content(Path("test_data/sample.pdf"))
    assert pdf_content['text']
    assert pdf_content['metadata']
    
    # Test TXT extraction
    txt_content = extractor.extract_content(Path("test_data/sample.txt"))
    assert txt_content['text']
```

### 2. Integration Tests
```python
async def test_metadata_enrichment():
    """Test full metadata enrichment pipeline."""
    enricher = MetadataEnricher(
        semantic_scholar_api=mock_semantic_scholar(),
        arxiv_api=mock_arxiv(),
        ollama_client=mock_ollama()
    )
    
    metadata = await enricher.enrich_metadata(
        initial_metadata={'title': 'Test Paper'},
        content='Sample content'
    )
    
    assert metadata.authors
    assert metadata.year
    assert metadata.title
```

## Documentation

### 1. Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Configure Ollama
# Make sure Ollama is running and the model is loaded
ollama run drummer-knowledge
```

### 2. Usage
```bash
# Basic usage
reference-renamer /path/to/papers

# With options
reference-renamer --recursive --dry-run /path/to/papers

# Generate citations only
reference-renamer --citations-only /path/to/papers
```

### 3. Configuration
```yaml
# config.yaml
processing:
  supported_extensions:
    - .pdf
    - .txt
  recursive: true
  max_title_words: 5

apis:
  semantic_scholar:
    enabled: true
    timeout: 30
  arxiv:
    enabled: true
    max_results: 3

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## Future Enhancements

1. GUI Interface
   - Web-based interface for file management
   - Drag-and-drop support
   - Preview of changes

2. Extended Format Support
   - Support for more document formats
   - Better OCR integration
   - Handling of scanned documents

3. Enhanced Metadata
   - Citation network analysis
   - Author disambiguation
   - Institution detection

4. Batch Processing
   - Parallel processing for large collections
   - Distributed processing support
   - Progress tracking and resumability

## Maintenance Plan

1. Regular Updates
   - Weekly dependency updates
   - Monthly feature releases
   - Quarterly major versions

2. Monitoring
   - Error tracking
   - Usage statistics
   - API quota management

3. Documentation
   - API documentation
   - User guides
   - Troubleshooting guides

## Security Considerations

1. API Keys
   - Secure storage
   - Rotation policies
   - Access controls

2. File Operations
   - Backup before rename
   - Checksums for verification
   - Permission checking

3. Data Privacy
   - Local processing when possible
   - Data retention policies
   - User consent for API usage 