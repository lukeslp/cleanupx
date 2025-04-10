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
from typing import Dict, Optional, List, Set
from datetime import datetime

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    logging.error("Rich not installed. Install with: pip install rich")

try:
    import inquirer
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False
    logging.error("Inquirer not installed. Install with: pip install inquirer")

from cleanupx.utils.cache import load_cache, load_rename_log, save_rename_log
from cleanupx.ui.reporting import display_rename_report
from cleanupx.utils.documentation import DocumentationManager
from cleanupx.config import (
    IMAGE_EXTENSIONS, 
    TEXT_EXTENSIONS, 
    DOCUMENT_EXTENSIONS, 
    ARCHIVE_EXTENSIONS,
    CACHE_FILE
)

# Configure logging
logger = logging.getLogger(__name__)

def scramble_directory(target_dir: Path, rename_log: Optional[Dict] = None) -> int:
    """
    Scramble all filenames in the specified directory with random alphanumeric strings.
    Files are renamed while preserving extensions.
    
    Args:
        target_dir: Directory containing files to scramble
        rename_log: Optional rename log dictionary to update
    
    Returns:
        Number of files successfully scrambled
    """
    if not RICH_AVAILABLE:
        logger.error("Rich library not available for UI. Install with: pip install rich")
        return 0
        
    console = Console()
    target_dir = Path(target_dir)
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
        save_rename_log(rename_log)
    
    return scrambled_count

def main_menu(console: Console) -> str:
    """Display the main menu and get user choice."""
    questions = [
        inquirer.List(
            'action',
            message="What would you like to do?",
            choices=[
                ('Process and rename files', 'process'),
                ('Generate directory summaries', 'summary'),
                ('Manage citations', 'citations'),
                ('Scramble filenames', 'scramble'),
                ('Deduplicate images', 'dedupe_images'),
                ('Find duplicates', 'dedupe'),
                ('Reorganize files', 'reorganize'),
                ('Exit', 'exit')
            ],
        ),
    ]
    answer = inquirer.prompt(questions)
    return answer['action'] if answer else 'exit'

def process_files_menu(console: Console) -> Dict:
    """Get file processing preferences from user."""
    questions = [
        inquirer.Path(
            'directory',
            message="Enter the directory path to process",
            exists=True,
            path_type=inquirer.Path.DIRECTORY,
            default="inbox"
        ),
        inquirer.List(
            'scope',
            message="How would you like to process the directory?",
            choices=[
                ('Current directory only', 'single'),
                ('Include subdirectories (recursive)', 'recursive')
            ],
        ),
        inquirer.List(
            'renamed_files',
            message="How should previously renamed files be handled?",
            choices=[
                ('Skip previously renamed files', 'skip'),
                ('Process all files', 'all')
            ],
        ),
        inquirer.List(
            'cache',
            message="How should the cache be handled?",
            choices=[
                ('Use existing cache', 'use'),
                ('Clear cache before starting', 'clear')
            ],
        ),
        inquirer.Text(
            'max_size',
            message="Maximum file size to process in MB (larger files will be skipped)",
            default="25"
        ),
        inquirer.Checkbox(
            'file_types',
            message="Which file types would you like to process?",
            choices=[
                ('Images (jpg, png, etc.)', 'images'),
                ('Text files (txt, md, etc.)', 'text'),
                ('Documents (pdf, docx, etc.)', 'documents'),
                ('Archives (zip, rar, etc.)', 'archives')
            ],
            default=['images', 'text', 'documents', 'archives']
        ),
        inquirer.Confirm(
            'show_preview',
            message="Show preview of files to be processed/renamed before confirming?",
            default=True
        ),
        inquirer.Confirm(
            'generate_image_md',
            message="Generate .md files for image descriptions?",
            default=True
        ),
        inquirer.Confirm(
            'generate_archive_md',
            message="Generate .md archive summaries for archives?",
            default=True
        ),
        inquirer.Confirm(
            'proceed',
            message="Ready to start processing?",
            default=True
        ),
    ]
    return inquirer.prompt(questions)

def summary_menu(console: Console) -> Dict:
    """Get summary generation preferences from user."""
    questions = [
        inquirer.Path(
            'directory',
            message="Select directory to generate summary for",
            exists=True,
            path_type=inquirer.Path.DIRECTORY,
            default="inbox"
        ),
        inquirer.Checkbox(
            'summary_types',
            message="Which summaries would you like to generate?",
            choices=[
                ('Hidden summary (.cleanupx)', 'hidden'),
                ('README.md', 'readme'),
                ('Directory analysis', 'analysis'),
                ('Organization suggestions', 'suggestions')
            ],
            default=['hidden', 'readme', 'analysis', 'suggestions']
        ),
        inquirer.Confirm(
            'proceed',
            message="Generate summaries?",
            default=True
        ),
    ]
    return inquirer.prompt(questions)

