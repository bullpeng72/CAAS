"""
Artifact Configuration Constants

✅ v0.5.0: Single Source of Truth for artifact type defaults

All artifact type default values are defined HERE and only here.
Other modules import from this file to avoid duplication.
"""

from typing import Dict

# ============================================================================
# Artifact Type Default Configuration - SINGLE SOURCE OF TRUTH
# ============================================================================

ARTIFACT_TYPES_DEFAULT: Dict[str, bool] = {
    "project_proposal": True,
    "requirements_spec": True,
    "architecture_design": True,
    "data_design": True,
    "api_design": True,  # ✅ v0.5.0: Changed to True
    "agent_design": True,
    "test_plan": True,  # ✅ v0.5.0: Changed to True
    "test_report": True,  # ✅ v0.5.0: Changed to True
    "code_review": True,  # ✅ v0.4.2: Changed to True
    "deployment_guide": True,  # ✅ v0.5.0: Changed to True
}
"""
Default artifact type generation settings.

All 10 artifact types are enabled by default (True).

Usage:
    >>> from caas_framework.models.artifact_constants import ARTIFACT_TYPES_DEFAULT
    >>> config = ArtifactGenerationConfig(enabled_types=ARTIFACT_TYPES_DEFAULT.copy())
"""

# ============================================================================
# Helper Functions
# ============================================================================


def get_default_artifact_types() -> Dict[str, bool]:
    """
    Get a copy of default artifact types configuration.

    Returns:
        Dict[str, bool]: Copy of ARTIFACT_TYPES_DEFAULT

    Usage:
        >>> types = get_default_artifact_types()
        >>> types["code_review"] = False  # Modify without affecting original
    """
    return ARTIFACT_TYPES_DEFAULT.copy()


def merge_artifact_types(
    base: Dict[str, bool], overrides: Dict[str, bool]
) -> Dict[str, bool]:
    """
    Merge artifact type configurations.

    Args:
        base: Base configuration
        overrides: Override values

    Returns:
        Dict[str, bool]: Merged configuration
    """
    result = base.copy()
    result.update(overrides)
    return result


__all__ = [
    "ARTIFACT_TYPES_DEFAULT",
    "get_default_artifact_types",
    "merge_artifact_types",
]
