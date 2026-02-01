"""
App Core BMAD - Backward Compatibility Shim

DEPRECATED: This module re-exports from caas_framework.bmad for backward compatibility.

All new code should import directly from caas_framework.bmad:
    from caas_framework.bmad import BMADEngine

This shim will be removed in v3.0.

Migration Guide:
    # Old (deprecated)
    from app.core.bmad import BMADEngine
    from app.core.bmad.reflection import ReflectionEngine
    from app.core.bmad.analyzer import AnalysisResult

    # New (recommended)
    from caas_framework.bmad import BMADEngine
    from caas_framework.bmad.reflection import ReflectionEngine
    from caas_framework.bmad.code_analyzer import CodeAnalyzer

Component Name Changes:
    analyzer → code_analyzer
    validator → completeness_validator
    mapper → semantic_mapper
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from app.core.bmad is deprecated. "
    "Use 'from caas_framework.bmad import ...' instead. "
    "This shim will be removed in v3.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from caas_framework.bmad
from caas_framework.bmad import *

# Component aliases for backward compatibility
from caas_framework.bmad import code_analyzer as analyzer
from caas_framework.bmad import completeness_validator as validator
from caas_framework.bmad import semantic_mapper as mapper
from caas_framework.bmad import reflection
from caas_framework.bmad import models
from caas_framework.bmad import adaptive
from caas_framework.bmad import personality
from caas_framework.bmad import planner
from caas_framework.bmad import sharding
from caas_framework.bmad import task_refiner
from caas_framework.bmad import tester
from caas_framework.bmad import deployer

# Legacy classes for backward compatibility (not in framework)
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PhaseStatus(str, Enum):
    """단계 상태 (Legacy - for backward compatibility only)"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class FeatureItem(BaseModel):
    """기능 항목 (Legacy - for backward compatibility only)"""
    id: str
    name: str
    description: str
    priority: int = Field(ge=1, le=5)
    complexity: str = "medium"
    estimated_effort: Optional[str] = None


class SprintItem(BaseModel):
    """스프린트 항목 (Legacy - for backward compatibility only)"""
    id: str
    name: str
    features: List[str] = []
    agents: List[str] = []
    tasks: List[str] = []
    status: PhaseStatus = PhaseStatus.PENDING


class BMADContext(BaseModel):
    """BMAD 실행 컨텍스트 (Legacy - for backward compatibility only)"""
    project_name: str
    requirement: str
    domain: Optional[str] = None
    concretized_requirement: Optional[Dict[str, Any]] = None
    golden_data_validation_enabled: bool = True
    analysis: Optional[Dict[str, Any]] = None
    features: List[FeatureItem] = []
    architecture_design: Optional[Dict[str, Any]] = None
    agent_specs: List[Dict[str, Any]] = []
    task_specs: List[Dict[str, Any]] = []
    spec_yaml: Optional[str] = None
    generated_code: Optional[Dict[str, str]] = None
    sprints: List[SprintItem] = []
    current_sprint_index: int = 0


# Provide direct aliases for commonly imported classes
try:
    from caas_framework.bmad.code_analyzer import CodeAnalyzer as Analyzer
except ImportError:
    pass

try:
    from caas_framework.bmad.completeness_validator import CompletenessValidator as Validator
except ImportError:
    pass

try:
    from caas_framework.bmad.semantic_mapper import SemanticMapper as Mapper
except ImportError:
    pass
