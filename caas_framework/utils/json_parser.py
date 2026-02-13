"""
Safe JSON parsing utilities for LLM responses

✅ v0.4.3 (Bug #3): Robust JSON parsing with multiple fallback strategies

Handles various response formats:
- LLMResponse objects
- Raw JSON strings
- Markdown-wrapped JSON
- Malformed JSON with automatic repair
"""

import json
import re
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class LLMResponseParser:
    """
    Safe parser for LLM responses with multiple fallback strategies

    Provides robust JSON parsing for various LLM response formats:
    1. LLMResponse objects with .content attribute
    2. Plain JSON strings
    3. Markdown code blocks (```json ... ```)
    4. Malformed JSON with automatic repair

    Example:
        >>> from caas_framework.utils.json_parser import parse_llm_json
        >>> response = LLMResponse(content='```json\\n{"key": "value"}\\n```')
        >>> result = parse_llm_json(response)
        >>> print(result)
        {"key": "value"}
    """

    @staticmethod
    def to_string(response: Any) -> str:
        """
        Convert any response type to string.

        Args:
            response: LLM response (LLMResponse, str, dict, etc.)

        Returns:
            String representation

        Strategy:
            1. Return if already string
            2. Extract .content if LLMResponse object
            3. JSON dump if dictionary
            4. str() fallback for other types
        """
        # Case 1: Already a string
        if isinstance(response, str):
            return response

        # Case 2: LLMResponse object with content attribute
        if hasattr(response, 'content'):
            content = response.content
            if isinstance(content, str):
                return content
            return str(content)

        # Case 3: Dictionary (convert to JSON)
        if isinstance(response, dict):
            return json.dumps(response, ensure_ascii=False)

        # Case 4: Other types
        return str(response)

    @staticmethod
    def extract_json(text: str) -> str:
        """
        Extract JSON from text with markdown code blocks.

        Args:
            text: Text potentially containing JSON

        Returns:
            Extracted JSON string

        Patterns:
            1. ```json ... ``` (markdown with json tag)
            2. ``` ... ``` (markdown without tag)
            3. {...} (direct JSON object)
        """
        # Strategy 1: Extract from markdown code block
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
            r'```\s*([\s\S]*?)\s*```',       # ``` ... ```
            r'\{[\s\S]*\}',                   # Direct JSON object
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                # Extract matched group
                extracted = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)

                # Validate it looks like JSON
                stripped = extracted.strip()
                if stripped.startswith('{') or stripped.startswith('['):
                    return stripped

        # No pattern matched - return original
        return text.strip()

    @staticmethod
    def repair_json(text: str) -> str:
        """
        Attempt to repair malformed JSON.

        Args:
            text: Potentially malformed JSON

        Returns:
            Repaired JSON string

        Repairs:
            1. Remove trailing commas
            2. Fix unquoted keys (simple cases)
            3. Convert single quotes to double quotes

        Warning:
            This is best-effort repair and may not handle all cases.
            Complex malformations may still fail.
        """
        # Remove trailing commas before } or ]
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)

        # Fix unquoted keys (simple cases: word characters only)
        # Before: {key: "value"}
        # After: {"key": "value"}
        text = re.sub(r'(\w+):', r'"\1":', text)

        # Fix single quotes to double quotes
        # Warning: This is naive and may break nested strings
        text = text.replace("'", '"')

        return text

    @classmethod
    def parse_json_safe(
        cls,
        response: Any,
        default: Optional[Dict] = None,
        repair: bool = True,
    ) -> Dict[str, Any]:
        """
        Safely parse JSON from LLM response with multiple fallback strategies.

        Args:
            response: LLM response (any type)
            default: Default value if parsing fails (default: {})
            repair: Whether to attempt JSON repair (default: True)

        Returns:
            Parsed dictionary or default value

        Strategy:
            1. Convert response to string (handle LLMResponse objects)
            2. Extract JSON from markdown code blocks
            3. Try direct JSON parsing
            4. If fails, attempt JSON repair (if enabled)
            5. Return default on complete failure

        Example:
            >>> response = LLMResponse(content='```json\\n{"key": "value"}\\n```')
            >>> parsed = LLMResponseParser.parse_json_safe(response)
            >>> print(parsed)
            {"key": "value"}

            >>> malformed = '{"key": "value",}'  # trailing comma
            >>> parsed = LLMResponseParser.parse_json_safe(malformed)
            >>> print(parsed)
            {"key": "value"}
        """
        if default is None:
            default = {}

        try:
            # Step 1: Convert to string
            text = cls.to_string(response)

            # Step 2: Extract JSON from markdown
            json_text = cls.extract_json(text)

            # Step 3: Try direct parse
            try:
                return json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.debug(f"Initial JSON parse failed: {e}")

                if not repair:
                    raise

                # Step 4: Attempt repair
                logger.info("Attempting JSON repair...")
                repaired = cls.repair_json(json_text)

                try:
                    return json.loads(repaired)
                except json.JSONDecodeError as e2:
                    logger.warning(f"JSON repair failed: {e2}")
                    raise

        except Exception as e:
            logger.error(f"JSON parsing failed completely: {e}")
            logger.debug(f"Response type: {type(response)}")
            logger.debug(f"Response content (first 200 chars): {str(response)[:200]}")
            return default


# Convenience function for easy import
def parse_llm_json(response: Any, default: Optional[Dict] = None) -> Dict:
    """
    Convenience function for safe JSON parsing.

    Args:
        response: LLM response (any type)
        default: Default value if parsing fails

    Returns:
        Parsed dictionary or default

    Example:
        >>> from caas_framework.utils.json_parser import parse_llm_json
        >>> result = parse_llm_json(llm_response, default={"sections": []})
    """
    return LLMResponseParser.parse_json_safe(response, default=default)
