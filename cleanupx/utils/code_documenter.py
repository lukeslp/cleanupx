#!/usr/bin/env python3
"""
Code documentation generator for CleanupX.

This module provides functionality to analyze code files
and generate comprehensive documentation.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set

from cleanupx.utils.common import read_text_file, is_ignored_file

# Configure logging
logger = logging.getLogger(__name__)

# Constants for supported languages
LANGUAGE_INFO = {
    ".py": {
        "name": "Python",
        "class_pattern": r"class\s+(\w+)(?:\(([^)]*)\))?:",
        "function_pattern": r"def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^:]*))?\s*:",
        "docstring_pattern": r'"""(.*?)"""',
        "comment_pattern": r"#\s*(.*)",
        "module_docstring_pattern": r'^"""(.*?)"""',
        "multi_line_start": '"""',
        "multi_line_end": '"""',
        "import_pattern": r"(?:import|from)\s+([^;\n]+)",
    },
    ".js": {
        "name": "JavaScript",
        "class_pattern": r"class\s+(\w+)(?:\s+extends\s+([^\s{]+))?",
        "function_pattern": r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:function|\([^)]*\)\s*=>))",
        "docstring_pattern": r"/\*\*(.*?)\*/",
        "comment_pattern": r"//\s*(.*)",
        "module_docstring_pattern": r"^/\*\*(.*?)\*/",
        "multi_line_start": "/*",
        "multi_line_end": "*/",
        "import_pattern": r"(?:import|require)\s*\(?\s*['\"]([^'\"]+)",
    },
    ".ts": {
        "name": "TypeScript",
        "class_pattern": r"class\s+(\w+)(?:\s+extends\s+([^\s{]+))?",
        "function_pattern": r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:function|\([^)]*\)\s*=>)|(?:(\w+)\([^)]*\)\s*:\s*[^{]*)|(?:(\w+)\s*:\s*(?:Function|[^=;]*=>\s*[^=;]*)))",
        "docstring_pattern": r"/\*\*(.*?)\*/",
        "comment_pattern": r"//\s*(.*)",
        "module_docstring_pattern": r"^/\*\*(.*?)\*/",
        "multi_line_start": "/*",
        "multi_line_end": "*/",
        "import_pattern": r"(?:import|from)\s+['\"]([^'\"]+)",
    },
    ".java": {
        "name": "Java",
        "class_pattern": r"(?:public|private|protected)?\s*class\s+(\w+)(?:\s+extends\s+([^\s{]+))?",
        "function_pattern": r"(?:public|private|protected)?\s*(?:static)?\s*(?:[\w<>[\],\s]+)\s+(\w+)\s*\(([^)]*)\)",
        "docstring_pattern": r"/\*\*(.*?)\*/",
        "comment_pattern": r"//\s*(.*)",
        "module_docstring_pattern": r"^/\*\*(.*?)\*/",
        "multi_line_start": "/*",
        "multi_line_end": "*/",
        "import_pattern": r"import\s+([^;\n]+)",
    },
    ".rb": {
        "name": "Ruby",
        "class_pattern": r"class\s+(\w+)(?:\s*<\s*([^\s]+))?",
        "function_pattern": r"def\s+(\w+)(?:\(([^)]*)\))?",
        "docstring_pattern": r"=begin(.*?)=end",
        "comment_pattern": r"#\s*(.*)",
        "module_docstring_pattern": r"^#\s*(.*)",
        "multi_line_start": "=begin",
        "multi_line_end": "=end",
        "import_pattern": r"(?:require|include)\s+['\"]([^'\"]+)",
    },
    ".go": {
        "name": "Go",
        "class_pattern": r"type\s+(\w+)\s+struct",
        "function_pattern": r"func\s+(?:\(([^)]*)\)\s*)?(\w+)\s*\(([^)]*)\)",
        "docstring_pattern": r"/\*(.*?)\*/",
        "comment_pattern": r"//\s*(.*)",
        "module_docstring_pattern": r"^//\s*(.*)",
        "multi_line_start": "/*",
        "multi_line_end": "*/",
        "import_pattern": r"import\s+(?:\([^)]*\)|['\"]([^'\"]+))",
    },
    ".cs": {
        "name": "C#",
        "class_pattern": r"(?:public|private|protected|internal)?\s*(?:static)?\s*class\s+(\w+)(?:\s*:\s*([^{]+))?",
        "function_pattern": r"(?:public|private|protected|internal)?\s*(?:static)?\s*(?:[\w<>[\],\s]+)\s+(\w+)\s*\(([^)]*)\)",
        "docstring_pattern": r"///\s*<summary>(.*?)</summary>",
        "comment_pattern": r"//\s*(.*)",
        "module_docstring_pattern": r"^///\s*<summary>(.*?)</summary>",
        "multi_line_start": "/*",
        "multi_line_end": "*/",
        "import_pattern": r"using\s+([^;\n]+)",
    },
}

