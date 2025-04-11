"""
CleanupX command line interface.
"""

import argparse
import logging
import sys
from pathlib import Path

from cleanupx.core.processor import FileProcessor
from cleanupx.core.config import DEFAULT_EXTENSIONS, PROTECTED_PATTERNS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description='CleanupX - File organization and cleanup tool')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up and organize files')
    cleanup_parser.add_argument('directory', help='Directory to process')
    cleanup_parser.add_argument('--recursive', '-r', action='store_true', help='Process directories recursively')
    cleanup_parser.add_argument('--max-size', type=int, help='Maximum file size in MB to process')
    
    # Citations command
    citations_parser = subparsers.add_parser('citations', help='Manage citations')
    citations_parser.add_argument('directory', help='Directory to process')
    citations_parser.add_argument('--recursive', '-r', action='store_true', help='Process directories recursively')
    
    # Snippets command
    snippets_parser = subparsers.add_parser('snippets', help='Manage code snippets')
    snippets_parser.add_argument('directory', help='Directory to process')
    snippets_parser.add_argument('--recursive', '-r', action='store_true', help='Process directories recursively')
    
    # Organize command
    organize_parser = subparsers.add_parser('organize', help='Organize files')
    organize_parser.add_argument('directory', help='Directory to process')
    organize_parser.add_argument('--recursive', '-r', action='store_true', help='Process directories recursively')
    
    # Dedupe command
    dedupe_parser = subparsers.add_parser('dedupe', help='Deduplicate files')
    dedupe_parser.add_argument('directory', help='Directory to process')
    dedupe_parser.add_argument('--recursive', '-r', action='store_true', help='Process directories recursively')
    
    # Scramble command
    scramble_parser = subparsers.add_parser('scramble', help='Scramble file names')
    scramble_parser.add_argument('directory', help='Directory to process')
    scramble_parser.add_argument('--recursive', '-r', action='store_true', help='Process directories recursively')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Generate test documents')
    test_parser.add_argument('directory', help='Directory to process')
    test_parser.add_argument('--recursive', '-r', action='store_true', help='Process directories recursively')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        directory = Path(args.directory)
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            sys.exit(1)
            
        processor = FileProcessor()
        
        if args.command == 'cleanup':
            processor.process_directory(
                directory,
                recursive=args.recursive,
                max_size=args.max_size
            )
        elif args.command == 'citations':
            # Handle citations
            pass
        elif args.command == 'snippets':
            # Handle snippets
            pass
        elif args.command == 'organize':
            # Handle organization
            pass
        elif args.command == 'dedupe':
            # Handle deduplication
            pass
        elif args.command == 'scramble':
            # Handle scrambling
            pass
        elif args.command == 'test':
            # Handle test generation
            pass
            
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 