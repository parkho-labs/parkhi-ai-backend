import logging
import uuid
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ...core.exceptions import VideoTutorError

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        
        try:
            response = await call_next(request)
            
            if response.status_code == status.HTTP_404_NOT_FOUND:
                return self._handle_not_found(request, request_id)
                
            return response
            
        except VideoTutorError as exc:
            return self._handle_video_tutor_error(exc, request_id)
            
        except Exception as exc:
            return self._handle_unexpected_error(exc, request_id)
    
    def _handle_video_tutor_error(self, exc: VideoTutorError, request_id: str) -> JSONResponse:
        error_data = exc.to_dict()
        error_data["request_id"] = request_id
        
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(exc, (ValidationError, JobNotFoundError)):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, (RateLimitError, TimeoutError)):
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        
        logger.error(
            "Application error: %s", 
            error_data,
            exc_info=True,
            extra={"request_id": request_id}
        )
        
        return JSONResponse(
            status_code=status_code,
            content=error_data
        )
    
    def _handle_unexpected_error(self, exc: Exception, request_id: str) -> JSONResponse:
        error_data = {
            "request_id": request_id,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": {}
        }
        
        logger.critical(
            "Unexpected error: %s", 
            str(exc),
            exc_info=True,
            extra={"request_id": request_id}
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_data
        )
    
    def _handle_not_found(self, request: Request, request_id: str) -> JSONResponse:
        error_data = {
            "request_id": request_id,
            "error_code": "NOT_FOUND",
            "message": f"The requested resource {request.url} was not found",
            "details": {"path": str(request.url)}
        }
        
        logger.warning(
            "Resource not found: %s", 
            request.url,
            extra={"request_id": request_id}
        )
        
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_data
        )
