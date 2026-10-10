"""Custom domain exceptions for bug detector."""


class BugDetectionException(Exception):
    """Base exception for all domain-specific errors."""
    pass


class StorageError(BugDetectionException):
    """Raised when a persistence or database operation fails."""
    pass


class RecordNotFoundError(StorageError):
    """Raised when a requested review record does not exist."""
    pass
