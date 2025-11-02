from typing import Dict, Any
from datetime import datetime

from .video_extractor import VideoExtractorAgent
from .content_analyzer import ContentAnalyzerAgent
from .question_generator import QuestionGeneratorAgent
from ..models.video_job import VideoJob
from ..core.database import SessionLocal
from ..core.websocket_manager import websocket_manager


class VideoWorkflow:
    def __init__(self):
        self.video_extractor = VideoExtractorAgent()
        self.content_analyzer = ContentAnalyzerAgent()
        self.question_generator = QuestionGeneratorAgent()

    async def process_video(self, job_id: int, video_url: str, processing_params: Dict[str, Any] = None):
        processing_params = processing_params or {}

        data = {
            "video_url": video_url,
            **processing_params
        }

        try:
            await self.mark_job_started(job_id)

            data = await self.video_extractor.run(job_id, data)
            data = await self.content_analyzer.run(job_id, data)
            data = await self.question_generator.run(job_id, data)
            await self.mark_job_completed(job_id)

        except Exception as e:
            await self.mark_job_failed(job_id, str(e))
            raise

    async def mark_job_started(self, job_id: int):
        db = SessionLocal()
        try:
            job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
            if job:
                job.status = "processing"
                job.progress = 0.0
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    async def mark_job_completed(self, job_id: int):
        db = SessionLocal()
        try:
            job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
            if job:
                job.status = "completed"
                job.completed_at = datetime.now()
                job.progress = 100.0
            db.commit()

            await websocket_manager.broadcast_to_job(job_id, {
                "type": "completion",
                "status": "completed",
                "message": "Video processing completed! Your results are ready.",
                "progress": 100.0
            })
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    async def mark_job_failed(self, job_id: int, error_message: str):
        db = SessionLocal()
        try:
            job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.completed_at = datetime.now()
                job.error_message = error_message
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()