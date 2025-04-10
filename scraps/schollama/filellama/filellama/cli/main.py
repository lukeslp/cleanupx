"""
Command-line interface for Reference Renamer.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
import sys

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.file_processor import FileProcessor
from ..core.content_extractor import ContentExtractor
from ..core.metadata_enricher import MetadataEnricher
from ..core.filename_generator import FilenameGenerator
from ..core.change_logger import ChangeLogger
from ..api.arxiv import ArxivAPI
from ..api.semantic_scholar import SemanticScholarAPI
from ..api.ollama import OllamaAPI
from ..utils.logging import setup_accessibility_logging, get_logger
from ..utils.exceptions import ReferenceRenamerError

console = Console()

@click.group()
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Set logging level"
)
@click.option(
    "--log-file",
    type=click.Path(),
    help="Log file path"
)
@click.option(
    "--accessible/--no-accessible",
    default=True,
    help="Enable accessibility features"
)
def cli(log_level: str, log_file: Optional[str], accessible: bool):
    """
    Reference Renamer - Standardize academic article filenames.
    
    This tool processes academic articles (PDF, TXT) and renames them using
    a standardized format based on metadata extracted from the content and
    verified through academic APIs.
    """
    # Set up logging
    level = getattr(logging, log_level.upper())
    logger = get_logger("reference_renamer", level=level)
    
    if log_file:
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        logger.addHandler(handler)
        
    if accessible:
        setup_accessibility_logging(logger, level)
        
@cli.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path)
)
@click.option(
    "--recursive/--no-recursive",
    default=True,
    help="Process subdirectories recursively"
)
@click.option(
    "--dry-run/--no-dry-run",
    default=False,
    help="Show changes without applying them"
)
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create backups before renaming"
)
@click.option(
    "--log-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("logs"),
    help="Directory for log files"
)
async def rename(
    directory: Path,
    recursive: bool,
    dry_run: bool,
    backup: bool,
    log_dir: Path
):
    """
    Rename files in DIRECTORY using standardized format.
    
    This command processes all supported files in the specified directory,
    extracts metadata, and renames them using the format:
    Author_Year_FiveWordTitle.ext
    """
    logger = get_logger(__name__)
    
    try:
        # Initialize components
        file_processor = FileProcessor(
            str(directory),
            recursive=recursive
        )
        content_extractor = ContentExtractor()
        metadata_enricher = MetadataEnricher(
            semantic_scholar_api=SemanticScholarAPI(),
            arxiv_api=ArxivAPI(),
            ollama_api=OllamaAPI()
        )
        filename_generator = FilenameGenerator()
        change_logger = ChangeLogger(log_dir)
        
        # Find files
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Scanning directory...", total=None)
            files = file_processor.scan_directory()
            progress.update(task, completed=True)
            
            if not files:
                console.print("[yellow]No files found to process[/yellow]")
                return
                
            console.print(f"Found {len(files)} files to process")
            
            # Process each file
            for file_path in progress.track(
                files,
                description="Processing files..."
            ):
                try:
                    # Validate file
                    if not file_processor.validate_file(file_path):
                        logger.warning(f"Skipping invalid file: {file_path}")
                        continue
                        
                    # Create backup if needed
                    if backup and not dry_run:
                        backup_path = file_processor.create_backup(file_path)
                        logger.info(f"Created backup: {backup_path}")
                        
                    # Extract content
                    content_data = content_extractor.extract_content(file_path)
                    
                    # Enrich metadata
                    metadata = await metadata_enricher.enrich_metadata(
                        content_data.get("metadata", {}),
                        content_data.get("text", "")
                    )
                    
                    # Generate new filename
                    new_filename = filename_generator.generate_filename(
                        metadata,
                        file_path.suffix
                    )
                    
                    # Ensure unique filename
                    new_path = directory / new_filename
                    if new_path.exists():
                        new_filename = filename_generator.generate_unique_filename(
                            new_filename,
                            directory
                        )
                        new_path = directory / new_filename
                        
                    # Apply changes
                    if dry_run:
                        console.print(
                            f"Would rename: {file_path.name} -> {new_filename}"
                        )
                    else:
                        file_path.rename(new_path)
                        change_logger.log_change(file_path, new_path, metadata)
                        console.print(
                            f"[green]Renamed:[/green] {file_path.name} -> {new_filename}"
                        )
                        
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
                    console.print(
                        f"[red]Error processing {file_path}: {str(e)}[/red]"
                    )
                    
            # Show summary
            if dry_run:
                console.print("\n[yellow]Dry run completed[/yellow]")
            else:
                citation_count = change_logger.get_citation_count()
                console.print(
                    f"\n[green]Processing completed[/green]. "
                    f"Added {citation_count} citations."
                )
                
    except ReferenceRenamerError as e:
        logger.error(str(e))
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        sys.exit(1)
        
@cli.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path)
)
@click.option(
    "--format",
    type=click.Choice(["bibtex", "csv"]),
    default="bibtex",
    help="Output format for citations"
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output file path"
)
async def citations(directory: Path, format: str, output: Optional[Path]):
    """
    Generate citations for files in DIRECTORY.
    
    This command processes files and generates a citation database without
    renaming the files.
    """
    logger = get_logger(__name__)
    
    try:
        # Initialize components
        file_processor = FileProcessor(str(directory))
        content_extractor = ContentExtractor()
        metadata_enricher = MetadataEnricher(
            semantic_scholar_api=SemanticScholarAPI(),
            arxiv_api=ArxivAPI(),
            ollama_api=OllamaAPI()
        )
        
        # Set up output
        if not output:
            output = directory / f"citations.{format}"
            
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Find files
            task = progress.add_task("Scanning directory...", total=None)
            files = file_processor.scan_directory()
            progress.update(task, completed=True)
            
            if not files:
                console.print("[yellow]No files found to process[/yellow]")
                return
                
            console.print(f"Found {len(files)} files to process")
            
            # Process files
            citations = []
            for file_path in progress.track(
                files,
                description="Extracting citations..."
            ):
                try:
                    # Extract content
                    content_data = content_extractor.extract_content(file_path)
                    
                    # Enrich metadata
                    metadata = await metadata_enricher.enrich_metadata(
                        content_data.get("metadata", {}),
                        content_data.get("text", "")
                    )
                    
                    citations.append(metadata)
                    
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
                    console.print(
                        f"[red]Error processing {file_path}: {str(e)}[/red]"
                    )
                    
            # Write citations
            if format == "bibtex":
                from ..utils.citations import write_bibtex
                write_bibtex(citations, output)
            else:
                from ..utils.citations import write_csv
                write_csv(citations, output)
                
            console.print(
                f"\n[green]Citations written to {output}[/green]"
            )
            
    except ReferenceRenamerError as e:
        logger.error(str(e))
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        sys.exit(1)
        
def main():
    """Entry point for the CLI."""
    # Use asyncio.run for async commands
    asyncio.run(cli()) 