"""
File processing module for Reference Renamer.
Handles file discovery and content extraction.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import os

from ..utils.exceptions import FileProcessingError
from ..utils.logging import get_logger

class FileProcessor:
    """Handles file discovery and initial processing."""
    
    def __init__(
        self, 
        base_directory: str,
        supported_extensions: List[str] = ['.pdf', '.txt'],
        recursive: bool = True,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the file processor.
        
        Args:
            base_directory: Root directory to process
            supported_extensions: List of file extensions to process
            recursive: Whether to search subdirectories
            logger: Optional logger instance
        """
        self.base_directory = Path(base_directory)
        self.supported_extensions = supported_extensions
        self.recursive = recursive
        self.logger = logger or get_logger(__name__)
        
        if not self.base_directory.exists():
            raise FileProcessingError(f"Directory not found: {base_directory}")
        
    def scan_directory(self) -> List[Path]:
        """
        Scans directory for supported files.
        
        Returns:
            List[Path]: List of paths to supported files
            
        Raises:
            FileProcessingError: If directory scanning fails
        """
        try:
            self.logger.info(f"Scanning directory: {self.base_directory}")
            pattern = '**/*' if self.recursive else '*'
            files = []
            
            for ext in self.supported_extensions:
                found = list(self.base_directory.glob(f'{pattern}{ext}'))
                self.logger.debug(f"Found {len(found)} files with extension {ext}")
                files.extend(found)
                
            self.logger.info(f"Total files found: {len(files)}")
            return files
            
        except Exception as e:
            raise FileProcessingError(f"Error scanning directory: {str(e)}")
            
    def validate_file(self, file_path: Path) -> bool:
        """
        Validates if a file can be processed.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            bool: Whether the file is valid for processing
        """
        try:
            if not file_path.exists():
                self.logger.warning(f"File not found: {file_path}")
                return False
                
            if not file_path.is_file():
                self.logger.warning(f"Not a file: {file_path}")
                return False
                
            if file_path.suffix.lower() not in self.supported_extensions:
                self.logger.warning(f"Unsupported file type: {file_path}")
                return False
                
            # Check if file is readable
            try:
                file_path.open('rb').close()
            except Exception as e:
                self.logger.warning(f"File not readable: {file_path} - {str(e)}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating file {file_path}: {str(e)}")
            return False
            
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Gets basic information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dict containing:
                - name: Original filename
                - extension: File extension
                - size: File size in bytes
                - created: Creation timestamp
                - modified: Last modified timestamp
        """
        try:
            stats = file_path.stat()
            return {
                'name': file_path.name,
                'extension': file_path.suffix.lower(),
                'size': stats.st_size,
                'created': stats.st_ctime,
                'modified': stats.st_mtime
            }
        except Exception as e:
            raise FileProcessingError(f"Error getting file info: {str(e)}")
            
    def create_backup(self, file_path: Path) -> Path:
        """
        Creates a backup of a file before processing.
        
        Args:
            file_path: Path to the file to backup
            
        Returns:
            Path to the backup file
            
        Raises:
            FileProcessingError: If backup creation fails
        """
        try:
            backup_path = file_path.with_suffix(file_path.suffix + '.bak')
            self.logger.info(f"Creating backup: {backup_path}")
            
            import shutil
            shutil.copy2(file_path, backup_path)
            
            return backup_path
            
        except Exception as e:
            raise FileProcessingError(f"Error creating backup: {str(e)}")
            
    def restore_from_backup(self, backup_path: Path) -> bool:
        """
        Restores a file from its backup.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            bool: Whether restoration was successful
        """
        try:
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
                
            original_path = backup_path.with_suffix('')
            self.logger.info(f"Restoring from backup: {original_path}")
            
            import shutil
            shutil.move(backup_path, original_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error restoring from backup: {str(e)}")
            return False 