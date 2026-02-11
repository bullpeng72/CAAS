"""
Common Typing Imports

Consolidates typing imports to reduce duplication across 195+ files.
All modules should import from this file instead of directly from typing.

Usage:
    from caas_framework.utils.typing_common import Any, Dict, List, Optional

Benefits:
- Single source of truth for typing imports
- Easier to add new types or aliases
- Reduces import line duplication
- Consistent typing conventions across codebase
"""

# Standard typing imports (most commonly used)
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

# Advanced typing imports
from typing import (
    TYPE_CHECKING,
    Awaitable,
    ClassVar,
    Generic,
    Literal,
    Protocol,
    Type,
    TypeVar,
)

# Type aliases for common patterns
from typing import (
    AsyncIterator,
    Coroutine,
    Iterator,
)

# Collections typing
from collections.abc import (
    Iterable,
    Mapping,
    Sequence,
)

# Pydantic-style type checking
try:
    from typing import Annotated  # Python 3.9+
except ImportError:
    from typing_extensions import Annotated  # fallback

# Common type aliases
JSONDict = Dict[str, Any]
JSONList = List[Any]
JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]

# Configuration type
ConfigDict = Dict[str, Any]

# Agent/Task types
AgentDict = Dict[str, Any]
TaskDict = Dict[str, Any]

# Validation result types
ValidationResult = Dict[str, Any]

# LLM response types
LLMResponse = Union[str, Dict[str, Any]]

__all__ = [
    # Basic types
    "Any",
    "Callable",
    "Dict",
    "List",
    "Optional",
    "Set",
    "Tuple",
    "Union",
    # Advanced types
    "TYPE_CHECKING",
    "Awaitable",
    "ClassVar",
    "Generic",
    "Literal",
    "Protocol",
    "Type",
    "TypeVar",
    # Iterators
    "AsyncIterator",
    "Coroutine",
    "Iterator",
    # Collections
    "Iterable",
    "Mapping",
    "Sequence",
    # Annotations
    "Annotated",
    # Type aliases
    "JSONDict",
    "JSONList",
    "JSONValue",
    "ConfigDict",
    "AgentDict",
    "TaskDict",
    "ValidationResult",
    "LLMResponse",
]