class CodeFile:
    """Represents a code file with its parsed components."""
    
    def __init__(self, path: Path):
        self.path = path
        self.relative_path = path
        self.language = ""
        self.name = path.name
        self.size = 0
        self.content = ""
        self.classes: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
        self.imports: List[str] = []
        self.docstring = ""
        self.comments: List[Dict[str, Any]] = []
        self.loc = 0  # Lines of code
        self.doc_coverage = 0.0  # Documentation coverage
        
    def load(self, root_dir: Path) -> bool:
        """Load and parse the file."""
        try:
            self.relative_path = self.path.relative_to(root_dir)
            self.size = self.path.stat().st_size
            self.content = read_text_file(self.path)
            self.loc = len(self.content.splitlines())
            return True
        except Exception as e:
            logger.error(f"Error loading {self.path}: {e}")
            return False
    
    def parse(self) -> bool:
        """Parse the file contents based on language."""
        suffix = self.path.suffix.lower()
        if suffix not in LANGUAGE_INFO:
            return False
            
        language_data = LANGUAGE_INFO[suffix]
        self.language = language_data["name"]
        
        # Extract docstring
        module_docstring_matches = re.search(language_data["module_docstring_pattern"], self.content, re.DOTALL)
        if module_docstring_matches:
            self.docstring = self._clean_docstring(module_docstring_matches.group(1))
        
        # Extract classes
        class_matches = re.finditer(language_data["class_pattern"], self.content)
        for match in class_matches:
            class_name = match.group(1)
            class_info = {
                "name": class_name,
                "docstring": self._extract_entity_docstring(match.start(), language_data),
                "line": self.content[:match.start()].count('\n') + 1,
                "methods": [],
            }
            
            if len(match.groups()) > 1 and match.group(2):
                class_info["inherits"] = match.group(2).strip()
                
            self.classes.append(class_info)
        
        # Extract functions/methods
        function_matches = re.finditer(language_data["function_pattern"], self.content)
        for match in class_matches:
            # Determine function name (patterns may have multiple capture groups for function name)
            function_name = None
            for i in range(1, len(match.groups()) + 1):
                if match.group(i) and not function_name:
                    function_name = match.group(i)
            
            if not function_name:
                continue
                
            function_info = {
                "name": function_name,
                "docstring": self._extract_entity_docstring(match.start(), language_data),
                "line": self.content[:match.start()].count('\n') + 1,
            }
            
            # Add parameter info if available
            params_index = 2  # Most patterns have params in group 2
            if len(match.groups()) >= params_index and match.group(params_index):
                function_info["parameters"] = match.group(params_index).strip()
                
            self.functions.append(function_info)
        
        # Extract imports
        import_matches = re.finditer(language_data["import_pattern"], self.content)
        for match in import_matches:
            import_stmt = match.group(1).strip() if match.group(1) else ""
            if import_stmt:
                self.imports.append(import_stmt)
        
        # Extract comments
        comment_matches = re.finditer(language_data["comment_pattern"], self.content, re.MULTILINE)
        for match in comment_matches:
            comment = match.group(1).strip()
            if comment:
                self.comments.append({
                    "text": comment,
                    "line": self.content[:match.start()].count('\n') + 1
                })
        
        # Calculate doc coverage
        self._calculate_doc_coverage()
        
        return True
    
    def _extract_entity_docstring(self, start_pos: int, language_data: Dict[str, str]) -> str:
        """Extract docstring for a class or function."""
        # Look for docstring after the entity definition
        content_after = self.content[start_pos:]
        docstring_match = re.search(language_data["docstring_pattern"], content_after, re.DOTALL)
        
        if docstring_match and docstring_match.start() < 50:  # Only consider docstrings close to the definition
            return self._clean_docstring(docstring_match.group(1))
            
        # Look for docstring before the entity definition
        content_before = self.content[:start_pos]
        lines_before = content_before.splitlines()
        if lines_before:
            # Look at the line just before the entity
            last_line = lines_before[-1].strip()
            if last_line.startswith("///") or last_line.startswith("//") or last_line.startswith("#"):
                # Try to gather consecutive comment lines
                docstring_lines = []
                for i in range(len(lines_before) - 1, -1, -1):
                    line = lines_before[i].strip()
                    if line.startswith("///") or line.startswith("//") or line.startswith("#"):
                        docstring_lines.insert(0, line.lstrip("#/").strip())
                    else:
                        break
                
                if docstring_lines:
                    return "\n".join(docstring_lines)
        
        return ""
    
    def _clean_docstring(self, docstring: str) -> str:
        """Clean up a docstring by removing extra whitespace and formatting."""
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in docstring.splitlines()]
        
        # Remove empty lines from the beginning and end
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
            
        if not lines:
            return ""
            
        # Determine the minimum indentation
        indentation = min(len(line) - len(line.lstrip()) for line in lines if line)
        
        # Remove the common indentation from all lines
        cleaned_lines = [line[indentation:] if line else line for line in lines]
        
        return "\n".join(cleaned_lines)
    
    def _calculate_doc_coverage(self) -> None:
        """Calculate documentation coverage percentage."""
        documentable_items = len(self.classes) + len(self.functions) + 1  # +1 for module docstring
        documented_items = sum(1 for cls in self.classes if cls.get("docstring"))
        documented_items += sum(1 for func in self.functions if func.get("docstring"))
        documented_items += 1 if self.docstring else 0
        
        self.doc_coverage = (documented_items / documentable_items) * 100 if documentable_items > 0 else 0

