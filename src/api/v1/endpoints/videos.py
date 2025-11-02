import structlog
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from ...dependencies import get_video_job_repository, get_current_user_optional
from ..schemas import (
    VideoProcessingRequest,
    ProcessingJobResponse,
    JobStatusResponse,
    ProcessingResults,
    JobsListResponse,
    SummaryResponse,
    TranscriptResponse,
)
from ....config import get_settings
from ....services.video_processor import video_processor
from ....core.exceptions import JobNotFoundError, ValidationError
from ....models.user import User
from ....models.video_job import VideoJob

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter()




@router.post("/process", response_model=ProcessingJobResponse)
async def process_video(
    request: VideoProcessingRequest,
    background_tasks: BackgroundTasks,
    repo = Depends(get_video_job_repository),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> ProcessingJobResponse:
    try:
        # Check if job already exists for this video URL
        existing_job = repo.find_by_url(str(request.video_url))
        
        if existing_job:
            logger.info(
                "Returning existing job for video URL",
                job_id=existing_job.id,
                video_url=str(request.video_url),
                existing_status=existing_job.status
            )
            
            return ProcessingJobResponse(
                job_id=existing_job.id,
                status=existing_job.status,
                message=f"Job already exists with status: {existing_job.status}",
                estimated_duration_minutes=5,
                websocket_url=f"ws://localhost:{settings.api_port}/ws/jobs/{existing_job.id}"
            )
        
        # Create new job if none exists
        user_id = current_user.id if current_user else None
        job = repo.create_job(str(request.video_url), user_id=user_id)
        
        processing_params = {
            "question_types": request.question_types,
            "difficulty_level": request.difficulty_level,
            "num_questions": request.num_questions,
            "generate_summary": request.generate_summary,
            "llm_provider": request.llm_provider
        }
        
        # Start background processing using FastAPI's BackgroundTasks
        logger.info("⏰ Adding background task", job_id=job.id, video_url=str(request.video_url))
        background_tasks.add_task(
            video_processor.process_video_background_sync,
            job.id,
            str(request.video_url),
            processing_params
        )

        logger.info(
            "✅ New video processing job created and started",
            job_id=job.id,
            video_url=str(request.video_url),
            question_types=request.question_types,
            difficulty=request.difficulty_level
        )
        
        return ProcessingJobResponse(
            job_id=job.id,
            status=job.status,
            message="Video processing job created and started successfully",
            estimated_duration_minutes=5,
            websocket_url=f"ws://localhost:{settings.api_port}/ws/jobs/{job.id}"
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create processing job", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create processing job")


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: int,
    repo = Depends(get_video_job_repository)
) -> JobStatusResponse:
    try:
        job = repo.get(job_id)
        if not job:
            raise JobNotFoundError(job_id)

        return JobStatusResponse(
            id=job.id,
            status=job.status,
            progress=job.progress,
            created_at=job.created_at,
            completed_at=job.completed_at,
            video_url=job.video_url,
            video_title=job.video_title,
            video_duration=job.video_duration,
            error_message=job.error_message
        )
        
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get job status", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve job status")


@router.get("/{job_id}/results", response_model=ProcessingResults)
async def get_job_results(
    job_id: int,
    repo = Depends(get_video_job_repository)
) -> ProcessingResults:
    try:
        job = repo.get(job_id)
        if not job:
            raise JobNotFoundError(job_id)

        if job.status != "completed":
            raise HTTPException(
                status_code=409,
                detail=f"Job not complete. Current status: {job.status}"
            )

        processing_duration = None
        if job.completed_at and job.created_at:
            processing_duration = int((job.completed_at - job.created_at).total_seconds())

        return ProcessingResults(
            job_id=job.id,
            status=job.status,
            video_title=job.video_title,
            video_duration=job.video_duration,
            processing_duration_seconds=processing_duration,
            created_at=job.created_at,
            completed_at=job.completed_at
        )
        
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job results", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve job results")


@router.get("/{job_id}/summary", response_model=SummaryResponse)
async def get_job_summary(
    job_id: int,
    repo = Depends(get_video_job_repository)
) -> SummaryResponse:
    try:
        job = repo.get(job_id)
        if not job:
            raise JobNotFoundError(job_id)

        if job.status != "completed":
            raise HTTPException(
                status_code=409,
                detail=f"Job not complete. Current status: {job.status}"
            )

        return SummaryResponse(summary=job.summary)

    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get summary", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve summary")


