import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict
from pythonjsonlogger import jsonlogger
from contextvars import ContextVar
from app.core.config import settings

# Context variables for request tracking
request_id: ContextVar[str] = ContextVar('request_id', default='')
user_id: ContextVar[str] = ContextVar('user_id', default='')


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter that adds additional fields for structured logging.
    """
    def add_fields(
        self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        # Add timestamp with timezone awareness
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        log_record['level'] = record.levelname
        log_record['environment'] = settings.ENVIRONMENT

        # Add context variables if they exist
        req_id = request_id.get()
        if req_id:
            log_record['request_id'] = req_id
        usr_id = user_id.get()
        if usr_id:
            log_record['user_id'] = usr_id

        # Add caller information in development mode
        if settings.DEBUG:
            log_record['function'] = record.funcName
            log_record['module'] = record.module
            log_record['line'] = record.lineno

        # Include exception information if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)


class RequestIdFilter(logging.Filter):
    """
    Logging filter that injects the current request ID into log records.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


def setup_logging() -> None:
    """
    Configure and setup the application's logging:
    - Uses a JSON formatter for structured logging.
    - Removes any pre-existing logging handlers.
    - Sets log levels for core and third-party loggers.
    """
    # Create the root logger and set its level
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    # Remove existing handlers from the root logger
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create a console handler and assign our custom JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter(
        fmt='%(timestamp)s %(levelname)s %(name)s %(message)s',
        json_ensure_ascii=False
    )
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIdFilter())

    # Add the console handler to the root logger
    root_logger.addHandler(console_handler)

    # Set third-party loggers to WARNING to reduce verbosity
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.WARNING)

    # Create a dedicated application logger
    app_logger = logging.getLogger('app')
    app_logger.setLevel(settings.LOG_LEVEL)


def get_logger(name: str) -> logging.Logger:
    """
    Retrieve a named logger under the 'app' namespace.
    """
    return logging.getLogger(f"app.{name}")


class LoggerContext:
    """
    Context manager for temporarily setting log context variables.
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
    Log an error with context using a structured JSON format.
    """
    error_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context or {}
    }
    logger.error(
        f"Error occurred: {error_data['error_type']}",
        extra={'error_details': error_data, 'stack_trace': True},
        exc_info=error
    )