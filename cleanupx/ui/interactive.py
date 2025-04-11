#!/usr/bin/env python3
"""
Interactive UI for CleanupX.
"""

import os
import logging
import random
import string
import sys
from pathlib import Path
from typing import Dict, Optional, List, Set, Union, Any
from datetime import datetime

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.layout import Layout
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    from rich import box
    from rich.live import Live
    from rich.tree import Tree
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    logging.error("Rich not installed. Install with: pip install rich")

# Try to import PyInquirer first (which has Separator), fallback to inquirer
try:
    from PyInquirer import prompt as pyinquirer_prompt
    from PyInquirer import Separator as PyInquirerSeparator
    PYINQUIRER_AVAILABLE = True
    
    # Create wrapper functions to handle PyInquirer vs inquirer differences
    def prompt(questions, theme=None):
        return pyinquirer_prompt(questions)
    
    # Use PyInquirer's Separator
    Separator = PyInquirerSeparator
    
    # Create wrappers for inquirer types
    class List:
        def __init__(self, name, message, choices, default=None, carousel=False):
            self.name = name
            self.message = message
            self.choices = choices
            self.default = default
            # Carousel not supported in PyInquirer
    
    class Confirm:
        def __init__(self, name, message, default=True):
            self.name = name
            self.message = message
            self.default = default
    
    class Text:
        def __init__(self, name, message, default=""):
            self.name = name
            self.message = message
            self.default = default
    
    class PathPrompt:
        DIRECTORY = 'directory'
        def __init__(self, name, message, exists=True, path_type=None, default="", mandatory=True):
            self.name = name
            self.message = message
            self.default = default
            # Other options not directly supported, would need custom validation
    
    class Checkbox:
        def __init__(self, name, message, choices, default=None):
            self.name = name
            self.message = message
            self.choices = choices
            self.default = default
    
    # Convert an inquirer-style question to PyInquirer format
    def convert_to_pyinquirer(question):
        if isinstance(question, List):
            return {
                'type': 'list',
                'name': question.name,
                'message': question.message,
                'choices': question.choices,
                'default': question.default
            }
        elif isinstance(question, Confirm):
            return {
                'type': 'confirm',
                'name': question.name,
                'message': question.message,
                'default': question.default
            }
        elif isinstance(question, Text):
            return {
                'type': 'input',
                'name': question.name,
                'message': question.message,
                'default': question.default
            }
        elif isinstance(question, PathPrompt):
            return {
                'type': 'input',
                'name': question.name,
                'message': question.message,
                'default': question.default
            }
        elif isinstance(question, Checkbox):
            return {
                'type': 'checkbox',
                'name': question.name,
                'message': question.message,
                'choices': question.choices,
                'default': question.default
            }
        return question
    
    # Override prompt to handle conversion
    def prompt(questions, theme=None):
        pyinquirer_questions = [convert_to_pyinquirer(q) for q in questions]
        return pyinquirer_prompt(pyinquirer_questions)
    
except ImportError:
    PYINQUIRER_AVAILABLE = False
    
    try:
        import inquirer
        from inquirer.themes import GreenPassion
        INQUIRER_AVAILABLE = True
        
        # Plain inquirer doesn't have Separator, so create a simple version
        class Separator:
            def __init__(self, title=""):
                self.title = title
                
            def __str__(self):
                return self.title
        
        # Use inquirer's prompt directly
        prompt = inquirer.prompt
        List = inquirer.List
        Confirm = inquirer.Confirm
        Text = inquirer.Text
        PathPrompt = inquirer.Path
        Checkbox = inquirer.Checkbox
        
    except ImportError:
        INQUIRER_AVAILABLE = False
        logging.error("Neither PyInquirer nor inquirer is installed. Install with: pip install PyInquirer")
        
# Configure logging
logger = logging.getLogger(__name__)

from cleanupx.utils.cache import load_cache, load_rename_log, save_rename_log, save_cache
from cleanupx.ui.reporting import display_rename_report
from cleanupx.utils.documentation import DocumentationManager
from cleanupx.config import (
    IMAGE_EXTENSIONS, 
    TEXT_EXTENSIONS, 
    DOCUMENT_EXTENSIONS, 
    ARCHIVE_EXTENSIONS,
    CACHE_FILE
)
from cleanupx.main import smart_merge_files
from cleanupx.processors import process_file

def display_summary_table(console: Console, title: str, data: Dict[str, str], style: str = "cyan"):
    """Display a summary table with the provided data."""
    table = Table(title=title, box=box.ROUNDED, border_style=style, header_style="bold white")
    table.add_column("Metric", style="bold " + style)
    table.add_column("Value", style="white")
    
    for key, value in data.items():
        table.add_row(key, str(value))
    
    console.print(table)
    return table

def scramble_directory(target_dir: Union[str, Path], rename_log: Optional[Dict] = None) -> int:
    """
    Scramble filenames in a directory with random names.
    
    Args:
        target_dir: Directory path to scramble
        rename_log: Optional dictionary to log old and new filenames
        
    Returns:
        Number of files successfully scrambled
    """
    if not RICH_AVAILABLE:
        logger.error("Rich library not available for UI. Install with: pip install rich")
        return 0
        
    console = Console()
    
    # Ensure target_dir is a pathlib.Path object
    target_dir = Path(target_dir) if not isinstance(target_dir, Path) else target_dir
    
    # Check if directory exists
    if not target_dir.exists() or not target_dir.is_dir():
        console.print(f"[yellow]Directory {target_dir} does not exist or is not a directory.[/yellow]")
        return 0
        
    files = list(target_dir.glob('*'))
    
    if not files:
        console.print("[yellow]No files found in directory.[/yellow]")
        return 0
    
    console.print(f"[cyan]Found {len(files)} files to rename in {target_dir}[/cyan]")
    
    # Process files with progress bar
    scrambled_count = 0
    with console.status(f"[green]Scrambling filenames...[/green]", spinner="dots") as status:
        for file_path in files:
            if file_path.is_file():
                # Generate random name (10 characters)
                random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                new_name = f"{random_name}{file_path.suffix}"
                new_path = file_path.parent / new_name
                
                # Handle name collisions
                while new_path.exists():
                    random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                    new_name = f"{random_name}{file_path.suffix}"
                    new_path = file_path.parent / new_name
                
                try:
                    # Rename the file
                    file_path.rename(new_path)
                    console.print(f"Renamed: {file_path.name} → {new_name}")
                    scrambled_count += 1
                    
                    # Update rename log if provided
                    if rename_log is not None:
                        rename_entry = {
                            "original_path": str(file_path),
                            "new_path": str(new_path),
                            "timestamp": datetime.now().isoformat()
                        }
                        rename_log["renames"].append(rename_entry)
                except Exception as e:
                    console.print(f"[bold red]Error renaming {file_path.name}: {e}[/bold red]")
    
    console.print(f"[green]Successfully scrambled {scrambled_count} filenames![/green]")
    
    # Save rename log
    if rename_log is not None:
        rename_log["timestamp"] = datetime.now().isoformat()
        save_rename_log(rename_log, target_dir)
    
    return scrambled_count

