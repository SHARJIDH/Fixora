"""
Structured logger for CloudAgentPR backend.
Uses structlog for Pino-style JSON logging.

Usage:
    from utils.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Processing issue", repo="owner/repo", issue=123)
"""
import os
import logging
import structlog

# Map string log levels to logging module integers
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def configure_logging(json_logs: bool = None, log_level: str = None):
    """
    Configure structlog with appropriate processors.
    
    Args:
        json_logs: If True, output JSON. If False, use colored console output.
                   Defaults to JSON in production (when LOG_FORMAT=json).
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR).
    """
    if json_logs is None:
        json_logs = os.environ.get("LOG_FORMAT", "").lower() == "json"
    
    if log_level is None:
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    
    # Get the numeric log level
    numeric_level = LOG_LEVELS.get(log_level, logging.INFO)
    
    # Shared processors for all outputs
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    
    if json_logs:
        # Production: JSON output
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ]
    else:
        # Development: Colored console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name, typically __name__
        
    Returns:
        Configured structlog BoundLogger
    """
    logger = structlog.get_logger()
    if name:
        return logger.bind(logger_name=name)
    return logger


# Configure on import
configure_logging()
