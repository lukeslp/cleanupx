"""
Custom exceptions for Reference Renamer.
"""

class ReferenceRenamerError(Exception):
    """Base exception for Reference Renamer."""
    pass

class FileProcessingError(ReferenceRenamerError):
    """Raised when file processing fails."""
    pass

class ContentExtractionError(ReferenceRenamerError):
    """Raised when content extraction fails."""
    pass

class MetadataEnrichmentError(ReferenceRenamerError):
    """Raised when metadata enrichment fails."""
    pass

class FilenameGenerationError(ReferenceRenamerError):
    """Raised when filename generation fails."""
    pass

class LoggingError(ReferenceRenamerError):
    """Raised when logging operations fail."""
    pass

class APIError(ReferenceRenamerError):
    """Raised when API operations fail."""
    
    def __init__(self, message: str, api_name: str, status_code: int = None):
        """
        Initialize API error.
        
        Args:
            message: Error message
            api_name: Name of the API that failed
            status_code: Optional HTTP status code
        """
        self.api_name = api_name
        self.status_code = status_code
        super().__init__(f"{api_name} API Error: {message}" + 
                        (f" (Status: {status_code})" if status_code else ""))

class ConfigurationError(ReferenceRenamerError):
    """Raised when configuration is invalid."""
    pass

class ValidationError(ReferenceRenamerError):
    """Raised when validation fails."""
    pass

class FileLlamaError(Exception):
    """Base exception for all filellama errors."""
    pass

class ProcessingError(FileLlamaError):
    """Raised when file processing fails."""
    pass

class ExtractionError(FileLlamaError):
    """Raised when content extraction fails."""
    pass

class MetadataError(FileLlamaError):
    """Raised when metadata processing fails."""
    pass

class EnrichmentError(MetadataError):
    """Raised when metadata enrichment fails."""
    pass

class FilenameError(FileLlamaError):
    """Raised when filename generation fails."""
    pass

class ConfigError(FileLlamaError):
    """Raised when configuration is invalid."""
    pass

class APIError(FileLlamaError):
    """Raised when an API request fails."""
    pass

class ValidationError(FileLlamaError):
    """Raised when data validation fails."""
    pass 