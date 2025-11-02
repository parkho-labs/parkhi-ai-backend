from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class VideoProcessingRequest(BaseModel):
    video_url: HttpUrl
    question_types: List[QuestionType] = Field(default=[QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE])
    difficulty_level: DifficultyLevel = Field(default=DifficultyLevel.INTERMEDIATE)
    num_questions: int = Field(default=10, ge=1, le=50)
    generate_summary: bool = Field(default=True)
    llm_provider: LLMProvider = Field(default=LLMProvider.OPENAI)


class JobStatusResponse(BaseModel):
    id: int
    status: JobStatus
    progress: float = Field(..., ge=0.0, le=100.0)
    created_at: datetime
    completed_at: Optional[datetime]
    video_url: str
    video_title: Optional[str]
    video_duration: Optional[int]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class ProcessingJobResponse(BaseModel):
    job_id: int
    status: JobStatus
    message: str
    estimated_duration_minutes: int
    websocket_url: str


class ProcessingResults(BaseModel):
    job_id: int
    status: JobStatus
    video_title: Optional[str]
    video_duration: Optional[int]
    processing_duration_seconds: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]


class SummaryResponse(BaseModel):
    summary: Optional[str]


class TranscriptResponse(BaseModel):
    transcript: Optional[str]


class WebSocketMessage(BaseModel):
    job_id: int
    message_type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobsListResponse(BaseModel):
    total: int
    jobs: List[JobStatusResponse]


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str
    timestamp: datetime
    environment: str
    uptime_check: str


class QuizQuestionResponse(BaseModel):
    question_id: str
    question: str
    type: str
    options: Optional[List[str]] = None
    context: Optional[str] = None
    max_score: int


class QuizResponse(BaseModel):
    questions: List[QuizQuestionResponse]
    total_questions: int
    max_score: int


class QuizSubmission(BaseModel):
    answers: Dict[str, str]