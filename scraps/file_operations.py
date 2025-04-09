import os
import shutil
import tempfile
import logging
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

def safe_rename(src: str, dst: str, backup: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Safely rename a file with optional backup creation.
    
    Args:
        src: Source file path
        dst: Destination file path
        backup: Whether to create a backup before renaming
        
    Returns:
        Tuple of (success: bool, backup_path: Optional[str])
        
    Raises:
        OSError: If the rename operation fails and cannot be recovered
    """
    src_path = Path(src)
    dst_path = Path(dst)
    
    if not src_path.exists():
        logger.error(f"Source file does not exist: {src}")
        return False, None
        
    if src_path == dst_path:
        logger.info(f"Source and destination are the same: {src}")
        return True, None
    
    backup_path = None
    
    try:
        # Create destination directory if it doesn't exist
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create backup if requested
        if backup and dst_path.exists():
            backup_path = str(dst_path) + ".bak"
            shutil.copy2(str(dst_path), backup_path)
            logger.info(f"Created backup at: {backup_path}")
        
        # Use atomic rename when possible (same filesystem)
        try:
            os.replace(str(src_path), str(dst_path))
            logger.info(f"Renamed {src} to {dst}")
            return True, backup_path
            
        # Fall back to copy + delete if atomic rename fails
        except OSError:
            logger.warning(f"Atomic rename failed, falling back to copy + delete for {src}")
            # Use temporary file for atomic copy
            temp_dir = dst_path.parent
            with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False) as tmp:
                shutil.copy2(str(src_path), tmp.name)
                os.replace(tmp.name, str(dst_path))
            os.unlink(str(src_path))
            logger.info(f"Completed copy + delete rename from {src} to {dst}")
            return True, backup_path
            
    except OSError as e:
        logger.error(f"Failed to rename {src} to {dst}: {str(e)}")
        # Try to restore backup if it exists
        if backup_path and os.path.exists(backup_path):
            try:
                os.replace(backup_path, str(dst_path))
                logger.info(f"Restored backup from {backup_path}")
            except OSError as restore_error:
                logger.error(f"Failed to restore backup: {str(restore_error)}")
        raise
        
def bulk_rename(file_pairs: list[Tuple[str, str]], backup: bool = True) -> list[Tuple[str, str, bool]]:
    """
    Safely rename multiple files with optional backups.
    
    Args:
        file_pairs: List of (source, destination) path tuples
        backup: Whether to create backups before renaming
        
    Returns:
        List of (source, destination, success) tuples
    """
    results = []
    for src, dst in file_pairs:
        try:
            success, _ = safe_rename(src, dst, backup=backup)
            results.append((src, dst, success))
        except OSError as e:
            logger.error(f"Failed to rename {src} to {dst}: {str(e)}")
            results.append((src, dst, False))
    return results 