def citations_menu(console: Console) -> Dict:
    """Get citation management preferences from user."""
    questions = [
        inquirer.Path(
            'directory',
            message="Select directory to manage citations for",
            exists=True,
            path_type=inquirer.Path.DIRECTORY,
            default="inbox"
        ),
        inquirer.List(
            'action',
            message="What would you like to do with citations?",
            choices=[
                ('Update citations', 'update'),
                ('Display citations', 'display'),
                ('Export citations to markdown', 'export')
            ],
        ),
        inquirer.Confirm(
            'proceed',
            message="Proceed with citation management?",
            default=True
        ),
    ]
    return inquirer.prompt(questions)

def dedupe_menu(console: Console) -> Dict:
    """Get deduplication preferences from user."""
    questions = [
        inquirer.Path(
            'directory',
            message="Select directory to find duplicates in",
            exists=True,
            path_type=inquirer.Path.DIRECTORY,
            default="inbox"
        ),
        inquirer.List(
            'scope',
            message="How would you like to search for duplicates?",
            choices=[
                ('Current directory only', 'single'),
                ('Include subdirectories (recursive)', 'recursive')
            ],
        ),
        inquirer.List(
            'action',
            message="How should duplicates be handled?",
            choices=[
                ('Show duplicates only (dry run)', 'dry_run'),
                ('Delete duplicates automatically', 'auto_delete'),
                ('Ask before deleting each duplicate', 'interactive')
            ],
        ),
        inquirer.Confirm(
            'proceed',
            message="Start duplicate search?",
            default=True
        ),
    ]
    return inquirer.prompt(questions)

def reorganize_menu(console: Console) -> Dict:
    """Get reorganization preferences from user."""
    questions = [
        inquirer.Path(
            'directory',
            message="Select directory to reorganize",
            exists=True,
            path_type=inquirer.Path.DIRECTORY,
            default="inbox"
        ),
        inquirer.List(
            'method',
            message="How would you like to reorganize?",
            choices=[
                ('By file type', 'type'),
                ('By content category', 'category'),
                ('By date', 'date'),
                ('Custom organization', 'custom')
            ],
        ),
        inquirer.Confirm(
            'proceed',
            message="Start reorganization?",
            default=True
        ),
    ]
    return inquirer.prompt(questions)

