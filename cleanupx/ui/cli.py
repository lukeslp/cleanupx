#!/usr/bin/env python3
"""
Command-line interface for CleanupX.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

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

from cleanupx.ui.interactive import interactive_mode, scramble_directory
from cleanupx.utils.cache import load_rename_log
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

def parse_args(args: List[str]) -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Args:
        args: List of command-line arguments
        
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Process images, text files, and documents to generate descriptions and rename them."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        help="Directory containing files to process",
        default="inbox"
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Process subdirectories recursively"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Process all files, including previously renamed ones"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache before processing"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    parser.add_argument(
        "--scramble", "-s",
        action="store_true",
        help="Scramble filenames with random strings instead of content-based renaming"
    )
    parser.add_argument(
        "--max-size",
        type=float,
        default=25.0,
        help="Skip files larger than this size in MB (default: 25MB)"
    )
    parser.add_argument(
        "--images-only",
        action="store_true",
        help="Process only image files"
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Process only text files"
    )
    parser.add_argument(
        "--documents-only",
        action="store_true",
        help="Process only document files"
    )
    parser.add_argument(
        "--archives-only",
        action="store_true",
        help="Process only archive files"
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip processing of image files"
    )
    parser.add_argument(
        "--skip-text",
        action="store_true",
        help="Skip processing of text files"
    )
    parser.add_argument(
        "--skip-documents",
        action="store_true",
        help="Skip processing of document files"
    )
    parser.add_argument(
        "--skip-archives",
        action="store_true",
        help="Skip processing of archive files"
    )
    
    # Add new options for deduplication
    parser.add_argument(
        "--dedupe",
        action="store_true",
        help="Find and remove duplicate files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes (works with --dedupe)"
    )
    parser.add_argument(
        "--auto-delete",
        action="store_true",
        help="Automatically delete duplicates without confirmation (use with --dedupe)"
    )
    
    # Add options for directory summaries
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Generate or update a directory summary without processing files"
    )
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Suggest organization improvements based on directory summary"
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip generating directory summaries after processing"
    )
    
    # Add option for interactive organization preferences
    parser.add_argument(
        "--ask-preferences", "-p",
        action="store_true",
        help="Prompt for organization preferences before processing"
    )
    
    # Add options for citations and hidden summary
    parser.add_argument(
        "--citations",
        action="store_true",
        help="Display APA citations extracted from documents in the directory"
    )
    
    parser.add_argument(
        "--update-citations",
        action="store_true",
        help="Scan all documents and update the citations file"
    )
    
    parser.add_argument(
        "--hidden-summary",
        action="store_true",
        help="Display the hidden directory summary"
    )
    
    parser.add_argument(
        "--update-hidden-summary",
        action="store_true",
        help="Update the hidden directory summary file (.cleanupx)"
    )
    
    parser.add_argument(
        "--reorganize",
        action="store_true",
        help="Interactively reorganize files based on suggestions"
    )
    
    # Add export options for reports
    parser.add_argument(
        "--export-citations",
        action="store_true",
        help="Export citation information to a CITATIONS.md file"
    )
    
    parser.add_argument(
        "--export-summary",
        action="store_true",
        help="Export directory summary to a DIRECTORY_SUMMARY.md file"
    )
    
    # Add batch processing option
    parser.add_argument(
        "--batch-size",
        type=int,
        default=0,
        help="Number of files to process before asking for confirmation (0 = all files)"
    )
    
    # Add categorization options
    parser.add_argument(
        "--categorize",
        action="store_true",
        help="Categorize files based on content analysis"
    )
    
    parser.add_argument(
        "--move-to-categories",
        action="store_true",
        help="Move files to folders based on their categories"
    )
    
    # Add PDF naming options
    parser.add_argument(
        "--citation-style-pdfs",
        action="store_true",
        help="Use citation-style naming for PDFs (based on author, title, year)"
    )
    
    parser.add_argument(
        "--normal-pdf-naming",
        action="store_true",
        help="Use normal content-based naming for PDFs (default)"
    )
    
    return parser.parse_args(args)

def run_cli(args: Optional[List[str]] = None) -> int:
    """
    Run the command-line interface.
    
    Args:
        args: Optional list of command-line arguments (uses sys.argv if None)
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Use sys.argv if no args provided
    if args is None:
        args = sys.argv[1:]
    
    # Check if no arguments were provided
    if len(args) == 0:
        return interactive_mode()
    
    parsed_args = parse_args(args)
    
    # Interactive mode
    if parsed_args.interactive:
        return interactive_mode()
    
    # Ensure console is available for UI
    if not RICH_AVAILABLE:
        print("Rich library not available. Install with: pip install rich")
        return 1
        
    console = Console()
    
    directory = Path(parsed_args.directory)
    if not directory.is_dir():
        console.print(f"[bold red]Error: {directory} is not a valid directory[/bold red]")
        return 1
    
    # Update hidden summary only mode
    if parsed_args.update_hidden_summary:
        from cleanupx.utils.hidden_summary import update_hidden_summary
        try:
            console.print(f"[bold cyan]Updating hidden directory summary (.cleanupx) for {directory}[/bold cyan]")
            summary = update_hidden_summary(directory, full_analysis=True)
            console.print("[bold green]Hidden directory summary updated successfully[/bold green]")
            
            # If requested, also display the summary
            if parsed_args.hidden_summary:
                display_hidden_summary(directory, console)
                
            return 0
        except Exception as e:
            console.print(f"[bold red]Error updating hidden summary: {e}[/bold red]")
            return 1
    
    # Citation update only mode
    if parsed_args.update_citations:
        try:
            console.print(f"[bold cyan]Updating citation information for {directory}[/bold cyan]")
            
            # Import necessary modules
            from cleanupx.processors.citation import process_file_for_citations, get_citation_stats
            from cleanupx.config import DOCUMENT_EXTENSIONS
            
            # Find all document files
            document_files = []
            if parsed_args.recursive:
                for root, _, filenames in os.walk(directory):
                    for filename in filenames:
                        file_path = Path(root) / filename
                        if file_path.suffix.lower() in DOCUMENT_EXTENSIONS:
                            document_files.append(file_path)
            else:
                document_files = [f for f in directory.iterdir() 
                                if f.is_file() and f.suffix.lower() in DOCUMENT_EXTENSIONS]
            
            console.print(f"Found {len(document_files)} document files to process")
            
            # Process each document file
            with console.status("[bold cyan]Processing documents for citations..."):
                for file_path in document_files:
                    try:
                        console.print(f"Processing {file_path.name}...", end="\r")
                        process_file_for_citations(file_path)
                    except Exception as e:
                        console.print(f"[yellow]Error processing {file_path.name}: {e}[/yellow]")
            
            # Get updated stats
            stats = get_citation_stats(directory)
            
            # Display results
            console.print("")
            console.print("[bold green]Citation update complete![/bold green]")
            console.print(f"[cyan]Total citations:[/cyan] {stats.get('total', 0)}")
            console.print(f"[cyan]References:[/cyan] {stats.get('reference', 0)}")
            console.print(f"[cyan]DOI citations:[/cyan] {stats.get('doi', 0)}")
            console.print(f"[cyan]In-text citations:[/cyan] {stats.get('in_text', 0)}")
            
            # If requested, also display the citations
            if parsed_args.citations:
                display_citations(directory, console)
                
            # If requested, export to markdown
            if parsed_args.export_citations:
                from cleanupx.processors.citation import save_markdown_citations
                md_file = save_markdown_citations(directory)
                if md_file:
                    console.print(f"[bold green]Exported citations to {md_file}[/bold green]")
                    
            return 0
        except Exception as e:
            console.print(f"[bold red]Error updating citations: {e}[/bold red]")
            return 1
    
    # Summary-only mode
    if parsed_args.summary:
        from cleanupx.utils.directory_summary import update_directory_summary
        console.print(f"[bold cyan]Generating directory summary for {directory}[/bold cyan]")
        
        # Include user preferences if requested
        include_prefs = parsed_args.ask_preferences
        summary = update_directory_summary(directory, include_user_prefs=include_prefs)
        
        # Also update the hidden summary
        try:
            from cleanupx.utils.hidden_summary import update_hidden_summary
            update_hidden_summary(directory, full_analysis=True)
            console.print("[green]Hidden directory summary (.cleanupx) also updated[/green]")
        except Exception as e:
            console.print(f"[yellow]Note: Hidden summary update failed: {e}[/yellow]")
        
        console.print("[bold green]Directory summary updated[/bold green]")
        
        # If requested, export to markdown
        if parsed_args.export_summary:
            try:
                from cleanupx.utils.directory_summary import export_summary_to_markdown
                md_file = export_summary_to_markdown(directory, summary)
                console.print(f"[bold green]Exported summary to {md_file}[/bold green]")
            except Exception as e:
                console.print(f"[yellow]Failed to export summary to markdown: {e}[/yellow]")
        
        return 0
    
    # Suggestion-only mode
    if parsed_args.suggest:
        from cleanupx.utils.directory_summary import get_directory_summary
        console.print(f"[bold cyan]Analyzing directory {directory} for organization suggestions[/bold cyan]")
        
        # Include user preferences if requested
        include_prefs = parsed_args.ask_preferences
        summary = get_directory_summary(directory, include_user_prefs=include_prefs)
        
        suggestions = summary.get("suggestions", [])
        if suggestions:
            console.print("[bold yellow]Organization suggestions:[/bold yellow]")
            
            # Sort suggestions by priority if available
            try:
                suggestions.sort(key=lambda x: {
                    "high": 0,
                    "medium": 1,
                    "normal": 2,
                    "low": 3
                }.get(x.get("priority", "normal"), 2))
            except:
                pass  # If sorting fails, just use original order
                
            for suggestion in suggestions:
                suggestion_type = suggestion.get("type", "")
                reason = suggestion.get("reason", "")
                
                # Add priority indication if available
                priority_str = ""
                if "priority" in suggestion:
                    priority_str = f"[{suggestion['priority']}] "
                
                # Add indicator if this was user-requested or from project plan
                source = ""
                if suggestion.get("user_requested", False):
                    source = "[User preference] "
                elif suggestion.get("project_plan", False):
                    source = "[From PROJECT_PLAN.md] "
                    
                console.print(f"[cyan]- {suggestion_type}:[/cyan] {priority_str}{source}{reason}")
        else:
            console.print("[green]No suggestions available - directory seems well organized[/green]")
        return 0
    
    # Citations display mode
    if parsed_args.citations:
        display_citations(directory, console)
        return 0
    
    # Hidden summary display mode
    if parsed_args.hidden_summary:
        display_hidden_summary(directory, console)
        return 0
    
    # Deduplication mode
    if parsed_args.dedupe:
        from cleanupx.main import dedupe_files
        console.print(f"[bold cyan]Scanning for duplicates in {directory}[/bold cyan]")
        
        # Confirm if not in dry-run mode and auto-delete is enabled
        if parsed_args.auto_delete and not parsed_args.dry_run:
            if INQUIRER_AVAILABLE:
                confirm = inquirer.confirm(
                    message=f"This will automatically delete duplicate files in {directory}. Continue?",
                    default=False
                )
                if not confirm:
                    console.print("[yellow]Operation cancelled by user[/yellow]")
                    return 1
            else:
                confirm = input(f"This will automatically delete duplicate files in {directory}. Continue? (y/N): ").lower().strip() == 'y'
                if not confirm:
                    console.print("Operation cancelled by user")
                    return 1
                
        result = dedupe_files(
            directory=directory,
            recursive=parsed_args.recursive,
            auto_delete=parsed_args.auto_delete,
            dry_run=parsed_args.dry_run
        )
        
        console.print(f"\n[bold green]Deduplication complete![/bold green]")
        console.print(f"[cyan]Duplicate groups found:[/cyan] {result.get('duplicate_groups', 0)}")
        console.print(f"[cyan]Total duplicates:[/cyan] {result.get('total_duplicates', 0)}")
        
        if parsed_args.auto_delete and not parsed_args.dry_run:
            console.print(f"[cyan]Files deleted:[/cyan] {result.get('deleted', 0)}")
        elif parsed_args.dry_run:
            console.print(f"[cyan]Files that would be deleted:[/cyan] {result.get('total_duplicates', 0)}")
            console.print("[yellow]Dry run completed. Use --auto-delete without --dry-run to actually delete files.[/yellow]")
        else:
            console.print("[yellow]No files were deleted. Use --auto-delete to remove duplicates.[/yellow]")
            
        return 0
    
    # Scramble mode
    if parsed_args.scramble:
        if INQUIRER_AVAILABLE:
            confirm = inquirer.confirm(
                message=f"This will rename ALL files in {directory} with random names. Continue?",
                default=False
            )
            if not confirm:
                console.print("[yellow]Operation cancelled by user[/yellow]")
                return 1
        else:
            console.print("[yellow]Inquirer not installed. Proceeding without confirmation.[/yellow]")
        
        rename_log = load_rename_log()
        scrambled_count = scramble_directory(directory, rename_log)
        
        console.print(f"\n[bold green]Scrambling complete![/bold green]")
        console.print(f"[cyan]Total files scrambled:[/cyan] {scrambled_count}")
        
        # Display the comprehensive report
        display_rename_report(rename_log)
        
        return 0
    
    # Normal renaming mode
    if parsed_args.clear_cache and os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        console.print("[yellow]Cache cleared[/yellow]")
    
    # Configure file type filtering
    from cleanupx import config
    file_type_selection = []
    
    # "Only" flags have priority over "skip" flags
    if parsed_args.images_only or parsed_args.text_only or parsed_args.documents_only or parsed_args.archives_only:
        # If any "only" flag is set, first empty all extensions
        config.IMAGE_EXTENSIONS = set()
        config.TEXT_EXTENSIONS = set()
        config.DOCUMENT_EXTENSIONS = set()
        config.ARCHIVE_EXTENSIONS = set()
        
        # Then selectively restore based on flags
        if parsed_args.images_only:
            config.IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.heif'}
            file_type_selection.append("images")
        if parsed_args.text_only:
            config.TEXT_EXTENSIONS = {'.txt', '.md', '.markdown', '.rst', '.text', '.log', '.csv', '.tsv', '.json', '.xml', '.yaml', '.yml', '.html', '.htm', '.py', '.zip'}
            file_type_selection.append("text")
        if parsed_args.documents_only:
            config.DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.doc', '.ppt', '.pptx'}
            file_type_selection.append("documents")
        if parsed_args.archives_only:
            config.ARCHIVE_EXTENSIONS = {'.zip', '.tar', '.tgz', '.tar.gz', '.rar'}
            file_type_selection.append("archives")
    else:
        # Default is to process all types, then selectively skip
        file_type_selection = ["images", "text", "documents", "archives"]
        if parsed_args.skip_images:
            config.IMAGE_EXTENSIONS = set()
            file_type_selection.remove("images")
        if parsed_args.skip_text:
            config.TEXT_EXTENSIONS = set()
            file_type_selection.remove("text")
        if parsed_args.skip_documents:
            config.DOCUMENT_EXTENSIONS = set()
            file_type_selection.remove("documents")
        if parsed_args.skip_archives:
            config.ARCHIVE_EXTENSIONS = set()
            file_type_selection.remove("archives")
    
    # Pass the batch size option to the processing function
    if parsed_args.directory and not (parsed_args.dedupe or parsed_args.scramble or 
                                     parsed_args.summary or parsed_args.suggest or 
                                     parsed_args.citations or parsed_args.hidden_summary or
                                     parsed_args.reorganize):
        console.print(Panel(
            f"[bold]Processing directory:[/bold] {directory}\n"
            f"[bold]Recursive:[/bold] {'Yes' if parsed_args.recursive else 'No'}\n"
            f"[bold]Skip renamed:[/bold] {'No' if parsed_args.force else 'Yes'}\n"
            f"[bold]Ask for preferences:[/bold] {'Yes' if parsed_args.ask_preferences else 'No'}\n"
            f"[bold]File types:[/bold] {', '.join(file_type_selection) or 'None - no files will be processed'}\n"
            f"[bold]Update hidden summary:[/bold] {'No' if parsed_args.no_summary else 'Yes'}\n"
            f"[bold]Update citations:[/bold] Yes for document files\n"
            f"[bold]Batch size:[/bold] {'All files' if parsed_args.batch_size == 0 else parsed_args.batch_size}\n"
            f"[bold]PDF naming:[/bold] {'Citation style' if parsed_args.citation_style_pdfs else 'Content-based'}",
            title="Processing Configuration",
            border_style="cyan"
        ))
        
    # Ask for confirmation before processing
    if INQUIRER_AVAILABLE:
        confirm = inquirer.confirm(
            message=f"Ready to process files in {directory}. Continue?",
            default=True
        )
        if not confirm:
            console.print("[yellow]Operation cancelled by user[/yellow]")
            return 1
    
    # Import process_directory here to avoid circular imports
    from cleanupx.main import process_directory
    
    # Process the directory
    stats = process_directory(
        directory=directory,
        recursive=parsed_args.recursive,
        skip_renamed=not parsed_args.force,
        max_size_mb=parsed_args.max_size,
        update_summary=not parsed_args.no_summary,
        include_user_prefs=parsed_args.ask_preferences,
        batch_size=parsed_args.batch_size,
        citation_style_pdfs=parsed_args.citation_style_pdfs
    )
    
    console.print(f"\n[bold green]Processing complete![/bold green]")
    console.print(f"[cyan]Files processed:[/cyan] {stats.get('total', 0)}")
    console.print(f"[cyan]Images renamed:[/cyan] {stats.get('images', 0)}")
    console.print(f"[cyan]Text files renamed:[/cyan] {stats.get('text', 0)}")
    console.print(f"[cyan]Documents renamed:[/cyan] {stats.get('documents', 0)}")
    console.print(f"[cyan]Files skipped:[/cyan] {stats.get('skipped', 0)}")
    console.print(f"[cyan]Files failed:[/cyan] {stats.get('failed', 0)}")
    
    # Display the comprehensive report
    rename_log = load_rename_log()
    display_rename_report(rename_log)
    
    # Show organization suggestions if available and summaries were generated
    if not parsed_args.no_summary:
        from cleanupx.utils.directory_summary import get_directory_summary
        summary = get_directory_summary(directory, include_user_prefs=False)  # Don't prompt again if already asked
        
        suggestions = summary.get("suggestions", [])
        if suggestions:
            console.print("\n[bold yellow]Organization suggestions:[/bold yellow]")
            for suggestion in suggestions:
                suggestion_type = suggestion.get("type", "")
                reason = suggestion.get("reason", "")
                console.print(f"[cyan]- {suggestion_type}:[/cyan] {reason}")
            
            console.print("\nRun with --suggest to see detailed suggestions or --dedupe to find duplicates")
    
    # Reorganize mode
    if parsed_args.reorganize:
        try:
            from cleanupx.utils.hidden_summary import get_reorganization_suggestions, create_suggested_structure
            console.print(f"[bold cyan]Reorganization Suggestions for {directory}[/bold cyan]")
            
            # Get the reorganization suggestions
            suggestions = get_reorganization_suggestions(directory)
            
            if not suggestions:
                console.print("[yellow]No reorganization suggestions available for this directory.[/yellow]")
                return 0
            
            # Display suggestions and let user choose
            for i, suggestion in enumerate(suggestions):
                suggestion_type = suggestion.get("type", "")
                reason = suggestion.get("reason", "")
                priority = suggestion.get("priority", "normal").upper()
                console.print(f"[cyan]{i+1}. {suggestion_type}[/cyan] [{priority}]: {reason}")
            
            # Ask user which suggestion to implement
            if INQUIRER_AVAILABLE:
                choices = [f"{i+1}. {s.get('type')} - {s.get('reason')[:40]}..." for i, s in enumerate(suggestions)]
                choices.append("Cancel - don't reorganize")
                
                questions = [
                    inquirer.List(
                        "choice",
                        message="Which suggestion would you like to implement?",
                        choices=choices
                    )
                ]
                
                answers = inquirer.prompt(questions)
                if not answers or answers["choice"] == "Cancel - don't reorganize":
                    console.print("[yellow]Operation cancelled by user[/yellow]")
                    return 0
                
                selected_index = int(answers["choice"].split(".")[0]) - 1
            else:
                console.print("\nEnter the number of the suggestion to implement (or 'q' to quit):")
                choice = input("> ").strip()
                if choice.lower() == 'q':
                    console.print("[yellow]Operation cancelled by user[/yellow]")
                    return 0
                
                try:
                    selected_index = int(choice) - 1
                    if selected_index < 0 or selected_index >= len(suggestions):
                        console.print("[bold red]Invalid choice[/bold red]")
                        return 1
                except ValueError:
                    console.print("[bold red]Invalid input[/bold red]")
                    return 1
            
            # Implement the selected suggestion
            selected = suggestions[selected_index]
            console.print(f"\n[bold cyan]Implementing suggestion: {selected.get('type')}[/bold cyan]")
            
            # Confirm before proceeding
            if INQUIRER_AVAILABLE:
                confirm = inquirer.confirm(
                    message=f"This will reorganize files in {directory}. Continue?",
                    default=False
                )
                if not confirm:
                    console.print("[yellow]Operation cancelled by user[/yellow]")
                    return 0
            else:
                confirm = input(f"This will reorganize files in {directory}. Continue? (y/N): ").lower().strip() == 'y'
                if not confirm:
                    console.print("[yellow]Operation cancelled by user[/yellow]")
                    return 0
            
            # Create the suggested structure
            success = create_suggested_structure(directory, selected)
            
            if success:
                console.print("[bold green]Reorganization complete![/bold green]")
                
                # Update the directory summary after reorganization
                from cleanupx.utils.directory_summary import update_directory_summary
                from cleanupx.utils.hidden_summary import update_hidden_summary
                update_directory_summary(directory)
                update_hidden_summary(directory, full_analysis=True)
            else:
                console.print("[bold red]Reorganization failed[/bold red]")
            
            return 0
        except Exception as e:
            console.print(f"[bold red]Error during reorganization: {e}[/bold red]")
            return 1
    
    # Add categorization functionality
    if parsed_args.categorize:
        try:
            from cleanupx.utils.categorization import categorize_files
            console.print(f"[bold cyan]Categorizing files in {directory}[/bold cyan]")
            
            categories = categorize_files(
                directory=directory,
                recursive=parsed_args.recursive
            )
            
            console.print(f"\n[bold green]Categorization complete![/bold green]")
            
            # Display category summary
            table = Table(title="File Categories")
            table.add_column("Category", style="cyan")
            table.add_column("Count", style="green")
            
            for category, files in categories.items():
                table.add_row(category, str(len(files)))
            
            console.print(table)
            
            # Option to move files to category folders
            if parsed_args.move_to_categories:
                from cleanupx.utils.categorization import move_to_category_folders
                
                if INQUIRER_AVAILABLE:
                    confirm = inquirer.confirm(
                        message=f"Move files to category folders in {directory}?",
                        default=False
                    )
                    if confirm:
                        move_to_category_folders(directory, categories)
                        console.print("[bold green]Files moved to category folders[/bold green]")
                else:
                    confirm = input(f"Move files to category folders in {directory}? (y/N): ").lower().strip() == 'y'
                    if confirm:
                        move_to_category_folders(directory, categories)
                        console.print("[bold green]Files moved to category folders[/bold green]")
            
        except Exception as e:
            console.print(f"[bold red]Error during categorization: {e}[/bold red]")
            return 1
    
    return 0

