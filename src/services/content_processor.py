import asyncio
import structlog
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
import threading

from ..agents.content_workflow import ContentWorkflow
from ..config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class ContentProcessorService:
    def __init__(self):
        self.workflow = ContentWorkflow()
        self.executor = ThreadPoolExecutor(max_workers=settings.max_concurrent_jobs)
        self.running_jobs = set()

    def process_content_background_sync(self, job_id: int):
        logger.info("Content processing background sync started", job_id=job_id)

        def run_in_thread():
            logger.info("Content processing thread started", job_id=job_id)
            try:
                asyncio.run(self.process_content_background(job_id))
            except Exception as e:
                logger.error("Content processing thread failed", job_id=job_id, error=str(e), exc_info=True)

        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        logger.info("Content processing thread spawned", job_id=job_id, thread_id=thread.ident)

    async def process_content_background(self, job_id: int):
        logger.info("Starting content processing", job_id=job_id)

        if job_id in self.running_jobs:
            logger.warning("Job already running", job_id=job_id)
            return

        self.running_jobs.add(job_id)

        try:
            logger.info("Calling workflow.process_content", job_id=job_id)
            await self.workflow.process_content(job_id)
            logger.info("Content processing completed successfully", job_id=job_id)
        except Exception as e:
            logger.error("Content processing failed", job_id=job_id, error=str(e), exc_info=True)
        finally:
            self.running_jobs.discard(job_id)
            logger.info("Job removed from running jobs", job_id=job_id)

    def is_job_running(self, job_id: int) -> bool:
        return job_id in self.running_jobs

    def get_running_jobs_count(self) -> int:
        return len(self.running_jobs)


content_processor = ContentProcessorService()