import tempfile
import shutil
from typing import Dict, Any, Optional
from pathlib import Path

import yt_dlp
import whisper

from .base import VideoTutorAgent
from ..config import get_settings
from ..models.video_job import VideoJob
from ..core.database import SessionLocal

settings = get_settings()


class VideoExtractorAgent(VideoTutorAgent):
    def __init__(self):
        super().__init__("video_extractor")
        self.whisper_model: Optional[Any] = None
    
    def load_whisper_model(self):
        if self.whisper_model is None:
            self.whisper_model = whisper.load_model(settings.whisper_model)
        return self.whisper_model

    async def run(self, job_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        video_url = data.get("video_url")
        if not video_url:
            raise ValueError("No video_url provided in job data")

        temp_dir = Path(tempfile.mkdtemp(prefix="video_tutor_"))
        try:
            await self.update_job_progress(job_id, 10.0, "Extracting video metadata")
            metadata, audio_path = await self.extract_video_data(video_url, temp_dir)
            await self.update_video_metadata(job_id, metadata)
            await self.update_job_progress(job_id, 30.0, "Generating transcript with Whisper")
            await self.update_job_progress(job_id, 40.0, "Transcription in progress...")
            transcript = await self.generate_transcript(audio_path)
            await self.update_transcript(job_id, transcript)
            await self.update_job_progress(job_id, 50.0, "Video extraction completed")

            data.update({
                "video_metadata": metadata,
                "transcript": transcript,
                "temp_dir": str(temp_dir)
            })

            return data

        except Exception as e:
            await self.mark_job_failed(job_id, f"Video extraction failed: {str(e)}")
            raise
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def extract_video_data(self, video_url: str, temp_dir: Path) -> tuple[Dict[str, Any], Path]:
        audio_path = temp_dir / "audio.%(ext)s"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(audio_path),
            'extractaudio': True,
            'audioformat': 'wav',
            'audioquality': 192,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                duration = info.get('duration', 0)
                max_duration = settings.max_video_length_minutes * 60
                
                if duration > max_duration:
                    raise ValueError(f"Video too long: {duration/60:.1f} minutes (max: {settings.max_video_length_minutes} minutes)")
                
                ydl.download([video_url])
                audio_files = list(temp_dir.glob("audio.*"))
                if not audio_files:
                    raise ValueError("Audio file not found after download")
                
                actual_audio_path = audio_files[0]
                metadata = {
                    "title": info.get('title', 'Unknown'),
                    "duration": duration,
                    "thumbnail": info.get('thumbnail'),
                    "uploader": info.get('uploader', 'Unknown'),
                    "upload_date": info.get('upload_date'),
                    "view_count": info.get('view_count', 0),
                    "description": info.get('description', '')[:1000],
                    "video_id": info.get('id'),
                    "format": info.get('format_id')
                }
                return metadata, actual_audio_path
                
        except Exception as e:
            raise ValueError(f"Failed to process video: {str(e)}")
    
    async def generate_transcript(self, audio_path: Path) -> str:
        try:
            model = self.load_whisper_model()
            result = model.transcribe(str(audio_path))
            transcript = result["text"].strip()
            
            if not transcript:
                raise ValueError("Whisper returned empty transcript")
            
            return transcript
            
        except Exception as e:
            raise ValueError(f"Transcription failed: {str(e)}")
    
    async def update_video_metadata(self, job_id: int, metadata: Dict[str, Any]):
        db = SessionLocal()
        try:
            job = self._get_job(db, job_id)
            if job:
                job.video_title = metadata.get("title")
                job.video_duration = metadata.get("duration")
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    async def update_transcript(self, job_id: int, transcript: str):
        db = SessionLocal()
        try:
            job = self._get_job(db, job_id)
            if job:
                job.transcript = transcript
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