class CodeDocumenter:
    """Analyzes code files and generates documentation."""
    
    def __init__(self, directory: Path, output_path: Optional[Path] = None):
        """
        Initialize the code documenter.
        
        Args:
            directory: Directory containing code files
            output_path: Path to save documentation (defaults to directory/CODE_DOCS.md)
        """
        self.directory = Path(directory)
        self.output_path = output_path or (self.directory / "CODE_DOCS.md")
        self.code_files: List[CodeFile] = []
        self.language_stats: Dict[str, int] = {}
        self.total_loc = 0
        self.dependencies: Dict[str, Set[str]] = {}  # Maps files to their imports
        
    def scan_directory(self, recursive: bool = True) -> int:
        """
        Scan directory for code files.
        
        Args:
            recursive: Whether to scan subdirectories
            
        Returns:
            Number of files scanned
        """
        logger.info(f"Scanning directory: {self.directory}")
        
        # Function to process a file
        def process_file(file_path: Path) -> None:
            if is_ignored_file(file_path):
                return
                
            # Check if the file is a supported code file
            if file_path.suffix.lower() in LANGUAGE_INFO:
                code_file = CodeFile(file_path)
                if code_file.load(self.directory) and code_file.parse():
                    self.code_files.append(code_file)
                    self.language_stats[code_file.language] = self.language_stats.get(code_file.language, 0) + 1
                    self.total_loc += code_file.loc
        
        # Walk the directory structure
        if recursive:
            for root, dirs, files in os.walk(self.directory):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if not is_ignored_file(Path(root) / d)]
                
                # Process each file
                for file in files:
                    process_file(Path(root) / file)
        else:
            # Only process files in the root directory
            for item in self.directory.iterdir():
                if item.is_file():
                    process_file(item)
        
        logger.info(f"Scanned {len(self.code_files)} code files.")
        return len(self.code_files)
    
    def build_dependency_graph(self) -> Dict[str, Set[str]]:
        """
        Build a graph of file dependencies based on imports.
        
        Returns:
            Dictionary mapping file paths to sets of imported modules
        """
        # Build the dependency graph
        for code_file in self.code_files:
            file_path = str(code_file.relative_path)
            self.dependencies[file_path] = set()
            
            # Add imports as dependencies
            for import_stmt in code_file.imports:
                # Try to map the import to an actual file in the project
                potential_files = self._find_matching_files(import_stmt)
                for potential_file in potential_files:
                    self.dependencies[file_path].add(str(potential_file.relative_path))
        
        return self.dependencies
    
    def _find_matching_files(self, import_stmt: str) -> List[CodeFile]:
        """Find code files that match an import statement."""
        matching_files = []
        
        # Remove quotes and common prefixes
        import_stmt = import_stmt.strip('\'"')
        
        for code_file in self.code_files:
            # Very basic matching - would need to be improved for a real implementation
            file_path = str(code_file.relative_path)
            module_name = str(code_file.path.stem)
            
            if import_stmt.endswith(module_name) or import_stmt == module_name:
                matching_files.append(code_file)
        
        return matching_files
    
    def generate_markdown_documentation(self) -> Path:
        """
        Generate markdown documentation for the code.
        
        Returns:
            Path to the generated documentation file
        """
        logger.info(f"Generating documentation for {len(self.code_files)} files")
        
        # Calculate overall statistics
        doc_files = [f for f in self.code_files if f.docstring]
        doc_coverage = sum(f.doc_coverage for f in self.code_files) / len(self.code_files) if self.code_files else 0
        
        # Start the markdown content
        content = f"# Code Documentation: {self.directory.name}\n\n"
        content += "Automatically generated by CleanupX\n\n"
        
        # Add summary section
        content += "## Summary\n\n"
        content += f"- **Files:** {len(self.code_files)}\n"
        content += f"- **Lines of Code:** {self.total_loc}\n"
        content += f"- **Languages:** {', '.join(self.language_stats.keys())}\n"
        content += f"- **Documentation Coverage:** {doc_coverage:.1f}%\n\n"
        
        # Add language breakdown
        content += "### Language Breakdown\n\n"
        content += "| Language | Files | % of Codebase |\n"
        content += "|----------|-------|---------------|\n"
        for language, count in self.language_stats.items():
            percentage = (count / len(self.code_files)) * 100 if self.code_files else 0
            content += f"| {language} | {count} | {percentage:.1f}% |\n"
        content += "\n"
        
        # Add file listing
        content += "## Files\n\n"
        content += "| File | Language | Lines | Classes | Functions | Doc Coverage |\n"
        content += "|------|----------|-------|---------|-----------|-------------|\n"
        
        # Sort files by relative path
        sorted_files = sorted(self.code_files, key=lambda f: str(f.relative_path))
        for code_file in sorted_files:
            content += f"| [{code_file.relative_path}](#{self._create_anchor(str(code_file.relative_path))}) | {code_file.language} | {code_file.loc} | {len(code_file.classes)} | {len(code_file.functions)} | {code_file.doc_coverage:.1f}% |\n"
        content += "\n"
        
        # Add detailed file documentation
        content += "## File Details\n\n"
        for code_file in sorted_files:
            content += f"### {code_file.relative_path} {{{self._create_anchor(str(code_file.relative_path))}}}\n\n"
            content += f"**Language:** {code_file.language}  \n"
            content += f"**Lines:** {code_file.loc}  \n"
            content += f"**Documentation Coverage:** {code_file.doc_coverage:.1f}%  \n\n"
            
            # Add module docstring if available
            if code_file.docstring:
                content += "**Description:**\n\n"
                content += f"{code_file.docstring}\n\n"
            
            # Add dependencies
            file_path = str(code_file.relative_path)
            if file_path in self.dependencies and self.dependencies[file_path]:
                content += "**Dependencies:**\n\n"
                for dependency in sorted(self.dependencies[file_path]):
                    content += f"- [{dependency}](#{self._create_anchor(dependency)})\n"
                content += "\n"
            
            # Add imports
            if code_file.imports:
                content += "**Imports:**\n\n"
                for import_stmt in sorted(code_file.imports):
                    content += f"- `{import_stmt}`\n"
                content += "\n"
            
            # Add classes
            if code_file.classes:
                content += "**Classes:**\n\n"
                for cls in code_file.classes:
                    content += f"#### {cls['name']}\n\n"
                    if cls.get("inherits"):
                        content += f"*Inherits from: {cls['inherits']}*\n\n"
                    if cls.get("docstring"):
                        content += f"{cls['docstring']}\n\n"
                    content += f"*Defined at line {cls['line']}*\n\n"
            
            # Add functions
            if code_file.functions:
                content += "**Functions:**\n\n"
                for func in code_file.functions:
                    content += f"#### {func['name']}"
                    if func.get("parameters"):
                        content += f"({func['parameters']})"
                    content += "\n\n"
                    
                    if func.get("docstring"):
                        content += f"{func['docstring']}\n\n"
                    content += f"*Defined at line {func['line']}*\n\n"
            
            # Add a divider between files
            content += "---\n\n"
        
        # Write the content to the output file
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info(f"Documentation generated at {self.output_path}")
        return self.output_path
    
    def _create_anchor(self, text: str) -> str:
        """Create a GitHub-compatible markdown anchor."""
        # Convert to lowercase, replace spaces with hyphens, remove non-alphanumeric chars
        anchor = text.lower().replace(' ', '-')
        anchor = re.sub(r'[^\w\-]', '', anchor)
        return anchor

def generate_code_documentation(directory: Path, output_path: Optional[Path] = None) -> Path:
    """
    Generate comprehensive documentation for code in a directory.
    
    Args:
        directory: Directory containing code files
        output_path: Path to save documentation (defaults to directory/CODE_DOCS.md)
        
    Returns:
        Path to the generated documentation file
    """
    documenter = CodeDocumenter(directory, output_path)
    documenter.scan_directory(recursive=True)
    documenter.build_dependency_graph()
    return documenter.generate_markdown_documentation() 