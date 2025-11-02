from typing import Optional, List
from sqlalchemy.orm import Session

from ..api.v1.schemas import FileProcessingResult, JobStatus
from ..repositories.content_job_repository import ContentJobRepository
from ..models.content_job import ContentJob


class DuplicateDetector:
    """
    Service for detecting duplicate file processing requests
    and creating appropriate 207 Multi-Status responses.
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.content_job_repo = ContentJobRepository(db_session)

    def check_file_processing_status(self, file_id: str) -> FileProcessingResult:
        """
        Check the current processing status of a file_id and return
        appropriate FileProcessingResult for 207 Multi-Status response.
        """
        existing_job = self.content_job_repo.find_existing_job_by_file_id(file_id)

        if not existing_job:
            # No existing job found - file can be processed
            return FileProcessingResult(
                file_id=file_id,
                job_id=None,
                status=JobStatus.PENDING,
                message="File ready for processing",
                estimated_duration_minutes=None,
                websocket_url=None
            )

        # Existing job found - determine response based on status
        if existing_job.status == "pending":
            return FileProcessingResult(
                file_id=file_id,
                job_id=existing_job.id,
                status=JobStatus.PENDING,
                message="File processing already queued",
                estimated_duration_minutes=5,
                websocket_url=f"ws://127.0.0.1:8080/ws/jobs/{existing_job.id}"
            )

        elif existing_job.status == "processing":
            return FileProcessingResult(
                file_id=file_id,
                job_id=existing_job.id,
                status=JobStatus.PROCESSING,
                message="File is currently being processed",
                estimated_duration_minutes=max(1, int((100 - existing_job.progress) / 20)),
                websocket_url=f"ws://127.0.0.1:8080/ws/jobs/{existing_job.id}"
            )

        elif existing_job.status == "completed":
            return FileProcessingResult(
                file_id=file_id,
                job_id=existing_job.id,
                status=JobStatus.COMPLETED,
                message="File has already been processed successfully",
                estimated_duration_minutes=0,
                websocket_url=None
            )

        elif existing_job.status == "failed":
            # For failed jobs, allow reprocessing by returning pending status
            return FileProcessingResult(
                file_id=file_id,
                job_id=None,
                status=JobStatus.PENDING,
                message="Previous processing failed - file ready for retry",
                estimated_duration_minutes=None,
                websocket_url=None
            )

        else:
            # Unknown status - treat as available for processing
            return FileProcessingResult(
                file_id=file_id,
                job_id=None,
                status=JobStatus.PENDING,
                message="File ready for processing",
                estimated_duration_minutes=None,
                websocket_url=None
            )

    def check_multiple_files(self, file_ids: List[str]) -> List[FileProcessingResult]:
        """
        Check processing status for multiple file_ids.
        Returns a list of FileProcessingResult for 207 Multi-Status response.
        """
        results = []
        for file_id in file_ids:
            result = self.check_file_processing_status(file_id)
            results.append(result)

        return results

    def can_process_file(self, file_id: str) -> bool:
        """
        Simple boolean check if a file can be processed (not currently processing).
        """
        result = self.check_file_processing_status(file_id)
        return result.status in [JobStatus.PENDING] and result.job_id is None

    def get_existing_job_for_file(self, file_id: str) -> Optional[ContentJob]:
        """
        Get the existing ContentJob for a file_id, if any.
        """
        return self.content_job_repo.find_existing_job_by_file_id(file_id)