"""
Safe Access Utilities

Provides safe getter functions for accessing values from dicts or Pydantic models.
Eliminates duplicate _safe_get() implementations across the codebase.
"""

from typing import Any, Dict, Union

from pydantic import BaseModel


def safe_get_value(obj: Union[Dict, BaseModel], key: str, default: Any = None) -> Any:
    """
    Safely get value from dict or Pydantic model.

    This utility function handles both dictionary and Pydantic model objects,
    providing a unified interface for attribute/key access with default values.

    Args:
        obj: Dict or Pydantic model object
        key: Key (for dict) or attribute name (for model)
        default: Default value to return if key/attribute not found

    Returns:
        Found value or default

    Examples:
        >>> data = {"name": "Agent", "role": "Analyst"}
        >>> safe_get_value(data, "name")
        'Agent'
        >>> safe_get_value(data, "missing", "default")
        'default'

        >>> from pydantic import BaseModel
        >>> class Agent(BaseModel):
        ...     name: str
        ...     role: str
        >>> agent = Agent(name="Agent", role="Analyst")
        >>> safe_get_value(agent, "name")
        'Agent'
        >>> safe_get_value(agent, "missing", "default")
        'default'
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    else:
        # Pydantic model or other object with attributes
        return getattr(obj, key, default)
