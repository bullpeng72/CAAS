"""
CAAS Framework Logging Utility

UI-independent logging for the framework.
Does not depend on app/ layer.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Rich is optional - framework works without it
try:
    from rich.console import Console
    from rich.logging import RichHandler
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


def setup_logger(
    name: str = "caas_framework",
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """
    Setup and return a logger instance.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path

    Returns:
        logging.Logger: Configured logger instance
    """
    log_level = level or "INFO"

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Prevent propagation to parent logger (avoid duplicate logs)
    logger.propagate = False

    # Setup handler
    if RICH_AVAILABLE:
        # Rich handler (console output with formatting)
        handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,  # Simplified for framework use
            rich_tracebacks=True,
            tracebacks_show_locals=False,
        )
        formatter = logging.Formatter("%(message)s", datefmt="[%X]")
    else:
        # Basic stream handler (fallback)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setLevel(getattr(logging, log_level.upper()))
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (typically module name)

    Returns:
        logging.Logger: Logger instance
    """
    return setup_logger(f"caas_framework.{name}")


# Default logger instance (lazy initialization)
_default_logger = None

def get_default_logger() -> logging.Logger:
    """Get default framework logger (lazy initialization)"""
    global _default_logger
    if _default_logger is None:
        _default_logger = setup_logger()
    return _default_logger


# Default logger for backward compatibility
logger = get_default_logger()
