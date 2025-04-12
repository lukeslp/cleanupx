#!/usr/bin/env python3
"""
scramble.py - A utility to scramble filenames in a directory.
This script allows users to select a directory and randomize all filenames within it,
while preserving file extensions.
"""

import os
import sys
import random
import string
from pathlib import Path
import inquirer
from rich.console import Console
from rich.progress import Progress

console = Console()

def scramble_directory():
    """
    Prompt user to select a directory and scramble all filenames within it.
    Files are renamed with random alphanumeric strings while preserving extensions.
    """
    # Prompt user to select directory
    questions = [
        inquirer.Path(
            'directory',
            message="Select directory to scramble filenames",
            path_type=inquirer.Path.DIRECTORY,
            exists=True
        ),
        inquirer.Confirm(
            'confirm',
            message="This will rename ALL files in the directory. Continue?",
            default=False
        )
    ]
    
    answers = inquirer.prompt(questions)
    
    if not answers or not answers['confirm']:
        console.print("[yellow]Operation cancelled.[/yellow]")
        return
    
    target_dir = Path(answers['directory'])
    files = list(target_dir.glob('*'))
    
    if not files:
        console.print("[yellow]No files found in directory.[/yellow]")
        return
    
    console.print(f"[cyan]Found {len(files)} files to rename in {target_dir}[/cyan]")
    
    # Create a rename log
    rename_log = []
    
    # Process files with progress bar
    with Progress() as progress:
        task = progress.add_task("[green]Scrambling filenames...", total=len(files))
        
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
                    rename_log.append((str(file_path), str(new_path)))
                    console.print(f"Renamed: {file_path.name} → {new_name}")
                except Exception as e:
                    console.print(f"[bold red]Error renaming {file_path.name}: {e}[/bold red]")
            
            progress.update(task, advance=1)
    
    # Save rename log
    log_path = target_dir / "scramble_rename_log.txt"
    try:
        with open(log_path, 'w') as f:
            f.write("Original Name,New Name\n")
            for original, new in rename_log:
                f.write(f"{original},{new}\n")
        console.print(f"[green]Rename log saved to {log_path}[/green]")
    except Exception as e:
        console.print(f"[bold red]Error saving rename log: {e}[/bold red]")
    
    console.print(f"[green]Successfully scrambled {len(rename_log)} filenames![/green]")

if __name__ == "__main__":
    scramble_directory()