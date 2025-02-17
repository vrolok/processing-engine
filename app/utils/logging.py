import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict
from pythonjsonlogger import jsonlogger
from contextvars import ContextVar

from app.core.config import settings

# Context variables for request tracking
request_id: ContextVar[str] = ContextVar('request_id', default='')
user_id: ContextVar[str] = ContextVar('user_id', default='')

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter that adds additional fields and formatting.
    """
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['environment'] = settings.ENVIRONMENT
        
        # Add context variables if they exist
        req_id = request_id.get()
        if req_id:
            log_record['request_id'] = req_id
            
        usr_id = user_id.get()
        if usr_id:
            log_record['user_id'] = usr_id
        
        # Add caller information in development
        if settings.DEBUG:
            log_record['function'] = record.funcName
            log_record['module'] = record.module
            log_record['line'] = record.lineno
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)

class RequestIdFilter(logging.Filter):
    """
    Filter that adds request_id to log records.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True

def setup_logging() -> None:
    """
    Configure logging for the application.
    Sets up JSON logging with appropriate handlers and formatters.
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Create formatter
    formatter = CustomJsonFormatter(
        fmt='%(timestamp)s %(level)s %(name)s %(message)s',
        json_ensure_ascii=False
    )
    console_handler.setFormatter(formatter)
    
    # Add request ID filter
    console_handler.addFilter(RequestIdFilter())
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set third-party loggers to WARNING level
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.WARNING)
    
    # Create logger for our application
    app_logger = logging.getLogger('app')
    app_logger.setLevel(settings.LOG_LEVEL)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    """
    return logging.getLogger(f"app.{name}")

class LoggerContext:
    """
    Context manager for temporarily setting context variables in logs.
    """
    def __init__(self, **kwargs):
        self.context = kwargs
        self.tokens = {}

    def __enter__(self):
        for key, value in self.context.items():
            if key == 'request_id':
                self.tokens[key] = request_id.set(value)
            elif key == 'user_id':
                self.tokens[key] = user_id.set(value)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for key, token in self.tokens.items():
            if key == 'request_id':
                request_id.reset(token)
            elif key == 'user_id':
                user_id.reset(token)

def log_error(logger: logging.Logger, error: Exception, context: Dict[str, Any] = None) -> None:
    """
    Helper function to log errors with additional context.
    """
    error_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context or {}
    }
    
    logger.error(
        f"Error occurred: {error_data['error_type']}",
        extra={
            'error_details': error_data,
            'stack_trace': True
        },
        exc_info=error
    )

# Usage examples:
"""
# Initialize logging
setup_logging()

# Get a logger instance
logger = get_logger(__name__)

# Basic logging
logger.info("Processing started", extra={"job_id": "123"})

# Error logging with context
try:
    # Some code that might raise an exception
    raise ValueError("Invalid input")
except Exception as e:
    log_error(logger, e, {"job_id": "123"})

# Using context manager
with LoggerContext(request_id="req-123", user_id="user-456"):
    logger.info("Processing request")
"""