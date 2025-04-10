"""
Semantic Scholar API integration module for Reference Renamer.
Handles searching and retrieving paper metadata from Semantic Scholar.
"""

import logging
from typing import Dict, Any, List, Optional
import json

import aiohttp
import backoff

from ..utils.exceptions import APIError
from ..utils.logging import get_logger

class SemanticScholarAPI:
    """Client for interacting with Semantic Scholar API."""
    
    def __init__(
        self,
        base_url: str = "https://api.semanticscholar.org/v1",
        api_key: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Semantic Scholar API client.
        
        Args:
            base_url: Base URL for Semantic Scholar API
            api_key: Optional API key for higher rate limits
            logger: Optional logger instance
        """
        self.base_url = base_url
        self.api_key = api_key
        self.logger = logger or get_logger(__name__)
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Accept": "application/json"
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers
        
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, TimeoutError),
        max_tries=3
    )
    async def search_paper(
        self,
        query: str,
        limit: int = 5,
        fields: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for papers matching query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            fields: Fields to include in response
            
        Returns:
            List of paper metadata dictionaries
            
        Raises:
            APIError: If API request fails
        """
        if fields is None:
            fields = [
                "title",
                "authors",
                "year",
                "abstract",
                "doi",
                "keywords",
                "venue",
                "url"
            ]
            
        try:
            url = f"{self.base_url}/paper/search"
            params = {
                "query": query,
                "limit": limit,
                "fields": ",".join(fields)
            }
            
            self.logger.debug(f"Searching Semantic Scholar with query: {query}")
            
            async with aiohttp.ClientSession(headers=self._get_headers()) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        raise APIError(
                            f"Semantic Scholar API returned status {response.status}",
                            "Semantic Scholar",
                            response.status
                        )
                        
                    data = await response.json()
                    return self._process_search_results(data.get("data", []))
                    
        except aiohttp.ClientError as e:
            raise APIError(
                f"Semantic Scholar API request failed: {str(e)}",
                "Semantic Scholar"
            )
        except Exception as e:
            raise APIError(
                f"Error searching Semantic Scholar: {str(e)}",
                "Semantic Scholar"
            )
            
    async def get_paper_by_doi(
        self,
        doi: str,
        fields: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get paper metadata by DOI.
        
        Args:
            doi: Paper DOI
            fields: Fields to include in response
            
        Returns:
            Paper metadata or None if not found
        """
        if fields is None:
            fields = [
                "title",
                "authors",
                "year",
                "abstract",
                "doi",
                "keywords",
                "venue",
                "url"
            ]
            
        try:
            url = f"{self.base_url}/paper/{doi}"
            params = {
                "fields": ",".join(fields)
            }
            
            self.logger.debug(f"Fetching Semantic Scholar paper with DOI: {doi}")
            
            async with aiohttp.ClientSession(headers=self._get_headers()) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 404:
                        return None
                    elif response.status != 200:
                        raise APIError(
                            f"Semantic Scholar API returned status {response.status}",
                            "Semantic Scholar",
                            response.status
                        )
                        
                    data = await response.json()
                    return self._process_paper_data(data)
                    
        except aiohttp.ClientError as e:
            raise APIError(
                f"Semantic Scholar API request failed: {str(e)}",
                "Semantic Scholar"
            )
        except Exception as e:
            raise APIError(
                f"Error fetching paper from Semantic Scholar: {str(e)}",
                "Semantic Scholar"
            )
            
    def _process_search_results(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process search results into standardized format.
        
        Args:
            results: Raw API results
            
        Returns:
            Processed results
        """
        processed = []
        for paper in results:
            processed_paper = self._process_paper_data(paper)
            if processed_paper:
                processed.append(processed_paper)
                
        self.logger.info(
            f"Processed {len(processed)} results from Semantic Scholar"
        )
        return processed
        
    def _process_paper_data(self, paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process paper data into standardized format.
        
        Args:
            paper: Raw paper data
            
        Returns:
            Processed paper data
        """
        if not paper or not paper.get("title"):
            return None
            
        # Extract authors
        authors = []
        for author in paper.get("authors", []):
            name = author.get("name")
            if name:
                authors.append(name)
                
        # Extract keywords
        keywords = []
        for topic in paper.get("topics", []):
            topic_name = topic.get("topic")
            if topic_name:
                keywords.append(topic_name)
                
        # Construct standardized metadata
        return {
            "title": paper.get("title"),
            "authors": authors,
            "year": paper.get("year"),
            "abstract": paper.get("abstract"),
            "doi": paper.get("doi"),
            "keywords": keywords,
            "venue": paper.get("venue"),
            "url": paper.get("url"),
            "source": "semantic_scholar"
        } 