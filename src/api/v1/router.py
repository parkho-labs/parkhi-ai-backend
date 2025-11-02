from fastapi import APIRouter

from .endpoints import videos, websocket, quiz, auth

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(quiz.router, prefix="/videos/{video_id}/quiz", tags=["quiz"])
api_router.include_router(websocket.router, tags=["websocket"])