def main_menu(console: Console) -> str:
    """Display the main menu and return the selected action."""
    # Create a visually appealing header
    header = Panel(
        "[bold cyan]Welcome to CleanupX![/bold cyan]\n"
        "[white]The intelligent file organization and cleanup tool[/white]",
        border_style="cyan",
        box=box.ROUNDED
    )
    console.print(header)
    
    # Show main menu with improved categories
    console.print("\n[bold blue]Select an option from the menu below:[/bold blue]")
    
    # Use only actual choice tuples in the inquirer list
    questions = [
        List(
            'action',
            message="Select an action:",
            choices=[
                # File Processing options
                ('Process Files', 'process'),
                ('Batch Process Multiple Directories', 'batch_process'),
                ('Generate File Metadata', 'metadata'),
                
                # Organization options
                ('Organize Files by Topic', 'organize_topic'),
                ('Organize Files by Project', 'organize_project'),
                ('Organize Files by Date', 'organize_date'),
                ('Reorganize Directory', 'reorganize'),
                
                # Document Management options
                ('Smart Merge Similar Documents', 'smart_merge'),
                ('Snippet Deduplication', 'snippet_deduplication'),  # Add this option
                
                # Documentation & Reporting options
                ('Generate Directory Summary', 'summary'),
                ('Generate Bibliography', 'bibliography'),
                ('Generate HTML Report', 'report'),
                ('Manage Citations', 'citations'),
                ('Code Documentation', 'code_docs'),
                
                # Utilities options
                ('Scramble Filenames', 'scramble'),
                ('Deduplicate Images', 'dedupe_images'),
                ('General Deduplication', 'dedupe'),
                ('Cache Management', 'cache_management'),
                
                # Exit option
                ('Exit', 'exit')
            ],
            carousel=True
        )
    ]
    
    # Print section headers before showing the menu
    console.print(
        "\n[bold blue]=== File Processing ===[/bold blue]\n"
        "[bold blue]=== Organization ===[/bold blue]\n"
        "[bold blue]=== Document Management ===[/bold blue]\n"
        "[bold blue]=== Documentation & Reporting ===[/bold blue]\n"
        "[bold blue]=== Utilities ===[/bold blue]\n"
    )
    
    try:
        # Use our prompt function which handles both libraries
        answers = prompt(questions, theme=GreenPassion() if INQUIRER_AVAILABLE else None)
        return answers['action'] if answers else 'exit'
    except Exception as e:
        console.print(f"[red]Error displaying menu: {e}[/red]")
        return 'exit'

def process_files_menu(console: Console) -> Dict:
    """Display the process files menu and return user choices."""
    console.print(Panel("[bold blue]Process Files[/bold blue]\n"
                       "Analyze and rename files based on their content",
                       border_style="blue", box=box.ROUNDED))
    
    questions = [
        PathPrompt(
            'directory',
            message="Select directory to process",
            exists=True,
            path_type=PathPrompt.DIRECTORY,
            default="inbox"
        ),
        Confirm(
            'recursive',
            message="Process directory recursively?",
            default=False
        ),
        Text(
            'max_size',
            message="Maximum file size to process (MB)",
            default="25"
        ),
        Confirm(
            'generate_dashboard',
            message="Generate HTML dashboard after processing?",
            default=False
        ),
        Confirm(
            'proceed',
            message="Proceed with file processing?",
            default=True
        )
    ]
    
    try:
        answers = prompt(questions, theme=GreenPassion() if INQUIRER_AVAILABLE else None)
        if answers and answers.get('proceed', False):
            # Convert max size to float
            try:
                max_size = float(answers['max_size'])
            except ValueError:
                console.print(Panel("[yellow]Invalid max size, using default (25MB)[/yellow]", 
                                   border_style="yellow"))
                max_size = 25.0
            
            # Load cache and rename log
            cache = load_cache()
            rename_log = load_rename_log(Path.cwd())
            
            # Process files
            directory = Path(answers['directory'])
            files = list(directory.rglob('*') if answers['recursive'] else directory.glob('*'))
            files = [f for f in files if f.is_file()]
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=None),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
                expand=True
            ) as progress:
                task = progress.add_task(f"Processing files in {directory}", total=len(files))
                
                renamed_files = []
                failed_files = []
                skipped_files = []
                
                for file_path in files:
                    try:
                        result = process_file(
                            file_path, 
                            cache, 
                            rename_log,
                            max_size_mb=max_size,
                            generate_dashboard=answers['generate_dashboard']
                        )
                        if result[1]:  # new_path exists
                            renamed_files.append((str(file_path), str(result[1])))
                            console.print(f"[green]Renamed:[/green] {file_path.name} → {result[1].name}")
                        else:
                            skipped_files.append(str(file_path))
                    except Exception as e:
                        failed_files.append((str(file_path), str(e)))
                        console.print(f"[red]Error processing {file_path.name}:[/red] {str(e)}")
                    progress.update(task, advance=1)
            
            # Save cache and rename log
            save_cache(cache)
            save_rename_log(rename_log, directory)
            
            # Display summary
            summary = {
                "Total Files": len(files),
                "Files Renamed": len(renamed_files),
                "Files Skipped": len(skipped_files),
                "Files Failed": len(failed_files)
            }
            display_summary_table(console, "Processing Summary", summary, "green")
            
            return answers
        return {}
    except Exception as e:
        console.print(f"[red]Error displaying menu: {e}[/red]")
        return {}

def summary_menu(console: Console) -> Dict:
    """Get summary generation preferences from user."""
    console.print(Panel("[bold blue]Directory Summary[/bold blue]\n"
                       "Generate documentation and analysis for a directory's contents",
                       border_style="blue", box=box.ROUNDED))
    
    questions = [
        PathPrompt(
            'directory',
            message="Select directory to generate summary for",
            exists=True,
            path_type=PathPrompt.DIRECTORY,
            default="inbox"
        ),
        Checkbox(
            'summary_types',
            message="Which summaries would you like to generate?",
            choices=[
                ('Hidden summary (.cleanupx)', 'hidden'),
                ('README.md', 'readme'),
                ('Directory analysis', 'analysis'),
                ('File categorization', 'categorization'),
                ('Organization suggestions', 'suggestions')
            ],
            default=['hidden', 'readme', 'analysis', 'suggestions']
        ),
        Confirm(
            'include_images',
            message="Include image previews in summaries?",
            default=True
        ),
        Confirm(
            'include_stats',
            message="Include file statistics in summaries?",
            default=True
        ),
        Confirm(
            'proceed',
            message="Generate summaries?",
            default=True
        ),
    ]
    
    try:
        answers = prompt(questions, theme=GreenPassion() if INQUIRER_AVAILABLE else None)
        if answers and answers.get('proceed', False):
            # Display configuration summary
            config = {
                "Directory": answers['directory'],
                "Summary Types": ", ".join(answers['summary_types']),
                "Include Images": "Yes" if answers['include_images'] else "No",
                "Include Statistics": "Yes" if answers['include_stats'] else "No"
            }
            display_summary_table(console, "Summary Generation Configuration", config, "blue")
            
            return answers
        return {}
    except Exception as e:
        console.print(f"[red]Error displaying menu: {e}[/red]")
        return {}

def bibliography_menu(console: Console) -> Dict:
    """Get bibliography generation preferences from user."""
    console.print(Panel("[bold blue]Bibliography Generation[/bold blue]\n"
                       "Create a structured bibliography from files in a directory",
                       border_style="blue", box=box.ROUNDED))
    
    questions = [
        PathPrompt(
            'directory',
            message="Select directory to generate bibliography for",
            exists=True,
            path_type=PathPrompt.DIRECTORY,
            default="inbox"
        ),
        PathPrompt(
            'output_file',
            message="Output file path",
            exists=False,
            default="bibliography.md"
        ),
        List(
            'format',
            message="Output format:",
            choices=[
                ('Markdown (.md)', 'markdown'),
                ('HTML (.html)', 'html'),
                ('JSON (.json)', 'json'),
            ],
            default='markdown'
        ),
        Confirm(
            'recursive',
            message="Include files in subdirectories?",
            default=False
        ),
        Confirm(
            'include_metadata',
            message="Include file metadata in bibliography?",
            default=True
        ),
        Confirm(
            'proceed',
            message="Generate bibliography?",
            default=True
        ),
    ]
    
    try:
        answers = prompt(questions, theme=GreenPassion() if INQUIRER_AVAILABLE else None)
        if answers and answers.get('proceed', False):
            # Display configuration summary
            config = {
                "Source Directory": answers['directory'],
                "Output File": answers['output_file'],
                "Format": answers['format'].upper(),
                "Recursive": "Yes" if answers['recursive'] else "No",
                "Include Metadata": "Yes" if answers['include_metadata'] else "No"
            }
            display_summary_table(console, "Bibliography Configuration", config, "magenta")
            
            return answers
        return {}
    except Exception as e:
        console.print(f"[red]Error displaying menu: {e}[/red]")
        return {}

