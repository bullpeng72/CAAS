"""
JSON Helper

JSON parsing and extraction utilities for LLM responses.
Simplified version for framework use (no file I/O dependencies).
"""

import json
import re
import logging
from typing import Any, Dict, Optional, List

logger = logging.getLogger("caas_framework.utils.json_helper")


class JSONHelper:
    """JSON processing utilities for LLM responses"""

    @staticmethod
    def extract_from_markdown(
        content: str,
        fallback: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from Markdown code blocks

        Extracts JSON from LLM responses in ```json ... ``` format.

        Args:
            content: Markdown string
            fallback: Value to return on extraction failure

        Returns:
            Parsed Dict or fallback
        """
        if not content:
            logger.warning("Content is empty")
            return fallback

        content = content.strip()

        # Pattern 1: ```json ... ```
        if "```json" in content:
            try:
                extracted = content.split("```json")[1].split("```")[0].strip()
                logger.debug("JSON code block extracted successfully (json)")
                return JSONHelper.safe_parse(extracted, fallback)
            except (IndexError, ValueError) as e:
                logger.warning(f"JSON block extraction failed: {e}")

        # Pattern 2: ``` ... ``` (general code block)
        if "```" in content:
            try:
                extracted = content.split("```")[1].split("```")[0].strip()
                logger.debug("JSON code block extracted successfully (general)")
                return JSONHelper.safe_parse(extracted, fallback)
            except (IndexError, ValueError) as e:
                logger.warning(f"Code block extraction failed: {e}")

        # Pattern 3: Direct JSON (no code block)
        return JSONHelper.safe_parse(content, fallback)

    @staticmethod
    def safe_parse(
        json_str: str,
        fallback: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Safe JSON parsing

        Args:
            json_str: JSON string
            fallback: Value to return on parsing failure

        Returns:
            Parsed Dict or fallback
        """
        if not json_str or not json_str.strip():
            logger.warning("JSON string is empty")
            return fallback

        try:
            data = json.loads(json_str)
            logger.debug(f"JSON parsed successfully: {len(json_str)} bytes")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.debug(f"Failed JSON content: {json_str[:200]}...")
            return fallback

    @staticmethod
    def sanitize_response(content: str) -> str:
        """
        Sanitize LLM response (preprocessing before JSON extraction)

        Args:
            content: LLM response string

        Returns:
            Sanitized string
        """
        if not content:
            return content

        # Remove leading/trailing whitespace
        content = content.strip()

        # Remove common LLM response patterns
        # Example: "Here's the JSON:" explanatory text
        patterns = [
            r"^Here['\s]s the JSON:?\s*",
            r"^The JSON is:?\s*",
            r"^Response:?\s*",
            r"^Output:?\s*",
        ]

        for pattern in patterns:
            content = re.sub(pattern, "", content, flags=re.IGNORECASE)

        return content.strip()

    @staticmethod
    def sanitize_id(raw_id: str) -> str:
        """
        Normalize ID string to snake_case

        Args:
            raw_id: Original ID

        Returns:
            Normalized ID
        """
        if not raw_id:
            return ""

        # Convert to lowercase
        sanitized = raw_id.lower()

        # Replace spaces and hyphens with underscores
        sanitized = sanitized.replace(" ", "_").replace("-", "_")

        # Remove special characters (allow only alphanumeric and underscore)
        sanitized = re.sub(r'[^a-z0-9_]', '', sanitized)

        # Collapse consecutive underscores to single
        sanitized = re.sub(r'__+', '_', sanitized)

        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')

        # Handle empty string
        if not sanitized:
            logger.warning(f"ID normalization resulted in empty string: {raw_id}")
            return "unnamed"

        # Handle IDs starting with digit
        if sanitized[0].isdigit():
            sanitized = "id_" + sanitized

        logger.debug(f"ID normalized: {raw_id} -> {sanitized}")
        return sanitized

    @staticmethod
    def format_dump(
        data: Any,
        indent: int = 2,
        ensure_ascii: bool = False,
        sort_keys: bool = False
    ) -> str:
        """
        Format JSON (consistent style)

        Args:
            data: Data to serialize
            indent: Indentation size
            ensure_ascii: ASCII-only mode
            sort_keys: Sort keys alphabetically

        Returns:
            Formatted JSON string
        """
        return json.dumps(
            data,
            indent=indent,
            ensure_ascii=ensure_ascii,
            sort_keys=sort_keys
        )


# Convenience functions
def extract_json(content: str, fallback: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Extract JSON from Markdown (shortcut)"""
    return JSONHelper.extract_from_markdown(content, fallback)


def parse_json(json_str: str, fallback: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Parse JSON (shortcut)"""
    return JSONHelper.safe_parse(json_str, fallback)


def dump_json(data: Any, **kwargs) -> str:
    """Dump JSON (shortcut)"""
    return JSONHelper.format_dump(data, **kwargs)


def sanitize_id(raw_id: str) -> str:
    """Normalize ID (shortcut)"""
    return JSONHelper.sanitize_id(raw_id)