def interactive_mode() -> int:
    """
    Run the interactive mode with menu-driven interface.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not RICH_AVAILABLE or not INQUIRER_AVAILABLE:
        print("Required libraries not available. Please install with:")
        print("  pip install rich inquirer")
        return 1
        
    console = Console()
    console.print(Panel(
        "[bold cyan]Welcome to CleanupX![/bold cyan]\n"
        "This tool helps organize your files by analyzing their content and renaming them appropriately.", 
        border_style="cyan", 
        title="CleanupX File Organizer", 
        subtitle="v1.0"
    ))
    
    while True:
        action = main_menu(console)
        
        if action == 'exit':
            console.print("\n[green]Thank you for using CleanupX![/green]")
            return 0
            
        elif action == 'process':
            answers = process_files_menu(console)
            if not answers or not answers.get('proceed', False):
                continue
            
            directory = Path(answers['directory'])
            recursive = answers['scope'] == 'recursive'
            skip_renamed = answers['renamed_files'] == 'skip'
            clear_cache = answers['cache'] == 'clear'
            try:
                max_size = float(answers['max_size'])
            except ValueError:
                console.print("[yellow]Invalid max size value, using default of 25MB[/yellow]")
                max_size = 25.0
            # Preview step: list files to process with their status
            all_files = list(directory.glob('**/*')) if recursive else list(directory.glob('*'))
            preview_files = []
            for f in all_files:
                if f.is_file():
                    status_str = "Renamed" if not f.exists() else "Pending"
                    preview_files.append((f.name, status_str))

            if answers.get('show_preview', False):
                preview_table = Table(title="Files Preview", style="bright_blue")
                preview_table.add_column("File Name", style="bold")
                preview_table.add_column("Status", style="green")
                for name, stat in preview_files:
                    preview_table.add_row(name, stat)
                console.print(preview_table)

                confirm = inquirer.prompt([inquirer.Confirm('confirm_process', message="Proceed with processing these files?", default=True)])
                if not (confirm and confirm.get('confirm_process', False)):
                    console.print("[yellow]Processing cancelled by user.[/yellow]")
                    continue

            # Display processing configuration
            config_panel = Panel(
                f"[bold]Processing directory:[/bold] {directory}\n"
                f"[bold]Recursive:[/bold] {'Yes' if recursive else 'No'}\n"
                f"[bold]Skip renamed:[/bold] {'Yes' if skip_renamed else 'No'}\n"
                f"[bold]Maximum file size:[/bold] {max_size}MB\n"
                f"[bold]Generate Image MD:[/bold] {'Yes' if answers.get('generate_image_md') else 'No'}\n"
                f"[bold]Generate Archive MD:[/bold] {'Yes' if answers.get('generate_archive_md') else 'No'}",
                title="Processing Configuration",
                border_style="cyan"
            )
            console.print(config_panel)

            console.print("[blue]Starting file processing...[/blue]")
            try:
                from cleanupx.main import process_directory
                with console.status("[bold green]Processing files...[/bold green]", spinner="dots") as status:
                    stats = process_directory(directory, recursive=recursive, skip_renamed=skip_renamed, max_size_mb=max_size, generate_image_md=answers.get('generate_image_md', True), generate_archive_md=answers.get('generate_archive_md', True))

                detail_table = Table(title="File Processing Details", style="bright_yellow")
                detail_table.add_column("Metric", style="bold cyan")
                detail_table.add_column("Count", style="bold magenta")
                detail_table.add_row("Total Files", str(stats.get('total', 0)))
                detail_table.add_row("Images Processed", str(stats.get('images', 0)))
                detail_table.add_row("Text Files Processed", str(stats.get('text', 0)))
                detail_table.add_row("Documents Processed", str(stats.get('documents', 0)))
                detail_table.add_row("Archives Processed", str(stats.get('archives', 0)))
                detail_table.add_row("Files Skipped", str(stats.get('skipped', 0)))
                detail_table.add_row("Large Files Skipped", str(stats.get('skipped_large', 0)))
                detail_table.add_row("Files Failed", str(stats.get('failed', 0)))
                console.print(detail_table)

                from cleanupx.ui.reporting import display_rename_report
                rename_log = __import__('cleanupx.utils.cache', fromlist=['load_rename_log']).load_rename_log()
                console.print(Panel("Rename Report", style="bold green", border_style="green"))
                display_rename_report(rename_log)
            except KeyboardInterrupt:
                console.print("\n[yellow]Operation cancelled by user[/yellow]")
            except Exception as e:
                console.print(f"\n[bold red]Error: {e}[/bold red]")
            
        elif action == 'summary':
            answers = summary_menu(console)
            if not answers or not answers['proceed']:
                continue
                
            directory = Path(answers['directory'])
            doc_manager = DocumentationManager(directory)
            
            if 'hidden' in answers['summary_types']:
                doc_manager.update_hidden_summary()
            if 'readme' in answers['summary_types']:
                doc_manager.generate_readme()
            if 'analysis' in answers['summary_types']:
                doc_manager.display_summary()
            if 'suggestions' in answers['summary_types']:
                # TODO: Implement organization suggestions
                pass
                
        elif action == 'citations':
            answers = citations_menu(console)
            if not answers or not answers['proceed']:
                continue
                
            directory = Path(answers['directory'])
            doc_manager = DocumentationManager(directory)
            
            if answers['action'] == 'update':
                doc_manager.update_citations()
            elif answers['action'] == 'display':
                doc_manager.display_citations()
            elif answers['action'] == 'export':
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
                inquirer.Path(
                    'directory',
                    message="Select directory to scramble filenames",
                    exists=True,
                    path_type=inquirer.Path.DIRECTORY,
                    default="inbox"
                ),
                inquirer.Confirm(
                    'confirm',
                    message="This will rename ALL files in the directory with random names. Continue?",
                    default=False
                )
            ]
            
            answers = inquirer.prompt(questions)
            if not answers or not answers['confirm']:
                continue
                
            directory = Path(answers['directory'])
            rename_log = load_rename_log()
            scrambled_count = scramble_directory(directory, rename_log)
            
            console.print(f"\n[bold green]Scrambling complete![/bold green]")
            console.print(f"[cyan]Total files scrambled:[/cyan] {scrambled_count}")
            
            from cleanupx.ui.reporting import display_rename_report
            display_rename_report(rename_log)
            
        elif action == 'dedupe_images':
            questions = [
                inquirer.Path(
                    'directory',
                    message="Select directory to deduplicate images",
                    exists=True,
                    path_type=inquirer.Path.DIRECTORY,
                    default="inbox"
                ),
                inquirer.Confirm(
                    'proceed',
                    message="Proceed with image deduplication?",
                    default=True
                )
            ]
            dedupe_answers = inquirer.prompt(questions)
            if dedupe_answers and dedupe_answers.get('proceed', False):
                try:
                    from scripts.dedupe import dedupe_images
                    count = dedupe_images(dedupe_answers['directory'])
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
            
        console.print("\n[cyan]Press Enter to continue...[/cyan]")
        input()
