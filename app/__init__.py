"""
CAAS - CrewAI Agent Auto-generation System

BMAD/SDD 방법론 기반 멀티에이전트 자동 생성 플랫폼입니다.
"""

__version__ = "0.1.0"
__author__ = "AIDX Team"

from app.utils.config import get_settings, settings
from caas_framework.utils.logger import logger, get_logger

__all__ = [
    "__version__",
    "__author__",
    "get_settings",
    "settings",
    "logger",
    "get_logger",
]
