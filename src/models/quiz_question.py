from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func

from ..core.database import Base

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("content_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    type = Column(String, nullable=False)
    answer_config = Column(JSON, nullable=False)
    context = Column(Text, nullable=True)
    max_score = Column(Integer, nullable=False, default=10)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )