"""
Metadata enrichment module for Reference Renamer.
Handles extraction and enrichment of document metadata using multiple sources.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
from pathlib import Path
import aiohttp
import asyncio
from pydantic import BaseModel
import re

from ..api.semantic_scholar import SemanticScholarAPI
from ..api.arxiv import ArxivAPI
from ..api.ollama import OllamaAPI
from ..utils.exceptions import MetadataEnrichmentError, EnrichmentError
from ..utils.logging import get_logger

class MetadataExtractionError(Exception):
    """Raised when metadata extraction fails."""
    pass

@dataclass
class ArticleMetadata:
    """Structured container for article metadata."""
    authors: List[str]
    year: Optional[int]
    title: str
    doi: Optional[str]
    abstract: Optional[str]
    keywords: List[str]
    source: Optional[str] = None
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            'authors': self.authors,
            'year': self.year,
            'title': self.title,
            'doi': self.doi,
            'abstract': self.abstract,
            'keywords': self.keywords,
            'source': self.source,
            'confidence': self.confidence
        }
        
    @property
    def dict(self) -> Dict[str, Any]:
        """Property for compatibility with older code."""
        return self.to_dict()
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArticleMetadata':
        """Create metadata from dictionary."""
        return cls(
            authors=data.get('authors', []),
            year=data.get('year'),
            title=data.get('title', ''),
            doi=data.get('doi'),
            abstract=data.get('abstract'),
            keywords=data.get('keywords', []),
            source=data.get('source'),
            confidence=data.get('confidence', 0.0)
        )

class Author(BaseModel):
    """Author information model."""
    last_name: str
    first_name: str
    middle_names: Optional[List[str]] = None
    affiliations: Optional[List[str]] = None

class Metadata(BaseModel):
    """Document metadata model."""
    authors: List[Author]
    year: int
    title: str
    keywords: List[str]
    summary: str
    confidence: float
    source: str

class MetadataEnricher:
    """Enriches document metadata based on content and type."""

    # Document type patterns and required fields
    DOCUMENT_TYPES = {
        'academic': {
            'patterns': [
                r'doi:?\s*([^\s]+)',
                r'abstract',
                r'references',
                r'citations'
            ],
            'required': ['title', 'authors', 'year']
        },
        'clinical': {
            'patterns': [
                r'patient',
                r'diagnosis',
                r'treatment',
                r'clinical',
                r'medical'
            ],
            'required': ['type', 'date', 'condition']
        },
        'technical': {
            'patterns': [
                r'version:?\s*([\d.]+)',
                r'specification',
                r'manual',
                r'documentation'
            ],
            'required': ['product', 'version']
        }
    }

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the metadata enricher.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or get_logger(__name__)

    def enrich_metadata(self, content: Dict[str, str], initial_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich document metadata based on content analysis.
        
        Args:
            content: Document content as a dictionary with text sections
            initial_metadata: Initial metadata from extraction
            
        Returns:
            Enriched metadata dictionary
            
        Raises:
            MetadataExtractionError: If required metadata cannot be extracted
        """
        try:
            # Create searchable text from content sections
            searchable_text = ""
            for section, text in content.items():
                if isinstance(text, str) and text.strip():
                    searchable_text += f"\n{text.strip()}"
            searchable_text = searchable_text.strip()

            # Determine document type
            doc_type = self._determine_type(searchable_text, initial_metadata)
            self.logger.info(f"Determined document type: {doc_type}")

            # Start with initial metadata
            metadata = initial_metadata.copy()
            metadata['type'] = doc_type

            # Extract common metadata
            metadata.update(self._extract_common_metadata(searchable_text))

            # Extract type-specific metadata
            if doc_type == 'academic':
                metadata.update(self._extract_academic_metadata(searchable_text))
            elif doc_type == 'clinical':
                metadata.update(self._extract_clinical_metadata(searchable_text))
            elif doc_type == 'technical':
                metadata.update(self._extract_technical_metadata(searchable_text))

            # Generate keywords if not present
            if 'keywords' not in metadata or not metadata['keywords']:
                metadata['keywords'] = self._generate_keywords(searchable_text, metadata)

            # Validate required fields
            self._validate_metadata(metadata, doc_type)

            return metadata

        except Exception as e:
            raise MetadataExtractionError(f"Failed to enrich metadata: {str(e)}")

    def _determine_type(self, content: str, metadata: Dict[str, Any]) -> str:
        """Determine document type from content and metadata.
        
        Args:
            content: Document content (string or dict with text fields)
            metadata: Initial metadata
            
        Returns:
            Document type string
        """
        # Check explicit type in metadata
        if 'type' in metadata:
            return metadata['type']

        # Handle content as dictionary
        if isinstance(content, dict):
            searchable_text = ' '.join(str(v) for v in content.values() if v)
        else:
            searchable_text = str(content)

        # Check content against type patterns
        searchable_text = searchable_text.lower()
        for doc_type, config in self.DOCUMENT_TYPES.items():
            if any(re.search(pattern, searchable_text) for pattern in config['patterns']):
                return doc_type

        # Default to general
        return 'general'

    def _extract_common_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata common to all document types.
        
        Args:
            content: Document content (string or dict with text fields)
            
        Returns:
            Common metadata dictionary
        """
        metadata = {}

        # Convert content to searchable text
        if isinstance(content, dict):
            searchable_text = ' '.join(str(v) for v in content.values() if v)
        else:
            searchable_text = str(content)

        # Extract title if not present
        if 'title' not in metadata or not metadata['title']:
            title_match = re.search(r'^(?:title:?)?\s*([^\n]+)', searchable_text, re.I)
            if title_match:
                metadata['title'] = title_match.group(1).strip()

        # Extract date if not present
        if 'date' not in metadata:
            date_patterns = [
                r'date:?\s*(\d{4}-\d{2}-\d{2})',
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{2}/\d{2}/\d{4})',
            ]
            for pattern in date_patterns:
                date_match = re.search(pattern, searchable_text)
                if date_match:
                    try:
                        date_str = date_match.group(1)
                        metadata['date'] = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y%m%d')
                        break
                    except ValueError:
                        continue

        return metadata

    def _extract_academic_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata specific to academic documents.
        
        Args:
            content: Document content (string or dict with text fields)
            
        Returns:
            Academic metadata dictionary
        """
        metadata = {}

        # Extract DOI
        doi_match = re.search(r'(?:doi:?\s*|https?://doi\.org/)(10\.\d{4,}[/.]\S+)', content, re.I)
        if doi_match:
            metadata['doi'] = doi_match.group(1)

        # Extract year
        year_patterns = [
            r'(?:received|accepted|published):\s*(?:\d{1,2}\s+\w+\s+)?(\d{4})',
            r'©\s*(\d{4})',
            r'copyright\s*(\d{4})',
            r'\b(20\d{2})\b'
        ]
        for pattern in year_patterns:
            year_match = re.search(pattern, content, re.I)
            if year_match:
                try:
                    metadata['year'] = int(year_match.group(1))
                    break
                except ValueError:
                    continue

        # Extract title
        # First look for explicit title markers
        title_patterns = [
            r'(?:original\s+article|research\s+paper|article\s+type)\s*[:\n]\s*([^\n]+)',
            r'title\s*[:\n]\s*([^\n]+)',
            r'^([^\n]+)(?:\n+(?:authors?|abstract|introduction))',
        ]
        for pattern in title_patterns:
            title_match = re.search(pattern, content, re.I | re.M)
            if title_match:
                title = title_match.group(1).strip()
                # Clean up title
                title = re.sub(r'\s+', ' ', title)
                title = re.sub(r'^\W+|\W+$', '', title)
                if title:
                    metadata['title'] = title
                    break

        # Extract authors
        # First try to find an explicit author section
        author_section = re.search(r'authors?:?\s*([^\n]+(?:\n[^\n]+)*?)(?:\n\s*\n|\n\s*(?:abstract|introduction|affiliations))', content, re.I)
        if author_section:
            author_text = author_section.group(1)
        else:
            # Try to find authors after title
            lines = content.split('\n')
            title_index = -1
            for i, line in enumerate(lines):
                if metadata.get('title', '').strip() in line:
                    title_index = i
                    break
            
            if title_index >= 0 and title_index + 1 < len(lines):
                # Look at the next few lines for author names
                author_text = ' '.join(lines[title_index+1:title_index+4])
            else:
                # Just use the first few non-empty lines
                author_text = ' '.join(line for line in lines[:4] if line.strip())

        # Process author text to extract names
        authors = []
        if author_text:
            # Split on common author separators
            author_parts = re.split(r'[,;]|\s+and\s+|\s*&\s*', author_text)
            for part in author_parts:
                # Clean up the name
                name = part.strip()
                # Remove numbers, affiliations, and email addresses
                name = re.sub(r'[\d,].*$', '', name)
                name = re.sub(r'\s*\(.*?\)', '', name)
                name = re.sub(r'\s*<.*?>', '', name)
                name = re.sub(r'\s*\[.*?\]', '', name)
                # Remove institution affiliations (numbers and superscripts)
                name = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰]+', '', name)
                name = re.sub(r'[0-9]+(?:,[0-9]+)*', '', name)
                
                if name and len(name.split()) >= 2:  # Only include if it looks like a full name
                    authors.append(name)

        if authors:
            metadata['authors'] = authors

        # Extract abstract if present
        abstract_match = re.search(r'abstract\s*[:\n]\s*([^\n]+(?:\n(?!\s*(?:introduction|methods|results|discussion))[^\n]+)*)', content, re.I)
        if abstract_match:
            abstract = abstract_match.group(1).strip()
            # Clean up abstract
            abstract = re.sub(r'\s+', ' ', abstract)
            metadata['abstract'] = abstract

        return metadata

    def _extract_clinical_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata specific to clinical documents.
        
        Args:
            content: Document content
            
        Returns:
            Clinical metadata dictionary
        """
        metadata = {}

        # Extract condition/diagnosis
        condition_patterns = [
            r'diagnosis:?\s*([^\n]+)',
            r'condition:?\s*([^\n]+)',
            r'assessment:?\s*([^\n]+)'
        ]
        for pattern in condition_patterns:
            condition_match = re.search(pattern, content, re.I)
            if condition_match:
                metadata['condition'] = condition_match.group(1).strip()
                break

        # Set clinical type if not present
        if 'type' not in metadata:
            type_patterns = [
                (r'clinical\s+guideline', 'guideline'),
                (r'case\s+report', 'case_report'),
                (r'medical\s+record', 'record'),
                (r'treatment\s+plan', 'treatment_plan')
            ]
            for pattern, doc_type in type_patterns:
                if re.search(pattern, content, re.I):
                    metadata['type'] = doc_type
                    break
            if 'type' not in metadata:
                metadata['type'] = 'clinical'

        return metadata

    def _extract_technical_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata specific to technical documents.
        
        Args:
            content: Document content
            
        Returns:
            Technical metadata dictionary
        """
        metadata = {}

        # Extract product name
        product_patterns = [
            r'product:?\s*([^\n]+)',
            r'software:?\s*([^\n]+)',
            r'system:?\s*([^\n]+)'
        ]
        for pattern in product_patterns:
            product_match = re.search(pattern, content, re.I)
            if product_match:
                metadata['product'] = product_match.group(1).strip()
                break

        # Extract version
        version_patterns = [
            r'version:?\s*([\d.]+)',
            r'v([\d.]+)',
            r'release:?\s*([\d.]+)'
        ]
        for pattern in version_patterns:
            version_match = re.search(pattern, content, re.I)
            if version_match:
                metadata['version'] = version_match.group(1)
                break

        return metadata

    def _generate_keywords(self, content: str, metadata: Dict[str, Any]) -> List[str]:
        """Generate keywords from content and metadata.
        
        Args:
            content: Document content
            metadata: Current metadata
            
        Returns:
            List of keywords
        """
        keywords = set()

        # Extract from explicit keywords section
        keyword_section = re.search(r'keywords?:?\s*([^\n]+)', content, re.I)
        if keyword_section:
            found_keywords = keyword_section.group(1).split(',')
            keywords.update(k.strip().lower() for k in found_keywords if k.strip())

        # Extract from title
        if 'title' in metadata:
            title_words = re.findall(r'\w+', metadata['title'].lower())
            keywords.update(w for w in title_words if len(w) > 3)

        # Extract from first paragraph (assumed to be abstract/summary)
        first_para = content.split('\n\n')[0] if content else ''
        para_words = re.findall(r'\w+', first_para.lower())
        keywords.update(w for w in para_words if len(w) > 3)

        # Filter common words
        stop_words = {'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        keywords = {k for k in keywords if k not in stop_words}

        # Ensure we have at least 5 keywords
        keywords_list = list(keywords)[:5]
        while len(keywords_list) < 5:
            keywords_list.append(f"keyword{len(keywords_list)+1}")

        return keywords_list

    def _validate_metadata(self, metadata: Dict[str, Any], doc_type: str):
        """Validate required metadata fields are present.
        
        Args:
            metadata: Metadata dictionary
            doc_type: Document type
            
        Raises:
            MetadataExtractionError: If required fields are missing
        """
        if doc_type in self.DOCUMENT_TYPES:
            required_fields = self.DOCUMENT_TYPES[doc_type]['required']
            missing_fields = [f for f in required_fields if f not in metadata]
            if missing_fields:
                raise MetadataExtractionError(
                    f"Missing required metadata for {doc_type} document: {', '.join(missing_fields)}"
                )

    def _clean_text(self, text: str) -> str:
        """Clean text for LLM processing.
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Remove common academic paper artifacts while preserving metadata
        text = re.sub(r'©.*?(?=\n|$)', '', text)  # Copyright notices
        text = re.sub(r'ISBN:.*?(?=\n|$)', '', text)  # ISBN numbers
        
        # Remove email addresses and URLs
        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', text)
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove page numbers and headers/footers
        text = re.sub(r'(?m)^\d+$', '', text)
        text = re.sub(r'(?m)^.*?Page \d+.*?$', '', text)
        
        # Clean up remaining text
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'\s*\n\s*', '\n', text)  # Clean up newlines
        
        # Limit length based on model's context window
        max_length = 4000
        if len(text) > max_length:
            # Keep first 3000 characters (likely contains most metadata)
            text = text[:3000]
        
        return text.strip()

    async def _process_with_llm(self, prompt: str) -> Dict[str, Any]:
        """Process text with Ollama LLM.
        
        Args:
            prompt: Prompt text
            
        Returns:
            Parsed JSON response
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False
                    }
                ) as response:
                    if response.status != 200:
                        raise EnrichmentError(f"Ollama API error: {response.status}")
                    
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    # Extract JSON from response
                    try:
                        # Find JSON object in response
                        start = response_text.find('{')
                        end = response_text.rfind('}') + 1
                        if start >= 0 and end > start:
                            json_str = response_text[start:end]
                            return json.loads(json_str)
                        else:
                            raise ValueError("No JSON object found in response")
                    except json.JSONDecodeError as e:
                        raise EnrichmentError(f"Failed to parse LLM response: {str(e)}")
                    
        except Exception as e:
            raise EnrichmentError(f"LLM processing failed: {str(e)}")
    
    async def _extract_with_llm(self, content: str) -> ArticleMetadata:
        """
        Extracts metadata from content using LLM.
        
        Args:
            content: Document content
            
        Returns:
            ArticleMetadata from LLM extraction
        """
        try:
            # Prepare content for LLM (truncate if needed)
            max_content_length = 2000
            truncated_content = content[:max_content_length]
            
            # Extract using Ollama
            result = await self.ollama.extract_metadata(truncated_content)
            
            if not result or not isinstance(result, dict):
                raise ValueError("Invalid LLM response")
                
            metadata = ArticleMetadata(
                authors=result.get('authors', []),
                year=self._parse_year(result.get('year')),
                title=result.get('title', ''),
                doi=result.get('doi'),
                abstract=result.get('abstract'),
                keywords=result.get('keywords', []),
                source='llm',
                confidence=0.7
            )
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"LLM extraction failed: {str(e)}")
            return ArticleMetadata(
                authors=[],
                year=None,
                title='',
                doi=None,
                abstract=None,
                keywords=[],
                source='llm_failed',
                confidence=0.0
            )
            
    async def _search_arxiv(self, metadata: ArticleMetadata) -> Optional[ArticleMetadata]:
        """
        Searches arXiv for matching paper.
        
        Args:
            metadata: Current metadata to use for search
            
        Returns:
            ArticleMetadata from arXiv or None if not found
        """
        try:
            # Construct search query
            query = f"ti:{metadata.title}"
            if metadata.authors:
                query += f" AND au:{metadata.authors[0]}"
                
            results = await self.arxiv.search_papers(query)
            if not results:
                return None
                
            # Get best match
            best_match = results[0]
            return ArticleMetadata(
                authors=best_match.get('authors', []),
                year=self._parse_year(best_match.get('year')),
                title=best_match.get('title', ''),
                doi=best_match.get('doi'),
                abstract=best_match.get('abstract'),
                keywords=best_match.get('keywords', []),
                source='arxiv',
                confidence=0.9
            )
            
        except Exception as e:
            self.logger.error(f"arXiv search failed: {str(e)}")
            return None
            
    async def _search_semantic_scholar(
        self,
        metadata: ArticleMetadata
    ) -> Optional[ArticleMetadata]:
        """
        Searches Semantic Scholar for matching paper.
        
        Args:
            metadata: Current metadata to use for search
            
        Returns:
            ArticleMetadata from Semantic Scholar or None if not found
        """
        try:
            # Search by DOI if available
            if metadata.doi:
                result = await self.semantic_scholar.get_paper_by_doi(metadata.doi)
                if result:
                    return self._parse_semantic_scholar_result(result)
                    
            # Search by title
            results = await self.semantic_scholar.search_paper(metadata.title)
            if not results:
                return None
                
            # Get best match
            best_match = results[0]
            return self._parse_semantic_scholar_result(best_match)
            
        except Exception as e:
            self.logger.error(f"Semantic Scholar search failed: {str(e)}")
            return None
            
    def _combine_metadata(
        self,
        initial: Dict[str, Any],
        llm: ArticleMetadata,
        arxiv: Optional[ArticleMetadata],
        scholar: Optional[ArticleMetadata]
    ) -> ArticleMetadata:
        """
        Combines metadata from multiple sources.
        
        Args:
            initial: Initial metadata from file
            llm: Metadata from LLM
            arxiv: Metadata from arXiv
            scholar: Metadata from Semantic Scholar
            
        Returns:
            Combined ArticleMetadata
        """
        # Start with highest confidence source
        sources = [
            (scholar, 0.9),
            (arxiv, 0.8),
            (llm, 0.7)
        ]
        
        base = None
        confidence = 0.0
        
        for source, conf in sources:
            if source and source.title:
                base = source
                confidence = conf
                break
                
        if not base:
            # Fall back to LLM results
            return llm
            
        # Enhance with other sources
        base.confidence = confidence
        
        # Add any missing information from other sources
        for source, _ in sources:
            if not source or source == base:
                continue
                
            if not base.doi and source.doi:
                base.doi = source.doi
            if not base.abstract and source.abstract:
                base.abstract = source.abstract
            if not base.year and source.year:
                base.year = source.year
                
            # Combine keywords
            base.keywords = list(set(base.keywords + source.keywords))
            
        return base
        
    def _parse_year(self, year_str: Optional[str]) -> Optional[int]:
        """Parses year from string."""
        if not year_str:
            return None
            
        try:
            # Try direct conversion
            year = int(year_str)
            if 1900 <= year <= datetime.now().year:
                return year
                
            # Try extracting from date string
            from dateutil import parser
            date = parser.parse(year_str)
            return date.year
            
        except Exception:
            return None
            
    def _parse_semantic_scholar_result(self, result: Dict[str, Any]) -> ArticleMetadata:
        """Parses Semantic Scholar API result."""
        return ArticleMetadata(
            authors=[a.get('name', '') for a in result.get('authors', [])],
            year=self._parse_year(result.get('year')),
            title=result.get('title', ''),
            doi=result.get('doi'),
            abstract=result.get('abstract'),
            keywords=result.get('keywords', []),
            source='semantic_scholar',
            confidence=0.9
        ) 