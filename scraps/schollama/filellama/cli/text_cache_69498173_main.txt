"""Command line interface for the filellama tool."""

import sys
import asyncio
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..core.processor import FileProcessor
from ..utils.exceptions import ProcessingError
from ..utils.logging import setup_logging

# Initialize rich console
console = Console()

def print_version(ctx, param, value):
    """Print version information."""
    if not value or ctx.resilient_parsing:
        return
    import pkg_resources
    version = pkg_resources.get_distribution('filellama').version
    click.echo(f'filellama version {version}')
    ctx.exit()

@click.group()
@click.option('--version', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True, help='Show version information.')
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output.')
@click.option('-c', '--config', type=click.Path(exists=True, dir_okay=False),
              help='Path to configuration file.')
def cli(verbose: bool, config: Optional[str]):
    """Intelligent academic file management and organization tool.
    
    FileLlama helps you manage academic papers by:
    - Extracting metadata from PDFs
    - Generating standardized filenames
    - Organizing files intelligently
    """
    # Setup logging
    setup_logging(verbose=verbose)

@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('-r', '--recursive', is_flag=True, help='Process directories recursively.')
@click.option('-p', '--pattern', default='*.pdf', help='File pattern to match.')
@click.option('-d', '--dry-run', is_flag=True, help='Show what would be done without making changes.')
@click.option('-b', '--backup/--no-backup', default=True, help='Create backups before renaming.')
@click.option('--backup-dir', type=click.Path(), help='Directory for backups.')
@click.option('--ollama-url', default='http://localhost:11434', help='Ollama API URL.')
@click.option('--model', default='schollama', help='LLM model to use.')
def process(
    path: str,
    recursive: bool,
    pattern: str,
    dry_run: bool,
    backup: bool,
    backup_dir: Optional[str],
    ollama_url: str,
    model: str
):
    """Process academic files for intelligent renaming.
    
    PATH can be a single file or directory.
    
    Examples:
        filellama process paper.pdf
        filellama process papers/ -r
        filellama process papers/ -r --dry-run
    """
    try:
        # Initialize processor
        processor = FileProcessor(
            ollama_base_url=ollama_url,
            model_name=model,
            backup_dir=Path(backup_dir) if backup_dir else None
        )
        
        # Create progress display
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Process path
            path_obj = Path(path)
            task = progress.add_task(
                description=f"Processing {'directory' if path_obj.is_dir() else 'file'} {path}...",
                total=None
            )
            
            # Run async processing
            if path_obj.is_file():
                results = [asyncio.run(processor.process_file(
                    file_path=path_obj,
                    dry_run=dry_run,
                    create_backup=backup
                ))]
            else:
                results = asyncio.run(processor.process_directory(
                    directory=path_obj,
                    file_pattern=pattern,
                    recursive=recursive,
                    dry_run=dry_run,
                    create_backup=backup
                ))
            
            progress.update(task, completed=True)
        
        # Display results
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Original")
        table.add_column("New Name")
        table.add_column("Status")
        
        for result in results:
            if 'error' in result:
                table.add_row(
                    result['original_path'],
                    '',
                    f"[red]Error: {result['error']}"
                )
            else:
                status_color = {
                    "unchanged": "blue",
                    "renamed": "green",
                    "would rename": "yellow"
                }.get(result['status'], "white")
                
                table.add_row(
                    result['original_path'],
                    result['new_path'],
                    f"[{status_color}]{result['status'].title()}"
                )
        
        console.print(table)
        
    except ProcessingError as e:
        console.print(f"[red]Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}")
        sys.exit(1)

@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('-r', '--recursive', is_flag=True, help='Process directories recursively.')
@click.option('-p', '--pattern', default='*.pdf', help='File pattern to match.')
def citations(path: str, recursive: bool, pattern: str):
    """Extract and manage citations from academic papers.
    
    PATH can be a single file or directory.
    
    Examples:
        filellama citations paper.pdf
        filellama citations papers/ -r
    """
    console.print("[yellow]Citation management coming soon!")

@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('-r', '--recursive', is_flag=True, help='Process directories recursively.')
@click.option('-p', '--pattern', default='*.pdf', help='File pattern to match.')
def extract(path: str, recursive: bool, pattern: str):
    """Extract metadata and content from academic papers.
    
    PATH can be a single file or directory.
    
    Examples:
        filellama extract paper.pdf
        filellama extract papers/ -r
    """
    console.print("[yellow]Metadata extraction coming soon!")

@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('-r', '--recursive', is_flag=True, help='Process directories recursively.')
@click.option('-p', '--pattern', default='*.pdf', help='File pattern to match.')
def organize(path: str, recursive: bool, pattern: str):
    """Organize academic papers into a logical directory structure.
    
    PATH can be a single file or directory.
    
    Examples:
        filellama organize paper.pdf
        filellama organize papers/ -r
    """
    console.print("[yellow]File organization coming soon!")

def main():
    """Entry point for the FileLlama CLI."""
    cli()

if __name__ == '__main__':
    main() 