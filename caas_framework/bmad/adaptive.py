"""
BMAD Scale-Adaptive Intelligence

프로젝트 복잡도에 따라 워크플로우 자동 조정
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from caas_framework.bmad.code_analyzer import AnalysisResult
from caas_framework.utils.logger import get_logger

logger = get_logger(name="caas_framework.bmad.adaptive")


class ProjectScale(str, Enum):
    """프로젝트 규모"""

    QUICK_FIX = "quick_fix"  # < 5분: 버그 수정, 간단한 변경
    STANDARD = "standard"  # < 15분: 일반 프로젝트
    ENTERPRISE = "enterprise"  # < 30분: 엔터프라이즈, 컴플라이언스


class AdaptiveWorkflowConfig(BaseModel):
    """적응형 워크플로우 설정"""

    scale: ProjectScale
    skip_phases: List[str] = Field(default_factory=list)
    max_iterations: int = 15
    require_tests: bool = True
    require_docs: bool = True
    require_security_audit: bool = False
    parallel_execution: bool = False
    enable_sharding: bool = True
    enable_reflection: bool = True
    quality_threshold: float = 0.7  # Reflection 품질 임계값


class ScaleAdaptiveEngine:
    """
    규모 적응형 엔진

    프로젝트의 복잡도를 분석하여 최적의 워크플로우를 자동으로 설정합니다.
    BMAD 방법론의 핵심으로 Quick Fix부터 Enterprise까지 대응합니다.
    """

    def __init__(self):
        self.logger = logger
        self.logger.info("ScaleAdaptiveEngine 초기화")

        # 복잡도 기준
        self.complexity_thresholds = {
            ProjectScale.QUICK_FIX: 3,  # 복잡도 3 이하
            ProjectScale.STANDARD: 7,  # 복잡도 7 이하
            ProjectScale.ENTERPRISE: 10,  # 복잡도 8 이상
        }

        # 기능 개수 기준
        self.feature_thresholds = {
            ProjectScale.QUICK_FIX: 2,
            ProjectScale.STANDARD: 8,
            ProjectScale.ENTERPRISE: 9,
        }

    def analyze_scale(self, analysis: AnalysisResult) -> ProjectScale:
        """
        프로젝트 규모 판단

        Args:
            analysis: 요구사항 분석 결과

        Returns:
            ProjectScale: 프로젝트 규모
        """
        complexity = analysis.complexity_score
        feature_count = len(analysis.features)

        self.logger.info(
            f"규모 분석: complexity={complexity}, features={feature_count}"
        )

        # Quick Fix: 복잡도 ≤ 3, 기능 1-2개
        if (
            complexity <= self.complexity_thresholds[ProjectScale.QUICK_FIX]
            and feature_count <= self.feature_thresholds[ProjectScale.QUICK_FIX]
        ):
            scale = ProjectScale.QUICK_FIX
            self.logger.info("규모 판정: QUICK_FIX (< 5분)")

        # Enterprise: 복잡도 ≥ 8 또는 기능 10개 이상
        elif (
            complexity >= self.complexity_thresholds[ProjectScale.ENTERPRISE]
            or feature_count >= self.feature_thresholds[ProjectScale.ENTERPRISE]
        ):
            scale = ProjectScale.ENTERPRISE
            self.logger.info("규모 판정: ENTERPRISE (< 30분)")

        # Standard: 나머지
        else:
            scale = ProjectScale.STANDARD
            self.logger.info("규모 판정: STANDARD (< 15분)")

        return scale

    def create_workflow_config(
        self, scale: ProjectScale, custom_overrides: Optional[Dict[str, Any]] = None
    ) -> AdaptiveWorkflowConfig:
        """
        규모별 워크플로우 설정 생성

        Args:
            scale: 프로젝트 규모
            custom_overrides: 사용자 커스텀 설정

        Returns:
            AdaptiveWorkflowConfig: 워크플로우 설정
        """
        self.logger.info(f"워크플로우 설정 생성: scale={scale}")

        if scale == ProjectScale.QUICK_FIX:
            config = AdaptiveWorkflowConfig(
                scale=scale,
                skip_phases=[],  # 모든 단계 실행하되 간소화
                max_iterations=5,
                require_tests=False,  # 테스트 선택적
                require_docs=False,  # 문서 생략
                require_security_audit=False,
                parallel_execution=False,
                enable_sharding=False,  # 샤딩 불필요
                enable_reflection=True,  # 간단한 반성만
                quality_threshold=0.6,  # 낮은 품질 기준
            )

        elif scale == ProjectScale.ENTERPRISE:
            config = AdaptiveWorkflowConfig(
                scale=scale,
                skip_phases=[],  # 모든 단계 필수
                max_iterations=30,
                require_tests=True,
                require_docs=True,
                require_security_audit=True,  # 보안 감사 필수
                parallel_execution=True,  # 병렬 실행
                enable_sharding=True,  # 샤딩 활성화
                enable_reflection=True,
                quality_threshold=0.8,  # 높은 품질 기준
            )

        else:  # STANDARD
            config = AdaptiveWorkflowConfig(
                scale=scale,
                skip_phases=[],
                max_iterations=15,
                require_tests=True,
                require_docs=True,
                require_security_audit=False,
                parallel_execution=False,
                enable_sharding=True,
                enable_reflection=True,
                quality_threshold=0.7,
            )

        # 사용자 커스텀 설정 적용
        if custom_overrides:
            for key, value in custom_overrides.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                    self.logger.debug(f"커스텀 설정 적용: {key}={value}")

        self.logger.info(f"워크플로우 설정 완료: {config}")
        return config

    def estimate_duration(self, scale: ProjectScale) -> Dict[str, Any]:
        """
        예상 소요 시간 계산

        Args:
            scale: 프로젝트 규모

        Returns:
            Dict: 예상 소요 시간 정보
        """
        duration_map = {
            ProjectScale.QUICK_FIX: {
                "min_minutes": 2,
                "max_minutes": 5,
                "avg_minutes": 3,
                "description": "간단한 버그 수정 또는 변경",
            },
            ProjectScale.STANDARD: {
                "min_minutes": 5,
                "max_minutes": 15,
                "avg_minutes": 10,
                "description": "일반적인 프로젝트 또는 기능 개발",
            },
            ProjectScale.ENTERPRISE: {
                "min_minutes": 15,
                "max_minutes": 30,
                "avg_minutes": 22,
                "description": "엔터프라이즈급 프로젝트 (보안, 컴플라이언스 포함)",
            },
        }

        return duration_map.get(scale, duration_map[ProjectScale.STANDARD])

    def recommend_optimizations(
        self, scale: ProjectScale, analysis: AnalysisResult
    ) -> List[str]:
        """
        규모별 최적화 권장사항 제공

        Args:
            scale: 프로젝트 규모
            analysis: 분석 결과

        Returns:
            List[str]: 최적화 권장사항
        """
        recommendations = []

        if scale == ProjectScale.QUICK_FIX:
            recommendations.append(
                "간단한 변경이므로 빠른 반복을 위해 테스트를 간소화합니다."
            )
            recommendations.append("문서화를 생략하고 코드에 집중합니다.")

        elif scale == ProjectScale.ENTERPRISE:
            recommendations.append(
                "대규모 프로젝트이므로 Document Sharding을 활성화합니다."
            )
            recommendations.append("보안 감사 및 컴플라이언스 검증을 수행합니다.")
            recommendations.append("병렬 실행으로 처리 시간을 단축합니다.")

            if len(analysis.features) > 15:
                recommendations.append(
                    f"{len(analysis.features)}개 기능이 감지됨. 스프린트 단위로 분할을 권장합니다."
                )

        else:  # STANDARD
            recommendations.append("표준 워크플로우를 사용합니다.")
            recommendations.append("품질과 속도의 균형을 맞춥니다.")

        # 복잡도 기반 권장사항
        if analysis.complexity_score >= 8:
            recommendations.append(
                "복잡도가 높으므로 Reflection Engine으로 품질을 보장합니다."
            )

        # 제약사항 기반 권장사항
        if analysis.constraints:
            recommendations.append(
                f"{len(analysis.constraints)}개 제약사항이 있으므로 검증을 강화합니다."
            )

        return recommendations
