"""
Text Processing Utilities

Shared utilities for text processing, JSON parsing, and object access.
Consolidates duplicate code patterns from across the framework.
"""

import json
import re
from typing import Any, Dict, List, Optional, Union

from caas_framework.utils.logger import get_logger


class ObjectAccessor:
    """Utilities for accessing values from dicts or objects uniformly"""

    @staticmethod
    def get_value(obj: Union[Dict, Any], key: str, default: Any = None) -> Any:
        """
        Get value from dict or object attribute.

        Consolidates the 5x duplicated get_nfr_value() pattern.

        Args:
            obj: Dictionary or object to access
            key: Key/attribute name
            default: Default value if not found

        Returns:
            Value from dict or object, or default if not found
        """
        if isinstance(obj, dict):
            return obj.get(key, default)
        else:
            return getattr(obj, key, default)

    @staticmethod
    def to_dict(obj: Union[Dict, Any]) -> Dict[str, Any]:
        """
        Convert Pydantic model or dict to dict.

        Consolidates the repeated hasattr(obj, 'model_dump') pattern.

        Args:
            obj: Dict or object (Pydantic model) to convert

        Returns:
            Dict representation of the object

        Example:
            >>> from pydantic import BaseModel
            >>> class MyModel(BaseModel):
            ...     name: str
            ...
            >>> model = MyModel(name="test")
            >>> ObjectAccessor.to_dict(model)
            {'name': 'test'}
            >>>
            >>> plain_dict = {"name": "test"}
            >>> ObjectAccessor.to_dict(plain_dict)
            {'name': 'test'}
        """
        if isinstance(obj, dict):
            return obj
        elif hasattr(obj, "model_dump"):
            # Pydantic v2
            return obj.model_dump()
        elif hasattr(obj, "dict"):
            # Pydantic v1 or similar
            return obj.dict()
        elif hasattr(obj, "__dict__"):
            # Generic object with __dict__
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        else:
            # Fallback: return empty dict
            return {}

    @staticmethod
    def to_dict_list(items: List[Union[Dict, Any]]) -> List[Dict[str, Any]]:
        """
        Convert list of Pydantic models or dicts to list of dicts.

        Convenience method for converting lists of objects.

        Args:
            items: List of dicts or objects to convert

        Returns:
            List of dict representations

        Example:
            >>> models = [MyModel(name="a"), MyModel(name="b")]
            >>> ObjectAccessor.to_dict_list(models)
            [{'name': 'a'}, {'name': 'b'}]
        """
        return [ObjectAccessor.to_dict(item) for item in items]


