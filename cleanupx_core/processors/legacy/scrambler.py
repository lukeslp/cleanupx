#!/usr/bin/env python3
"""
scramble.py - A utility for scrambling filenames or generating sample files in a directory.

This utility provides an interactive command-line interface to perform two main operations:
1. Scramble Filenames: Randomizes the names of all files within a chosen directory while preserving file extensions.
2. Generate Sample Files: Populates a chosen directory with sample files spanning multiple file types,
   including images, documents, archives, audio, video, web files, source code, and disk images,
   with content tailored to each format.

Usage:
    Run the script and follow the interactive prompts to select the desired operation.
"""

import os
import sys
import random
import string
from pathlib import Path
import inquirer
from rich.console import Console
from rich.progress import Progress
import zipfile
import gzip

console = Console()

def scramble_directory() -> None:
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
    if not answers or not answers.get('confirm'):
        console.print("[yellow]Operation cancelled.[/yellow]")
        return
    target_dir = Path(answers['directory'])
    files = list(target_dir.glob('*'))
    if not files:
        console.print("[yellow]No files found in directory.[/yellow]")
        return
    console.print(f"[cyan]Found {len(files)} files to rename in {target_dir}[/cyan]")
    rename_log: list[tuple[str, str]] = []
    with Progress() as progress:
        task = progress.add_task("[green]Scrambling filenames...", total=len(files))
        for file_path in files:
            if file_path.is_file():
                random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                new_name = f"{random_name}{file_path.suffix}"
                new_path = file_path.parent / new_name
                while new_path.exists():
                    random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                    new_name = f"{random_name}{file_path.suffix}"
                    new_path = file_path.parent / new_name
                try:
                    file_path.rename(new_path)
                    rename_log.append((str(file_path), str(new_path)))
                    console.print(f"Renamed: {file_path.name} → {new_name}")
                except Exception as e:
                    console.print(f"[bold red]Error renaming {file_path.name}: {e}[/bold red]")
            progress.update(task, advance=1)
    log_path = target_dir / "scramble_rename_log.txt"
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("Original Name,New Name\n")
            for original, new in rename_log:
                f.write(f"{original},{new}\n")
        console.print(f"[green]Rename log saved to {log_path}[/green]")
    except Exception as e:
        console.print(f"[bold red]Error saving rename log: {e}[/bold red]")
    console.print(f"[green]Successfully scrambled {len(rename_log)} filenames![/green]")

def generate_sample_files() -> None:
    questions = [
        inquirer.Path(
            'directory',
            message="Select directory to populate with sample files",
            path_type=inquirer.Path.DIRECTORY,
            exists=True
        ),
        inquirer.Text(
            'files_per_ext',
            message="How many sample files per file type (default 3)?",
            default="3"
        ),
    ]
    answers = inquirer.prompt(questions)
    if not answers:
        console.print("[yellow]Operation cancelled.[/yellow]")
        return
    target_dir = Path(answers['directory'])
    try:
        files_per_ext = int(answers['files_per_ext'])
    except ValueError:
        console.print("[yellow]Invalid number provided, defaulting to 3 sample files per extension.[/yellow]")
        files_per_ext = 3
    sample_extensions = [
        ".jpg", ".png", ".gif", ".heic", ".docx", ".pptx", ".zip", ".gz",
        ".txt", ".pdf", ".csv", ".json", ".xml", ".mp3", ".mp4", ".avi",
        ".mkv", ".html", ".css", ".js", ".py", ".rb", ".java", ".c",
        ".cpp", ".sh", ".bat", ".iso"
    ]
    total_files = len(sample_extensions) * files_per_ext
    console.print(f"[cyan]Generating {total_files} sample files in {target_dir}[/cyan]")
    generated_files: list[str] = []
    sample_image_bytes = {
        ".jpg": b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9',
        ".png": b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDAT\x08\xd7c\x00\x01\x00\x00\x05\x00\x01\x0d\n,\x89\x00\x00\x00\x00IEND\xaeB`\x82',
        ".gif": b'GIF89a\x01\x00\x01\x00\x80\xff\x00\xff\xff\xff\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;',
        ".heic": b'\x00\x00\x00\x18ftypheic\x00\x00\x00\x00heic'
    }
    
    def create_sample_file(new_path: Path, ext: str) -> None:
        try:
            if ext in sample_image_bytes:
                with open(new_path, "wb") as f:
                    f.write(sample_image_bytes[ext])
            elif ext in {".zip", ".docx", ".pptx"}:
                with zipfile.ZipFile(new_path, 'w') as zf:
                    zf.writestr("dummy.txt", f"This is a dummy file inside the {ext} archive.")
            elif ext == ".gz":
                with gzip.open(new_path, 'wb') as f:
                    f.write(f"Dummy content for {ext} file.".encode('utf-8'))
            elif ext == ".pdf":
                pdf_content = b"%PDF-1.4\n%Dummy PDF content\n%%EOF"
                with open(new_path, "wb") as f:
                    f.write(pdf_content)
            elif ext in {".mp3", ".mp4", ".avi", ".mkv", ".iso"}:
                content = f"Dummy binary content for {ext} file.".encode('utf-8')
                with open(new_path, "wb") as f:
                    f.write(content)
            else:
                with open(new_path, "w", encoding="utf-8") as f:
                    f.write(f"Sample content for {ext} file.")
        except Exception as e:
            raise Exception(f"Error creating {new_path.name}: {e}")
    
    with Progress() as progress:
        task = progress.add_task("[green]Generating sample files...", total=total_files)
        for ext in sample_extensions:
            for _ in range(files_per_ext):
                random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                new_name = f"{random_name}{ext}"
                new_path = target_dir / new_name
                while new_path.exists():
                    random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                    new_name = f"{random_name}{ext}"
                    new_path = target_dir / new_name
                try:
                    create_sample_file(new_path, ext)
                    generated_files.append(str(new_path))
                    console.print(f"Created: {new_name}")
                except Exception as e:
                    console.print(f"[bold red]Error creating {new_name}: {e}[/bold red]")
                progress.update(task, advance=1)
    console.print(f"[green]Successfully generated {len(generated_files)} sample files![/green]")

def interactive_cli() -> None:
    questions = [
        inquirer.List(
            'operation',
            message="Select operation",
            choices=['Scramble Filenames', 'Generate Sample Files']
        )
    ]
    answers = inquirer.prompt(questions)
    if not answers:
        console.print("[yellow]No operation selected. Exiting.[/yellow]")
        return
    operation = answers['operation']
    if operation == 'Scramble Filenames':
        scramble_directory()
    elif operation == 'Generate Sample Files':
        generate_sample_files()
    else:
        console.print("[red]Invalid operation selected.[/red]")

if __name__ == "__main__":
    interactive_cli()