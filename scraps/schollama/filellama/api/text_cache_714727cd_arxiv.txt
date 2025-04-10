"""
arXiv API integration module for Reference Renamer.
Handles searching and retrieving paper metadata from arXiv.
"""

import urllib.parse
import logging
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET
from datetime import datetime

import aiohttp
import backoff

from ..utils.exceptions import APIError
from ..utils.logging import get_logger

class ArxivAPI:
    """Client for interacting with arXiv API."""
    
    def __init__(
        self,
        base_url: str = "http://export.arxiv.org/api/query",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize arXiv API client.
        
        Args:
            base_url: Base URL for arXiv API
            logger: Optional logger instance
        """
        self.base_url = base_url
        self.logger = logger or get_logger(__name__)
        
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, TimeoutError),
        max_tries=3
    )
    async def search_papers(
        self,
        query: str,
        max_results: int = 5,
        sort_by: str = "relevance",
        sort_order: str = "descending"
    ) -> List[Dict[str, Any]]:
        """
        Search arXiv for papers matching query.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            sort_by: Sort field (relevance, lastUpdatedDate, submittedDate)
            sort_order: Sort order (ascending, descending)
            
        Returns:
            List of paper metadata dictionaries
            
        Raises:
            APIError: If API request fails
        """
        try:
            # Construct search query
            search_query = f'all:"{query}" OR abs:"{query}" OR ti:"{query}"'
            encoded_query = urllib.parse.quote(search_query)
            
            params = {
                "search_query": encoded_query,
                "start": 0,
                "max_results": max_results,
                "sortBy": sort_by,
                "sortOrder": sort_order,
            }
            
            self.logger.debug(f"Searching arXiv with query: {query}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status != 200:
                        raise APIError(
                            f"arXiv API returned status {response.status}",
                            "arXiv",
                            response.status
                        )
                        
                    content = await response.text()
                    return self._parse_response(content)
                    
        except aiohttp.ClientError as e:
            raise APIError(f"arXiv API request failed: {str(e)}", "arXiv")
        except Exception as e:
            raise APIError(f"Error searching arXiv: {str(e)}", "arXiv")
            
    def _parse_response(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse arXiv API XML response.
        
        Args:
            content: XML response content
            
        Returns:
            List of parsed paper metadata
        """
        try:
            root = ET.fromstring(content)
            entries = root.findall("{http://www.w3.org/2005/Atom}entry")
            
            if not entries:
                self.logger.info("No papers found in arXiv response")
                return []
                
            results = []
            for entry in entries:
                # Extract basic metadata
                title = entry.find("{http://www.w3.org/2005/Atom}title")
                title_text = title.text.strip() if title is not None else "Unknown Title"
                
                # Extract authors
                authors = entry.findall("{http://www.w3.org/2005/Atom}author")
                author_names = []
                for author in authors:
                    name = author.find("{http://www.w3.org/2005/Atom}name")
                    if name is not None and name.text:
                        author_names.append(name.text)
                        
                # Extract other fields
                summary = entry.find("{http://www.w3.org/2005/Atom}summary")
                summary_text = (
                    summary.text.strip() if summary is not None else None
                )
                
                published = entry.find("{http://www.w3.org/2005/Atom}published")
                if published is not None and published.text:
                    try:
                        pub_date = datetime.strptime(
                            published.text,
                            "%Y-%m-%dT%H:%M:%SZ"
                        )
                        year = pub_date.year
                    except ValueError:
                        year = None
                else:
                    year = None
                    
                # Get DOI if available
                doi = None
                for link in entry.findall("{http://www.w3.org/2005/Atom}link"):
                    if link.get("title") == "doi":
                        doi = link.get("href")
                        break
                        
                # Extract categories/keywords
                categories = entry.findall(
                    "{http://www.w3.org/2005/Atom}category"
                )
                keywords = [
                    cat.get("term") for cat in categories if cat.get("term")
                ]
                
                # Construct result
                paper = {
                    "title": title_text,
                    "authors": author_names,
                    "year": year,
                    "abstract": summary_text,
                    "doi": doi,
                    "keywords": keywords,
                    "source": "arxiv"
                }
                
                results.append(paper)
                
            self.logger.info(f"Found {len(results)} papers on arXiv")
            return results
            
        except ET.ParseError as e:
            raise APIError(f"Error parsing arXiv response: {str(e)}", "arXiv")
        except Exception as e:
            raise APIError(f"Error processing arXiv results: {str(e)}", "arXiv")
            
    async def get_paper_by_id(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """
        Get paper metadata by arXiv ID.
        
        Args:
            arxiv_id: arXiv paper ID
            
        Returns:
            Paper metadata or None if not found
        """
        try:
            params = {
                "id_list": arxiv_id,
            }
            
            self.logger.debug(f"Fetching arXiv paper: {arxiv_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status != 200:
                        raise APIError(
                            f"arXiv API returned status {response.status}",
                            "arXiv",
                            response.status
                        )
                        
                    content = await response.text()
                    results = self._parse_response(content)
                    return results[0] if results else None
                    
        except aiohttp.ClientError as e:
            raise APIError(f"arXiv API request failed: {str(e)}", "arXiv")
        except Exception as e:
            raise APIError(f"Error fetching arXiv paper: {str(e)}", "arXiv") 