def report_menu(console: Console) -> Dict:
    """Get HTML report generation preferences from user."""
    console.print(Panel("[bold blue]HTML Report Generation[/bold blue]\n"
                       "Create a visually rich HTML report of directory contents",
                       border_style="blue", box=box.ROUNDED))
    
    questions = [
        PathPrompt(
            'directory',
            message="Select directory to generate report for",
            exists=True,
            path_type=PathPrompt.DIRECTORY,
            default="inbox"
        ),
        Confirm(
            'include_images',
            message="Include image previews in report?",
            default=True
        ),
        Confirm(
            'include_descriptions',
            message="Include file descriptions in report?",
            default=True
        ),
        Confirm(
            'include_stats',
            message="Include file statistics in report?",
            default=True
        ),
        List(
            'theme',
            message="Report theme:",
            choices=[
                ('Light', 'light'),
                ('Dark', 'dark'),
                ('Colorful', 'colorful'),
                ('Minimal', 'minimal')
            ],
            default='light'
        ),
        Confirm(
            'proceed',
            message="Generate HTML report?",
            default=True
        ),
    ]
    
    try:
        answers = prompt(questions, theme=GreenPassion() if INQUIRER_AVAILABLE else None)
        if answers and answers.get('proceed', False):
            # Display configuration summary
            config = {
                "Directory": answers['directory'],
                "Include Images": "Yes" if answers['include_images'] else "No",
                "Include Descriptions": "Yes" if answers['include_descriptions'] else "No",
                "Include Statistics": "Yes" if answers['include_stats'] else "No",
                "Theme": answers['theme'].capitalize()
            }
            display_summary_table(console, "HTML Report Configuration", config, "cyan")
            
            return answers
        return {}
    except Exception as e:
        console.print(f"[red]Error displaying menu: {e}[/red]")
        return {}

def citations_menu(console: Console) -> Dict:
    """Get citation management preferences from user."""
    console.print(Panel("[bold blue]Citation Management[/bold blue]\n"
                       "Update, display, and export citation information for files",
                       border_style="blue", box=box.ROUNDED))
    
    questions = [
        PathPrompt(
            'directory',
            message="Select directory to manage citations for",
            exists=True,
            path_type=PathPrompt.DIRECTORY,
            default="inbox"
        ),
        List(
            'action',
            message="What would you like to do with citations?",
            choices=[
                ('Update citations', 'update'),
                ('Display citations', 'display'),
                ('Export citations to markdown', 'export_md'),
                ('Export citations to BibTeX', 'export_bibtex'),
                ('Export citations to CSL-JSON', 'export_csl')
            ],
        ),
        Confirm(
            'proceed',
            message="Proceed with citation management?",
            default=True
        ),
    ]
    
    try:
        answers = prompt(questions, theme=GreenPassion() if INQUIRER_AVAILABLE else None)
        if answers and answers.get('proceed', False):
            # Display configuration summary
            config = {
                "Directory": answers['directory'],
                "Action": answers['action'].replace('_', ' ').title()
            }
            display_summary_table(console, "Citation Management", config, "magenta")
            
            return answers
        return {}
    except Exception as e:
        console.print(f"[red]Error displaying menu: {e}[/red]")
        return {}

def dedupe_menu(console: Console) -> Dict:
    """Get deduplication preferences from user."""
    questions = [
        PathPrompt(
            'directory',
            message="Select directory to find duplicates in",
            exists=True,
            path_type=PathPrompt.DIRECTORY,
            default="inbox"
        ),
        List(
            'scope',
            message="How would you like to search for duplicates?",
            choices=[
                ('Current directory only', 'single'),
                ('Include subdirectories (recursive)', 'recursive')
            ],
        ),
        List(
            'action',
            message="How should duplicates be handled?",
            choices=[
                ('Show duplicates only (dry run)', 'dry_run'),
                ('Delete duplicates automatically', 'auto_delete'),
                ('Ask before deleting each duplicate', 'interactive')
            ],
        ),
        Confirm(
            'proceed',
            message="Start duplicate search?",
            default=True
        ),
    ]
    return prompt(questions, theme=GreenPassion() if INQUIRER_AVAILABLE else None)

def reorganize_menu(console: Console) -> Dict:
    """Get reorganization preferences from user."""
    questions = [
        PathPrompt(
            'directory',
            message="Select directory to reorganize",
            exists=True,
            path_type=PathPrompt.DIRECTORY,
            default="inbox"
        ),
        List(
            'method',
            message="How would you like to reorganize?",
            choices=[
                ('By file type', 'type'),
                ('By content category', 'category'),
                ('By date', 'date'),
                ('Custom organization', 'custom')
            ],
        ),
        Confirm(
            'proceed',
            message="Start reorganization?",
            default=True
        ),
    ]
    return prompt(questions, theme=GreenPassion() if INQUIRER_AVAILABLE else None)

def cache_management_menu(console: Console) -> Dict:
    """Display the cache management menu and return user choices."""
    console.print("[bold blue]--- Cache Management Options ---[/bold blue]")
    
    questions = [
        PathPrompt(
            'directory',
            message="Select directory to manage cache files (leave empty for global cache)",
            exists=True,
            path_type=PathPrompt.DIRECTORY,
            default=""
        ),
        List(
            'action',
            message="Select a cache action:",
            choices=[
                ('List cache files', 'list'),
                ('Clear all cache files', 'clear_all'),
                ('Clear text extraction cache only', 'clear_text'),
                ('Clear global cache only (not text files)', 'clear_global'),
                ('Disable cache for this session', 'disable')
            ],
            default='list'
        ),
        Confirm(
            'proceed',
            message="Proceed with cache action?",
            default=True
        )
    ]
    
    try:
        answers = prompt(questions, theme=GreenPassion() if INQUIRER_AVAILABLE else None)
        if answers:
            return answers
        return {}
    except Exception as e:
        console.print(f"[red]Error displaying menu: {e}[/red]")
        return {}

def code_crawler_menu(console: Console) -> Dict:
    """Display the code crawler menu and return user choices."""
    console.print(Panel("[bold blue]Code Documentation Generator[/bold blue]\n"
                       "Scan code, extract snippets, and generate comprehensive documentation",
                       border_style="blue", box=box.ROUNDED))
    
    questions = [
        PathPrompt(
            'directory',
            message="Select directory containing code to document",
            exists=True,
            path_type=PathPrompt.DIRECTORY,
            default="."
        ),
        Text(
            'output_dir',
            message="Select output directory for documentation (leave empty for default)",
            default=""
        ),
        Confirm(
            'extract_credentials',
            message="Extract and document credentials found in code?",
            default=True
        ),
        Confirm(
            'extract_snippets',
            message="Extract meaningful code snippets?",
            default=True
        ),
        Confirm(
            'generate_readme',
            message="Generate comprehensive README documentation?",
            default=True
        ),
        Confirm(
            'open_after_generation',
            message="Open documentation when complete?",
            default=True
        ),
        Confirm(
            'proceed',
            message="Begin code documentation process?",
            default=True
        )
    ]
    
    try:
        answers = prompt(questions, theme=GreenPassion() if INQUIRER_AVAILABLE else None)
        if answers and answers.get('proceed', False):
            # Display configuration summary
            config = {
                "Code Directory": answers['directory'],
                "Output Directory": answers['output_dir'] if answers['output_dir'] else "Default (./cleanupx_dev)",
                "Extract Credentials": "Yes" if answers['extract_credentials'] else "No",
                "Extract Snippets": "Yes" if answers['extract_snippets'] else "No",
                "Generate README": "Yes" if answers['generate_readme'] else "No",
                "Open Documentation": "Yes" if answers['open_after_generation'] else "No"
            }
            display_summary_table(console, "Code Documentation Configuration", config, "blue")
            
            return answers
        return {}
    except Exception as e:
        console.print(f"[red]Error displaying menu: {e}[/red]")
        return {}

