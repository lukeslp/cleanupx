"""
Logging utilities for Reference Renamer.
Provides enhanced logging setup with accessibility features.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from rich.logging import RichHandler
import structlog
from datetime import datetime

def setup_logging(
    verbose: bool = False,
    log_file: Optional[Path] = None,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
) -> None:
    """Set up logging configuration.
    
    Args:
        verbose: If True, set log level to DEBUG
        log_file: Optional path to log file
        log_format: Format string for log messages
    """
    # Set up basic configuration
    level = logging.DEBUG if verbose else logging.INFO
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.render_to_log_kwargs,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Create handlers
    handlers = []
    
    # Console handler with rich formatting
    console_handler = RichHandler(
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        show_time=False,
        omit_repeated_times=False,
        show_level=True,
        show_path=True
    )
    console_handler.setLevel(level)
    handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=handlers,
        force=True
    )
    
    # Quiet some noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)

def setup_structlog() -> None:
    """
    Configures structlog for structured logging.
    """
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def create_rotating_log(
    name: str,
    log_dir: Path,
    max_bytes: int = 1024 * 1024,  # 1MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Creates a rotating log file that maintains size limits.
    
    Args:
        name: Logger name
        log_dir: Directory for log files
        max_bytes: Maximum size of each log file
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger with rotating handler
    """
    from logging.handlers import RotatingFileHandler
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Create log directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create rotating handler
    log_file = log_dir / f"{name}.log"
    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    
    # Set formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger

def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context
) -> None:
    """
    Logs a message with additional context.
    
    Args:
        logger: Logger to use
        level: Logging level
        message: Message to log
        **context: Additional context to include
    """
    # Add timestamp to context
    context['timestamp'] = datetime.now().isoformat()
    
    # Format context
    context_str = ' '.join(f"{k}={v}" for k, v in context.items())
    full_message = f"{message} [{context_str}]"
    
    # Log with appropriate level
    logger.log(level, full_message)

class AccessibleFormatter(logging.Formatter):
    """
    Custom formatter that provides screen reader friendly output.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def format(self, record: logging.LogRecord) -> str:
        # Add screen reader friendly markers
        level_marker = {
            logging.DEBUG: "Debug:",
            logging.INFO: "Info:",
            logging.WARNING: "Warning:",
            logging.ERROR: "Error:",
            logging.CRITICAL: "Critical:"
        }.get(record.levelno, "Log:")
        
        # Format the message
        formatted = super().format(record)
        
        # Add markers and structure
        structured = f"{level_marker} {formatted}"
        
        return structured

def setup_accessibility_logging(
    logger: logging.Logger,
    level: int = logging.INFO
) -> None:
    """
    Configures a logger with accessibility-focused formatting.
    
    Args:
        logger: Logger to configure
        level: Logging level
    """
    # Remove existing handlers
    logger.handlers = []
    
    # Create console handler with accessible formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(AccessibleFormatter(
        "%(asctime)s - %(name)s - %(message)s"
    ))
    console_handler.setLevel(level)
    logger.addHandler(console_handler)
    
    # Set logger level
    logger.setLevel(level) 