@router.get("/{job_id}/transcript", response_model=TranscriptResponse)
async def get_job_transcript(
    job_id: int,
    repo = Depends(get_video_job_repository)
) -> TranscriptResponse:
    try:
        job = repo.get(job_id)
        if not job:
            raise JobNotFoundError(job_id)

        if job.status != "completed":
            raise HTTPException(
                status_code=409,
                detail=f"Job not complete. Current status: {job.status}"
            )

        return TranscriptResponse(transcript=job.transcript)

    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get transcript", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve transcript")


@router.post("/{job_id}/cancel", response_model=JobStatusResponse)
async def cancel_job(
    job_id: int,
    repo = Depends(get_video_job_repository)
) -> JobStatusResponse:
    try:
        job = repo.get(job_id)
        
        if job.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job in {job.status} state"
            )

        job.status = "cancelled"
        job.error_message = "Job cancelled by user"
        repo.session.commit()
        
        return JobStatusResponse(
            id=job.id,
            status=job.status,
            progress=job.progress,
            created_at=job.created_at,
            completed_at=job.completed_at,
            video_url=job.video_url,
            video_title=job.video_title,
            video_duration=job.video_duration,
            error_message="Job cancelled by user"
        )
        
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel job", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to cancel job")


@router.get("/jobs", response_model=JobsListResponse)
async def get_jobs_list(
    limit: int = 50,
    offset: int = 0,
    repo = Depends(get_video_job_repository),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> JobsListResponse:
    """Get paginated list of processing jobs."""
    try:
        if current_user:
            jobs = repo.get_jobs_by_user(current_user.id, limit=limit, offset=offset)
            total_count = repo.session.query(VideoJob).filter(VideoJob.user_id == current_user.id).count()
        else:
            jobs = repo.get_all_jobs(limit=limit, offset=offset)
            total_count = repo.get_total_jobs_count()

        job_responses = []
        for job in jobs:
            job_responses.append(JobStatusResponse(
                id=job.id,
                status=job.status,
                progress=job.progress,
                created_at=job.created_at,
                completed_at=job.completed_at,
                video_url=job.video_url,
                video_title=job.video_title,
                video_duration=job.video_duration,
                error_message=job.error_message
            ))

        return JobsListResponse(
            total=total_count,
            jobs=job_responses
        )

    except Exception as e:
        logger.error("Failed to get jobs list", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve jobs list")


@router.get("/debug/jobs")
async def debug_jobs(repo = Depends(get_video_job_repository)):
    """Debug endpoint to list all jobs and their statuses."""
    try:
        # Get all jobs from database
        all_jobs = repo.get_all_jobs()

        jobs_info = []
        for job in all_jobs:
            jobs_info.append({
                "id": job.id,
                "video_url": job.video_url,
                "status": job.status,
                "progress": job.progress,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message
            })

        return {
            "total_jobs": len(jobs_info),
            "jobs": jobs_info
        }

    except Exception as e:
        logger.error("Failed to get debug job info", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get debug info")


@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    repo = Depends(get_video_job_repository)
):
    try:
        success = repo.delete_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found")

        logger.info("Job deleted successfully", job_id=job_id)
        return {"message": "Job deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete job", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete job")


@router.post("/{job_id}/retry", response_model=ProcessingJobResponse)
async def retry_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    repo = Depends(get_video_job_repository)
) -> ProcessingJobResponse:
    try:
        job = repo.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status != "failed":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry job with status: {job.status}. Only failed jobs can be retried."
            )

        # Reset job to pending state
        success = repo.reset_job_for_retry(job_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to reset job for retry")

        # Reuse existing processing logic
        background_tasks.add_task(
            video_processor.process_video_async,
            job_id,
            job.video_url
        )

        logger.info("Job retry started", job_id=job_id, video_url=job.video_url)

        return ProcessingJobResponse(
            job_id=job_id,
            status="pending",
            message="Job retry started successfully",
            estimated_duration_minutes=5,
            websocket_url=f"ws://localhost:8000/ws/jobs/{job_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retry job", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retry job")