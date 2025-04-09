#!/usr/bin/env python3
"""
Citation extraction and management for CleanupX.

This module extracts citations from academic papers and documents,
and maintains a running APA citation list in each directory.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import re
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Constants
CITATIONS_FILE = ".cleanupx-citations"

def extract_citations_from_text(text: str) -> List[Dict[str, str]]:
    """
    Extract potential citations from text content.
    
    Args:
        text: The text content to analyze
        
    Returns:
        List of dictionaries containing citation information
    """
    citations = []
    
    # Look for patterns that might indicate references
    # This is a simplified approach; a more comprehensive solution would use NLP
    
    # Match APA-style in-text citations
    in_text_citations = re.findall(r'\(([A-Za-z]+(?:[ ,&]+[A-Za-z]+)*,? \d{4}[a-z]?(?:, p\. \d+)?)\)', text)
    
    # Match potential reference list entries (simplified pattern)
    reference_entries = re.findall(r'([A-Za-z]+, [A-Z]\. [A-Z]\.(?:, & [A-Za-z]+, [A-Z]\. [A-Z]\.)*) \((\d{4})\)\. (.*?)\. (.*?)(?: |$)', text)
    
    # Process in-text citations
    for citation in in_text_citations:
        # Parse the citation to extract authors and year
        parts = citation.split(',')
        if len(parts) >= 2:
            authors = parts[0].strip()
            year_match = re.search(r'(\d{4})', parts[1])
            year = year_match.group(1) if year_match else ""
            
            citations.append({
                "type": "in-text",
                "authors": authors,
                "year": year,
                "raw": citation
            })
    
    # Process reference list entries
    for entry in reference_entries:
        if len(entry) >= 4:
            authors, year, title, source = entry[0], entry[1], entry[2], entry[3]
            
            citations.append({
                "type": "reference",
                "authors": authors,
                "year": year,
                "title": title,
                "source": source,
                "raw": " ".join(entry)
            })
    
    return citations

def extract_citations_from_doi(doi: str) -> Optional[Dict[str, str]]:
    """
    Extract citation information from a DOI using public APIs.
    
    Args:
        doi: Digital Object Identifier
        
    Returns:
        Dictionary containing citation information, or None if extraction failed
    """
    try:
        import requests
        
        # Try to get metadata from CrossRef
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url, headers={"Accept": "application/json"})
        
        if response.status_code == 200:
            data = response.json()
            message = data.get("message", {})
            
            # Extract relevant fields
            title = message.get("title", [""])[0]
            authors = []
            for author in message.get("author", []):
                given = author.get("given", "")
                family = author.get("family", "")
                if given and family:
                    authors.append(f"{family}, {given[0]}.")
            
            # Extract publication date
            date_parts = message.get("published", {}).get("date-parts", [[]])
            year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""
            
            # Extract container (journal)
            container = message.get("container-title", [""])[0]
            
            # Extract volume, issue, pages
            volume = message.get("volume", "")
            issue = message.get("issue", "")
            page = message.get("page", "")
            
            # Extract URL
            url = message.get("URL", "")
            
            # Construct APA citation
            author_string = ", ".join(authors)
            if author_string:
                author_string += "."
            
            citation = {
                "type": "doi",
                "authors": author_string,
                "year": year,
                "title": title,
                "source": container,
                "volume": volume,
                "issue": issue,
                "pages": page,
                "doi": doi,
                "url": url,
                "raw": f"{author_string} ({year}). {title}. {container}, {volume}({issue}), {page}. {doi}"
            }
            
            return citation
            
    except Exception as e:
        logger.error(f"Error extracting citation from DOI {doi}: {e}")
    
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
    citations_file = directory / CITATIONS_FILE
    citations = []
    
    # Load existing citations if the file exists
    if citations_file.exists():
        try:
            with open(citations_file, 'r', encoding='utf-8') as f:
                citations = json.load(f)
        except Exception as e:
            logger.error(f"Error reading citations file {citations_file}: {e}")
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
        with open(citations_file, 'w', encoding='utf-8') as f:
            json.dump(citations, f, indent=2)
        logger.info(f"Updated citations file {citations_file} with {len(new_citations)} new citations")
    except Exception as e:
        logger.error(f"Error writing to citations file {citations_file}: {e}")
    
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
        logger.error(f"Error generating APA citation list for {directory}: {e}")
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
        logger.error(f"Error generating markdown citation list for {directory}: {e}")
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
        output_file = directory / "CITATIONS.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
            
        logger.info(f"Saved markdown citations to {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Error saving markdown citations for {directory}: {e}")
        return None

def process_file_for_citations(file_path: Union[str, Path], directory: Optional[Path] = None) -> Dict[str, Any]:
    """
    Process a file to extract citations.
    
    Args:
        file_path: Path to the file
        directory: Directory to store the citations file (defaults to file's directory)
        
    Returns:
        Dictionary with processing results
    """
    file_path = Path(file_path)
    if directory is None:
        directory = file_path.parent
        
    # Check if file exists
    if not file_path.exists():
        logger.error(f"File does not exist: {file_path}")
        return {"success": False, "error": "File not found"}
    
    # Extract text based on file type
    ext = file_path.suffix.lower()
    text = ""
    
    if ext == ".pdf":
        # For PDFs, we want to scan potentially more pages for citations
        # than needed for just file renaming, but still limit for large files
        from cleanupx.processors.document import extract_text_from_pdf
        text = extract_text_from_pdf(file_path, max_pages=3)
    elif ext == ".docx":
        from cleanupx.processors.document import extract_text_from_docx
        text = extract_text_from_docx(file_path)
    elif ext in (".txt", ".md", ".rtf"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    else:
        logger.warning(f"Unsupported file type for citation extraction: {ext}")
        return {"success": False, "error": "Unsupported file type"}
    
    # Extract citations from the text
    citations = extract_citations_from_text(text)
    
    # Look for DOIs in the text
    doi_pattern = r'\b(10\.\d{4,}(?:\.\d+)*\/(?:(?![\'"])\S)+)\b'
    dois = re.findall(doi_pattern, text)
    
    # Extract citation information from DOIs
    for doi in dois:
        doi_citation = extract_citations_from_doi(doi)
        if doi_citation:
            citations.append(doi_citation)
    
    # Update the citations file with the new citations
    if citations:
        update_citations_file(directory, citations)
        
        # Also generate and save a markdown version
        save_markdown_citations(directory)
    
    return {"success": True, "citations": citations}

def get_citation_stats(directory: Path) -> Dict[str, Any]:
    """
    Get statistics about citations in a directory.
    
    Args:
        directory: Directory path to analyze
        
    Returns:
        Dictionary with citation statistics
    """
    citations_file = directory / CITATIONS_FILE
    if not citations_file.exists():
        return {
            "total": 0,
            "reference": 0,
            "in_text": 0,
            "doi": 0,
            "has_citations_file": False
        }
    
    try:
        with open(citations_file, 'r', encoding='utf-8') as f:
            citations = json.load(f)
            
        stats = {
            "total": len(citations),
            "reference": sum(1 for c in citations if c.get("type") == "reference"),
            "in_text": sum(1 for c in citations if c.get("type") == "in-text"),
            "doi": sum(1 for c in citations if c.get("type") == "doi"),
            "has_citations_file": True
        }
        
        return stats
    except Exception as e:
        logger.error(f"Error getting citation stats for {directory}: {e}")
        return {
            "total": 0,
            "reference": 0,
            "in_text": 0,
            "doi": 0,
            "has_citations_file": False,
            "error": str(e)
        } 