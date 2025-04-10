"""
Change logging and citation management module for Reference Renamer.
Handles logging of file operations and maintains citation records.
"""

import csv
from datetime import datetime
from pathlib import Path
import json
import logging
from typing import Dict, Any, Optional, List
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

from .metadata_enricher import ArticleMetadata
from ..utils.exceptions import LoggingError
from ..utils.logging import get_logger

class ChangeLogger:
    """Logs file changes and maintains citation records."""
    
    def __init__(
        self,
        log_directory: Path,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the change logger.
        
        Args:
            log_directory: Directory for log files
            logger: Optional logger instance
        """
        self.log_directory = Path(log_directory)
        self.logger = logger or get_logger(__name__)
        
        # Create log directory if it doesn't exist
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize log files
        self.rename_log = self.log_directory / 'rename_log.csv'
        self.citation_log = self.log_directory / 'citations.bib'
        self.error_log = self.log_directory / 'errors.log'
        
        # Initialize CSV headers if needed
        self._initialize_logs()
        
    def _initialize_logs(self):
        """Initialize log files with headers if they don't exist."""
        try:
            # Initialize rename log
            if not self.rename_log.exists():
                with open(self.rename_log, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=[
                        'timestamp',
                        'original_path',
                        'new_path',
                        'authors',
                        'year',
                        'title',
                        'doi'
                    ])
                    writer.writeheader()
                    
            # Initialize citation log
            if not self.citation_log.exists():
                self.citation_log.touch()
                
            # Initialize error log
            if not self.error_log.exists():
                self.error_log.touch()
                
        except Exception as e:
            raise LoggingError(f"Error initializing logs: {str(e)}")
            
    def log_change(
        self,
        original_path: Path,
        new_path: Path,
        metadata: ArticleMetadata
    ):
        """
        Logs a file rename operation.
        
        Args:
            original_path: Original file path
            new_path: New file path
            metadata: Article metadata
            
        Raises:
            LoggingError: If logging fails
        """
        try:
            # Log to CSV
            self._log_to_csv(original_path, new_path, metadata)
            
            # Add to citation database
            self._add_citation(metadata)
            
            self.logger.info(f"Logged change: {original_path} -> {new_path}")
            
        except Exception as e:
            raise LoggingError(f"Error logging change: {str(e)}")
            
    def _log_to_csv(
        self,
        original_path: Path,
        new_path: Path,
        metadata: ArticleMetadata
    ):
        """
        Logs change to CSV file.
        
        Args:
            original_path: Original file path
            new_path: New file path
            metadata: Article metadata
        """
        try:
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
                
                writer.writerow({
                    'timestamp': datetime.now().isoformat(),
                    'original_path': str(original_path),
                    'new_path': str(new_path),
                    'authors': '; '.join(metadata.authors),
                    'year': metadata.year,
                    'title': metadata.title,
                    'doi': metadata.doi
                })
                
        except Exception as e:
            raise LoggingError(f"Error writing to CSV log: {str(e)}")
            
    def _add_citation(self, metadata: ArticleMetadata):
        """
        Adds an entry to the citation database.
        
        Args:
            metadata: Article metadata
        """
        try:
            # Create BibTeX entry
            entry = {
                'ENTRYTYPE': 'article',
                'ID': self._generate_citation_key(metadata),
                'title': metadata.title,
                'author': ' and '.join(metadata.authors),
                'year': str(metadata.year) if metadata.year else '',
                'doi': metadata.doi or ''
            }
            
            # Add optional fields if available
            if metadata.abstract:
                entry['abstract'] = metadata.abstract
                
            if metadata.keywords:
                entry['keywords'] = ', '.join(metadata.keywords)
                
            # Read existing database
            try:
                with open(self.citation_log, 'r') as bibfile:
                    db = bibtexparser.load(bibfile)
            except:
                db = BibDatabase()
                
            # Add new entry
            db.entries.append(entry)
            
            # Write updated database
            writer = BibTexWriter()
            with open(self.citation_log, 'w') as bibfile:
                bibfile.write(writer.write(db))
                
        except Exception as e:
            raise LoggingError(f"Error adding citation: {str(e)}")
            
    def _generate_citation_key(self, metadata: ArticleMetadata) -> str:
        """
        Generates a unique citation key.
        
        Args:
            metadata: Article metadata
            
        Returns:
            Citation key in format: Author_Year
        """
        try:
            # Get author last name
            author = "Unknown"
            if metadata.authors:
                author = metadata.authors[0].split(',')[0].strip()
                author = ''.join(c for c in author if c.isalnum())
                
            # Get year
            year = metadata.year or "XXXX"
            
            # Create base key
            key = f"{author}_{year}"
            
            # Check for duplicates
            try:
                with open(self.citation_log, 'r') as bibfile:
                    db = bibtexparser.load(bibfile)
                    existing_keys = {entry['ID'] for entry in db.entries}
                    
                    # Add letter suffix if key exists
                    if key in existing_keys:
                        suffix = 'a'
                        while f"{key}_{suffix}" in existing_keys:
                            suffix = chr(ord(suffix) + 1)
                        key = f"{key}_{suffix}"
            except:
                pass
                
            return key
            
        except Exception as e:
            self.logger.error(f"Error generating citation key: {str(e)}")
            return f"Unknown_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
    def log_error(self, error: Exception, context: Dict[str, Any]):
        """
        Logs an error with context.
        
        Args:
            error: The error that occurred
            context: Additional context about the error
        """
        try:
            timestamp = datetime.now().isoformat()
            error_entry = {
                'timestamp': timestamp,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'context': context
            }
            
            with open(self.error_log, 'a') as f:
                f.write(f"{json.dumps(error_entry)}\n")
                
        except Exception as e:
            self.logger.error(f"Error logging error: {str(e)}")
            
    def get_recent_changes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Gets recent file changes.
        
        Args:
            limit: Maximum number of changes to return
            
        Returns:
            List of recent changes
        """
        try:
            changes = []
            with open(self.rename_log, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                changes = list(reader)[-limit:]
            return changes
        except Exception as e:
            self.logger.error(f"Error getting recent changes: {str(e)}")
            return []
            
    def get_citation_count(self) -> int:
        """
        Gets total number of citations in database.
        
        Returns:
            Number of citations
        """
        try:
            with open(self.citation_log, 'r') as bibfile:
                db = bibtexparser.load(bibfile)
                return len(db.entries)
        except Exception:
            return 0 