class JsonExtractor:
    """Utilities for extracting and parsing JSON from text"""

    @staticmethod
    def extract_json_block(text: str) -> str:
        """
        Extract JSON content from markdown code blocks.

        Consolidates 6x duplicate pattern across codebase.

        Args:
            text: Text that may contain JSON in markdown code blocks

        Returns:
            Extracted JSON text without markdown formatting
        """
        import re

        # Try to extract from ```json ... ``` block using regex (more robust)
        json_block_pattern = r"```json\s*\n(.*?)\n```"
        match = re.search(json_block_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try generic ``` ... ``` block
        code_block_pattern = r"```\s*\n(.*?)\n```"
        match = re.search(code_block_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try to find JSON object/array by looking for { or [
        # This handles cases where LLM returns JSON without code blocks
        json_start = -1
        for i, char in enumerate(text):
            if char in ("{", "["):
                json_start = i
                break

        if json_start >= 0:
            return text[json_start:].strip()

        return text.strip()

    @staticmethod
    def _attempt_json_repair(text: str, error: json.JSONDecodeError) -> Optional[str]:
        """
        Attempt to repair common JSON syntax errors.

        Common LLM JSON errors:
        1. Missing commas between array/object elements
        2. Trailing commas before closing brackets
        3. Unescaped quotes in strings
        4. Missing closing brackets
        5. Comments in JSON

        Args:
            text: Malformed JSON string
            error: The JSONDecodeError with position information

        Returns:
            Repaired JSON string or None if repair not possible
        """
        import re

        repaired = text

        # 1. Remove comments (// and /* */)
        repaired = re.sub(r"//.*?$", "", repaired, flags=re.MULTILINE)
        repaired = re.sub(r"/\*.*?\*/", "", repaired, flags=re.DOTALL)

        # 2. Fix trailing commas before closing brackets
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)

        # 3. Add missing commas between } and { or ] and [
        repaired = re.sub(r"}\s*\n\s*{", "},\n{", repaired)
        repaired = re.sub(r"]\s*\n\s*\[", "],\n[", repaired)

        # 4. Add missing commas between } and [ or ] and {
        repaired = re.sub(r"}\s*\n\s*\[", "},\n[", repaired)
        repaired = re.sub(r"]\s*\n\s*{", "],\n{", repaired)

        # 5. Add missing commas after closing quotes if followed by opening quote
        # This handles: "field": "value" "field2": "value2" -> "field": "value", "field2": "value2"
        repaired = re.sub(r'"\s*\n\s*"', '",\n"', repaired)

        # 6. Fix invalid unicode escape sequences (\uXXXX where XXXX is not hex)
        # This happens when LLM generates Python code with \u patterns (regex, paths, etc.)
        # embedded in JSON strings. Replace invalid \uXXXX with \\uXXXX (escaped backslash).
        try:
            repaired = re.sub(
                r'\\u(?![0-9a-fA-F]{4})',
                r'\\\\u',
                repaired
            )
        except Exception:
            pass

        # 7. Try to balance brackets if missing
        open_braces = repaired.count("{")
        close_braces = repaired.count("}")
        if open_braces > close_braces:
            repaired += "}" * (open_braces - close_braces)

        open_brackets = repaired.count("[")
        close_brackets = repaired.count("]")
        if open_brackets > close_brackets:
            repaired += "]" * (open_brackets - close_brackets)

        return repaired if repaired != text else None

    @staticmethod
    def safe_parse(
        text: str,
        default: Any = None,
        extract_markdown: bool = True,
        return_type: Optional[type] = None,
    ) -> Any:
        """
        Safely parse JSON with automatic markdown extraction and error handling.

        Consolidates 15+ duplicate JSON parsing patterns.

        Args:
            text: Text or JSON string to parse
            default: Default value to return on parse error (None, {}, [], etc.)
            extract_markdown: Whether to extract from markdown code blocks first
            return_type: Expected return type (dict, list) for type validation

        Returns:
            Parsed JSON object or default value on error
        """
        # Handle already parsed objects
        if isinstance(text, dict):
            return text
        if isinstance(text, list):
            return text

        # Extract content from response objects (LLM responses)
        if hasattr(text, "content"):
            text = text.content
        elif isinstance(text, dict) and "content" in text:
            text = text["content"]

        # Convert to string
        text_str = str(text)

        # Extract from markdown if requested
        if extract_markdown:
            text_str = JsonExtractor.extract_json_block(text_str)

        # Parse JSON
        try:
            result = json.loads(text_str)

            # Validate return type if specified
            if return_type is not None and not isinstance(result, return_type):
                logger = get_logger()
                logger.warning(
                    f"JSON parsed but wrong type: expected {return_type}, got {type(result)}"
                )
                return (
                    default
                    if default is not None
                    else ([] if return_type is list else {})
                )

            return result
        except json.JSONDecodeError as e:
            logger = get_logger()
            logger.error(f"JSON decode error: {e}")

            # Try to repair common JSON errors
            logger.info("Attempting to repair JSON...")
            repaired_json = JsonExtractor._attempt_json_repair(text_str, e)

            if repaired_json:
                try:
                    result = json.loads(repaired_json)
                    logger.info("✅ JSON repair successful!")

                    # Validate return type if specified
                    if return_type is not None and not isinstance(result, return_type):
                        logger.warning(
                            f"Repaired JSON has wrong type: expected {return_type}, got {type(result)}"
                        )
                        return (
                            default
                            if default is not None
                            else ([] if return_type is list else {})
                        )

                    return result
                except json.JSONDecodeError:
                    logger.warning("❌ JSON repair failed")

            # Log more context for debugging
            error_pos = getattr(e, "pos", 0)
            context_start = max(0, error_pos - 100)
            context_end = min(len(text_str), error_pos + 100)
            logger.debug(
                f"Failed JSON context: ...{text_str[context_start:context_end]}..."
            )

            return default if default is not None else None


class TextNormalizer:
    """Utilities for text normalization and sanitization"""

    @staticmethod
    def normalize_agent_task_ids(
        agents_data: List[Dict], tasks_data: List[Dict]
    ) -> None:
        """
        Normalize IDs for agents and tasks in place.

        This consolidates the duplicate ID normalization logic that appeared
        multiple times in agent_designer.py.

        Args:
            agents_data: List of agent dictionaries
            tasks_data: List of task dictionaries
        """
        for i, agent in enumerate(agents_data):
            if "id" in agent:
                normalized = TextNormalizer.normalize_id(agent["id"], ascii_only=True)
                if not normalized or normalized == "unnamed":
                    # Fallback: derive from role or use index
                    role = agent.get("role", "")
                    normalized = TextNormalizer.normalize_id(role, ascii_only=True) if role else ""
                    normalized = normalized or f"agent_{i}"
                agent["id"] = normalized[:64]  # enforce max length

        for j, task in enumerate(tasks_data):
            if "id" in task:
                normalized = TextNormalizer.normalize_id(task["id"], ascii_only=True)
                if not normalized or normalized == "unnamed":
                    desc = task.get("description", "")
                    normalized = TextNormalizer.normalize_id(desc[:30], ascii_only=True) if desc else ""
                    normalized = normalized or f"task_{j}"
                task["id"] = normalized[:64]
            # Also normalize agent reference
            if "agent" in task:
                normalized_ref = TextNormalizer.normalize_id(task["agent"], ascii_only=True)
                if not normalized_ref or normalized_ref == "unnamed":
                    normalized_ref = f"agent_{j}"
                task["agent"] = normalized_ref[:64]

    @staticmethod
    def normalize_id(text: str, max_length: int = 100, ascii_only: bool = False) -> str:
        """
        Normalize text to valid ID format.

        Args:
            text: Text to normalize
            max_length: Maximum length for normalized ID
            ascii_only: If True, remove non-ASCII characters

        Returns:
            Normalized ID string
        """
        # Convert to lowercase
        normalized = text.lower()

        # Replace special characters with underscores
        normalized = re.sub(r"[^\w가-힣\s-]", "_", normalized)

        # Replace whitespace and hyphens with underscores
        normalized = re.sub(r"[\s-]+", "_", normalized)

        # Remove consecutive underscores
        normalized = re.sub(r"_+", "_", normalized)

        # Strip leading/trailing underscores
        normalized = normalized.strip("_")

        # Remove non-ASCII if requested
        if ascii_only:
            normalized = re.sub(r"[^\x00-\x7F]+", "", normalized)

        # Limit length
        if len(normalized) > max_length:
            normalized = normalized[:max_length].rstrip("_")

        return normalized or "unnamed"

    @staticmethod
    def sanitize_for_mermaid(
        text: str, max_length: int = 50, allow_korean: bool = True
    ) -> str:
        """
        Sanitize text for use in Mermaid diagrams.

        Consolidates mermaid sanitization patterns from traceability.py.

        Args:
            text: Text to sanitize
            max_length: Maximum length for label
            allow_korean: Whether to allow Korean characters

        Returns:
            Sanitized text safe for Mermaid diagrams
        """
        if not text:
            return "empty"

        # Remove problematic characters for Mermaid
        # Replace special characters that break Mermaid syntax
        sanitized = re.sub(r"[\"\'`\[\]\{\}\(\)<>]", "", text)

        # Replace other special chars with spaces
        sanitized = re.sub(r"[^\w가-힣\s.-]", " ", sanitized)

        # Normalize whitespace
        sanitized = re.sub(r"\s+", " ", sanitized).strip()

        # Remove Korean if not allowed
        if not allow_korean:
            sanitized = re.sub(r"[가-힣]+", "", sanitized)
            sanitized = re.sub(r"\s+", " ", sanitized).strip()

        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip()

        return sanitized or "label"

    @staticmethod
    def sanitize_mermaid_id(
        text: str, allow_korean: bool = True, max_length: int = 64
    ) -> str:
        """
        Sanitize text to be a valid Mermaid node ID.

        Handles special Mermaid requirements:
        - IDs cannot start with digits
        - Only alphanumeric, underscore, and optionally Korean characters
        - Default max length 64 characters

        Args:
            text: Text to sanitize
            allow_korean: Whether to allow Korean characters
            max_length: Maximum ID length

        Returns:
            Valid Mermaid node ID
        """
        if not text:
            return "node"

        # Replace non-alphanumeric characters with underscores
        if allow_korean:
            sanitized = re.sub(r"[^\w가-힣]", "_", text)
        else:
            sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", text)

        # Remove consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)

        # Strip leading/trailing underscores
        sanitized = sanitized.strip("_")

        # Ensure doesn't start with digit (Mermaid requirement)
        if sanitized and sanitized[0].isdigit():
            sanitized = "n_" + sanitized

        # Default if empty
        if not sanitized:
            sanitized = "node"

        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized

    @staticmethod
    def clean_mermaid_label(text: str, max_length: int = 50) -> str:
        """
        Clean label text for Mermaid diagrams using entity escaping.

        Escapes problematic characters that break Mermaid syntax:
        - Quotes, angle brackets, pipes, hash symbols

        Args:
            text: Text to clean
            max_length: Maximum label length

        Returns:
            Cleaned label with entity escaping
        """
        if not text:
            return ""

        # Truncate if too long
        if len(text) > max_length:
            text = text[: max_length - 3] + "..."

        # Entity escape problematic characters
        # IMPORTANT: Escape # first to avoid double-escaping
        text = text.replace("#", "#hash;")
        text = text.replace('"', "#quot;")
        text = text.replace("<", "#lt;")
        text = text.replace(">", "#gt;")
        text = text.replace("|", "#vert;")

        # Normalize whitespace
        text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
        text = " ".join(text.split())

        return text.strip()

    @staticmethod
    def clean_label(text: str, max_length: int = 50) -> str:
        """
        Clean text for use as UI label.

        Args:
            text: Text to clean
            max_length: Maximum length for label

        Returns:
            Cleaned label text
        """
        if not text:
            return ""

        # Strip whitespace
        cleaned = text.strip()

        # Normalize whitespace (collapse multiple spaces)
        cleaned = re.sub(r"\s+", " ", cleaned)

        # Limit length
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length].rstrip() + "..."

        return cleaned


class CodeExtractor:
    """Utilities for extracting code elements from text"""

    @staticmethod
    def extract_keywords(text: str, min_length: int = 2) -> List[str]:
        """
        Extract keywords from text.

        Args:
            text: Text to extract keywords from
            min_length: Minimum keyword length

        Returns:
            List of extracted keywords
        """
        if not text:
            return []

        # Split on whitespace and punctuation
        words = re.findall(r"\b\w+\b", text.lower())

        # Filter by length
        keywords = [w for w in words if len(w) >= min_length]

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)

        return unique_keywords

    @staticmethod
    def extract_python_identifiers(code: str, pattern_type: str = "all") -> List[str]:
        """
        Extract Python identifiers (functions, classes, variables) from code.

        Args:
            code: Python code to analyze
            pattern_type: Type of identifiers to extract ("functions", "classes", "all")

        Returns:
            List of extracted identifier names
        """
        identifiers = []

        if pattern_type in ("functions", "all"):
            # Extract function definitions
            func_pattern = r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\("
            identifiers.extend(re.findall(func_pattern, code))

        if pattern_type in ("classes", "all"):
            # Extract class definitions
            class_pattern = r"class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[\(:]"
            identifiers.extend(re.findall(class_pattern, code))

        return identifiers
