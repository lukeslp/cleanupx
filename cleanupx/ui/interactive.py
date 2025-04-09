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
from typing import Dict, Optional, List

try:
    from rich.console import Console
    from rich.panel import Panel
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
                        from datetime import datetime
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
        from datetime import datetime
        rename_log["timestamp"] = datetime.now().isoformat()
        save_rename_log(rename_log)
    
    return scrambled_count

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
    console.print(Panel("[bold cyan]Welcome to CleanupX![/bold cyan]\nThis tool helps organize your files by analyzing their content and renaming them appropriately.", 
                      border_style="cyan", 
                      title="CleanupX File Organizer", 
                      subtitle="v1.0"))
    
    console.print("")
    
    # First, choose the operation mode
    mode_question = [
        inquirer.List(
            'mode',
            message="Choose operation mode",
            choices=[
                ('Rename files with descriptive names based on content (default)', 'rename'),
                ('Scramble filenames with random strings for privacy', 'scramble'),
            ],
        ),
    ]
    mode_answer = inquirer.prompt(mode_question)
    if not mode_answer:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        return 1
    
    if mode_answer['mode'] == 'scramble':
        # Scramble mode
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
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
            return 1
        
        directory = Path(answers['directory'])
        rename_log = load_rename_log()
        scrambled_count = scramble_directory(directory, rename_log)
        
        console.print(f"\n[bold green]Scrambling complete![/bold green]")
        console.print(f"[cyan]Total files scrambled:[/cyan] {scrambled_count}")
        
        # Display the comprehensive report
        display_rename_report(rename_log)
        
        return 0
    
    else:
        # Original rename mode
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
                'proceed',
                message="Ready to start processing?",
                default=True
            ),
        ]
        
        try:
            answers = inquirer.prompt(questions)
            if not answers or not answers['proceed']:
                console.print("\n[yellow]Operation cancelled by user[/yellow]")
                return 1
            
            # Process the user's choices
            directory = Path(answers['directory'])
            recursive = answers['scope'] == 'recursive'
            skip_renamed = answers['renamed_files'] == 'skip'
            clear_cache = answers['cache'] == 'clear'
            selected_types = set(answers['file_types'])
            
            # Parse max_size with error handling
            try:
                max_size = float(answers['max_size'])
            except ValueError:
                console.print("[yellow]Invalid max size value, using default of 25MB[/yellow]")
                max_size = 25.0
            
            if clear_cache and os.path.exists(CACHE_FILE):
                os.remove(CACHE_FILE)
                console.print("[yellow]Cache cleared[/yellow]")
                
            # Configure file types to process based on user selection
            global IMAGE_EXTENSIONS, TEXT_EXTENSIONS, DOCUMENT_EXTENSIONS, ARCHIVE_EXTENSIONS
            from cleanupx import config
            if 'images' not in selected_types:
                config.IMAGE_EXTENSIONS = set()
            if 'text' not in selected_types:
                config.TEXT_EXTENSIONS = set()
            if 'documents' not in selected_types:
                config.DOCUMENT_EXTENSIONS = set()
            if 'archives' not in selected_types:
                config.ARCHIVE_EXTENSIONS = set()
                
            console.print(Panel(
                f"[bold]Processing directory:[/bold] {directory}\n"
                f"[bold]Recursive:[/bold] {'Yes' if recursive else 'No'}\n"
                f"[bold]Skip renamed:[/bold] {'Yes' if skip_renamed else 'No'}\n"
                f"[bold]Maximum file size:[/bold] {max_size}MB\n"
                f"[bold]Selected file types:[/bold] {', '.join(selected_types) or 'None - no files will be processed'}",
                title="Processing Configuration",
                border_style="cyan"
            ))
            
            # Import process_directory here to avoid circular imports
            from cleanupx.main import process_directory
            
            with console.status("[bold green]Processing files...", spinner="dots") as status:
                stats = process_directory(directory, recursive=recursive, skip_renamed=skip_renamed, max_size_mb=max_size)
            
            console.print(Panel(
                f"[bold]Total files processed:[/bold] {stats['total']}\n"
                f"[bold]Images processed:[/bold] {stats['images']}\n"
                f"[bold]Text files processed:[/bold] {stats['text']}\n"
                f"[bold]Documents processed:[/bold] {stats['documents']}\n"
                f"[bold]Files skipped:[/bold] {stats['skipped']}\n"
                f"[bold]Files skipped (too large):[/bold] {stats.get('skipped_large', 0)}\n"
                f"[bold]Files failed:[/bold] {stats['failed']}",
                title="[bold green]Processing Complete![/bold green]",
                border_style="green"
            ))
            
            # Display comprehensive rename report
            rename_log = load_rename_log()
            display_rename_report(rename_log)
            
            return 0
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
            return 1
        except Exception as e:
            console.print(f"\n[bold red]Error: {e}[/bold red]")
            return 1
