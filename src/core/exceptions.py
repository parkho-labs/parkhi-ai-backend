"""Simplified exception hierarchy for the application following KISS principles."""

from typing import Optional, Dict, Any


class VideoTutorError(Exception):
    """Base exception for all video tutor errors."""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ValidationError(VideoTutorError):
    """Input validation and data integrity errors."""
    pass


class JobNotFoundError(VideoTutorError):
    """Job not found in database."""

    def __init__(self, job_id: int):
        super().__init__(
            message=f"Job {job_id} not found",
            error_code="JOB_NOT_FOUND",
            details={"job_id": job_id}
        )


class ProcessingError(VideoTutorError):
    """All video processing related errors (transcription, analysis, generation, etc.)."""
    pass