"""
CAAS Application Layer

Application-specific code including workflow, codegen, monitoring, and testing.
"""

__version__ = "0.1.0"
__author__ = "AIDX Team"

from caas_app.utils.config import get_settings, settings
from caas_framework.utils.logger import logger, get_logger

__all__ = [
    "__version__",
    "__author__",
    "get_settings",
    "settings",
    "logger",
    "get_logger",
]