def smart_merge_menu(console: Console) -> Dict:
    """Display the smart merge menu and return user choices."""
    console.print(Panel("[bold magenta]Smart Document Merge[/bold magenta]\n"
                       "Intelligently merge similar documents to create definitive versions",
                       border_style="magenta", box=box.ROUNDED))
    
    questions = [
        PathPrompt(
            'directory',
            message="Select directory containing documents to analyze",
            exists=True,
            path_type=PathPrompt.DIRECTORY,
            default="."
        ),
        Text(
            'output_dir',
            message="Output directory for merged documents (leave empty for default)",
            default=""
        ),
        Text(
            'archive_dir',
            message="Archive directory for source documents (leave empty for default)",
            default=""
        ),
        Text(
            'similarity_threshold',
            message="Similarity threshold (0.1-1.0, higher is more strict)",
            default="0.75"
        ),
        Confirm(
            'recursive',
            message="Process subdirectories recursively?",
            default=False
        ),
        Confirm(
            'dry_run',
            message="Dry run (only find similar documents without merging)?",
            default=True
        ),
        Confirm(
            'proceed',
            message="Proceed with document analysis and merge?",
            default=True
        )
    ]
    
    try:
        answers = prompt(questions, theme=GreenPassion() if INQUIRER_AVAILABLE else None)
        if answers and answers.get('proceed', False):
            # Convert similarity threshold to float
            try:
                answers['similarity_threshold'] = float(answers['similarity_threshold'])
                # Validate threshold is between 0.1 and 1.0
                if answers['similarity_threshold'] < 0.1 or answers['similarity_threshold'] > 1.0:
                    console.print(Panel("[yellow]Invalid similarity threshold, using default (0.75)[/yellow]", 
                                       border_style="yellow"))
                    answers['similarity_threshold'] = 0.75
            except ValueError:
                console.print(Panel("[yellow]Invalid similarity threshold, using default (0.75)[/yellow]", 
                                   border_style="yellow"))
                answers['similarity_threshold'] = 0.75
            
            # Set output and archive dirs to None if empty
            if not answers['output_dir']:
                answers['output_dir'] = None
            if not answers['archive_dir']:
                answers['archive_dir'] = None
                
            # Display configuration summary
            config = {
                "Directory": answers['directory'],
                "Output Directory": answers['output_dir'] or "[default: ./merged]",
                "Archive Directory": answers['archive_dir'] or "[default: ./archived]",
                "Similarity Threshold": f"{answers['similarity_threshold']}",
                "Recursive": "Yes" if answers['recursive'] else "No",
                "Dry Run": "Yes" if answers['dry_run'] else "No"
            }
            display_summary_table(console, "Smart Merge Configuration", config, "magenta")
            
            return answers
        return {}
    except Exception as e:
        console.print(f"[red]Error displaying menu: {e}[/red]")
        return {}

def snippet_deduplication_menu(console: Console) -> Dict:
    """
    Interactive menu for finding and consolidating duplicate code snippets.
    
    Args:
        console: Rich console for formatted output
        
    Returns:
        Dictionary with user selections
    """
    console.print(Panel(
        "[bold]Snippet Deduplication[/bold]\n\n"
        "This tool helps identify and consolidate duplicate code snippets using a combination "
        "of text similarity detection and LLM-powered analysis.\n\n"
        "It works by:\n"
        "1. Finding groups of potentially similar files using a customizable similarity threshold\n"
        "2. Sending these groups to an LLM in batches for intelligent analysis\n"
        "3. Creating consolidated versions that combine the best parts of each duplicate\n"
        "4. Maintaining detailed metadata about the deduplication process",
        title="Snippet Deduplication",
        border_style="blue"
    ))
    
    # Get directory to process
    result = prompt([
        PathPrompt(
            "directory",
            "Directory containing code snippets to deduplicate:",
            exists=True,
            path_type=PathPrompt.DIRECTORY
        ),
        PathPrompt(
            "output_dir",
            "Output directory for results (optional, leave empty for default):",
            exists=False,
            path_type=PathPrompt.DIRECTORY,
            mandatory=False,
            default=""
        ),
        Text(
            "threshold",
            "Similarity threshold (0.0-1.0):",
            default="0.25"
        ),
        List(
            "processing_option",
            "Processing mode:",
            choices=[
                "Complete workflow (find duplicates and process with LLM)",
                "Generate batch files only (no LLM processing)",
                "Process existing batch files with LLM"
            ],
            default="Complete workflow (find duplicates and process with LLM)"
        )
    ])
    
    if not result:
        return {"action": "back"}
    
    directory = Path(result["directory"])
    
    try:
        # If we're processing existing batch files, use a different path
        processing_mode = result["processing_option"]
        if "Process existing batch files" in processing_mode:
            from cleanupx.utils.snippet_deduplication import process_batch_files
            
            # Ask for batch directory
            batch_result = prompt([
                PathPrompt(
                    "batch_dir",
                    "Directory containing batch files to process:",
                    exists=True,
                    path_type=PathPrompt.DIRECTORY
                ),
                PathPrompt(
                    "output_dir",
                    "Directory for consolidated files (optional):",
                    exists=False,
                    path_type=PathPrompt.DIRECTORY,
                    mandatory=False,
                    default=""
                )
            ])
            
            if not batch_result:
                return {"action": "back"}
            
            # Process the batch files
            with console.status("[bold cyan]Processing batch files with LLM...[/bold cyan]"):
                process_results = process_batch_files(
                    batch_dir=batch_result["batch_dir"],
                    output_dir=batch_result["output_dir"] if batch_result["output_dir"] else None
                )
            
            if process_results["success"]:
                console.print("[bold green]Batch processing complete![/bold green]")
                
                # Print any output
                for line in process_results["output"]:
                    if "error" in line.lower():
                        console.print(f"[red]{line}[/red]")
                    elif "warning" in line.lower():
                        console.print(f"[yellow]{line}[/yellow]")
                    else:
                        console.print(line)
            else:
                console.print("[bold red]Error processing batch files![/bold red]")
                if "error_message" in process_results:
                    console.print(f"[red]Error: {process_results['error_message']}[/red]")
                
                # Print any errors
                for line in process_results.get("errors", []):
                    console.print(f"[red]{line}[/red]")
                
                return {"action": "error"}
            
            return {"action": "done"}
        
        # Import the deduplication module
        from cleanupx.utils.snippet_deduplication import deduplicate_snippets
        from datetime import datetime
        
        # Parse threshold
        try:
            threshold = float(result["threshold"])
        except ValueError:
            console.print("[yellow]Invalid threshold value, using default (0.25)[/yellow]")
            threshold = 0.25
        
        # Set skip_processing based on the selected mode
        skip_processing = "Generate batch files only" in processing_mode
        
        # Run the deduplication
        with console.status("[bold cyan]Running snippet deduplication...[/bold cyan]"):
            dedup_results = deduplicate_snippets(
                directory=directory,
                output_dir=result["output_dir"] if result["output_dir"] else None,
                threshold=threshold,
                skip_processing=skip_processing
            )
        
        if dedup_results["success"]:
            console.print("[bold green]Snippet deduplication complete![/bold green]")
            
            # Print filtered output
            for line in dedup_results["output"]:
                if "error" in line.lower():
                    console.print(f"[red]{line}[/red]")
                elif "warning" in line.lower():
                    console.print(f"[yellow]{line}[/yellow]")
                elif any(s in line.lower() for s in ["complete", "success", "finished"]):
                    console.print(f"[green]{line}[/green]")
                else:
                    console.print(line)
            
            # Option to view results
            output_path = Path(dedup_results["output_dir"]) if dedup_results["output_dir"] else directory / f"deduplication_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            view_result = prompt([
                Confirm("view_results", "View consolidated files?", default=True)
            ])
            
            if view_result.get("view_results", False):
                # Show consolidated files
                consolidated_dir = output_path / "consolidated"
                if consolidated_dir.exists():
                    files = list(consolidated_dir.glob("*"))
                    if files:
                        # Filter out metadata and results files
                        content_files = [f for f in files if not f.name.endswith('.json')]
                        
                        if content_files:
                            table = Table(title="Consolidated Files")
                            table.add_column("File", style="cyan")
                            table.add_column("Duplicates", style="green")
                            
                            for file in content_files:
                                # Check for metadata file
                                meta_file = file.with_suffix(file.suffix + ".meta.json")
                                duplicates = []
                                
                                if meta_file.exists():
                                    try:
                                        import json
                                        with open(meta_file, 'r') as f:
                                            metadata = json.load(f)
                                            duplicates = metadata.get("duplicates", [])
                                    except Exception as e:
                                        console.print(f"[yellow]Error reading metadata: {e}[/yellow]")
                                
                                table.add_row(str(file.name), ", ".join(duplicates))
                            
                            console.print(table)
                        else:
                            console.print("[yellow]No consolidated files found (only metadata).[/yellow]")
                    else:
                        console.print("[yellow]No files found in consolidated directory.[/yellow]")
                else:
                    console.print(f"[yellow]Consolidated directory not found at {consolidated_dir}[/yellow]")
                    
                    # Check for batch files if we used --skip-processing
                    batches_dir = output_path / "batches"
                    if batches_dir.exists() and list(batches_dir.glob("batch_*.txt")):
                        console.print(f"[green]Batch files generated at {batches_dir}[/green]")
                        console.print("[cyan]Use 'Process existing batch files with LLM' option to process these files.[/cyan]")
            
            return {"action": "done"}
        else:
            console.print("[bold red]Snippet deduplication failed![/bold red]")
            if "error_message" in dedup_results:
                console.print(f"[red]Error: {dedup_results['error_message']}[/red]")
            
            # Print any errors
            for line in dedup_results.get("errors", []):
                console.print(f"[red]{line}[/red]")
            
            return {"action": "error"}
        
    except ImportError:
        console.print("[bold red]Error: snippet_deduplication module not found![/bold red]")
        console.print("[yellow]Please ensure the deduplication scripts are installed correctly.[/yellow]")
        return {"action": "error"}
    except Exception as e:
        console.print(f"[bold red]Error in snippet deduplication: {e}[/bold red]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/red]")
        return {"action": "error"}

