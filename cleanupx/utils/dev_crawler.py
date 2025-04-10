#!/usr/bin/env python3
"""
Developer directory crawler utility for CleanupX.

This module provides functionality to:
1. Crawl a directory structure to extract useful code snippets
2. Identify and securely record credentials
3. Generate comprehensive README documentation using xAI
"""

import os
import re
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

from cleanupx.utils.common import read_text_file, is_ignored_file
from cleanupx.api import call_xai_api
from cleanupx.config import XAI_MODEL_TEXT, CODE_FUNCTION_SCHEMA, FILE_CODE_PROMPT

# Configure logging
logger = logging.getLogger(__name__)

# Constants for credential detection
CREDENTIAL_PATTERNS = [
    r"(?i)api[_\-\s]*key[_\-\s]*=\s*[\'\"]([^\'\"]+)",
    r"(?i)password[_\-\s]*=\s*[\'\"]([^\'\"]+)",
    r"(?i)secret[_\-\s]*=\s*[\'\"]([^\'\"]+)",
    r"(?i)token[_\-\s]*=\s*[\'\"]([^\'\"]+)",
    r"(?i)auth[_\-\s]*=\s*[\'\"]([^\'\"]+)",
    r"(?i)access[_\-\s]*key[_\-\s]*=\s*[\'\"]([^\'\"]+)",
    r"(?i)connection[_\-\s]*string[_\-\s]*=\s*[\'\"]([^\'\"]+)",
    r"(?:https?://)[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+[^'\"\s]*:[^'\"\s]+@",  # URLs with credentials
]

# Constants for code snippet extraction
SNIPPET_EXTENSIONS = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.ts': 'TypeScript',
    '.jsx': 'React JSX',
    '.tsx': 'React TSX',
    '.html': 'HTML',
    '.css': 'CSS',
    '.scss': 'SCSS',
    '.rb': 'Ruby',
    '.go': 'Go',
    '.java': 'Java',
    '.c': 'C',
    '.cpp': 'C++',
    '.cs': 'C#',
    '.php': 'PHP',
    '.swift': 'Swift',
    '.rs': 'Rust',
    '.sh': 'Shell',
    '.ps1': 'PowerShell',
}

# File patterns to ignore during crawling
CRAWLER_IGNORE_PATTERNS = [
    "node_modules",
    ".git",
    "__pycache__",
    "*.pyc",
    ".venv",
    "venv",
    "env",
    ".env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "coverage",
    ".coverage",
    ".DS_Store",
    "*.log",
    "*.tmp",
]

