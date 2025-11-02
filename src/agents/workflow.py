from typing import Dict, Any
from datetime import datetime
import structlog

from .video_extractor import VideoExtractorAgent
from .content_analyzer import ContentAnalyzerAgent
from .question_generator import QuestionGeneratorAgent
from ..models.video_job import VideoJob
from ..core.database import SessionLocal
from ..core.websocket_manager import websocket_manager
from ..parsers.content_parser_factory import ContentParserFactory

logger = structlog.get_logger(__name__)


class VideoWorkflow:
    def __init__(self):
        self.video_extractor = VideoExtractorAgent()
        self.content_analyzer = ContentAnalyzerAgent()
        self.question_generator = QuestionGeneratorAgent()
        self.parser_factory = ContentParserFactory()

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

    async def process_content(self, job_id: int, source_path: str, processing_params: Dict[str, Any] = None):
        """
        Process multimodal content using parsers instead of video extractor.

        Args:
            job_id: The job ID
            source_path: Path to file or URL
            processing_params: Processing configuration including input_type
        """
        processing_params = processing_params or {}
        input_type = processing_params.get("input_type")

        logger.info("🚀 Starting content processing workflow", job_id=job_id, input_type=input_type)

        try:
            await self.mark_job_started(job_id)

            # Stage 1: Parse content using appropriate parser
            logger.info("📄 Stage 1: Parsing content", job_id=job_id, input_type=input_type)
            await self.update_job_progress(job_id, 10.0, f"Parsing {input_type} content...")

            parser = self.parser_factory.get_parser(input_type)
            if not parser:
                raise ValueError(f"No parser available for input type: {input_type}")

            # Parse the content
            parse_result = await parser.parse(source_path)
            if not parse_result.success:
                raise ValueError(f"Failed to parse content: {parse_result.error}")

            logger.info("✅ Content parsed successfully", job_id=job_id, content_length=len(parse_result.content))

            # Store the parsed content as "transcript" for compatibility with existing agents
            await self.update_job_transcript(job_id, parse_result.content)
            await self.update_job_title(job_id, parse_result.title)

            # Stage 2: Analyze content (reuse existing content analyzer)
            logger.info("🧠 Stage 2: Analyzing content", job_id=job_id)
            await self.update_job_progress(job_id, 40.0, "Analyzing content structure...")

            data = {
                "transcript": parse_result.content,
                "video_title": parse_result.title,
                "metadata": parse_result.metadata,
                **processing_params
            }

            data = await self.content_analyzer.run(job_id, data)

            # Stage 3: Generate questions (reuse existing question generator)
            logger.info("❓ Stage 3: Generating questions", job_id=job_id)
            await self.update_job_progress(job_id, 70.0, "Generating quiz questions...")

            data = await self.question_generator.run(job_id, data)

            await self.mark_job_completed(job_id)
            logger.info("✅ Content processing workflow completed", job_id=job_id)

        except Exception as e:
            logger.error("❌ Content processing workflow failed", job_id=job_id, error=str(e))
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

    async def update_job_progress(self, job_id: int, progress: float, message: str = None):
        """Update job progress and send WebSocket notification."""
        db = SessionLocal()
        try:
            job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
            if job:
                job.progress = progress
            db.commit()

            # Send WebSocket update
            websocket_data = {
                "type": "progress",
                "progress": progress,
                "status": "processing"
            }
            if message:
                websocket_data["message"] = message

            await websocket_manager.broadcast_to_job(job_id, websocket_data)

        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    async def update_job_transcript(self, job_id: int, content: str):
        """Update job with parsed content."""
        db = SessionLocal()
        try:
            job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
            if job:
                job.transcript = content
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    async def update_job_title(self, job_id: int, title: str):
        """Update job with content title."""
        if not title:
            return

        db = SessionLocal()
        try:
            job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
            if job:
                job.video_title = title  # Reuse video_title field for content title
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()