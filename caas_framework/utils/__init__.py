"""
CAAS Framework Utilities

Framework-specific utilities that are UI-independent.
"""

from caas_framework.utils.logger import get_logger, setup_logger
from caas_framework.utils.text_processing import (
    ObjectAccessor,
    JsonExtractor,
    TextNormalizer,
    CodeExtractor,
)
from caas_framework.utils.llm_helper import LLMHelper
from caas_framework.utils.response_parser import ResponseParser
from caas_framework.utils.prompt_builder import PromptBuilder
from caas_framework.utils.golden_data_matcher import GoldenDataMatcher

__all__ = [
    "get_logger",
    "setup_logger",
    "ObjectAccessor",
    "JsonExtractor",
    "TextNormalizer",
    "CodeExtractor",
    "LLMHelper",
    "ResponseParser",
    "PromptBuilder",
    "GoldenDataMatcher",
]