class DevCrawler:
    """
    Utility to crawl directories and extract developer-focused information.
    """
    
    def __init__(self, directory: Path, output_dir: Optional[Path] = None):
        """
        Initialize the DevCrawler.
        
        Args:
            directory: Root directory to crawl
            output_dir: Directory to save outputs (defaults to directory/cleanupx_dev)
        """
        self.directory = Path(directory)
        self.output_dir = output_dir or (self.directory / "cleanupx_dev")
        self.snippets_dir = self.output_dir / "snippets"
        self.credentials_file = self.output_dir / "CREDENTIALS.md"
        self.readme_file = self.output_dir / "README.md"
        
        # Track discovered information
        self.credentials: Dict[str, List[Dict[str, str]]] = {}
        self.snippets: List[Dict[str, Any]] = []
        self.file_count = 0
        self.directory_count = 0
        self.languages: Dict[str, int] = {}
        self.file_extensions: Dict[str, int] = {}
        self.project_structure: Dict[str, Any] = {}
        
        # Ensure output directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.snippets_dir.mkdir(parents=True, exist_ok=True)
    
    def should_ignore_path(self, path: Path) -> bool:
        """
        Check if a path should be ignored during crawling.
        
        Args:
            path: Path to check
            
        Returns:
            True if the path should be ignored, False otherwise
        """
        # Check if the path is in the ignore patterns
        path_str = str(path)
        
        # Check basic patterns first
        for pattern in CRAWLER_IGNORE_PATTERNS:
            if "*" in pattern:
                # Handle glob patterns
                if path.match(pattern):
                    return True
            else:
                # Handle exact matches
                if pattern in path_str:
                    return True
        
        # Call the common ignore function as well
        return is_ignored_file(path)
    
    def extract_credentials(self, file_path: Path, content: str) -> List[Dict[str, str]]:
        """
        Extract potential credentials from file content.
        
        Args:
            file_path: Path to the file
            content: Content of the file
            
        Returns:
            List of discovered credentials
        """
        results = []
        
        for pattern in CREDENTIAL_PATTERNS:
            matches = re.finditer(pattern, content)
            for match in matches:
                try:
                    credential = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    line_number = content[:match.start()].count('\n') + 1
                    results.append({
                        "file": str(file_path.relative_to(self.directory)),
                        "line": line_number,
                        "credential_type": self._determine_credential_type(pattern),
                        "credential": credential,
                        "context": self._get_line_context(content, line_number)
                    })
                except Exception as e:
                    logger.debug(f"Error extracting credential: {e}")
        
        return results
    
    def _determine_credential_type(self, pattern: str) -> str:
        """Determine the type of credential based on the regex pattern."""
        if "api" in pattern.lower():
            return "API Key"
        elif "password" in pattern.lower():
            return "Password"
        elif "secret" in pattern.lower():
            return "Secret"
        elif "token" in pattern.lower():
            return "Token"
        elif "auth" in pattern.lower():
            return "Authentication"
        elif "access" in pattern.lower():
            return "Access Key"
        elif "connection" in pattern.lower():
            return "Connection String"
        elif "@" in pattern:
            return "URL with Credentials"
        else:
            return "Unknown Credential"
    
    def _get_line_context(self, content: str, line_number: int, context_lines: int = 1) -> str:
        """Get the context around a specific line."""
        lines = content.splitlines()
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)
        
        return "\n".join(lines[start:end])
    
    def analyze_code_with_xai(self, file_path: Path, content: str) -> Optional[Dict[str, Any]]:
        """
        Analyze code content using xAI API.
        
        Args:
            file_path: Path to the code file
            content: Content of the code file
            
        Returns:
            Dictionary with code analysis or None if analysis failed
        """
        try:
            # Prepare prompt for xAI
            prompt = FILE_CODE_PROMPT.format(
                name=file_path.name,
                suffix=file_path.suffix,
                content=content[:10000]  # Limit content length
            )
            
            # Call xAI API
            result = call_xai_api(XAI_MODEL_TEXT, prompt, CODE_FUNCTION_SCHEMA)
            if not result:
                logger.warning(f"Failed to analyze code: {file_path.name}")
                return None
                
            logger.info(f"Successfully analyzed code: {file_path.name}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing code with xAI: {e}")
            return None
    
    def extract_code_snippet(self, file_path: Path, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract a useful code snippet from the file.
        
        Args:
            file_path: Path to the file
            content: Content of the file
            
        Returns:
            Dictionary with snippet information or None if no snippet could be extracted
        """
        ext = file_path.suffix.lower()
        if ext not in SNIPPET_EXTENSIONS:
            return None
            
        # Analyze code with xAI
        analysis = self.analyze_code_with_xai(file_path, content)
        if not analysis:
            return None
            
        # Create snippet from analysis
        snippet = {
            "file": str(file_path.relative_to(self.directory)),
            "language": SNIPPET_EXTENSIONS[ext],
            "type": analysis.get("code_type", "Code"),
            "name": analysis.get("name", file_path.stem),
            "content": content[:1000],  # Limit content length
            "line_count": content.count('\n') + 1,
            "description": analysis.get("description", ""),
            "dependencies": analysis.get("dependencies", []),
            "complexity": analysis.get("complexity", "unknown")
        }
        
        return snippet
    
    def save_snippet(self, snippet: Dict[str, Any]) -> Path:
        """
        Save a code snippet to a file, handling deduplication and merging of similar implementations.
        
        Args:
            snippet: Snippet data
            
        Returns:
            Path to the saved snippet file
        """
        # Create base filename
        ext = "." + snippet["language"].lower().replace(" ", "_").replace("+", "p").replace("#", "sharp")
        base_filename = f"{snippet['type'].lower()}_{snippet['name']}"
        
        # Check for existing similar snippets
        existing_snippets = []
        for file in self.snippets_dir.glob(f"{base_filename}*{ext}"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract metadata from existing snippet
                    metadata = self._extract_snippet_metadata(content)
                    existing_snippets.append((file, metadata))
            except Exception as e:
                logger.warning(f"Error reading existing snippet {file}: {e}")
        
        # Analyze similarity with existing snippets
        similar_snippet = None
        for file, metadata in existing_snippets:
            if self._are_snippets_similar(snippet, metadata):
                similar_snippet = (file, metadata)
                break
        
        if similar_snippet:
            # Merge with existing snippet
            existing_file, existing_metadata = similar_snippet
            merged_snippet = self._merge_snippets(snippet, existing_metadata)
            
            # Update the existing file
            with open(existing_file, 'w', encoding='utf-8') as f:
                f.write(self._format_snippet_markdown(merged_snippet))
            
            return existing_file
        else:
            # Create a new snippet file
            safe_filename = re.sub(r'[^\w\-_\.]', '_', base_filename + ext)
            snippet_path = self.snippets_dir / safe_filename
            
            # If file exists, append a number
            counter = 1
            while snippet_path.exists():
                snippet_path = self.snippets_dir / f"{base_filename}_{counter}{ext}"
                counter += 1
            
            # Write new snippet
            with open(snippet_path, 'w', encoding='utf-8') as f:
                f.write(self._format_snippet_markdown(snippet))
            
            return snippet_path
    
    def _extract_snippet_metadata(self, content: str) -> Dict[str, Any]:
        """
        Extract metadata from an existing snippet file.
        
        Args:
            content: Content of the snippet file
            
        Returns:
            Dictionary containing extracted metadata
        """
        metadata = {}
        
        # Extract name and type from header
        header_match = re.match(r'#\s*(.*?)\s*\((.*?)\)', content)
        if header_match:
            metadata['name'] = header_match.group(1)
            metadata['type'] = header_match.group(2)
        
        # Extract file path
        file_match = re.search(r'\*\*File:\*\*\s*(.*?)\s*\n', content)
        if file_match:
            metadata['file'] = file_match.group(1)
        
        # Extract language
        lang_match = re.search(r'\*\*Language:\*\*\s*(.*?)\s*\n', content)
        if lang_match:
            metadata['language'] = lang_match.group(1)
        
        # Extract line count
        lines_match = re.search(r'\*\*Lines:\*\*\s*(\d+)', content)
        if lines_match:
            metadata['line_count'] = int(lines_match.group(1))
        
        # Extract code content
        code_match = re.search(r'```.*?\n(.*?)```', content, re.DOTALL)
        if code_match:
            metadata['content'] = code_match.group(1).strip()
        
        # Extract description
        desc_match = re.search(r'\*\*Description:\*\*\s*(.*?)(?=\n\*\*|\n\n|$)', content, re.DOTALL)
        if desc_match:
            metadata['description'] = desc_match.group(1).strip()
        
        return metadata
    
    def _are_snippets_similar(self, snippet1: Dict[str, Any], snippet2: Dict[str, Any]) -> bool:
        """
        Determine if two snippets are similar enough to be merged.
        
        Args:
            snippet1: First snippet metadata
            snippet2: Second snippet metadata
            
        Returns:
            True if snippets are similar, False otherwise
        """
        # Check basic similarity
        if snippet1.get('type') != snippet2.get('type'):
            return False
        
        if snippet1.get('language') != snippet2.get('language'):
            return False
        
        # Compare names (allowing for slight variations)
        name1 = snippet1.get('name', '').lower()
        name2 = snippet2.get('name', '').lower()
        if name1 != name2:
            # Check for common variations
            if not (name1 in name2 or name2 in name1):
                return False
        
        # Compare content similarity
        content1 = snippet1.get('content', '')
        content2 = snippet2.get('content', '')
        
        # Calculate similarity ratio
        similarity = self._calculate_content_similarity(content1, content2)
        return similarity > 0.7  # 70% similarity threshold
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """
        Calculate similarity ratio between two code snippets.
        
        Args:
            content1: First code snippet
            content2: Second code snippet
            
        Returns:
            Similarity ratio between 0 and 1
        """
        # Normalize content
        content1 = self._normalize_code(content1)
        content2 = self._normalize_code(content2)
        
        # Calculate similarity using Levenshtein distance
        from difflib import SequenceMatcher
        return SequenceMatcher(None, content1, content2).ratio()
    
    def _normalize_code(self, code: str) -> str:
        """
        Normalize code for comparison by removing:
        - Comments
        - Whitespace
        - Variable names
        - String literals
        """
        # Remove comments
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        
        # Remove string literals
        code = re.sub(r'[\'"].*?[\'"]', '""', code)
        
        # Remove variable names (replace with generic names)
        code = re.sub(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', 'var', code)
        
        # Remove whitespace
        code = re.sub(r'\s+', ' ', code)
        
        return code.strip()
    
    def _merge_snippets(self, new_snippet: Dict[str, Any], existing_snippet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two similar snippets into one.
        
        Args:
            new_snippet: New snippet to merge
            existing_snippet: Existing snippet to merge with
            
        Returns:
            Merged snippet data
        """
        merged = existing_snippet.copy()
        
        # Update file paths
        if 'file' in new_snippet:
            if 'file' in merged:
                if new_snippet['file'] not in merged['file']:
                    merged['file'] = f"{merged['file']}, {new_snippet['file']}"
            else:
                merged['file'] = new_snippet['file']
        
        # Update line count
        merged['line_count'] = max(
            merged.get('line_count', 0),
            new_snippet.get('line_count', 0)
        )
        
        # Merge descriptions
        if 'description' in new_snippet:
            if 'description' in merged:
                if new_snippet['description'] not in merged['description']:
                    merged['description'] = f"{merged['description']}\n\nAdditional implementation:\n{new_snippet['description']}"
            else:
                merged['description'] = new_snippet['description']
        
        # Merge code content
        if 'content' in new_snippet:
            if 'content' in merged:
                if new_snippet['content'] not in merged['content']:
                    merged['content'] = f"{merged['content']}\n\n# Alternative Implementation\n{new_snippet['content']}"
            else:
                merged['content'] = new_snippet['content']
        
        return merged
    
    def _format_snippet_markdown(self, snippet: Dict[str, Any]) -> str:
        """
        Format snippet data as markdown.
        
        Args:
            snippet: Snippet data to format
            
        Returns:
            Formatted markdown string
        """
        markdown = f"""# {snippet['name']} ({snippet['type']})

**File:** {snippet.get('file', '')}  
**Language:** {snippet.get('language', '')}  
**Lines:** {snippet.get('line_count', 0)}  

"""
        
        if 'description' in snippet:
            markdown += f"**Description:** {snippet['description']}\n\n"
        
        if 'content' in snippet:
            markdown += f"```{snippet.get('language', '').lower()}\n{snippet['content']}\n```\n\n"
        
        # Add additional metadata if available
        if 'parameters' in snippet:
            markdown += f"**Parameters:** `{snippet['parameters']}`  \n"
        if 'return_type' in snippet and snippet['return_type']:
            markdown += f"**Returns:** `{snippet['return_type']}`  \n"
        if 'parent' in snippet and snippet['parent']:
            markdown += f"**Extends:** `{snippet['parent']}`  \n"
        
        return markdown
    
    def save_credentials(self) -> Path:
        """
        Save discovered credentials to a markdown file.
        
        Returns:
            Path to the saved credentials file
        """
        content = "# Security Audit: Discovered Credentials\n\n"
        content += "⚠️ **WARNING**: This file contains potentially sensitive information discovered during code analysis.\n"
        content += "Secure or remove these credentials and consider implementing a secure credential management solution.\n\n"
        
        if not self.credentials:
            content += "No credentials were found during the scan.\n"
        else:
            content += "## Overview\n\n"
            
            # Count credential types
            credential_counts = {}
            total_count = 0
            for file_creds in self.credentials.values():
                for cred in file_creds:
                    cred_type = cred['credential_type']
                    credential_counts[cred_type] = credential_counts.get(cred_type, 0) + 1
                    total_count += 1
            
            content += f"**Total credentials found:** {total_count}\n\n"
            content += "| Credential Type | Count |\n"
            content += "|----------------|-------|\n"
            for cred_type, count in credential_counts.items():
                content += f"| {cred_type} | {count} |\n"
            
            content += "\n## Detailed Findings\n\n"
            
            # List all credentials by file
            for file_path, file_creds in self.credentials.items():
                content += f"### {file_path}\n\n"
                
                for cred in file_creds:
                    content += f"**{cred['credential_type']} (Line {cred['line']}):**\n\n"
                    content += "```\n"
                    content += cred['context'] + "\n"
                    content += "```\n\n"
        
        # Write to file
        with open(self.credentials_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return self.credentials_file
    
    def generate_readme(self) -> Path:
        """
        Generate a comprehensive README with project information using xAI.
        
        Returns:
            Path to the generated README file
        """
        try:
            # Prepare project overview for xAI
            project_overview = {
                "name": self.directory.name,
                "file_count": self.file_count,
                "directory_count": self.directory_count,
                "languages": self.languages,
                "file_extensions": self.file_extensions,
                "snippets": self.snippets,
                "credentials": self.credentials,
                "structure": self._format_directory_structure(self.project_structure)
            }
            
            # Create prompt for xAI
            prompt = f"""Generate a comprehensive README for a code project with the following information:

Project Name: {project_overview['name']}
Total Files: {project_overview['file_count']}
Total Directories: {project_overview['directory_count']}

Languages Used:
{json.dumps(project_overview['languages'], indent=2)}

File Types:
{json.dumps(project_overview['file_extensions'], indent=2)}

Project Structure:
{project_overview['structure']}

Code Snippets: {len(project_overview['snippets'])}
Security Issues Found: {sum(len(creds) for creds in project_overview['credentials'].values())}

Please generate a well-structured README that includes:
1. Project overview and purpose
2. Installation instructions
3. Usage guide with examples
4. Project structure explanation
5. Code documentation and snippets
6. Security considerations
7. Development guidelines
8. Contributing guidelines

The README should be:
- Professional and well-formatted
- Include proper markdown syntax
- Be comprehensive but concise
- Focus on practical information
- Include code examples where relevant
"""

            # Call xAI API for README generation
            result = call_xai_api(
                XAI_MODEL_TEXT,
                prompt,
                {
                    "name": "generate_readme",
                    "description": "Generate a comprehensive README for a code project",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "readme_content": {
                                "type": "string",
                                "description": "The complete README content in markdown format"
                            },
                            "project_overview": {
                                "type": "string",
                                "description": "Brief overview of the project's purpose and main features"
                            },
                            "installation_steps": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Step-by-step installation instructions"
                            },
                            "usage_examples": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Code examples showing how to use the project"
                            },
                            "security_notes": {
                                "type": "string",
                                "description": "Security considerations and best practices"
                            }
                        },
                        "required": ["readme_content"]
                    }
                }
            )
            
            if not result:
                logger.error("xAI API returned no result")
                return self._generate_basic_readme()
            
            if "readme_content" not in result:
                logger.error("xAI API response missing readme_content")
                return self._generate_basic_readme()
            
            # Validate the generated content
            readme_content = result["readme_content"]
            if not readme_content.strip():
                logger.error("Generated README content is empty")
                return self._generate_basic_readme()
            
            # Write the xAI-generated README
            with open(self.readme_file, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            # Also save the structured data for potential future use
            structured_data = {
                "project_overview": result.get("project_overview", ""),
                "installation_steps": result.get("installation_steps", []),
                "usage_examples": result.get("usage_examples", []),
                "security_notes": result.get("security_notes", "")
            }
            
            with open(self.output_dir / "README_STRUCTURE.json", 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, indent=2)
            
            logger.info("Successfully generated README with xAI")
            return self.readme_file
            
        except Exception as e:
            logger.error(f"Error generating README with xAI: {e}")
            return self._generate_basic_readme()
    
    def _generate_basic_readme(self) -> Path:
        """Generate a basic README when xAI generation fails."""
        content = f"# {self.directory.name} Code Documentation\n\n"
        content += f"Automatically generated documentation by CleanupX for `{self.directory}`.\n\n"
        
        # Add project stats
        content += "## Project Statistics\n\n"
        content += f"- Files: {self.file_count}\n"
        content += f"- Directories: {self.directory_count}\n"
        
        # Add language breakdown
        if self.languages:
            content += "\n### Languages\n\n"
            content += "| Language | Files |\n"
            content += "|----------|-------|\n"
            sorted_languages = sorted(self.languages.items(), key=lambda x: x[1], reverse=True)
            for lang, count in sorted_languages:
                content += f"| {lang} | {count} |\n"
        
        # Add file extension breakdown
        if self.file_extensions:
            content += "\n### File Types\n\n"
            content += "| Extension | Count |\n"
            content += "|-----------|-------|\n"
            sorted_extensions = sorted(self.file_extensions.items(), key=lambda x: x[1], reverse=True)
            for ext, count in sorted_extensions:
                content += f"| {ext or '(no extension)'} | {count} |\n"
        
        # Add project structure
        content += "\n## Project Structure\n\n"
        content += "```\n"
        content += self._format_directory_structure(self.project_structure)
        content += "```\n\n"
        
        # Add code snippets
        if self.snippets:
            content += "## Code Snippets\n\n"
            content += "Below are key code components discovered during analysis:\n\n"
            
            # Group snippets by type
            snippets_by_type = {}
            for snippet in self.snippets:
                snippet_type = snippet.get("type", "Other")
                if snippet_type not in snippets_by_type:
                    snippets_by_type[snippet_type] = []
                snippets_by_type[snippet_type].append(snippet)
            
            for snippet_type, type_snippets in snippets_by_type.items():
                content += f"### {snippet_type}s\n\n"
                content += "| Name | File | Language | Lines | Description |\n"
                content += "|------|------|----------|-------|-------------|\n"
                
                for snippet in type_snippets:
                    name = snippet.get("name", "Unknown")
                    file_path = snippet.get("file", "")
                    language = snippet.get("language", "")
                    line_count = snippet.get("line_count", 0)
                    description = snippet.get("description", "")
                    
                    snippet_file = re.sub(r'[^\w\-_\.]', '_', f"{snippet_type.lower()}_{name}")
                    content += f"| [{name}](./snippets/{snippet_file}) | {file_path} | {language} | {line_count} | {description} |\n"
                
                content += "\n"
        
        # Add security information
        content += "## Security Information\n\n"
        
        if not self.credentials:
            content += "No potential security issues were found during the scan.\n"
        else:
            total_creds = sum(len(creds) for creds in self.credentials.values())
            content += f"⚠️ **Warning:** {total_creds} potential credentials were found in the codebase.\n"
            content += f"See [CREDENTIALS.md](./CREDENTIALS.md) for details.\n"
        
        # Write to file
        with open(self.readme_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return self.readme_file
    
    def _format_directory_structure(self, structure: Dict[str, Any], indent: int = 0) -> str:
        """Format a directory structure as a string."""
        result = ""
        items = list(structure.items())
        
        # Sort by type (directories first) and then by name
        items.sort(key=lambda x: (0 if isinstance(x[1], dict) else 1, x[0].lower()))
        
        for i, (name, value) in enumerate(items):
            is_last = i == len(items) - 1
            prefix = "└── " if is_last else "├── "
            result += "│   " * indent + prefix + name + "\n"
            
            if isinstance(value, dict):
                next_indent = indent + 1
                next_prefix = "    " if is_last else "│   "
                result += self._format_directory_structure(value, next_indent).replace("│   " * indent, "│   " * indent + next_prefix)
        
        return result
    
    def build_project_structure(self) -> Dict[str, Any]:
        """Build a hierarchical representation of the project structure."""
        structure = {}
        
        for root, dirs, files in os.walk(self.directory):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if not self.should_ignore_path(Path(root) / d)]
            
            # Get relative path
            rel_path = os.path.relpath(root, self.directory)
            
            # Skip the root directory
            if rel_path == ".":
                for file in files:
                    if not self.should_ignore_path(Path(root) / file):
                        structure[file] = {}
                continue
            
            # Navigate to the current position in the structure
            current = structure
            path_parts = rel_path.split(os.sep)
            
            for part in path_parts:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Add files
            for file in files:
                if not self.should_ignore_path(Path(root) / file):
                    current[file] = {}
        
        return structure
    
    def crawl(self) -> Tuple[Path, Path, Path]:
        """
        Perform a comprehensive crawl of the directory.
        
        Returns:
            Tuple of (snippets directory, credentials file, readme file)
        """
        logger.info(f"Starting comprehensive scan of {self.directory}")
        
        # Scan the directory structure first
        logger.info("Building project structure...")
        self.project_structure = self.build_project_structure()
        
        # Process files
        for root, dirs, files in os.walk(self.directory):
            # Update counts
            self.directory_count += 1
            
            # Skip ignored directories
            dirs[:] = [d for d in dirs if not self.should_ignore_path(Path(root) / d)]
            
            # Process each file
            for file in files:
                file_path = Path(root) / file
                
                # Skip ignored files
                if self.should_ignore_path(file_path):
                    continue
                
                # Update counters
                self.file_count += 1
                
                # Update extension stats
                ext = file_path.suffix.lower()
                self.file_extensions[ext] = self.file_extensions.get(ext, 0) + 1
                
                # Update language stats
                if ext in SNIPPET_EXTENSIONS:
                    lang = SNIPPET_EXTENSIONS[ext]
                    self.languages[lang] = self.languages.get(lang, 0) + 1
                
                try:
                    # Skip binary files and focus on text-based files
                    if ext in SNIPPET_EXTENSIONS or ext in ['.md', '.txt', '.json', '.xml', '.yaml', '.yml', '.env', '.config', '.ini']:
                        content = read_text_file(file_path)
                        
                        # Extract credentials
                        credentials = self.extract_credentials(file_path, content)
                        if credentials:
                            rel_path = str(file_path.relative_to(self.directory))
                            self.credentials[rel_path] = credentials
                        
                        # Extract code snippets
                        snippet = self.extract_code_snippet(file_path, content)
                        if snippet:
                            self.snippets.append(snippet)
                            self.save_snippet(snippet)
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
        
        # Generate outputs
        logger.info("Saving credentials information...")
        self.save_credentials()
        
        logger.info("Generating README documentation...")
        self.generate_readme()
        
        logger.info(f"Developer documentation generation complete! Output in {self.output_dir}")
        return self.snippets_dir, self.credentials_file, self.readme_file

def crawl_directory_for_developers(directory: Path, output_dir: Optional[Path] = None) -> Tuple[Path, Path, Path]:
    """
    Crawl a directory to extract code snippets, credentials, and generate documentation.
    
    Args:
        directory: Directory to crawl
        output_dir: Directory to save output (defaults to directory/cleanupx_dev)
        
    Returns:
        Tuple of (snippets directory, credentials file, readme file)
    """
    crawler = DevCrawler(directory, output_dir)
    return crawler.crawl() 