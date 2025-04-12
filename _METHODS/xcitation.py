"""
XCITATION - SNIPPET FILE
Goal is to create a bibliography while renaming journal articles in a directory (and/or harvest links) 
using xAI and tool use for things like unpaywall semantic scholar, arxiv, and general web search.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Any, Set
import re
import json
from datetime import datetime
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter
import csv
from functools import wraps
import time
import requests
import os
import subprocess
import io
import argparse
import sys
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Constants and configuration
DEFAULT_MODEL_TEXT = "grok-3-mini-latest"
API_BASE_URL = "https://api.assisted.space/v2"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
CITATIONS_FILE = ".cleanupx/citations.json"
API_TIMEOUT = 30

# File type constants
TEXT_EXTENSIONS = {'.txt', '.md', '.markdown', '.rst', '.text', '.log', '.csv', '.tsv', '.json', '.xml', '.yaml', '.yml', '.html', '.htm', '.py', '.db', '.sh', '.rtf', '.ics', '.icsv', '.icsx'}
DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.doc', '.ppt', '.pptx', '.xlsx', '.xls'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.heif', '.ico'}
MEDIA_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.m4v'}
ARCHIVE_EXTENSIONS = {'.zip', '.tar', '.tgz', '.tar.gz', '.rar', '.gz', '.pkg'}

# Supported file extensions for citation extraction
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS.union(DOCUMENT_EXTENSIONS)

# Optional imports with fallbacks
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import docx2txt
    DOCX2TXT_AVAILABLE = True
except ImportError:
    DOCX2TXT_AVAILABLE = False

try:
    from docx import Document
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False

class Logger:
    """Simple logging class for consistent output formatting."""
    
    @staticmethod
    def info(message):
        logging.info(message)
    
    @staticmethod
    def warning(message):
        logging.warning(message)
    
    @staticmethod
    def error(message):
        logging.error(message)
        
    @staticmethod
    def debug(message):
        if os.getenv("DEBUG", "").lower() in ("1", "true", "yes"):
            logging.debug(message)

def call_xai_api(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL_TEXT,
    temperature: float = 0.7,
    functions: Optional[List[Dict[str, Any]]] = None,
    retries: int = MAX_RETRIES
) -> Optional[Dict[str, Any]]:
    """
    Call the X.AI API with retry logic.
    
    Args:
        messages: List of message dictionaries
        model: Model name to use
        temperature: Temperature for generation
        functions: Optional list of function definitions
        retries: Number of retries on failure
        
    Returns:
        API response dictionary or None on failure
    """
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        Logger.error("XAI_API_KEY environment variable not set")
        return None
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messages": messages,
        "model": model,
        "temperature": temperature
    }
    
    if functions:
        data["functions"] = functions
        
    for attempt in range(retries):
        try:
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            Logger.warning(f"API call failed (attempt {attempt + 1}/{retries}): {str(e)}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                Logger.error("Max retries reached for API call")
                return None

def extract_citations_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extract citations from text using the X.AI API.
    
    Args:
        text: Text to analyze
        
    Returns:
        List of citation dictionaries
    """
    messages = [
        {
            "role": "system",
            "content": """You are a citation extraction assistant. Your task is to analyze text and extract academic citations and references.
            For each citation, provide:
            1. Authors (as a list)
            2. Year
            3. Title
            4. Source (journal, conference, etc.)
            5. DOI if available
            6. URL if available
            
            Format your response as a JSON array of citation objects."""
        },
        {
            "role": "user",
            "content": text
        }
    ]
    
    # First try API-based extraction
    response = call_xai_api(messages)
    if response and "choices" in response:
        try:
            content = response["choices"][0]["message"]["content"]
            citations = json.loads(content)
            if isinstance(citations, list):
                return citations
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            Logger.warning(f"Failed to parse API response: {str(e)}")
    
    # Fallback to regex-based extraction
    Logger.info("Falling back to regex-based citation extraction")
    citations = []
    
    # Common citation patterns
    patterns = [
        # Author (Year) pattern
        r'([A-Z][a-z]+(?:,?\s+(?:&\s+)?[A-Z][a-z]+)*)\s+\((\d{4})\)',
        # (Author, Year) pattern
        r'\(([A-Z][a-z]+(?:,?\s+(?:&\s+)?[A-Z][a-z]+)*),\s+(\d{4})\)',
        # Author et al. (Year) pattern
        r'([A-Z][a-z]+)\s+et\s+al\.\s+\((\d{4})\)'
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            citation = {
                "authors": [author.strip() for author in match.group(1).split('&')],
                "year": match.group(2),
                "title": None,
                "source": None
            }
            citations.append(citation)
    
    return citations

def ensure_metadata_dir(directory: Path) -> Path:
    """
    Ensure the metadata directory exists.
    
    Args:
        directory: Base directory path
        
    Returns:
        Path to the metadata directory
    """
    metadata_dir = directory / ".cleanupx"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    return metadata_dir

def extract_text_from_pdf(file_path: Union[str, Path], max_pages: int = 3) -> str:
    """
    Extract text from a PDF file using various methods.
    
    Args:
        file_path: Path to the PDF file
        max_pages: Maximum number of pages to process
        
    Returns:
        Extracted text content
    """
    file_path = Path(file_path)
    text = ""
    
    # Try PyPDF2 if available
    if PYPDF2_AVAILABLE:
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                pages_to_read = min(len(reader.pages), max_pages) if max_pages else len(reader.pages)
                for i in range(pages_to_read):
                    text += reader.pages[i].extract_text() + "\n"
            if text.strip():
                return text
        except Exception as e:
            Logger.warning(f"PyPDF2 extraction failed for {file_path}: {e}")
    else:
        Logger.debug("PyPDF2 not available, skipping PyPDF2 extraction")
    
    # Try pdftotext as fallback
    try:
        page_option = []
        if max_pages:
            page_option = ["-l", str(max_pages)]
        result = subprocess.run(
            ["pdftotext"] + page_option + ["-layout", str(file_path), "-"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
        else:
            Logger.warning(f"pdftotext extraction failed for {file_path}: {result.stderr}")
    except Exception as e:
        Logger.warning(f"pdftotext extraction failed for {file_path}: {e}")
    
    return text

def extract_text_from_docx(file_path: Union[str, Path]) -> str:
    """
    Extract text from a DOCX file.
    
    Args:
        file_path: Path to the DOCX file
        
    Returns:
        Extracted text content
    """
    # Try docx2txt first if available
    if DOCX2TXT_AVAILABLE:
        try:
            text = docx2txt.process(file_path)
            if text:
                return text
        except Exception as e:
            Logger.warning(f"docx2txt extraction failed for {file_path}: {e}")
    
    # Try python-docx as fallback
    if PYTHON_DOCX_AVAILABLE:
        try:
            doc = Document(file_path)
            text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
            if text:
                return text
        except Exception as e:
            Logger.warning(f"python-docx extraction failed for {file_path}: {e}")
    
    Logger.error("No available DOCX extraction methods")
    return ""

def extract_text_from_txt(file_path: Union[str, Path]) -> str:
    """
    Extract text from a text file, trying multiple encodings.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        Extracted text content
    """
    encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()
                if text:
                    return text
        except UnicodeDecodeError:
            continue
        except Exception as e:
            Logger.error(f"Error reading {file_path} with {encoding}: {e}")
    
    # If all encodings fail, try binary read as last resort
    try:
        with open(file_path, 'rb') as f:
            return f.read().decode('utf-8', errors='replace')
    except Exception as e:
        Logger.error(f"Binary fallback failed for {file_path}: {e}")
    
    return ""

def extract_text_content(file_path: Union[str, Path]) -> str:
    """
    Extract text content from a file based on its type.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Extracted text content
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    
    try:
        # Use the appropriate extraction method based on file type
        if ext in TEXT_EXTENSIONS:
            return extract_text_from_txt(file_path)
        elif ext in {'.pdf'}:
            return extract_text_from_pdf(file_path)
        elif ext in {'.docx', '.doc'}:
            return extract_text_from_docx(file_path)
        elif ext in {'.xlsx', '.xls'}:
            # For Excel files, try to extract text using pandas
            if PANDAS_AVAILABLE:
                try:
                    df = pd.read_excel(file_path)
                    return df.to_string()
                except Exception as e:
                    Logger.error(f"Error processing Excel file {file_path}: {e}")
                    return ""
            else:
                Logger.warning("pandas not installed, cannot process Excel files")
                return ""
        else:
            # Fallback to general text extraction
            return extract_text_from_txt(file_path)
            
    except Exception as e:
        Logger.error(f"Error extracting text from {file_path}: {e}")
        return ""

def extract_citations_from_doi(doi: str) -> Optional[Dict[str, Any]]:
    """
    Extract citation information from a DOI using CrossRef API.
    
    Args:
        doi: DOI string
        
    Returns:
        Citation dictionary or None on failure
    """
    try:
        url = f"https://api.crossref.org/works/{quote_plus(doi)}"
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()["message"]
        
        citation = {
            "authors": [
                f"{author.get('given', '')} {author.get('family', '')}"
                for author in data.get("author", [])
            ],
            "year": data.get("published-print", {}).get("date-parts", [[None]])[0][0],
            "title": data.get("title", [None])[0],
            "source": data.get("container-title", [None])[0],
            "doi": doi,
            "url": data.get("URL")
        }
        
        return citation
        
    except Exception as e:
        Logger.warning(f"Failed to fetch citation for DOI {doi}: {str(e)}")
        return None

def update_citations_file(directory: Path, new_citations: List[Dict[str, Any]]) -> Path:
    """
    Update the citations file in the given directory.
    
    Args:
        directory: Directory path where the citations file should be updated
        new_citations: List of new citations to add
        
    Returns:
        Path to the updated citations file
    """
    citations_file = CITATIONS_FILE(directory)
    citations = []
    
    # Load existing citations if the file exists
    if citations_file.exists():
        try:
            with open(citations_file, 'r', encoding='utf-8') as f:
                citations = json.load(f)
        except Exception as e:
            Logger.error(f"Error reading citations file {citations_file}: {e}")
            citations = []
    
    # Add new citations, avoiding duplicates
    existing_raws = {c.get("raw", "") for c in citations}
    for citation in new_citations:
        if citation.get("raw", "") not in existing_raws:
            citation["date_added"] = datetime.now().isoformat()
            citations.append(citation)
            existing_raws.add(citation.get("raw", ""))
    
    # Sort citations by author then year
    citations.sort(key=lambda x: (x.get("authors", ""), x.get("year", "")))
    
    # Write updated citations to file
    try:
        # Ensure .cleanupx directory exists
        citations_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(citations_file, 'w', encoding='utf-8') as f:
            json.dump(citations, f, indent=2)
        Logger.info(f"Updated citations file {citations_file} with {len(new_citations)} new citations")
    except Exception as e:
        Logger.error(f"Error writing to citations file {citations_file}: {e}")
    
    return citations_file

def generate_apa_citation_list(directory: Path) -> str:
    """
    Generate a formatted APA citation list from the citations file.
    
    Args:
        directory: Directory path where the citations file is located
        
    Returns:
        Formatted string with APA citations
    """
    citations_file = directory / CITATIONS_FILE
    if not citations_file.exists():
        return "No citations found."
    
    try:
        with open(citations_file, 'r', encoding='utf-8') as f:
            citations = json.load(f)
        
        # Filter to include only reference and DOI citations (not in-text)
        references = [c for c in citations if c.get("type") in ["reference", "doi"]]
        
        # Generate formatted APA citations
        formatted_citations = []
        
        for ref in references:
            authors = ref.get("authors", "")
            year = ref.get("year", "")
            title = ref.get("title", "")
            source = ref.get("source", "")
            volume = ref.get("volume", "")
            issue = ref.get("issue", "")
            pages = ref.get("pages", "")
            doi = ref.get("doi", "")
            url = ref.get("url", "")
            
            # Format the citation in APA style
            citation = f"{authors} ({year}). {title}. "
            
            # Add source information
            if source:
                citation += f"{source}"
                if volume:
                    citation += f", {volume}"
                    if issue:
                        citation += f"({issue})"
                if pages:
                    citation += f", {pages}"
                citation += "."
            
            # Add DOI or URL
            if doi:
                citation += f" https://doi.org/{doi}"
            elif url:
                citation += f" Retrieved from {url}"
            
            formatted_citations.append(citation)
        
        # Join citations with line breaks
        return "\n\n".join(formatted_citations)
        
    except Exception as e:
        Logger.error(f"Error generating APA citation list for {directory}: {e}")
        return f"Error generating citations: {e}"

def generate_markdown_citation_list(directory: Path) -> str:
    """
    Generate a markdown-formatted citation list for the directory.
    
    Args:
        directory: Directory path where the citations file is located
        
    Returns:
        Markdown string with APA citations
    """
    citations_file = directory / CITATIONS_FILE
    if not citations_file.exists():
        return "# Citations\n\nNo citations found in this directory."
    
    try:
        with open(citations_file, 'r', encoding='utf-8') as f:
            citations = json.load(f)
        
        # Filter to include only reference and DOI citations (not in-text)
        references = [c for c in citations if c.get("type") in ["reference", "doi"]]
        
        # Generate markdown
        markdown = f"# Citations from {directory.name}\n\n"
        markdown += f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
        
        if not references:
            markdown += "No formal citations found in this directory.\n"
            return markdown
        
        markdown += "## References\n\n"
        
        for ref in references:
            authors = ref.get("authors", "")
            year = ref.get("year", "")
            title = ref.get("title", "")
            source = ref.get("source", "")
            volume = ref.get("volume", "")
            issue = ref.get("issue", "")
            pages = ref.get("pages", "")
            doi = ref.get("doi", "")
            url = ref.get("url", "")
            
            # Format the citation in APA style with markdown
            citation = f"{authors} ({year}). *{title}*. "
            
            # Add source information
            if source:
                citation += f"**{source}**"
                if volume:
                    citation += f", {volume}"
                    if issue:
                        citation += f"({issue})"
                if pages:
                    citation += f", {pages}"
                citation += "."
            
            # Add DOI or URL with markdown link
            if doi:
                doi_url = f"https://doi.org/{doi}"
                citation += f" [{doi}]({doi_url})"
            elif url:
                citation += f" [Link]({url})"
            
            markdown += f"- {citation}\n\n"
        
        return markdown
        
    except Exception as e:
        Logger.error(f"Error generating markdown citation list for {directory}: {e}")
        return f"# Citations\n\nError generating citations: {e}"

def save_markdown_citations(directory: Path) -> Optional[Path]:
    """
    Save the citations as a markdown file in the directory.
    
    Args:
        directory: Directory path where to save the markdown
        
    Returns:
        Path to the saved markdown file, or None if failed
    """
    try:
        markdown = generate_markdown_citation_list(directory)
        metadata_dir = ensure_metadata_dir(directory)
        output_file = metadata_dir / "CITATIONS.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
            
        Logger.info(f"Saved markdown citations to {output_file}")
        return output_file
    except Exception as e:
        Logger.error(f"Error saving markdown citations for {directory}: {e}")
        return None

def process_file_for_citations(
    file_path: Union[str, Path],
    metadata_dir: Path,
    mode: str = "all"
) -> Dict[str, Any]:
    """
    Process a single file for citations.
    
    Args:
        file_path: Path to the file to process
        metadata_dir: Directory to store metadata
        mode: Processing mode ('all', 'new', or 'update')
        
    Returns:
        Dictionary containing processing results
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}
            
        # Check if file type is supported
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return {"error": f"Unsupported file type: {file_path.suffix}"}
            
        # Get file modification time
        mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
        
        # Check if we should process this file based on mode
        citations_file = metadata_dir / "citations.json"  # Fixed path
        if mode != "all" and citations_file.exists():
            with open(citations_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
                file_key = str(file_path)
                
                if file_key in existing:
                    last_processed = datetime.fromisoformat(existing[file_key]["last_processed"])
                    if mode == "new" or (mode == "update" and mod_time <= last_processed):
                        return {"skipped": "Already processed"}
        
        # Extract content using appropriate method based on file type
        content = extract_text_content(file_path)
        if not content:
            return {"error": f"Failed to extract content from {file_path}"}
            
        # Extract citations using API
        citations = extract_citations_from_text(content)
        
        # Look for DOIs
        doi_pattern = r'\b(10\.\d{4,}(?:\.\d+)*\/(?:(?![\'"])\S)+)\b'
        dois = re.findall(doi_pattern, content)
        
        # Get citation info for each DOI
        for doi in dois:
            citation = extract_citations_from_doi(doi)
            if citation:
                citations.append(citation)
                
        # Update citations file
        if citations:
            citations_data = {
                str(file_path): {
                    "citations": citations,
                    "last_processed": mod_time.isoformat(),
                    "file_type": file_path.suffix.lower()
                }
            }
            
            if citations_file.exists():
                with open(citations_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                existing.update(citations_data)
                citations_data = existing
                
            # Ensure parent directory exists
            citations_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(citations_file, "w", encoding="utf-8") as f:
                json.dump(citations_data, f, indent=2)
                
            # Generate markdown version
            markdown_file = metadata_dir / "citations.md"
            with open(markdown_file, "w", encoding="utf-8") as f:
                f.write("# Citations\n\n")
                for file_info in citations_data.values():
                    for citation in file_info["citations"]:
                        authors = citation.get("authors", [])
                        if isinstance(authors, str):
                            authors = [authors]
                        author_text = ", ".join(authors) if authors else "Unknown Author"
                        
                        year = citation.get("year", "n.d.")
                        title = citation.get("title", "Untitled")
                        source = citation.get("source", "")
                        doi = citation.get("doi", "")
                        url = citation.get("url", "")
                        
                        f.write(f"## {title}\n\n")
                        f.write(f"**Authors:** {author_text}\n\n")
                        f.write(f"**Year:** {year}\n\n")
                        if source:
                            f.write(f"**Source:** {source}\n\n")
                        if doi:
                            f.write(f"**DOI:** [{doi}](https://doi.org/{doi})\n\n")
                        if url and url != f"https://doi.org/{doi}":
                            f.write(f"**URL:** {url}\n\n")
                        f.write("---\n\n")
            
        return {
            "processed": True,
            "citations_found": len(citations),
            "file": str(file_path)
        }
        
    except Exception as e:
        Logger.error(f"Error processing file {file_path}: {str(e)}")
        return {"error": str(e)}

def process_directory(
    directory: Union[str, Path],
    mode: str = "all",
    file_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Process a directory for citations.
    
    Args:
        directory: Directory to process
        mode: Processing mode ('all', 'new', or 'update')
        file_types: List of file extensions to process (defaults to SUPPORTED_FILE_TYPES)
        
    Returns:
        Dictionary containing processing results
    """
    try:
        directory = Path(directory)
        if not directory.exists():
            return {"error": f"Directory not found: {directory}"}
            
        # Initialize metadata directory
        metadata_dir = ensure_metadata_dir(directory)
        if not metadata_dir:
            return {"error": "Failed to create metadata directory"}
            
        # Get list of files to process
        if not file_types:
            file_types = SUPPORTED_EXTENSIONS
            
        files = []
        for ext in file_types:
            files.extend(directory.rglob(f"*{ext}"))
            
        results = {
            "total_files": len(files),
            "processed": 0,
            "skipped": 0,
            "errors": [],
            "citations_found": 0
        }
        
        # Process each file
        for file_path in files:
            result = process_file_for_citations(file_path, metadata_dir, mode)
            
            if "error" in result:
                results["errors"].append({
                    "file": str(file_path),
                    "error": result["error"]
                })
            elif "skipped" in result:
                results["skipped"] += 1
            else:
                results["processed"] += 1
                results["citations_found"] += result.get("citations_found", 0)
                
        # Generate summary markdown
        summary_file = metadata_dir / "processing_summary.md"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("# Citation Processing Summary\n\n")
            f.write(f"**Processed on:** {datetime.now().isoformat()}\n\n")
            f.write(f"**Mode:** {mode}\n\n")
            f.write(f"**Total files found:** {results['total_files']}\n")
            f.write(f"**Files processed:** {results['processed']}\n")
            f.write(f"**Files skipped:** {results['skipped']}\n")
            f.write(f"**Total citations found:** {results['citations_found']}\n\n")
            
            if results["errors"]:
                f.write("## Errors\n\n")
                for error in results["errors"]:
                    f.write(f"- {error['file']}: {error['error']}\n")
                    
        return results
        
    except Exception as e:
        Logger.error(f"Error processing directory {directory}: {str(e)}")
        return {"error": str(e)}

def interactive_cli():
    """Interactive command-line interface for citation processing."""
    print("\nWelcome to X.AI Citation Processor!")
    print("This script processes academic files to extract and manage citations.")
    print("Ensure your XAI_API_KEY environment variable is set.")
    
    while True:
        print("\nPlease choose an option:")
        print("  1. Process a directory for citations")
        print("  2. Process a single file for citations")
        print("  3. Generate bibliography in specific format")
        print("  4. Export citations")
        print("  5. Clear citation cache")
        print("  6. Exit")
        
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == "1":
            directory = input("Enter the full path to the directory: ").strip()
            if not os.path.isdir(directory):
                print(f"Error: {directory} is not a valid directory.")
                continue
            
            mode = input("Enter the mode ('all', 'new', or 'update'): ").strip().lower()
            if mode not in ['all', 'new', 'update']:
                print("Invalid mode. Using 'all'.")
                mode = 'all'
            
            file_types_input = input("Enter file types to process (comma-separated, e.g. '.pdf,.txt', or press Enter for all): ").strip()
            file_types = [ft.strip() for ft in file_types_input.split(',')] if file_types_input else None
            
            results = process_directory(directory, mode=mode, file_types=file_types)
            
            if "error" in results:
                print(f"\nProcessing failed: {results['error']}")
            else:
                print(f"\nProcessing complete!")
                print(f"Total files found: {results['total_files']}")
                print(f"Files processed: {results['processed']}")
                print(f"Files skipped: {results['skipped']}")
                print(f"Total citations found: {results['citations_found']}")
                if results["errors"]:
                    print(f"\nEncountered {len(results['errors'])} errors:")
                    for error in results["errors"]:
                        print(f"- {error['file']}: {error['error']}")
        
        elif choice == "2":
            file_path = input("Enter the full path to the file: ").strip()
            if not os.path.isfile(file_path):
                print(f"Error: {file_path} is not a valid file.")
                continue
            
            verbose_input = input("Enable verbose output? (y/n): ").strip().lower()
            verbose = verbose_input == "y"
            
            result = process_file_for_citations(file_path)
            
            if result["success"]:
                print(f"\nSuccessfully processed: {file_path}")
                print(f"Found {len(result['citations'])} citations")
                if verbose:
                    for citation in result["citations"]:
                        print(f"\n- {citation.get('authors', 'Unknown')} ({citation.get('year', 'Unknown')})")
                        print(f"  {citation.get('title', 'No title')}")
            else:
                print(f"\nError processing {file_path}: {result.get('error', 'Unknown error')}")
        
        elif choice == "3":
            directory = input("Enter the directory path: ").strip()
            if not os.path.isdir(directory):
                print(f"Error: {directory} is not a valid directory.")
                continue
            
            format_choice = input("Choose citation format (apa/mla/chicago/ieee): ").strip().lower()
            if format_choice not in ['apa', 'mla', 'chicago', 'ieee']:
                print("Invalid format. Using APA.")
                format_choice = 'apa'
            
            output = input("Enter output file name (default: bibliography.md): ").strip()
            if not output:
                output = "bibliography.md"
            
            bibliography = create_bibliography(directory, format_choice)
            if bibliography:
                try:
                    with open(os.path.join(directory, output), 'w', encoding='utf-8') as f:
                        f.write(bibliography)
                    print(f"\nBibliography saved to {output}")
                except Exception as e:
                    print(f"Error saving bibliography: {e}")
            else:
                print("No citations found to generate bibliography.")
        
        elif choice == "4":
            directory = input("Enter the directory path: ").strip()
            if not os.path.isdir(directory):
                print(f"Error: {directory} is not a valid directory.")
                continue
            
            format_choice = input("Choose export format (txt/md/bib/csv): ").strip().lower()
            if format_choice not in ['txt', 'md', 'bib', 'csv']:
                print("Invalid format. Using markdown.")
                format_choice = 'md'
            
            output = input("Enter output file name: ").strip()
            if not output:
                output = f"citations.{format_choice}"
            
            citations = generate_citation_list(directory, format_choice)
            if citations:
                try:
                    with open(os.path.join(directory, output), 'w', encoding='utf-8') as f:
                        f.write(citations)
                    print(f"\nCitations exported to {output}")
                except Exception as e:
                    print(f"Error exporting citations: {e}")
            else:
                print("No citations found to export.")
        
        elif choice == "5":
            directory = input("Enter the directory path (or leave blank for current directory): ").strip()
            if not directory:
                directory = os.getcwd()
            
            confirm = input("Are you sure you want to clear the citation cache? (y/n): ").strip().lower()
            if confirm == "y":
                cache_file = os.path.join(directory, CITATIONS_FILE)
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    print("Citation cache cleared.")
                else:
                    print("No citation cache found.")
        
        elif choice == "6":
            print("Exiting X.AI Citation Processor. Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="X.AI Citation Processor: Extract and manage academic citations from files.\n" +
                   "If no arguments are provided, an interactive CLI is launched."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--directory", help="Path to a directory to process for citations")
    group.add_argument("--file", help="Path to a single file to process")
    
    parser.add_argument("--mode", choices=["all", "new", "update"], default="all",
                      help="Processing mode (all, new, update)")
    parser.add_argument("--format", choices=["apa", "mla", "chicago", "ieee", "txt", "md", "bib", "csv"],
                      help="Output format for citations")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--recursive", "-r", action="store_true", help="Process subdirectories recursively")
    parser.add_argument("--clear-cache", action="store_true", help="Clear citation cache")
    
    args = parser.parse_args()
    
    if not any([args.directory, args.file, args.clear_cache]):
        interactive_cli()
    else:
        if args.clear_cache:
            directory = args.directory if args.directory else os.getcwd()
            cache_file = os.path.join(directory, CITATIONS_FILE)
            if os.path.exists(cache_file):
                os.remove(cache_file)
                print("Citation cache cleared.")
            else:
                print("No citation cache found.")
            return
        
        if args.file:
            result = process_file_for_citations(args.file)
            if result["success"]:
                print(f"Found {len(result['citations'])} citations")
                if args.verbose:
                    for citation in result["citations"]:
                        print(f"\n- {citation.get('authors', 'Unknown')} ({citation.get('year', 'Unknown')})")
                        print(f"  {citation.get('title', 'No title')}")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
        
        if args.directory:
            output_file = args.output if args.output else "citations.md"
            results = process_directory(
                args.directory,
                args.mode,
                args.verbose,
                output_file,
                args.recursive
            )
            
            if results["success"]:
                print(f"Processed {len(results['processed_files'])} files")
                print(f"Found {results['total_citations']} citations")
                if results["errors"]:
                    print(f"Encountered {len(results['errors'])} errors:")
                    for error in results["errors"]:
                        print(f"- {error['file']}: {error['error']}")
            else:
                print(f"Error: {results.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()