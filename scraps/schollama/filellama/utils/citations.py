"""
Citation utilities for Reference Renamer.
Handles writing citations to different formats (BibTeX, CSV).
"""

import csv
from pathlib import Path
from typing import Dict, List, Any

import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

def write_bibtex(citations: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Write citations to a BibTeX file.
    
    Args:
        citations: List of citation metadata dictionaries
        output_path: Path to write the BibTeX file
    """
    db = BibDatabase()
    db.entries = []
    
    for citation in citations:
        entry = {
            'ID': citation.get('citation_key', 'Unknown'),
            'ENTRYTYPE': 'article',
            'title': citation.get('title', 'Unknown Title'),
            'author': ' and '.join(citation.get('authors', ['Unknown'])),
            'year': str(citation.get('year', 'Unknown')),
            'journal': citation.get('journal', ''),
            'doi': citation.get('doi', ''),
            'url': citation.get('url', ''),
            'abstract': citation.get('abstract', ''),
            'keywords': ', '.join(citation.get('keywords', [])),
        }
        
        # Remove empty fields
        entry = {k: v for k, v in entry.items() if v}
        db.entries.append(entry)
        
    writer = BibTexWriter()
    writer.indent = '    '  # 4 spaces
    writer.comma_first = False
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(writer.write(db))
        
def write_csv(citations: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Write citations to a CSV file.
    
    Args:
        citations: List of citation metadata dictionaries
        output_path: Path to write the CSV file
    """
    fieldnames = [
        'citation_key',
        'title',
        'authors',
        'year',
        'journal',
        'doi',
        'url',
        'abstract',
        'keywords'
    ]
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for citation in citations:
            row = {
                'citation_key': citation.get('citation_key', ''),
                'title': citation.get('title', ''),
                'authors': '; '.join(citation.get('authors', [])),
                'year': citation.get('year', ''),
                'journal': citation.get('journal', ''),
                'doi': citation.get('doi', ''),
                'url': citation.get('url', ''),
                'abstract': citation.get('abstract', ''),
                'keywords': ', '.join(citation.get('keywords', []))
            }
            writer.writerow(row) 