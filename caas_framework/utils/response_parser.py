"""
Response Parser Utility

Unified utilities for parsing and validating LLM responses.
Consolidates duplicate response parsing patterns across agents and modules.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from .text_processing import JsonExtractor

logger = logging.getLogger(__name__)


class ResponseParser:
    """Unified LLM response parsing utility."""

    @staticmethod
    def parse_structured_response(
        response: Any,
        expected_fields: List[str],
        fallback_factory: Optional[Callable[[], Dict[str, Any]]] = None,
        validators: Optional[Dict[str, Callable[[Any], bool]]] = None,
        required_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Parse and validate LLM response with field extraction.

        Consolidates 11+ duplicate response parsing methods across:
        - agents/system_architect.py
        - agents/requirement_analyst.py
        - agents/agent_designer.py
        - agents/qa_specialist.py
        - agents/code_generator.py
        - bmad/engine.py
        - bmad/golden_data.py
        - refinement/expander.py

        Args:
            response: LLM response object (dict, string, or response object)
            expected_fields: List of field names to extract
            fallback_factory: Function to create fallback response on error
            validators: Dict of field_name -> validation_function
            required_fields: List of required field names (subset of expected_fields)

        Returns:
            Parsed and validated dictionary with expected fields

        Example:
            >>> response = llm.invoke(prompt)
            >>> result = ResponseParser.parse_structured_response(
            ...     response,
            ...     expected_fields=['components', 'dependencies', 'architecture'],
            ...     fallback_factory=lambda: {'components': [], 'dependencies': []},
            ...     validators={'components': lambda x: isinstance(x, list)},
            ...     required_fields=['components']
            ... )
        """
        try:
            # Use JsonExtractor for markdown/JSON parsing
            result = JsonExtractor.safe_parse(
                response, default={}, extract_markdown=True, return_type=dict
            )

            # Validate result is a dict
            if not isinstance(result, dict):
                logger.warning(f"Response is not a dict: {type(result)}")
                return fallback_factory() if fallback_factory else {}

            # Field validation
            if validators:
                for field, validator in validators.items():
                    if field in result:
                        try:
                            if not validator(result[field]):
                                logger.warning(f"Field '{field}' failed validation")
                                result[field] = None
                        except Exception as e:
                            logger.error(f"Validator error for field '{field}': {e}")
                            result[field] = None

            # Check required fields
            if required_fields:
                missing_fields = [
                    f for f in required_fields if f not in result or result[f] is None
                ]
                if missing_fields:
                    logger.warning(f"Missing required fields: {missing_fields}")
                    if fallback_factory:
                        return fallback_factory()

            # Extract expected fields
            parsed = {}
            for field in expected_fields:
                value = result.get(field)
                # Include field even if empty list/dict (but not None)
                if value is not None:
                    parsed[field] = value
                else:
                    # Log missing expected field
                    logger.debug(f"Expected field '{field}' is None in response")

            # Include any extra fields from response
            for key, value in result.items():
                if key not in parsed and value is not None:
                    parsed[key] = value

            return parsed

        except Exception as e:
            logger.error(f"Response parsing failed: {e}")
            return fallback_factory() if fallback_factory else {}

    @staticmethod
    def create_empty_response(
        fields: List[str],
        status: str = "failed",
        list_fields: Optional[List[str]] = None,
        dict_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create empty response with specified fields.

        Consolidates 5+ duplicate fallback creation methods.

        Args:
            fields: List of field names to initialize
            status: Status value (default: "failed")
            list_fields: Field names that should be lists (overrides inference)
            dict_fields: Field names that should be dicts (overrides inference)

        Returns:
            Dict with empty values for each field

        Example:
            >>> fallback = ResponseParser.create_empty_response(
            ...     fields=['components', 'dependencies', 'architecture'],
            ...     list_fields=['components', 'dependencies'],
            ...     dict_fields=['architecture']
            ... )
            >>> # {'components': [], 'dependencies': [], 'architecture': {}, 'status': 'failed'}
        """
        result = {"status": status}

        list_fields_set = set(list_fields or [])
        dict_fields_set = set(dict_fields or [])

        for field in fields:
            if field in list_fields_set:
                result[field] = []
            elif field in dict_fields_set:
                result[field] = {}
            elif field.endswith("s") or field in [
                "components",
                "dependencies",
                "gaps",
                "features",
                "tasks",
                "agents",
            ]:
                # Infer list from field name
                result[field] = []
            else:
                # Default to dict for other fields
                result[field] = {}

        return result

    @staticmethod
    def extract_content(response: Any) -> str:
        """
        Extract text content from various response formats.

        Handles:
        - Dict with 'content' key
        - Object with .content attribute
        - String responses
        - Other types (converted to string)

        Args:
            response: LLM response in any format

        Returns:
            Extracted content as string

        Example:
            >>> content = ResponseParser.extract_content(response)
        """
        if isinstance(response, dict):
            return response.get("content", str(response))
        elif hasattr(response, "content"):
            return response.content
        else:
            return str(response)

    @staticmethod
    def parse_list_response(
        response: Any, item_key: Optional[str] = None, fallback: Optional[List[Any]] = None
    ) -> List[Any]:
        """
        Parse response expected to be a list.

        Args:
            response: LLM response
            item_key: If response is dict, extract list from this key
            fallback: Fallback list on error (default: [])

        Returns:
            Parsed list

        Example:
            >>> items = ResponseParser.parse_list_response(
            ...     response,
            ...     item_key='questions',
            ...     fallback=[]
            ... )
        """
        try:
            result = JsonExtractor.safe_parse(
                response, default=fallback or [], extract_markdown=True
            )

            # If expecting a list but got dict with item_key
            if isinstance(result, dict) and item_key:
                result = result.get(item_key, fallback or [])

            # Validate it's a list
            if not isinstance(result, list):
                logger.warning(f"Expected list but got {type(result)}")
                return fallback or []

            return result

        except Exception as e:
            logger.error(f"List response parsing failed: {e}")
            return fallback or []
