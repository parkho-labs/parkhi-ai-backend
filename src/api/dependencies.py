import structlog
from typing import Generator, Optional
from fastapi import Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DatabaseError

from ..core.database import get_db as _get_db
from ..core.firebase import verify_firebase_token
from ..repositories.video_job_repository import VideoJobRepository
from ..repositories.quiz_repository import QuizRepository
from ..models.user import User

logger = structlog.get_logger(__name__)


def get_db() -> Generator[Session, None, None]:
    db = None
    try:
        db_gen = _get_db()
        db = next(db_gen)
        yield db
    except (OperationalError, DatabaseError) as e:
        logger.error("Database connection failed", error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable"
        )
    finally:
        if db:
            try:
                db.close()
            except Exception as e:
                logger.warning("Failed to close database connection", error=str(e))


async def log_request(request: Request):
    logger.info(
        "API request received",
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params),
        user_agent=request.headers.get("user-agent", "unknown"),
        remote_addr=request.client.host if request.client else "unknown",
    )


def get_video_job_repository(db: Session = Depends(get_db)) -> VideoJobRepository:
    return VideoJobRepository(db)


def get_quiz_repository(db: Session = Depends(get_db)) -> QuizRepository:
    return QuizRepository(db)


def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split("Bearer ")[1]
    firebase_data = verify_firebase_token(token)

    if not firebase_data:
        return None

    firebase_uid = firebase_data.get("uid")
    if not firebase_uid:
        return None

    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    return user