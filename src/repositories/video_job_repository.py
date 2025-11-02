from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.sql import func
import json

from ..models.video_job import VideoJob, JobStatus

class VideoJobRepository:

    def __init__(self, session: Session):
        self.session = session

    def create_job(self, video_url: str, user_id: Optional[int] = None) -> VideoJob:
        job = VideoJob(
            video_url=video_url,
            user_id=user_id,
            status=JobStatus.PENDING.value,
            progress=0.0
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get(self, job_id: int) -> Optional[VideoJob]:
        return self.session.query(VideoJob).filter(VideoJob.id == job_id).first()

    def find_by_url(self, video_url: str) -> Optional[VideoJob]:
        return (
            self.session.query(VideoJob)
            .filter(VideoJob.video_url == video_url)
            .order_by(desc(VideoJob.created_at))
            .first()
        )

    def update_progress(self, job_id: int, progress: float, status: str = None):
        job = self.get(job_id)
        if job:
            job.progress = progress
            if status:
                job.status = status
            self.session.commit()

    def update_video_metadata(self, job_id: int, title: str = None, duration: int = None):
        job = self.get(job_id)
        if job:
            if title:
                job.video_title = title
            if duration:
                job.video_duration = duration
            self.session.commit()

    def update_transcript(self, job_id: int, transcript: str):
        job = self.get(job_id)
        if job:
            job.transcript = transcript
            self.session.commit()

    def update_summary(self, job_id: int, summary: str):
        job = self.get(job_id)
        if job:
            job.summary = summary
            self.session.commit()

    def mark_completed(self, job_id: int):
        job = self.get(job_id)
        if job:
            job.status = JobStatus.COMPLETED.value
            job.progress = 100.0
            job.completed_at = func.now()
            self.session.commit()

    def mark_failed(self, job_id: int, error_message: str):
        job = self.get(job_id)
        if job:
            job.status = JobStatus.FAILED.value
            job.error_message = error_message
            job.completed_at = func.now()
            self.session.commit()

    def mark_processing(self, job_id: int):
        job = self.get(job_id)
        if job:
            job.status = JobStatus.PROCESSING.value
            self.session.commit()

    def get_all_jobs(self, limit: int = 50, offset: int = 0) -> List[VideoJob]:
        return (
            self.session.query(VideoJob)
            .order_by(desc(VideoJob.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_jobs_by_user(self, user_id: int, limit: int = 50, offset: int = 0) -> List[VideoJob]:
        return (
            self.session.query(VideoJob)
            .filter(VideoJob.user_id == user_id)
            .order_by(desc(VideoJob.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_total_jobs_count(self) -> int:
        return self.session.query(VideoJob).count()

    def delete_job(self, job_id: int) -> bool:
        job = self.get(job_id)
        if job:
            self.session.delete(job)
            self.session.commit()
            return True
        return False

    def reset_job_for_retry(self, job_id: int) -> bool:
        job = self.get(job_id)
        if job and job.status == JobStatus.FAILED.value:
            job.status = JobStatus.PENDING.value
            job.progress = 0.0
            job.error_message = None
            job.completed_at = None
            job.transcript = None
            job.summary = None
            self.session.commit()
            return True
        return False