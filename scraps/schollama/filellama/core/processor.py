"""Core file processing module."""

import logging
import shutil
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from .content_extractor import ContentExtractor
from .metadata_enricher import MetadataEnricher
from .filename_generator import FilenameGenerator
from ..utils.exceptions import ProcessingError
from ..utils.logging import get_logger

class FileProcessor:
    """Processes academic files for intelligent renaming."""

    SUPPORTED_EXTENSIONS = {
        'document': ['.pdf', '.txt', '.doc', '.docx', '.rtf', '.odt'],
        'presentation': ['.ppt', '.pptx', '.odp'],
        'spreadsheet': ['.xls', '.xlsx', '.ods'],
        'image': ['.jpg', '.jpeg', '.png', '.tiff', '.bmp'],
        'archive': ['.zip', '.tar.gz', '.rar']
    }

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        model_name: str = "schollama",
        backup_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize the file processor.
        
        Args:
            ollama_base_url: Base URL for Ollama API (used by Ollama client)
            model_name: Name of the LLM model to use
            backup_dir: Directory for file backups
            logger: Optional logger instance
        """
        self.backup_dir = backup_dir
        self.logger = logger or get_logger(__name__)
        self.ollama_base_url = ollama_base_url
        self.model_name = model_name
        
        # Initialize components
        self.content_extractor = ContentExtractor()
        self.metadata_enricher = MetadataEnricher(logger=self.logger)
        self.filename_generator = FilenameGenerator()

    def is_supported_file(self, file_path: Path) -> bool:
        """Check if file type is supported.
        
        Args:
            file_path: Path to check
            
        Returns:
            bool: Whether file type is supported
        """
        ext = file_path.suffix.lower()
        return any(ext in exts for exts in self.SUPPORTED_EXTENSIONS.values())

    async def process_file(
        self,
        file_path: Path,
        dry_run: bool = False,
        create_backup: bool = True
    ) -> Dict[str, Any]:
        """Process a single file.
        
        Args:
            file_path: Path to the file to process
            dry_run: Whether to perform a dry run
            create_backup: Whether to create a backup of the file
            
        Returns:
            Dictionary containing processing results
            
        Raises:
            ProcessingError: If file processing fails
        """
        try:
            self.logger.info(f"Processing file: {file_path}")
            
            if not self.is_supported_file(file_path):
                raise ProcessingError(f"Unsupported file type: {file_path.suffix}")
            
            # Create backup if requested
            if create_backup and not dry_run:
                backup_path = self._create_backup(file_path)
                self.logger.info(f"Created backup: {backup_path}")
            
            # Extract content
            content = self.content_extractor.extract_text(file_path)
            
            # Initialize metadata with basic file info
            initial_metadata = {
                'filename': file_path.name,
                'extension': file_path.suffix,
                'size': file_path.stat().st_size,
                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            }
            
            # Enrich metadata
            try:
                metadata = self.metadata_enricher.enrich_metadata(content, initial_metadata)
            except Exception as e:
                self.logger.error(f"Failed to enrich metadata: {str(e)}")
                raise ProcessingError(f"Failed to enrich metadata: {str(e)}")
            
            # Generate new filename
            try:
                new_filename = self.filename_generator.generate_filename(metadata, file_path)
                new_path = file_path.parent / new_filename
                
                # Check if file already has correct name
                if file_path.name == new_filename:
                    self.logger.info("File already has correct name")
                    return {
                        "original_path": str(file_path),
                        "new_path": str(file_path),
                        "status": "unchanged",
                        "dry_run": dry_run,
                        "metadata": metadata
                    }
                
                # Rename file if not dry run
                if not dry_run:
                    try:
                        file_path.rename(new_path)
                        self.logger.info(f"Renamed to: {new_filename}")
                    except Exception as e:
                        raise ProcessingError(f"Failed to rename file: {str(e)}")
                
                return {
                    "original_path": str(file_path),
                    "new_path": str(new_path),
                    "status": "renamed" if not dry_run else "would rename",
                    "dry_run": dry_run,
                    "metadata": metadata
                }
            
            except Exception as e:
                raise ProcessingError(f"Failed to generate filename: {str(e)}")
            
        except Exception as e:
            raise ProcessingError(f"Failed to process {file_path}: {str(e)}")

    def _create_backup(self, file_path: Path) -> Path:
        """Create a backup of the file.
        
        Args:
            file_path: Path to file to backup
            
        Returns:
            Path to backup file
            
        Raises:
            ProcessingError: If backup fails
        """
        try:
            # Generate backup path
            if self.backup_dir:
                backup_dir = Path(self.backup_dir)
            else:
                backup_dir = file_path.parent / ".backups"
            
            # Create backup directory if needed
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique backup name with original extension
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Handle long filenames
            max_length = 240  # Leave room for timestamp and extension
            stem = file_path.stem
            if len(stem) > max_length:
                # Truncate the stem while preserving some meaningful parts
                parts = stem.split('_')
                if len(parts) > 1:
                    # Keep first and last part if multiple parts
                    stem = f"{parts[0][:100]}...{parts[-1][-20:]}"
                else:
                    # Simple truncation for single part
                    stem = f"{stem[:100]}...{stem[-20:]}"
            
            backup_path = backup_dir / f"{stem}_{timestamp}{file_path.suffix}"
            
            # Create backup
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"Created backup: {backup_path}")
            
            return backup_path
            
        except Exception as e:
            raise ProcessingError(f"Failed to create backup of {file_path}: {str(e)}")

    async def process_directory(
        self,
        directory: Path,
        file_pattern: str = "*.*",
        recursive: bool = True,
        dry_run: bool = False,
        create_backup: bool = True
    ) -> List[Dict]:
        """Process all matching files in a directory.
        
        Args:
            directory: Directory to process
            file_pattern: Glob pattern for files
            recursive: If True, process subdirectories
            dry_run: If True, don't actually rename
            create_backup: If True, create backups
            
        Returns:
            List of processing results
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            self.logger.info(f"Processing directory: {directory}")
            
            # Find all matching files
            if recursive:
                files = list(directory.rglob(file_pattern))
            else:
                files = list(directory.glob(file_pattern))
                
            # Filter for supported files
            files = [f for f in files if self.is_supported_file(f)]
                
            if not files:
                self.logger.warning(f"No matching files found in {directory}")
                return []
                
            self.logger.info(f"Found {len(files)} files to process")
            
            # Process each file
            results = []
            for file_path in files:
                try:
                    result = await self.process_file(
                        file_path=file_path,
                        dry_run=dry_run,
                        create_backup=create_backup
                    )
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {str(e)}")
                    results.append({
                        "original_path": str(file_path),
                        "error": str(e)
                    })
            
            return results
            
        except Exception as e:
            raise ProcessingError(f"Failed to process directory {directory}: {str(e)}") 