"""
Ollama API integration module for Reference Renamer.
Handles interaction with Ollama LLM service for metadata extraction.
"""

import logging
from typing import Dict, Any, Optional, List
import json
import re

import aiohttp
import backoff

from ..utils.exceptions import APIError
from ..utils.logging import get_logger

class OllamaAPI:
    """Client for interacting with Ollama LLM service."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434/api",
        model: str = "drummer-knowledge",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Ollama API client.
        
        Args:
            base_url: Base URL for Ollama API
            model: Model to use for inference
            logger: Optional logger instance
        """
        self.base_url = base_url
        self.model = model
        self.logger = logger or get_logger(__name__)
        
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, TimeoutError),
        max_tries=3
    )
    async def extract_metadata(self, content: str) -> Dict[str, Any]:
        """
        Extract metadata from document content using LLM.
        
        Args:
            content: Document content to analyze
            
        Returns:
            Extracted metadata
            
        Raises:
            APIError: If API request fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/generate",
                    json={
                        "model": self.model,
                        "prompt": self._construct_metadata_prompt(content),
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 1000,
                            "stop": ["\n\n", "```"]
                        }
                    }
                ) as response:
                    if response.status != 200:
                        raise APIError(f"Ollama API error: {response.status}", "Ollama")
                    
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    # Log the response for debugging
                    self.logger.info(f"Ollama response: {response_text}")
                    
                    # Parse the response
                    return self._parse_metadata_response(response_text)
                    
        except Exception as e:
            self.logger.error(f"Error extracting metadata: {str(e)}")
            return {
                "authors": [],
                "year": None,
                "title": "",
                "doi": None,
                "abstract": None,
                "keywords": []
            }
            
    def _construct_metadata_prompt(self, content: str) -> str:
        """
        Construct prompt for metadata extraction.
        
        Args:
            content: Document content
            
        Returns:
            Formatted prompt
        """
        # Extract first page content (likely contains metadata)
        first_page_end = content.find("\nPage 2") if "\nPage 2" in content else len(content)
        first_page = content[:first_page_end].strip()
        
        # Extract potential abstract
        abstract_start = first_page.lower().find("abstract")
        abstract = ""
        if abstract_start > -1:
            abstract_end = first_page.find("\n\n", abstract_start)
            if abstract_end > -1:
                abstract = first_page[abstract_start:abstract_end].strip()
        
        # Extract DOI if present
        doi_match = re.search(r'DOI:\s*(10\.\d{4,}[/.]\S+)', first_page, re.IGNORECASE)
        doi = doi_match.group(1) if doi_match else None
        
        # Extract year from dates if present
        year_match = re.search(r'(?:Received|Accepted|Published):\s*\d{1,2}\s+\w+\s+(\d{4})', first_page)
        year = year_match.group(1) if year_match else None
        
        # Construct focused content
        focused_content = first_page
        if abstract:
            focused_content += f"\n\n{abstract}"
            
        # Add extracted metadata hints
        if doi:
            focused_content = f"DOI: {doi}\n\n{focused_content}"
        if year:
            focused_content = f"Year: {year}\n\n{focused_content}"
            
        # Truncate if still too long
        max_length = 2000
        if len(focused_content) > max_length:
            focused_content = focused_content[:max_length] + "..."
            
        return f"""You are a metadata extraction assistant. Extract metadata from this academic document content and respond ONLY with a JSON object.

Content:
{focused_content}

Required JSON format:
{{
    "authors": ["Author1 Name", "Author2 Name"],
    "year": 2024,
    "title": "Document Title",
    "doi": "DOI if present",
    "abstract": "Document abstract",
    "keywords": ["keyword1", "keyword2"]
}}

Important: 
1. Extract ONLY factual information present in the content
2. Do not make up or infer missing information
3. Return null for any fields not found in the content
4. Format authors as full names without numbers/superscripts
5. Include the DOI if present
6. Extract year from dates (Received/Accepted/Published) if present

Respond ONLY with the JSON object, no other text."""
        
    def _parse_metadata_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured metadata.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed metadata
            
        Raises:
            APIError: If response parsing fails
        """
        try:
            # Clean up response to ensure valid JSON
            response = response.strip() if response else ""
            
            # Find JSON object in response
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = response[start:end]
            else:
                # Return default structure if no JSON found
                return {
                    "authors": [],
                    "year": None,
                    "title": "",
                    "doi": None,
                    "abstract": None,
                    "keywords": []
                }
                
            # Parse JSON
            data = json.loads(json_str)
            
            # Validate and clean fields
            metadata = {
                "authors": self._clean_author_list(data.get("authors", [])),
                "year": self._parse_year(data.get("year")),
                "title": data.get("title") or "",
                "doi": data.get("doi"),
                "abstract": data.get("abstract"),
                "keywords": self._clean_keyword_list(data.get("keywords", []))
            }
            
            return metadata
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Invalid JSON response: {str(e)}")
            # Return default structure on parse error
            return {
                "authors": [],
                "year": None,
                "title": "",
                "doi": None,
                "abstract": None,
                "keywords": []
            }
        except Exception as e:
            self.logger.error(f"Error parsing metadata response: {str(e)}")
            # Return default structure on any error
            return {
                "authors": [],
                "year": None,
                "title": "",
                "doi": None,
                "abstract": None,
                "keywords": []
            }
            
    def _clean_author_list(self, authors: List[str]) -> List[str]:
        """Clean and validate author list."""
        if isinstance(authors, str):
            # Split string into list if needed
            authors = [a.strip() for a in authors.split(";")]
            
        return [
            author.strip()
            for author in authors
            if isinstance(author, str) and author.strip()
        ]
        
    def _clean_keyword_list(self, keywords: List[str]) -> List[str]:
        """Clean and validate keyword list."""
        if isinstance(keywords, str):
            # Split string into list if needed
            keywords = [k.strip() for k in keywords.split(",")]
            
        return [
            keyword.strip()
            for keyword in keywords
            if isinstance(keyword, str) and keyword.strip()
        ]
        
    def _parse_year(self, year: Any) -> Optional[int]:
        """Parse and validate year value."""
        if isinstance(year, int):
            return year
        elif isinstance(year, str):
            try:
                return int(year)
            except ValueError:
                return None
        return None 