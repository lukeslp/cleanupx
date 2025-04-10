#!/usr/bin/env python3
"""
Developer directory crawler utility for CleanupX.

This module provides functionality to:
1. Crawl a directory structure to extract useful code snippets
2. Identify and securely record credentials
3. Generate comprehensive README documentation
"""

import os
import re
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

from cleanupx.utils.common import read_text_file, is_ignored_file

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
            
        language = SNIPPET_EXTENSIONS[ext]
        relative_path = file_path.relative_to(self.directory)
        
        # Determine if file contains a class, function, or other useful code
        if ext == '.py':
            return self._extract_python_snippet(relative_path, content, language)
        elif ext in ['.js', '.ts', '.jsx', '.tsx']:
            return self._extract_js_snippet(relative_path, content, language)
        else:
            # For other languages, just extract the first non-empty 20 lines as a sample
            lines = content.splitlines()
            non_empty_lines = [line for line in lines if line.strip()]
            if len(non_empty_lines) >= 5:  # Only save if we have at least 5 non-empty lines
                snippet_content = "\n".join(non_empty_lines[:min(20, len(non_empty_lines))])
                return {
                    "file": str(relative_path),
                    "language": language,
                    "type": "Code Sample",
                    "name": file_path.name,
                    "content": snippet_content,
                    "line_count": len(lines)
                }
        
        return None
    
    def _extract_python_snippet(self, relative_path: Path, content: str, language: str) -> Optional[Dict[str, Any]]:
        """Extract useful Python code snippets."""
        # Look for classes
        class_matches = re.finditer(r"class\s+(\w+)(?:\(([^)]*)\))?:", content)
        for match in class_matches:
            class_name = match.group(1)
            parent_class = match.group(2) if match.group(2) else ""
            start_pos = match.start()
            
            # Find the class content (naive approach, but works for most cases)
            class_content = self._extract_block_content(content, start_pos)
            
            return {
                "file": str(relative_path),
                "language": language,
                "type": "Class",
                "name": class_name,
                "parent": parent_class,
                "content": class_content,
                "line_count": class_content.count('\n') + 1
            }
        
        # Look for functions
        function_matches = re.finditer(r"def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^:]*))?\s*:", content)
        for match in function_matches:
            function_name = match.group(1)
            params = match.group(2) if match.group(2) else ""
            return_type = match.group(3) if match.group(3) else ""
            start_pos = match.start()
            
            # Extract the function content
            function_content = self._extract_block_content(content, start_pos)
            
            return {
                "file": str(relative_path),
                "language": language,
                "type": "Function",
                "name": function_name,
                "parameters": params,
                "return_type": return_type,
                "content": function_content,
                "line_count": function_content.count('\n') + 1
            }
        
        return None
    
    def _extract_js_snippet(self, relative_path: Path, content: str, language: str) -> Optional[Dict[str, Any]]:
        """Extract useful JavaScript/TypeScript code snippets."""
        # Look for classes
        class_matches = re.finditer(r"class\s+(\w+)(?:\s+extends\s+([^\s{]+))?", content)
        for match in class_matches:
            class_name = match.group(1)
            parent_class = match.group(2) if match.group(2) else ""
            start_pos = match.start()
            
            # Find the class content
            class_content = self._extract_block_content(content, start_pos)
            
            return {
                "file": str(relative_path),
                "language": language,
                "type": "Class",
                "name": class_name,
                "parent": parent_class,
                "content": class_content,
                "line_count": class_content.count('\n') + 1
            }
        
        # Look for functions and arrow functions
        function_patterns = [
            r"function\s+(\w+)\s*\(([^)]*)\)",  # Named functions
            r"(?:const|let|var)\s+(\w+)\s*=\s*function\s*\(([^)]*)\)",  # Function expressions
            r"(?:const|let|var)\s+(\w+)\s*=\s*\(([^)]*)\)\s*=>",  # Arrow functions
        ]
        
        for pattern in function_patterns:
            function_matches = re.finditer(pattern, content)
            for match in function_matches:
                function_name = match.group(1)
                params = match.group(2) if match.group(2) else ""
                start_pos = match.start()
                
                # Extract the function content
                function_content = self._extract_block_content(content, start_pos)
                
                return {
                    "file": str(relative_path),
                    "language": language,
                    "type": "Function",
                    "name": function_name,
                    "parameters": params,
                    "content": function_content,
                    "line_count": function_content.count('\n') + 1
                }
        
        return None
    
    def _extract_block_content(self, content: str, start_pos: int, max_lines: int = 50) -> str:
        """Extract a code block starting from a given position."""
        # Get content from start position
        remaining = content[start_pos:]
        lines = remaining.splitlines()
        
        # Handle both brace-style and indentation-style blocks
        if '{' in remaining:
            # Handle brace-style blocks (like JS, Java)
            block_content = []
            brace_count = 0
            in_block = False
            
            for i, line in enumerate(lines):
                if i >= max_lines:
                    block_content.append("... (truncated)")
                    break
                    
                block_content.append(line)
                
                if '{' in line:
                    in_block = True
                    brace_count += line.count('{')
                
                if '}' in line:
                    brace_count -= line.count('}')
                
                if in_block and brace_count == 0:
                    break
            
            return "\n".join(block_content)
        else:
            # Handle indentation-style blocks (like Python)
            block_content = [lines[0]]
            base_indent = None
            
            for i, line in enumerate(lines[1:], 1):
                if i >= max_lines:
                    block_content.append("... (truncated)")
                    break
                    
                # Skip empty lines
                if not line.strip():
                    block_content.append(line)
                    continue
                
                # Determine indentation of the first non-empty line
                current_indent = len(line) - len(line.lstrip())
                if base_indent is None:
                    base_indent = current_indent
                    block_content.append(line)
                elif current_indent >= base_indent:
                    block_content.append(line)
                else:
                    break
            
            return "\n".join(block_content)
    
    def save_snippet(self, snippet: Dict[str, Any]) -> Path:
        """
        Save a code snippet to a file.
        
        Args:
            snippet: Snippet data
            
        Returns:
            Path to the saved snippet file
        """
        ext = "." + snippet["language"].lower().replace(" ", "_").replace("+", "p").replace("#", "sharp")
        filename = f"{snippet['type'].lower()}_{snippet['name']}{ext}"
        
        # Create a safe filename
        safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
        
        # If file exists, append a number
        counter = 1
        snippet_path = self.snippets_dir / safe_filename
        while snippet_path.exists():
            snippet_path = self.snippets_dir / f"{safe_filename.rsplit('.', 1)[0]}_{counter}.{safe_filename.rsplit('.', 1)[1]}"
            counter += 1
        
        # Format snippet markdown
        snippet_md = f"""# {snippet['name']} ({snippet['type']})

**File:** {snippet['file']}  
**Language:** {snippet['language']}  
**Lines:** {snippet['line_count']}  

```{snippet['language'].lower()}
{snippet['content']}
```

"""
        
        # Add additional metadata if available
        if 'parameters' in snippet:
            snippet_md += f"**Parameters:** `{snippet['parameters']}`  \n"
        if 'return_type' in snippet and snippet['return_type']:
            snippet_md += f"**Returns:** `{snippet['return_type']}`  \n"
        if 'parent' in snippet and snippet['parent']:
            snippet_md += f"**Extends:** `{snippet['parent']}`  \n"
        
        # Write to file
        with open(snippet_path, 'w', encoding='utf-8') as f:
            f.write(snippet_md)
        
        return snippet_path
    
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
        Generate a comprehensive README with project information.
        
        Returns:
            Path to the generated README file
        """
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
                content += "| Name | File | Language | Lines |\n"
                content += "|------|------|----------|-------|\n"
                
                for snippet in type_snippets:
                    name = snippet.get("name", "Unknown")
                    file_path = snippet.get("file", "")
                    language = snippet.get("language", "")
                    line_count = snippet.get("line_count", 0)
                    
                    snippet_file = re.sub(r'[^\w\-_\.]', '_', f"{snippet_type.lower()}_{name}")
                    content += f"| [{name}](./snippets/{snippet_file}) | {file_path} | {language} | {line_count} |\n"
                
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