def interactive_mode() -> int:
    """
    Run CleanupX in interactive mode with rich UI.
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    if not RICH_AVAILABLE:
        print("Rich library not available. Install with: pip install rich")
        return 1
        
    if not (INQUIRER_AVAILABLE or PYINQUIRER_AVAILABLE):
        print("Interactive prompt library not available. Install with either:")
        print("  pip install PyInquirer")
        print("  pip install inquirer")
        return 1
    
    console = Console()
    
    # Create a visually appealing splash screen
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=10),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    
    # Header with app banner
    banner = """
    ██████╗██╗     ███████╗ █████╗ ██╗   ██╗██████╗ ██╗  ██╗
   ██╔════╝██║     ██╔════╝██╔══██╗██║   ██║██╔══██╗╚██╗██╔╝
   ██║     ██║     █████╗  ███████║██║   ██║██████╔╝ ╚███╔╝ 
   ██║     ██║     ██╔══╝  ██╔══██║██║   ██║██╔═══╝  ██╔██╗ 
   ╚██████╗███████╗███████╗██║  ██║╚██████╔╝██║     ██╔╝ ██╗
    ╚═════╝╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝  ╚═╝
    """
    header_panel = Panel(
        banner,
        title="CleanupX",
        subtitle="Intelligent File Organization",
        border_style="cyan",
        box=box.ROUNDED
    )
    layout["header"].update(header_panel)
    
    # Body with description
    description = Panel(
        "[bold white]Welcome to CleanupX![/bold white]\n\n"
        "This tool helps you organize and manage your files intelligently by:\n"
        "• [cyan]Analyzing file content[/cyan] to understand what they contain\n"
        "• [cyan]Renaming files[/cyan] to be more descriptive and consistent\n"
        "• [cyan]Organizing files[/cyan] into logical folders based on content\n"
        "• [cyan]Generating documentation[/cyan] about your files and folders\n"
        "• [cyan]Creating reports[/cyan] to help you understand your data\n\n"
        "Press [bold green]Enter[/bold green] to continue to the main menu.",
        title="File Organization Assistant",
        border_style="green",
        box=box.ROUNDED
    )
    layout["body"].update(description)
    
    # Footer with version info
    footer = Panel(
        "Version 1.0.0 • © 2023 • Type 'exit' to quit at any time",
        border_style="blue",
        box=box.ROUNDED
    )
    layout["footer"].update(footer)
    
    # Display the splash screen
    console.print(layout)
    input()  # Wait for user to press Enter
    
    while True:
        console.clear()
        action = main_menu(console)
        
        if action == 'exit':
            console.print(Panel("[blue]Thank you for using CleanupX. Goodbye![/blue]", 
                               border_style="blue", box=box.ROUNDED))
            return 0
        
        elif action == 'process':
            result = process_files_menu(console)
            if result.get('action') == 'back':
                continue
            
        elif action == 'organize_topic' or action == 'organize_project' or action == 'organize_person' or action == 'organize_date':
            answers = organize_menu(console)
            if not answers or not answers.get('proceed', False):
                continue
                
            directory = Path(answers['directory'])
            destination = Path(answers['destination'])
            method = answers['method']
            recursive = answers.get('recursive', False)
            min_files = answers.get('min_files', 3)
            
            # Ensure the destination directory exists
            destination.mkdir(parents=True, exist_ok=True)
            
            # Load cache for content analysis
            cache = load_cache()
            
            try:
                # Pick the appropriate organize function based on method
                from cleanupx.utils.organize_utils import (
                    organize_files_by_topic, 
                    organize_files_by_project,
                    organize_files_by_person
                )
                
                with console.status(f"[bold green]Organizing files by {method}...", spinner="dots") as status:
                    # Convert Path objects to strings to prevent errors
                    dir_str = str(directory)
                    dest_str = str(destination)
                    
                    if method == 'topic':
                        file_count, created_folders = organize_files_by_topic(
                            dir_str, dest_str, cache, 
                            min_files_per_folder=min_files, recursive=recursive
                        )
                    elif method == 'project':
                        file_count, created_folders = organize_files_by_project(
                            dir_str, dest_str, cache, recursive=recursive
                        )
                    elif method == 'person':
                        file_count, created_folders = organize_files_by_person(
                            dir_str, dest_str, cache, recursive=recursive
                        )
                    elif method == 'date':
                        # Implement date-based organization
                        console.print("[yellow]Date-based organization not yet implemented[/yellow]")
                        file_count, created_folders = 0, []
                    elif method == 'type':
                        # Implement type-based organization
                        console.print("[yellow]Type-based organization not yet implemented[/yellow]")
                        file_count, created_folders = 0, []
                        
                # Save updated cache
                save_cache(cache)
                
                # Display results
                results = {
                    "Files Organized": file_count,
                    f"{method.capitalize()} Folders Created": len(created_folders),
                    "Source Directory": str(directory),
                    "Destination Directory": str(destination)
                }
                display_summary_table(console, "Organization Results", results, "green")
                
                if created_folders:
                    folder_table = Table(title=f"Created {method.capitalize()} Folders", 
                                       box=box.ROUNDED, border_style="cyan")
                    folder_table.add_column("Folder", style="blue")
                    folder_table.add_column("File Count", style="green")
                    
                    for folder in created_folders:
                        # Count files
                        file_count = len([f for f in folder.glob('*') if f.is_file()])
                        folder_table.add_row(folder.name, str(file_count))
                        
                    console.print(folder_table)
                    
                console.print(Panel(f"[bold green]Files successfully organized by {method}![/bold green]", 
                                  border_style="green", box=box.ROUNDED))
                
            except Exception as e:
                console.print(Panel(f"[bold red]Error organizing files: {e}[/bold red]", 
                                  border_style="red", box=box.ROUNDED))
                
        elif action == 'summary':
            answers = summary_menu(console)
            if not answers or not answers.get('proceed', False):
                continue
                
            directory = Path(answers['directory'])
            
            try:
                doc_manager = DocumentationManager(directory)
                
                with console.status("[bold green]Generating directory summaries...", spinner="dots") as status:
                    if 'hidden' in answers['summary_types']:
                        doc_manager.update_hidden_summary()
                        console.print("[green]Hidden summary (.cleanupx) updated[/green]")
                        
                    if 'readme' in answers['summary_types']:
                        doc_manager.generate_readme()
                        console.print("[green]README.md generated[/green]")
                        
                    if 'analysis' in answers['summary_types']:
                        doc_manager.display_summary()
                        
                    if 'categorization' in answers['summary_types']:
                        # Implement categorization display
                        console.print("[yellow]File categorization not yet implemented[/yellow]")
                        
                    if 'suggestions' in answers['summary_types']:
                        # Implement organization suggestions
                        console.print("[yellow]Organization suggestions not yet implemented[/yellow]")
                
                console.print(Panel("[bold green]Directory summaries generated successfully![/bold green]", 
                                  border_style="green", box=box.ROUNDED))
                
            except Exception as e:
                console.print(Panel(f"[bold red]Error generating summaries: {e}[/bold red]", 
                                  border_style="red", box=box.ROUNDED))
                
        elif action == 'bibliography':
            answers = bibliography_menu(console)
            if not answers or not answers.get('proceed', False):
                continue
                
            directory = Path(answers['directory'])
            output_file = Path(answers['output_file'])
            format = answers['format']
            recursive = answers.get('recursive', False)
            
            try:
                from cleanupx.utils.organize_utils import create_bibliography
                
                with console.status(f"[bold green]Generating {format} bibliography...", spinner="dots") as status:
                    # Convert Path objects to strings
                    dir_str = str(directory)
                    output_str = str(output_file)
                    
                    success = create_bibliography(dir_str, output_str, format, recursive)
                
                if success:
                    console.print(Panel(f"[bold green]Bibliography successfully generated:[/bold green] {output_file}", 
                                      border_style="green", box=box.ROUNDED))
                    
                    # Show preview for markdown format
                    if format == 'markdown' and output_file.exists():
                        try:
                            with open(output_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                preview = content[:500] + "..." if len(content) > 500 else content
                                
                            console.print(Panel(Markdown(preview), title="Bibliography Preview", 
                                                border_style="green", box=box.ROUNDED))
                        except Exception as e:
                            console.print(f"[yellow]Could not show preview: {e}[/yellow]")
                else:
                    console.print(Panel("[bold red]Failed to generate bibliography[/bold red]", 
                                      border_style="red", box=box.ROUNDED))
                    
            except Exception as e:
                console.print(Panel(f"[bold red]Error generating bibliography: {e}[/bold red]", 
                                  border_style="red", box=box.ROUNDED))
                
        elif action == 'report':
            answers = report_menu(console)
            if not answers or not answers.get('proceed', False):
                continue
                
            directory = Path(answers['directory'])
            
            try:
                from cleanupx.utils.report_utils import generate_folder_summary
                
                # Get renamed files from log
                rename_log = load_rename_log(Path.cwd())
                renamed_files = {item['original_path']: item['new_path'] 
                                for item in rename_log.get('renames', [])}
                
                # Get descriptions from cache
                cache = load_cache()
                descriptions = cache.get('descriptions', {})
                
                with console.status("[bold green]Generating HTML report...", spinner="dots") as status:
                    # Convert directory to string
                    dir_str = str(directory)
                    
                    # TODO: Pass theme and other options to the report generator when supported
                    report_path = generate_folder_summary(dir_str, renamed_files, descriptions)
                
                if report_path:
                    console.print(Panel(f"[bold green]HTML report successfully generated:[/bold green]\n{report_path}", 
                                      border_style="green", box=box.ROUNDED))
                    console.print("[cyan]Open this file in a web browser to view the report.[/cyan]")
                else:
                    console.print(Panel("[bold red]Failed to generate HTML report[/bold red]", 
                                      border_style="red", box=box.ROUNDED))
                    
            except Exception as e:
                console.print(Panel(f"[bold red]Error generating report: {e}[/bold red]", 
                                  border_style="red", box=box.ROUNDED))
                
        elif action == 'citations':
            answers = citations_menu(console)
            if not answers or not answers['proceed']:
                continue
                
            directory = Path(answers['directory'])
            # Convert Path to string when creating DocumentationManager
            doc_manager = DocumentationManager(str(directory))
            
            if answers['action'] == 'update':
                doc_manager.update_citations()
            elif answers['action'] == 'display':
                doc_manager.display_citations()
            elif answers['action'] == 'export_md':
                try:
                    citations_path = directory / ".cleanupx-citations"
                    md_path = directory / "CITATIONS.md"
                    with open(citations_path, 'r', encoding='utf-8') as f:
                        citations = f.read()
                    with open(md_path, 'w', encoding='utf-8') as f:
                        f.write("# Citations\n\n" + citations)
                    console.print(f"[green]Exported citations to {md_path}[/green]")
                except Exception as e:
                    console.print(f"[red]Error exporting citations: {e}[/red]")
                
        elif action == 'scramble':
            questions = [
                PathPrompt(
                    'directory',
                    message="Select directory to scramble filenames",
                    exists=True,
                    path_type=PathPrompt.DIRECTORY,
                    default="inbox"
                ),
                Confirm(
                    'confirm',
                    message="This will rename ALL files in the directory with random names. Continue?",
                    default=False
                )
            ]
            
            answers = prompt(questions, theme=GreenPassion() if INQUIRER_AVAILABLE else None)
            if not answers or not answers['confirm']:
                continue
                
            directory = Path(answers['directory'])
            # Import load_rename_log function here
            from cleanupx.utils.cache import load_rename_log
            rename_log = load_rename_log(Path.cwd())
            
            # Ensure directory is properly converted to a Path object before passing to scramble_directory
            scrambled_count = scramble_directory(directory, rename_log)
            
            console.print(f"\n[bold green]Scrambling complete![/bold green]")
            console.print(f"[cyan]Total files scrambled:[/cyan] {scrambled_count}")
            
            from cleanupx.ui.reporting import display_rename_report
            display_rename_report(rename_log)
            
        elif action == 'dedupe_images':
            questions = [
                PathPrompt(
                    'directory',
                    message="Select directory to deduplicate images",
                    exists=True,
                    path_type=PathPrompt.DIRECTORY,
                    default="inbox"
                ),
                Confirm(
                    'proceed',
                    message="Proceed with image deduplication?",
                    default=True
                )
            ]
            dedupe_answers = prompt(questions, theme=GreenPassion() if INQUIRER_AVAILABLE else None)
            if dedupe_answers and dedupe_answers.get('proceed', False):
                try:
                    from _METHODS.dedupe import dedupe_images
                    # Convert directory to string
                    dir_str = str(dedupe_answers['directory'])
                    count = dedupe_images(dir_str)
                    console.print(Panel(f"[green]Successfully deduplicated images. {count} duplicates removed.[/green]", title="Deduplication Result", border_style="green"))
                except Exception as e:
                    console.print(f"[red]Error during image deduplication: {e}[/red]")
            continue
            
        elif action == 'dedupe':
            answers = dedupe_menu(console)
            if not answers or not answers['proceed']:
                continue
                
            # TODO: Implement deduplication with these preferences
            
        elif action == 'reorganize':
            answers = reorganize_menu(console)
            if not answers or not answers['proceed']:
                continue
                
            # TODO: Implement reorganization with these preferences
            
        elif action == 'cache_management':
            answers = cache_management_menu(console)
            if not answers or not answers['proceed']:
                continue
                
            try:
                from cleanupx.utils.cache import clear_cache, _MEMORY_CACHE
                directory = None
                if answers['directory']:
                    directory = Path(answers['directory'])
                
                if answers['action'] == 'list':
                    # List cache files
                    import glob
                    import os
                    
                    # Display global cache files
                    from cleanupx.config import CACHE_FILE, RENAME_LOG_FILE
                    console.print("\n[bold cyan]Global Cache Files:[/bold cyan]")
                    if os.path.exists(CACHE_FILE):
                        size = os.path.getsize(CACHE_FILE) / 1024  # KB
                        console.print(f"[green]Cache file:[/green] {CACHE_FILE} ({size:.2f} KB)")
                    else:
                        console.print("[yellow]Cache file does not exist[/yellow]")
                        
                    if os.path.exists(RENAME_LOG_FILE):
                        size = os.path.getsize(RENAME_LOG_FILE) / 1024  # KB
                        console.print(f"[green]Rename log file:[/green] {RENAME_LOG_FILE} ({size:.2f} KB)")
                    else:
                        console.print("[yellow]Rename log file does not exist[/yellow]")
                    
                    # Display in-memory cache info
                    console.print("\n[bold cyan]In-Memory Cache:[/bold cyan]")
                    mem_cache_count = len(_MEMORY_CACHE)
                    if mem_cache_count > 0:
                        console.print(f"[green]Items in memory:[/green] {mem_cache_count}")
                        
                        # Show sample of memory cache keys
                        if mem_cache_count <= 10:
                            console.print("[bold blue]Memory cache keys:[/bold blue]")
                            for key in _MEMORY_CACHE.keys():
                                console.print(f"- {key}")
                        else:
                            console.print("[bold blue]Sample of memory cache keys:[/bold blue]")
                            for key in list(_MEMORY_CACHE.keys())[:5]:
                                console.print(f"- {key}")
                            console.print(f"... and {mem_cache_count - 5} more items")
                    else:
                        console.print("[yellow]Memory cache is empty[/yellow]")
                    
                    # Find and list text cache files
                    console.print("\n[bold cyan]Text Cache Files:[/bold cyan]")
                    text_cache_pattern = "text_cache*.txt"
                    search_dir = directory if directory else Path(".")
                    pattern = os.path.join(str(search_dir), "**", text_cache_pattern)
                    text_cache_files = glob.glob(pattern, recursive=True)
                    
                    if text_cache_files:
                        cache_table = Table(title=f"Text Cache Files ({len(text_cache_files)} found)", style="bright_yellow")
                        cache_table.add_column("File Path", style="cyan")
                        cache_table.add_column("Size", style="green")
                        cache_table.add_column("Modified", style="magenta")
                        
                        total_size = 0
                        for cache_file in text_cache_files[:20]:  # Show up to 20 files
                            try:
                                stats = os.stat(cache_file)
                                size_kb = stats.st_size / 1024
                                modified = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                                cache_table.add_row(cache_file, f"{size_kb:.2f} KB", modified)
                                total_size += stats.st_size
                            except Exception as e:
                                cache_table.add_row(cache_file, "Error", f"Error: {e}")
                                
                        if len(text_cache_files) > 20:
                            cache_table.add_row(f"... and {len(text_cache_files) - 20} more files", "", "")
                            
                        console.print(cache_table)
                        console.print(f"[cyan]Total size of text cache:[/cyan] {total_size / 1024 / 1024:.2f} MB")
                    else:
                        console.print("[yellow]No text cache files found[/yellow]")
                
                elif answers['action'] == 'clear_all':
                    # Clear all cache files
                    stats = clear_cache(directory)
                    console.print("[bold green]All cache files cleared successfully[/bold green]")
                    console.print(f"[cyan]Global cache files removed:[/cyan] {stats['global_cache']}")
                    console.print(f"[cyan]Rename log files removed:[/cyan] {stats['rename_log']}")
                    console.print(f"[cyan]Text cache files removed:[/cyan] {stats['text_cache']}")
                    console.print(f"[cyan]Memory cache items cleared:[/cyan] {stats['memory_cache']}")
                
                elif answers['action'] == 'clear_text':
                    # Clear only text cache files
                    import glob
                    import os
                    
                    text_cache_pattern = "text_cache*.txt"
                    search_dir = directory if directory else Path(".")
                    pattern = os.path.join(str(search_dir), "**", text_cache_pattern)
                    text_cache_files = glob.glob(pattern, recursive=True)
                    
                    removed = 0
                    for cache_file in text_cache_files:
                        try:
                            os.remove(cache_file)
                            removed += 1
                        except Exception as e:
                            console.print(f"[yellow]Failed to remove {cache_file}: {e}[/yellow]")
                    
                    console.print(f"[bold green]Removed {removed} text cache files[/bold green]")
                
                elif answers['action'] == 'clear_global':
                    # Clear only global cache files
                    from cleanupx.config import CACHE_FILE, RENAME_LOG_FILE
                    removed = 0
                    
                    if os.path.exists(CACHE_FILE):
                        os.remove(CACHE_FILE)
                        removed += 1
                        console.print(f"[green]Removed cache file: {CACHE_FILE}[/green]")
                        
                    if os.path.exists(RENAME_LOG_FILE):
                        os.remove(RENAME_LOG_FILE)
                        removed += 1
                        console.print(f"[green]Removed rename log file: {RENAME_LOG_FILE}[/green]")
                        
                    console.print(f"[bold green]Removed {removed} global cache files[/bold green]")
                
                elif answers['action'] == 'disable':
                    # Disable cache for this session
                    os.environ['CLEANUPX_NO_CACHE'] = "1"
                    # Also clear the memory cache
                    mem_cache_count = len(_MEMORY_CACHE)
                    _MEMORY_CACHE.clear()
                    console.print("[bold cyan]Cache disabled for this session[/bold cyan]")
                    console.print(f"[green]Cleared {mem_cache_count} items from memory cache[/green]")
                    console.print("[yellow]Note: This will not affect already created cache files[/yellow]")
                
            except Exception as e:
                console.print(f"[bold red]Error managing cache: {e}[/bold red]")
        
        elif action == 'code_docs':
            answers = code_crawler_menu(console)
            if not answers or not answers.get('proceed'):
                continue
                
            directory = Path(answers['directory'])
            output_dir = Path(answers['output_dir']) if answers['output_dir'] else None
            
            try:
                # Import the developer crawler module
                from cleanupx.utils.dev_crawler import crawl_directory_for_developers
                
                with console.status("[bold green]Analyzing code and generating documentation...", spinner="dots") as status:
                    # Convert directory and output_dir to strings if needed
                    dir_str = str(directory)
                    out_str = str(output_dir) if output_dir else None
                    
                    snippets_dir, credentials_file, readme_file = crawl_directory_for_developers(
                        dir_str, out_str
                    )
                
                # Display results
                results = {
                    "Code Directory": str(directory),
                    "Code Snippets": str(snippets_dir),
                    "Credentials Report": str(credentials_file),
                    "Documentation": str(readme_file)
                }
                display_summary_table(console, "Code Documentation Results", results, "green")
                
                console.print(Panel("[bold green]Documentation generation complete![/bold green]", 
                                  border_style="green", box=box.ROUNDED))
                
                # Open the documentation if requested
                if answers.get('open_after_generation', False):
                    try:
                        import subprocess
                        # Try to open the README file - make sure readme_file is a string
                        console.print("[cyan]Opening documentation...[/cyan]")
                        subprocess.run(['open', str(readme_file)], check=False)
                    except Exception as e:
                        console.print(f"[yellow]Could not open documentation: {e}[/yellow]")
                        
            except Exception as e:
                console.print(Panel(f"[bold red]Error generating code documentation: {e}[/bold red]", 
                                  border_style="red", box=box.ROUNDED))
        
        elif action == 'smart_merge':
            config = smart_merge_menu(console)
            if config:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[bold magenta]{task.description}[/bold magenta]"),
                    BarColumn(),
                    TimeElapsedColumn()
                ) as progress:
                    task = progress.add_task(f"Analyzing documents in {config['directory']}...", total=None)
                    
                    # Run smart merge
                    results = smart_merge_files(
                        directory=config['directory'],
                        output_dir=config.get('output_dir'),
                        similarity_threshold=config.get('similarity_threshold', 0.75),
                        archive_dir=config.get('archive_dir'),
                        recursive=config.get('recursive', False),
                        dry_run=config.get('dry_run', True)
                    )
                    
                    # Update progress
                    progress.update(task, completed=100, 
                                  description="Document analysis complete")
                
                # Display results
                if config.get('dry_run', True):
                    # Display groups of similar documents found
                    console.print(Panel(
                        f"[bold green]Found {results.get('total_groups', 0)} groups of similar documents[/bold green]",
                        border_style="green"
                    ))
                    
                    # Show each group with options to merge
                    for group_id, files in results.get('similar_files', {}).items():
                        console.print(f"[bold]Group {group_id}:[/bold]")
                        for i, file_path in enumerate(files, 1):
                            console.print(f"  {i}. {file_path}")
                        
                        # Ask if user wants to merge this group
                        merge_group = prompt([
                            Confirm(
                                'merge_now',
                                message=f"Would you like to merge this group now?",
                                default=False
                            )
                        ])
                        
                        if merge_group and merge_group.get('merge_now', False):
                            # Run merge for just this group
                            console.print(f"[cyan]Merging group {group_id}...[/cyan]")
                            from cleanupx.processors.smart_merge import find_similar_documents, merge_document_group
                            
                            # Convert string file paths back to Path objects
                            directory = Path(config['directory'])
                            # Create group to pass to merge function
                            group_files = []
                            for f in files:
                                file_path = Path(f)
                                # Extract text from file
                                try:
                                    from cleanupx.processors.smart_merge import extract_document_text
                                    text = extract_document_text(file_path)
                                    group_files.append((file_path, text))
                                except Exception as e:
                                    console.print(f"[red]Error reading {file_path}: {e}[/red]")
                            
                            # Define output directory
                            output_dir = Path(config.get('output_dir')) if config.get('output_dir') else directory / "merged"
                            output_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Merge the group
                            try:
                                merged_file, source_files = merge_document_group(group_files, output_dir, group_id)
                                console.print(f"[green]Created merged document: {merged_file}[/green]")
                                
                                # Display the merged content
                                console.print("[bold cyan]Preview of merged content:[/bold cyan]")
                                try:
                                    with open(merged_file, 'r', encoding='utf-8') as f:
                                        content = f.read()
                                        preview = content[:500] + "..." if len(content) > 500 else content
                                        console.print(Panel(preview, border_style="cyan"))
                                except Exception as e:
                                    console.print(f"[yellow]Could not preview content: {e}[/yellow]")
                                
                                # Ask what to do with source files
                                file_action = prompt([
                                    List(
                                        'action',
                                        message="What would you like to do with the source files?",
                                        choices=[
                                            ('Archive source files', 'archive'),
                                            ('Delete source files', 'delete'),
                                            ('Keep source files', 'keep')
                                        ],
                                        default='archive'
                                    )
                                ])
                                
                                if file_action and file_action.get('action') == 'archive':
                                    # Archive source files
                                    archive_dir = Path(config.get('archive_dir')) if config.get('archive_dir') else directory / "archived"
                                    archive_dir.mkdir(parents=True, exist_ok=True)
                                    
                                    from cleanupx.processors.smart_merge import archive_source_documents
                                    success = archive_source_documents(source_files, archive_dir)
                                    if success:
                                        console.print(f"[green]Source files archived to {archive_dir}[/green]")
                                    else:
                                        console.print("[yellow]Some files could not be archived[/yellow]")
                                
                                elif file_action and file_action.get('action') == 'delete':
                                    # Delete source files
                                    deleted = 0
                                    for file_path in source_files:
                                        try:
                                            file_path.unlink()
                                            deleted += 1
                                        except Exception as e:
                                            console.print(f"[red]Error deleting {file_path}: {e}[/red]")
                                    console.print(f"[green]Deleted {deleted} source files[/green]")
                                
                                else:
                                    console.print("[cyan]Source files kept in place[/cyan]")
                                    
                            except Exception as e:
                                console.print(f"[red]Error merging documents: {e}[/red]")
                        
                        console.print("")  # Add spacing between groups
                else:
                    # Display merge results
                    result_stats = {
                        "Total groups merged": results.get('merged_groups', 0),
                        "Merged files created": len(results.get('merged_files', [])),
                        "Source files archived": len(results.get('archived_files', [])),
                        "Total files processed": results.get('total_files', 0),
                        "Error files": len(results.get('error_files', []))
                    }
                    display_summary_table(console, "Smart Merge Results", result_stats, "green")
                    
                    # Show list of merged files with preview option
                    if results.get('merged_files'):
                        merged_files_table = Table(title="Merged Files", box=box.ROUNDED, border_style="cyan")
                        merged_files_table.add_column("#", style="cyan")
                        merged_files_table.add_column("File Path", style="bold white")
                        
                        for i, file_path in enumerate(results.get('merged_files', []), 1):
                            merged_files_table.add_row(str(i), file_path)
                        
                        console.print(merged_files_table)
                        
                        # Ask which file to preview
                        preview_choice = prompt([
                            List(
                                'file_number',
                                message="Select a file to preview content:",
                                choices=[('None', '0')] + [(f"File {i}", str(i)) for i in range(1, len(results.get('merged_files', [])) + 1)],
                                default='0'
                            )
                        ])
                        
                        if preview_choice and preview_choice.get('file_number', '0') != '0':
                            try:
                                idx = int(preview_choice.get('file_number')) - 1
                                file_path = results.get('merged_files', [])[idx]
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    preview = content[:1000] + "..." if len(content) > 1000 else content
                                    console.print(Panel(preview, title=f"Content Preview: {file_path}", border_style="cyan"))
                            except Exception as e:
                                console.print(f"[yellow]Could not preview file: {e}[/yellow]")
                        
                    input("\nPress Enter to continue...")
        
        elif action == 'snippet_deduplication':
            result = snippet_deduplication_menu(console)
            if result.get('action') == 'back':
                continue
            elif result.get('action') == 'done':
                console.print(Panel("[bold green]Snippet deduplication completed successfully![/bold green]", 
                                   border_style="green", box=box.ROUNDED))
            elif result.get('action') == 'error':
                console.print(Panel("[bold red]Error in snippet deduplication![/bold red]", 
                                   border_style="red", box=box.ROUNDED))
        
        # Wait for user to continue
        console.print("\n[cyan]Press Enter to return to the main menu...[/cyan]")
        input()

    return 0
