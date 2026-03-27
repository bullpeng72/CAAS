"""
Quality Gate Settings

Environment-based configuration for Quality Gate thresholds.
Supports preset profiles (strict, balanced, permissive) and custom settings.

Usage:
    from caas_framework.config.quality_settings import get_quality_settings

    settings = get_quality_settings()
    threshold = settings.discovery.requirement_clarity  # From .env
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class DiscoveryQualitySettings(BaseSettings):
    """Phase 1: DISCOVERY Quality Gate Settings"""

    requirement_clarity: float = Field(default=7.0, ge=0.0, le=10.0)
    feature_completeness: float = Field(default=7.0, ge=0.0, le=10.0)
    golden_data_alignment: float = Field(default=80.0, ge=0.0, le=100.0)
    min_pass_rate: float = Field(default=85.0, ge=0.0, le=100.0)

    class Config:
        env_prefix = "CAAS_QG_DISCOVERY_"
        case_sensitive = False
        extra = "ignore"


class ArchitectureQualitySettings(BaseSettings):
    """Phase 2: ARCHITECTURE Quality Gate Settings"""

    component_clarity: float = Field(default=7.0, ge=0.0, le=10.0)
    architectural_coherence: float = Field(default=7.0, ge=0.0, le=10.0)
    scalability_score: float = Field(default=6.0, ge=0.0, le=10.0)
    min_pass_rate: float = Field(default=80.0, ge=0.0, le=100.0)

    class Config:
        env_prefix = "CAAS_QG_ARCHITECTURE_"
        case_sensitive = False
        extra = "ignore"


class DesignQualitySettings(BaseSettings):
    """Phase 3: DESIGN Quality Gate Settings"""

    agent_role_clarity: float = Field(default=7.0, ge=0.0, le=10.0)
    task_completeness: float = Field(default=7.0, ge=0.0, le=10.0)
    dependency_correctness: float = Field(default=8.0, ge=0.0, le=10.0)
    tool_appropriateness: float = Field(default=7.0, ge=0.0, le=10.0)
    min_pass_rate: float = Field(default=85.0, ge=0.0, le=100.0)

    class Config:
        env_prefix = "CAAS_QG_DESIGN_"
        case_sensitive = False
        extra = "ignore"


class DeliveryQualitySettings(BaseSettings):
    """Phase 4: DELIVERY Quality Gate Settings"""

    code_quality: float = Field(default=7.0, ge=0.0, le=10.0)
    implementation_completeness: float = Field(default=7.5, ge=0.0, le=10.0)
    security_score: float = Field(default=7.5, ge=0.0, le=10.0)
    test_coverage: float = Field(default=70.0, ge=0.0, le=100.0)
    min_pass_rate: float = Field(default=80.0, ge=0.0, le=100.0)

    class Config:
        env_prefix = "CAAS_QG_DELIVERY_"
        case_sensitive = False
        extra = "ignore"


class QAQualitySettings(BaseSettings):
    """Phase 5: QUALITY_ASSURANCE Quality Gate Settings"""

    test_completeness: float = Field(default=7.0, ge=0.0, le=10.0)
    test_correctness: float = Field(default=8.0, ge=0.0, le=10.0)
    coverage_percentage: float = Field(default=75.0, ge=0.0, le=100.0)
    min_pass_rate: float = Field(default=85.0, ge=0.0, le=100.0)

    class Config:
        env_prefix = "CAAS_QG_QA_"
        case_sensitive = False
        extra = "ignore"


class QualityGateSettings(BaseSettings):
    """
    Unified Quality Gate Settings

    Loads all phase-specific settings from environment variables.
    Supports preset profiles: strict, balanced (default), permissive, custom.

    Environment Variables:
        CAAS_STRICT_QUALITY_GATES: Enable strict mode (true/false)
        CAAS_QG_PROFILE: Profile name (strict/balanced/permissive/custom)
        CAAS_QG_<PHASE>_<METRIC>: Individual metric thresholds

    Examples:
        # Use balanced profile (default)
        CAAS_QG_PROFILE=balanced

        # Use strict profile
        CAAS_QG_PROFILE=strict
        CAAS_STRICT_QUALITY_GATES=true

        # Custom settings
        CAAS_QG_PROFILE=custom
        CAAS_QG_DELIVERY_CODE_QUALITY=9.0
        CAAS_QG_DELIVERY_SECURITY_SCORE=9.5
    """

    # Global strict mode
    strict_quality_gates: bool = Field(
        default=True,
        description="Enable strict mode - halt workflow on Quality Gate failure",
    )

    # Preset profile
    profile: str = Field(
        default="balanced",
        description="Quality Gate profile: strict, balanced, permissive, custom",
    )

    # Phase-specific settings
    discovery: DiscoveryQualitySettings = Field(
        default_factory=DiscoveryQualitySettings
    )
    architecture: ArchitectureQualitySettings = Field(
        default_factory=ArchitectureQualitySettings
    )
    design: DesignQualitySettings = Field(default_factory=DesignQualitySettings)
    delivery: DeliveryQualitySettings = Field(default_factory=DeliveryQualitySettings)
    qa: QAQualitySettings = Field(default_factory=QAQualitySettings)

    class Config:
        env_prefix = "CAAS_"
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Apply profile after initialization
        if self.profile != "custom":
            self._apply_profile()

    def _apply_profile(self):
        """Apply preset profile if not using custom settings"""
        if self.profile == "strict":
            self._apply_strict_profile()
        elif self.profile == "permissive":
            self._apply_permissive_profile()
        elif self.profile == "balanced":
            # Default values (already set in Field defaults)
            pass

    def _apply_strict_profile(self):
        """
        Strict profile: High thresholds, 100% pass rate

        Use for production-critical code or compliance requirements.
        """
        # Discovery
        self.discovery.requirement_clarity = 8.5
        self.discovery.feature_completeness = 8.5
        self.discovery.golden_data_alignment = 90.0
        self.discovery.min_pass_rate = 100.0

        # Architecture
        self.architecture.component_clarity = 8.0
        self.architecture.architectural_coherence = 8.0
        self.architecture.scalability_score = 7.0
        self.architecture.min_pass_rate = 100.0

        # Design
        self.design.agent_role_clarity = 8.5
        self.design.task_completeness = 8.5
        self.design.dependency_correctness = 9.0
        self.design.tool_appropriateness = 8.0
        self.design.min_pass_rate = 100.0

        # Delivery
        self.delivery.code_quality = 8.5
        self.delivery.implementation_completeness = 9.0
        self.delivery.security_score = 9.0
        self.delivery.test_coverage = 85.0
        self.delivery.min_pass_rate = 100.0

        # QA
        self.qa.test_completeness = 8.5
        self.qa.test_correctness = 9.0
        self.qa.coverage_percentage = 85.0
        self.qa.min_pass_rate = 100.0

    def _apply_permissive_profile(self):
        """
        Permissive profile: Low thresholds, relaxed pass rate

        Use for rapid prototyping or early development.
        """
        # Discovery
        self.discovery.requirement_clarity = 5.0
        self.discovery.feature_completeness = 5.0
        self.discovery.golden_data_alignment = 60.0
        self.discovery.min_pass_rate = 60.0

        # Architecture
        self.architecture.component_clarity = 5.0
        self.architecture.architectural_coherence = 5.0
        self.architecture.scalability_score = 4.0
        self.architecture.min_pass_rate = 60.0

        # Design
        self.design.agent_role_clarity = 5.0
        self.design.task_completeness = 5.0
        self.design.dependency_correctness = 6.0
        self.design.tool_appropriateness = 5.0
        self.design.min_pass_rate = 60.0

        # Delivery
        self.delivery.code_quality = 5.0
        self.delivery.implementation_completeness = 6.0
        self.delivery.security_score = 6.0
        self.delivery.test_coverage = 50.0
        self.delivery.min_pass_rate = 60.0

        # QA
        self.qa.test_completeness = 5.0
        self.qa.test_correctness = 6.0
        self.qa.coverage_percentage = 60.0
        self.qa.min_pass_rate = 60.0

    def to_dict(self) -> dict:
        """Export settings as dictionary"""
        return {
            "strict_quality_gates": self.strict_quality_gates,
            "profile": self.profile,
            "discovery": {
                "requirement_clarity": self.discovery.requirement_clarity,
                "feature_completeness": self.discovery.feature_completeness,
                "golden_data_alignment": self.discovery.golden_data_alignment,
                "min_pass_rate": self.discovery.min_pass_rate,
            },
            "architecture": {
                "component_clarity": self.architecture.component_clarity,
                "architectural_coherence": self.architecture.architectural_coherence,
                "scalability_score": self.architecture.scalability_score,
                "min_pass_rate": self.architecture.min_pass_rate,
            },
            "design": {
                "agent_role_clarity": self.design.agent_role_clarity,
                "task_completeness": self.design.task_completeness,
                "dependency_correctness": self.design.dependency_correctness,
                "tool_appropriateness": self.design.tool_appropriateness,
                "min_pass_rate": self.design.min_pass_rate,
            },
            "delivery": {
                "code_quality": self.delivery.code_quality,
                "implementation_completeness": self.delivery.implementation_completeness,
                "security_score": self.delivery.security_score,
                "test_coverage": self.delivery.test_coverage,
                "min_pass_rate": self.delivery.min_pass_rate,
            },
            "qa": {
                "test_completeness": self.qa.test_completeness,
                "test_correctness": self.qa.test_correctness,
                "coverage_percentage": self.qa.coverage_percentage,
                "min_pass_rate": self.qa.min_pass_rate,
            },
        }


# Singleton instance
_quality_settings: Optional[QualityGateSettings] = None


def get_quality_settings() -> QualityGateSettings:
    """
    Get Quality Gate settings singleton

    Returns:
        QualityGateSettings: Singleton instance loaded from .env
    """
    global _quality_settings
    if _quality_settings is None:
        _quality_settings = QualityGateSettings()
    return _quality_settings


def reset_quality_settings():
    """Reset singleton (useful for testing)"""
    global _quality_settings
    _quality_settings = None
