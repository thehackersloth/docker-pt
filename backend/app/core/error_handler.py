"""
Enhanced error handling and logging
"""

import logging
import traceback
from typing import Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Enhanced error handler"""
    
    @staticmethod
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions"""
        request_id = str(uuid.uuid4())
        
        logger.error(
            f"HTTP {exc.status_code} error",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code,
                "detail": exc.detail
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "request_id": request_id,
                "status_code": exc.status_code,
                "detail": exc.detail,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    def _sanitize_errors(errors):
        """Sanitize validation errors to ensure JSON serializable"""
        sanitized = []
        for error in errors:
            clean_error = {}
            for key, value in error.items():
                if isinstance(value, bytes):
                    clean_error[key] = value.decode('utf-8', errors='replace')
                elif isinstance(value, (list, tuple)):
                    clean_error[key] = [
                        v.decode('utf-8', errors='replace') if isinstance(v, bytes) else v
                        for v in value
                    ]
                else:
                    clean_error[key] = value
            sanitized.append(clean_error)
        return sanitized

    @staticmethod
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation exceptions"""
        request_id = str(uuid.uuid4())
        errors = ErrorHandler._sanitize_errors(exc.errors())

        logger.warning(
            f"Validation error",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "errors": errors
            }
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "request_id": request_id,
                "status_code": 422,
                "detail": "Validation error",
                "errors": errors,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions"""
        request_id = str(uuid.uuid4())
        
        logger.error(
            f"Unhandled exception: {str(exc)}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__,
                "traceback": traceback.format_exc()
            },
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "request_id": request_id,
                "status_code": 500,
                "detail": "Internal server error",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
