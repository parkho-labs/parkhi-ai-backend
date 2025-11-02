import asyncio
import structlog
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
import threading

from ..agents.workflow import VideoWorkflow
from ..config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

class VideoProcessorService:

    def __init__(self):
        self.workflow = VideoWorkflow()
        self.executor = ThreadPoolExecutor(max_workers=settings.max_concurrent_jobs)
        self.running_jobs = set()

    def process_video_background_sync(self, job_id: int, video_url: str, processing_params: Dict[str, Any]):
        logger.info("🔧 process_video_background_sync called", job_id=job_id)

        def run_in_thread():
            logger.info("🧵 Thread started for job", job_id=job_id)
            try:
                asyncio.run(self.process_video_background(job_id, video_url, processing_params))
            except Exception as e:
                logger.error("🔥 Thread execution failed", job_id=job_id, error=str(e), exc_info=True)

        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        logger.info("✅ Thread spawned and started", job_id=job_id, thread_id=thread.ident)
    
    async def process_video_background(self, job_id: int, video_url: str, processing_params: Dict[str, Any]):
        logger.info("🚀 Starting background processing", job_id=job_id, video_url=video_url)

        if job_id in self.running_jobs:
            logger.warning("Job already running", job_id=job_id)
            return

        self.running_jobs.add(job_id)

        try:
            logger.info("📹 Calling workflow.process_video", job_id=job_id)
            await self.workflow.process_video(job_id, video_url, processing_params)
            logger.info("✅ Workflow completed successfully", job_id=job_id)
        except Exception as e:
            logger.error("❌ Background video processing failed", job_id=job_id, error=str(e), exc_info=True)
        finally:
            self.running_jobs.discard(job_id)
            logger.info("🏁 Job removed from running jobs", job_id=job_id)
    
    def start_processing(self, job_id: int, video_url: str, processing_params: Dict[str, Any] = None):
        processing_params = processing_params or {}
        asyncio.create_task(
            self.process_video_background(job_id, video_url, processing_params)
        )
        
    def is_job_running(self, job_id: int) -> bool:
        return job_id in self.running_jobs
    
    def get_running_jobs_count(self) -> int:
        return len(self.running_jobs)


video_processor = VideoProcessorService()