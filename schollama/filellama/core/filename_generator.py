"""
Filename generation module for Reference Renamer.
Handles generation of standardized filenames from metadata.
"""

import os
import re
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path
from unicodedata import normalize
from datetime import datetime

from .metadata_enricher import ArticleMetadata
from ..utils.exceptions import FilenameError, FilenameGenerationError
from ..utils.logging import get_logger

class FilenameGenerator:
    """Generates standardized filenames for documents."""

    # Document type patterns
    DOCUMENT_PATTERNS = {
        'academic': {
            'markers': ['doi', 'journal', 'conference', 'proceedings', 'thesis', 'dissertation'],
            'format': '{authors}_{year}_{keywords}'
        },
        'clinical': {
            'markers': ['patient', 'clinical', 'medical', 'diagnosis', 'treatment'],
            'format': '{type}_{date}_{condition}_{keywords}'
        },
        'technical': {
            'markers': ['manual', 'guide', 'documentation', 'specification'],
            'format': '{product}_{version}_{keywords}'
        },
        'general': {
            'markers': [],  # Default category
            'format': '{category}_{date}_{title}_{keywords}'
        }
    }

    def __init__(self, logger: logging.Logger = None):
        """Initialize the filename generator.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or get_logger(__name__)

    def generate_filename(self, metadata: Dict[str, Any], original_path: Path) -> str:
        """Generate a standardized filename.
        
        Args:
            metadata: Document metadata
            original_path: Original file path
            
        Returns:
            Standardized filename
            
        Raises:
            FilenameGenerationError: If filename generation fails
        """
        try:
            # Determine document type
            doc_type = self._determine_document_type(metadata)
            self.logger.info(f"Determined document type: {doc_type}")

            # Extract or generate keywords
            keywords = self._extract_keywords(metadata)
            self.logger.info(f"Generated keywords: {keywords}")

            # Format filename based on document type
            if doc_type == 'academic':
                filename = self._format_academic_filename(metadata, keywords)
            elif doc_type == 'clinical':
                filename = self._format_clinical_filename(metadata, keywords)
            elif doc_type == 'technical':
                filename = self._format_technical_filename(metadata, keywords)
            else:  # general
                filename = self._format_general_filename(metadata, keywords)

            # Add original extension
            filename = f"{filename}{original_path.suffix}"

            # Sanitize filename
            filename = self._sanitize_filename(filename)

            self.logger.info(f"Generated filename: {filename}")
            return filename

        except Exception as e:
            raise FilenameGenerationError(f"Failed to generate filename: {str(e)}")

    def _determine_document_type(self, metadata: Dict[str, Any]) -> str:
        """Determine document type and specific category."""
        # Check for academic paper indicators
        academic_indicators = [
            bool(metadata.get('doi')),  # Has a DOI
            bool(metadata.get('authors')) and bool(metadata.get('year')),  # Has authors and year
            bool(metadata.get('journal')),  # Published in a journal
            bool(metadata.get('conference')),  # Conference paper
            bool(metadata.get('abstract')),  # Has an abstract
            any(word in str(metadata.get('title', '')).upper() for word in [
                'ARTICLE', 'PAPER', 'STUDY', 'RESEARCH', 'PROCEEDINGS'
            ])
        ]
        
        if any(academic_indicators):
            return 'academic'
            
        # For non-academic documents, determine specific type
        title = str(metadata.get('title', '')).lower()
        content = str(metadata.get('content', '')).lower()
        
        # Define specific document types with their indicators
        document_types = {
            'assessment': ['assessment', 'evaluation', 'screening', 'diagnostic'],
            'guideline': ['guideline', 'protocol', 'standard', 'procedure'],
            'case_study': ['case study', 'case report', 'patient case'],
            'progress_note': ['progress', 'note', 'documentation', 'session'],
            'protocol': ['protocol', 'procedure', 'methodology'],
            'evaluation': ['evaluation', 'assessment', 'diagnostic'],
            'manual': ['manual', 'guide', 'handbook', 'instruction'],
            'template': ['template', 'form', 'worksheet', 'checklist'],
            'report': ['report', 'summary', 'analysis', 'review'],
            'training': ['training', 'workshop', 'course', 'education']
        }
        
        # Check title and content against document type indicators
        for doc_type, indicators in document_types.items():
            if any(indicator in title or indicator in content for indicator in indicators):
                return doc_type
                
        # Default to report if no specific type is identified
        return 'report'

    def _extract_keywords(self, metadata: Dict[str, Any]) -> List[str]:
        """Extract or generate five keywords.
        
        Args:
            metadata: Document metadata
            
        Returns:
            List of exactly 5 keywords
        """
        # First try to get keywords from metadata
        keywords = metadata.get('keywords', [])
        if isinstance(keywords, str):
            # Split string of keywords into list
            keywords = [k.strip() for k in re.split(r'[,;|]', keywords)]
        
        # Clean and normalize keywords
        keywords = [self._clean_keyword(k) for k in keywords if k]
        keywords = [k for k in keywords if k and len(k) >= 3]  # Remove empty or too short
        
        # For academic papers, try to extract meaningful keywords
        if metadata.get('type') == 'academic' or any(metadata.get(k) for k in ['doi', 'journal', 'authors']):
            # Try to extract from title first
            title_words = []
            if 'title' in metadata:
                # Split into words and clean
                title = str(metadata['title']).lower()
                # Remove common academic phrases
                title = re.sub(r'\b(study|research|analysis|investigation|paper|article)\b', '', title)
                # Split into word pairs to capture meaningful phrases
                words = title.split()
                for i in range(len(words)-1):
                    phrase = f"{words[i]}_{words[i+1]}"
                    if all(len(w) > 2 for w in words[i:i+2]) and not any(w in self.STOP_WORDS for w in words[i:i+2]):
                        title_words.append(phrase)
                # Also add single words
                single_words = [w for w in words if len(w) > 3 and w not in self.STOP_WORDS]
                title_words.extend(single_words)
            
            # Try to extract from abstract
            abstract_words = []
            if 'abstract' in metadata:
                abstract = str(metadata['abstract']).lower()
                # Look for key phrases often indicating important concepts
                key_phrases = re.findall(r'(?:investigate[ds]?|examine[ds]?|analyze[ds]?|study|research)\s+(\w+(?:\s+\w+){0,2})', abstract)
                for phrase in key_phrases:
                    words = phrase.split()
                    # Add word pairs
                    for i in range(len(words)-1):
                        pair = f"{words[i]}_{words[i+1]}"
                        if all(len(w) > 2 for w in words[i:i+2]) and not any(w in self.STOP_WORDS for w in words[i:i+2]):
                            abstract_words.append(pair)
                    # Add single words
                    abstract_words.extend([w for w in words if len(w) > 3 and w not in self.STOP_WORDS])
                
                # Also look for words in methods/results sections
                methods_results = re.findall(r'(?:method|result)s?[:\s]+([^.]+)', abstract)
                for section in methods_results:
                    words = section.lower().split()
                    # Add word pairs
                    for i in range(len(words)-1):
                        pair = f"{words[i]}_{words[i+1]}"
                        if all(len(w) > 2 for w in words[i:i+2]) and not any(w in self.STOP_WORDS for w in words[i:i+2]):
                            abstract_words.append(pair)
                    # Add single words
                    abstract_words.extend([w for w in words if len(w) > 3 and w not in self.STOP_WORDS])
            
            # Combine all potential keywords
            all_keywords = keywords + title_words + abstract_words
            
            # Clean keywords
            all_keywords = [self._clean_keyword(k) for k in all_keywords]
            
            # Remove duplicates and sort by relevance (prefer title words, then abstract words)
            seen = set()
            final_keywords = []
            
            # First add keywords from title
            for k in title_words:
                k = self._clean_keyword(k)
                if k and k not in seen and len(k) >= 3:
                    final_keywords.append(k)
                    seen.add(k)
            
            # Then add keywords from abstract
            for k in abstract_words:
                k = self._clean_keyword(k)
                if k and k not in seen and len(k) >= 3:
                    final_keywords.append(k)
                    seen.add(k)
            
            # Finally add any remaining keywords
            for k in keywords:
                k = self._clean_keyword(k)
                if k and k not in seen and len(k) >= 3:
                    final_keywords.append(k)
                    seen.add(k)
            
            # Take the first 5 unique keywords
            return final_keywords[:5]
        
        # For non-academic documents, use existing keywords or generate from content
        return keywords[:5] if keywords else ['untitled']

    def _clean_keyword(self, keyword: str) -> str:
        """Clean and normalize a keyword.
        
        Args:
            keyword: Keyword to clean
            
        Returns:
            Cleaned keyword
        """
        # Convert to lowercase and remove special characters
        keyword = re.sub(r'[^\w\s-]', '', keyword.lower())
        # Replace spaces with underscores
        keyword = re.sub(r'\s+', '_', keyword.strip())
        # Remove consecutive underscores
        keyword = re.sub(r'_+', '_', keyword)
        return keyword

    def _generate_keywords(self, metadata: Dict[str, Any], num_needed: int) -> List[str]:
        """Generate keywords from metadata.
        
        Args:
            metadata: Document metadata
            num_needed: Number of keywords needed
            
        Returns:
            List of generated keywords
        """
        keywords = []
        
        # Common words to exclude
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Try to extract from title
        if 'title' in metadata:
            # Split into words and clean
            words = re.findall(r'\w+', str(metadata['title']).lower())
            # Filter stop words and short words
            words = [w for w in words if len(w) > 3 and w not in stop_words]
            if words:
                keywords.extend(words)
        
        # Try to extract from abstract
        if len(keywords) < num_needed and 'abstract' in metadata:
            words = re.findall(r'\w+', str(metadata['abstract']).lower())
            words = [w for w in words if len(w) > 3 and w not in stop_words]
            # Add new words not already in keywords
            keywords.extend([w for w in words if w not in keywords])
        
        # Clean all keywords
        keywords = [self._clean_keyword(k) for k in keywords]
        keywords = [k for k in keywords if k and len(k) >= 3]
        
        # If still not enough, add generic keywords
        while len(keywords) < num_needed:
            generic = f"keyword{len(keywords)+1}"
            if generic not in keywords:
                keywords.append(generic)
        
        return keywords[:num_needed]

    def _format_academic_filename(self, metadata: Dict[str, Any], keywords: List[str]) -> str:
        """Format filename for academic papers: lastname_year_seven_word_summary."""
        # Get author's last name
        lastname = 'unknown'
        authors = metadata.get('authors', [])
        if authors and isinstance(authors, list) and authors[0]:
            lastname = authors[0].split()[-1].lower()
        elif authors and isinstance(authors, str):
            lastname = authors.split(',')[0].split()[-1].lower()

        # Get year
        year = metadata.get('year', datetime.now().year)

        # Generate seven word summary from title
        title = metadata.get('title', '').lower()
        # Remove special characters and extra spaces
        title = re.sub(r'[^\w\s-]', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Remove common academic words
        skip_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'were', 'will', 'with', 'study', 'research', 'analysis',
            'investigation', 'paper', 'article'
        }
        
        # Split into words and filter
        words = [w for w in title.split() if w not in skip_words and len(w) > 2]
        
        # Take exactly seven words, pad with placeholders if needed
        summary_words = words[:7]
        while len(summary_words) < 7:
            summary_words.append(f'word{len(summary_words)+1}')
        
        # Join with underscores
        summary = '_'.join(summary_words)
        
        return f"{lastname}_{year}_{summary}"

    def _format_clinical_filename(self, metadata: Dict[str, Any], keywords: List[str]) -> str:
        """Format filename for clinical documents using specific type format.
        
        Args:
            metadata: Document metadata
            keywords: List of keywords
            
        Returns:
            Formatted filename without extension
        """
        # Get specific document type
        doc_type = self._determine_document_type(metadata)
        
        # Get date in YYYYMMDD format
        date = datetime.now().strftime('%Y%m%d')
        if 'date' in metadata:
            try:
                date = datetime.strptime(str(metadata['date']), '%Y-%m-%d').strftime('%Y%m%d')
            except:
                pass
        
        # Generate seven word summary from title or content
        title = metadata.get('title', metadata.get('content', '')).lower()
        # Remove special characters and extra spaces
        title = re.sub(r'[^\w\s-]', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Split into words and filter common words
        skip_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'were', 'will', 'with'
        }
        
        words = [w for w in title.split() if w not in skip_words and len(w) > 2]
        
        # Take exactly seven words, pad with placeholders if needed
        summary_words = words[:7]
        while len(summary_words) < 7:
            summary_words.append(f'word{len(summary_words)+1}')
        
        # Join with underscores
        summary = '_'.join(summary_words)
        
        return f"{doc_type}_{date}_{summary}"

    def _format_technical_filename(self, metadata: Dict[str, Any], keywords: List[str]) -> str:
        """Format filename for technical documents.
        
        Args:
            metadata: Document metadata
            keywords: List of 5 keywords
            
        Returns:
            Formatted filename without extension
        """
        product = metadata.get('product', 'doc')
        version = metadata.get('version', 'v1')
        
        return f"{product}_{version}_{'_'.join(keywords)}"

    def _format_general_filename(self, metadata: Dict[str, Any], keywords: List[str]) -> str:
        """Format filename for non-academic documents: specific_type_date_seven_word_summary."""
        # Get specific document type
        doc_type = self._determine_document_type(metadata)
        
        # Get date in YYYYMMDD format
        date = datetime.now().strftime('%Y%m%d')
        if 'date' in metadata:
            try:
                date = datetime.strptime(str(metadata['date']), '%Y-%m-%d').strftime('%Y%m%d')
            except:
                pass
        
        # Generate seven word summary from title or content
        title = metadata.get('title', metadata.get('content', '')).lower()
        # Remove special characters and extra spaces
        title = re.sub(r'[^\w\s-]', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Split into words and filter common words
        skip_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'were', 'will', 'with'
        }
        
        words = [w for w in title.split() if w not in skip_words and len(w) > 2]
        
        # Take exactly seven words, pad with placeholders if needed
        summary_words = words[:7]
        while len(summary_words) < 7:
            summary_words.append(f'word{len(summary_words)+1}')
        
        # Join with underscores
        summary = '_'.join(summary_words)
        
        return f"{doc_type}_{date}_{summary}"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility.
        
        Args:
            filename: Raw filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        
        # Replace spaces with underscores
        filename = re.sub(r'\s+', '_', filename)
        
        # Remove consecutive underscores
        filename = re.sub(r'_+', '_', filename)
        
        # Convert to lowercase
        filename = filename.lower()
        
        # Handle long filenames (255 char limit on most filesystems)
        if len(filename) > 255:
            base, ext = os.path.splitext(filename)
            # Keep the structure but truncate the summary
            parts = base.split('_')
            if len(parts) >= 3:  # type_date_summary or lastname_year_summary
                prefix = f"{parts[0]}_{parts[1]}"
                summary_parts = parts[2:]
                summary = '_'.join(summary_parts)
                if len(summary) > 100:
                    summary = f"{summary[:50]}...{summary[-30:]}"
                base = f"{prefix}_{summary}"
            else:
                base = f"{base[:100]}...{base[-50:]}"
            filename = f"{base}{ext}"
        
        return filename

    def validate_filename(self, filename: str, directory: Path) -> bool:
        """
        Validates if a filename is usable.
        
        Args:
            filename: Proposed filename
            directory: Target directory
            
        Returns:
            Whether the filename is valid
        """
        try:
            # Check length
            if len(filename) > 255:
                self.logger.warning("Filename too long")
                return False
                
            # Check if file exists
            target_path = directory / filename
            if target_path.exists():
                self.logger.warning(f"File already exists: {filename}")
                return False
                
            # Try to create and remove a test file
            try:
                target_path.touch()
                target_path.unlink()
                return True
            except OSError:
                self.logger.warning(f"Cannot create file with name: {filename}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating filename: {str(e)}")
            return False
            
    def generate_unique_filename(
        self,
        base_filename: str,
        directory: Path
    ) -> str:
        """
        Generates a unique filename by adding a counter if needed.
        
        Args:
            base_filename: Original filename
            directory: Target directory
            
        Returns:
            Unique filename
        """
        if not self.validate_filename(base_filename, directory):
            # Split name and extension
            base, ext = os.path.splitext(base_filename)
            counter = 1
            
            while counter < 1000:  # Prevent infinite loop
                new_filename = f"{base}_{counter}{ext}"
                if self.validate_filename(new_filename, directory):
                    return new_filename
                counter += 1
                
            raise FilenameError("Could not generate unique filename")
            
        return base_filename

    # Add stop words as a class variable
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could',
        'study', 'research', 'paper', 'article', 'analysis', 'investigation',
        'method', 'result', 'conclusion', 'discussion', 'introduction',
        'background', 'objective', 'aim', 'purpose', 'finding'
    } 