def display_citations(directory: Path, console: Console) -> None:
    """Display citations from a directory"""
    try:
        from cleanupx.processors.citation import generate_apa_citation_list, get_citation_stats
        console.print(f"[bold cyan]APA Citations from {directory}[/bold cyan]")
        
        # Get citation stats
        stats = get_citation_stats(directory)
        
        # Show summary table
        table = Table(title="Citation Summary")
        table.add_column("Type", style="cyan")
        table.add_column("Count", style="green")
        
        table.add_row("Total Citations", str(stats.get("total", 0)))
        table.add_row("Formal References", str(stats.get("reference", 0)))
        table.add_row("DOI Citations", str(stats.get("doi", 0)))
        table.add_row("In-text Citations", str(stats.get("in_text", 0)))
        
        console.print(table)
        console.print("")
        
        # Generate the APA citation list
        apa_list = generate_apa_citation_list(directory)
        
        # Display the citations
        if apa_list == "No citations found.":
            console.print("[yellow]No citations found in this directory.[/yellow]")
        else:
            console.print(Panel(apa_list, title="APA Citations", border_style="green"))
        
    except Exception as e:
        console.print(f"[bold red]Error displaying citations: {e}[/bold red]")

def display_hidden_summary(directory: Path, console: Console) -> None:
    """Display the hidden directory summary"""
    try:
        from cleanupx.utils.hidden_summary import get_hidden_summary
        console.print(f"[bold cyan]Hidden Directory Summary for {directory}[/bold cyan]")
        
        # Get the hidden summary
        summary = get_hidden_summary(directory)
        
        # Display key information
        console.print(f"[bold]Directory:[/bold] {summary.get('directory')}")
        console.print(f"[bold]Last updated:[/bold] {summary.get('updated')}")
        console.print(f"[bold]File count:[/bold] {summary.get('file_count')}")
        console.print(f"[bold]Directory count:[/bold] {summary.get('directory_count')}")
        
        # Display content analysis
        content = summary.get("content_analysis", {})
        if content.get("topics"):
            console.print("\n[bold cyan]Topics:[/bold cyan]")
            for topic in content.get("topics", []):
                console.print(f"- {topic}")
        
        if content.get("keywords"):
            console.print("\n[bold cyan]Keywords:[/bold cyan]")
            console.print(", ".join(content.get("keywords", [])))
        
        # Display organization suggestions
        suggestions = summary.get("organization", {}).get("suggestions", [])
        if suggestions:
            console.print("\n[bold yellow]Organization Suggestions:[/bold yellow]")
            for suggestion in suggestions:
                suggestion_type = suggestion.get("type", "")
                reason = suggestion.get("reason", "")
                priority = suggestion.get("priority", "")
                if priority:
                    priority = f"[{priority.upper()}] "
                console.print(f"[cyan]- {suggestion_type}:[/cyan] {priority}{reason}")
        
    except Exception as e:
        console.print(f"[bold red]Error displaying hidden summary: {e}[/bold red]")
