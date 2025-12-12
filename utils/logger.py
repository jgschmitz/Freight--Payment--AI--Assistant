"""
Logging configuration for Freight Payment AI Assistant
"""
import logging
import sys
from typing import Optional
from pathlib import Path
import structlog
from rich.logging import RichHandler
from rich.console import Console

from config import get_settings


def setup_logging(log_level: Optional[str] = None) -> None:
    """Setup structured logging with rich formatting"""
    settings = get_settings()
    
    # Use provided log level or fall back to settings
    level = (log_level or settings.log_level).upper()
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Setup standard library logging
    logging.basicConfig(
        level=getattr(logging, level),
        format=settings.log_format,
        handlers=[
            RichHandler(
                console=Console(stderr=True),
                show_time=False,
                show_level=False,
                show_path=False,
                rich_tracebacks=True
            )
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.INFO)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured at {level} level")


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance"""
    return logging.getLogger(name)


class RequestLogger:
    """Middleware-style request logger"""
    
    def __init__(self, logger_name: str = "freight_ai.requests"):
        self.logger = get_logger(logger_name)
    
    def log_request(self, method: str, path: str, client_ip: str, user_agent: str = None):
        """Log incoming request"""
        self.logger.info(
            "Request received",
            extra={
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "user_agent": user_agent
            }
        )
    
    def log_response(self, method: str, path: str, status_code: int, duration_ms: float):
        """Log response"""
        level = logging.INFO
        if status_code >= 400:
            level = logging.WARNING
        if status_code >= 500:
            level = logging.ERROR
            
        self.logger.log(
            level,
            "Request completed",
            extra={
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2)
            }
        )


class PerformanceLogger:
    """Logger for performance metrics"""
    
    def __init__(self, logger_name: str = "freight_ai.performance"):
        self.logger = get_logger(logger_name)
    
    def log_search_performance(self, query: str, result_count: int, duration_ms: float, 
                              cache_hit: bool = False):
        """Log search performance metrics"""
        self.logger.info(
            "Search performance",
            extra={
                "query_length": len(query),
                "result_count": result_count,
                "duration_ms": round(duration_ms, 2),
                "cache_hit": cache_hit
            }
        )
    
    def log_embedding_performance(self, text_count: int, duration_ms: float):
        """Log embedding generation performance"""
        self.logger.info(
            "Embedding performance",
            extra={
                "text_count": text_count,
                "duration_ms": round(duration_ms, 2),
                "texts_per_second": round(text_count / (duration_ms / 1000), 2)
            }
        )
    
    def log_database_performance(self, operation: str, duration_ms: float, 
                                document_count: int = None):
        """Log database operation performance"""
        extra_data = {
            "operation": operation,
            "duration_ms": round(duration_ms, 2)
        }
        if document_count is not None:
            extra_data["document_count"] = document_count
            
        self.logger.info("Database performance", extra=extra_data)