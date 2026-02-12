"""
CAAS SDK Models
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ProjectStatus(str, Enum):
    """Project status"""

    PENDING = "pending"
    GENERATING = "generating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GenerationConfig:
    """Code generation configuration"""

    requirement: str
    domain: Optional[str] = None
    deployment_target: str = "docker"
    workflow_type: Optional[
        str
    ] = None  # "sequential", "hierarchical", or None for auto
    enable_validation: bool = True
    enable_auto_fix: bool = True
    enable_tests: bool = True
    enable_deployment: bool = True
    # ✅ v0.5.1: use_expert_agents removed (Expert Agent path is the only path)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Project:
    """Project model"""

    project_id: str
    status: str  # Changed from ProjectStatus to str for flexibility
    requirement: str
    created_at: str
    updated_at: str
    domain: Optional[str] = None
    progress: float = 0.0
    current_phase: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Additional fields from API
    deployment_target: str = "docker"
    enable_validation: bool = True
    enable_auto_fix: bool = True
    enable_tests: bool = True
    files: Dict[str, str] = field(default_factory=dict)
    generation_time: float = 0.0
    phases_completed: List[str] = field(default_factory=list)
    session_id: Optional[str] = None


@dataclass
class GenerationResult:
    """Generation result"""

    project_id: str
    success: bool
    files: Dict[str, str] = field(default_factory=dict)
    golden_data: Optional[Dict] = None
    validation_report: Optional[Dict] = None
    generation_time: float = 0.0
    phases_completed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class ProgressUpdate:
    """Progress update event"""

    project_id: str
    phase: str
    progress: float
    message: str
    timestamp: str
