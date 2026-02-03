"""
Requirement Expander

요구사항 자동 확장 - 갭을 채워 완전한 요구사항 생성
"""

from typing import Dict, List

from pydantic import BaseModel, Field

from ..models.specifications import (
    ConcretizedRequirement,
    DataModel,
    FeatureSpec,
    NonFunctionalRequirements,
    UIComponent,
)
from ..utils import JsonExtractor, ObjectAccessor
from .gap_analyzer import GapType, RequirementGap


class AutoFixResult(BaseModel):
    """자동 수정 결과"""

    features: List[FeatureSpec] = Field(default_factory=list)
    data_models: List[DataModel] = Field(default_factory=list)
    ui_components: List[UIComponent] = Field(default_factory=list)
    nfr_updates: Dict[str, str] = Field(default_factory=dict)
    fixed_gap_count: int = 0


class BestPractice(BaseModel):
    """모범 사례"""

    domain: str
    category: str
    recommendation: str
    reasoning: str


class ExpandedRequirement(BaseModel):
    """확장된 요구사항"""

    original: ConcretizedRequirement
    auto_expanded_features: List[FeatureSpec] = Field(default_factory=list)
    auto_expanded_data_models: List[DataModel] = Field(default_factory=list)
    auto_expanded_ui_components: List[UIComponent] = Field(default_factory=list)
    suggested_nfr: NonFunctionalRequirements = Field(
        default_factory=NonFunctionalRequirements
    )
    best_practices: List[BestPractice] = Field(default_factory=list)
    remaining_gaps: List[RequirementGap] = Field(default_factory=list)
    expansion_summary: str = ""


class RequirementExpander:
    """요구사항 자동 확장기"""

    def __init__(self, llm_client, pattern_library=None):
        """
        Args:
            llm_client: LLM 클라이언트
            pattern_library: 패턴 라이브러리 (선택적)
        """
        self.llm = llm_client
        self.patterns = pattern_library

    def expand_requirement(
        self,
        requirement: str,
        concretized: ConcretizedRequirement,
        gaps: List[RequirementGap],
    ) -> ExpandedRequirement:
        """
        요구사항 확장

        Args:
            requirement: 원본 요구사항
            concretized: 구체화된 요구사항
            gaps: 탐지된 갭 목록

        Returns:
            ExpandedRequirement: 확장된 요구사항
        """
        # 1. Auto-fixable gaps 자동 해결
        auto_fixes = self._apply_auto_fixes(concretized, gaps)

        # 2. Best Practice 적용
        best_practices = self._apply_best_practices(concretized)

        # 3. 확장 요약 생성
        summary = self._generate_expansion_summary(auto_fixes, best_practices)

        # 4. 남은 갭 (수동 입력 필요)
        remaining_gaps = [g for g in gaps if not g.auto_fixable]

        return ExpandedRequirement(
            original=concretized,
            auto_expanded_features=auto_fixes.features,
            auto_expanded_data_models=auto_fixes.data_models,
            auto_expanded_ui_components=auto_fixes.ui_components,
            suggested_nfr=self._build_nfr_from_fixes(concretized, auto_fixes),
            best_practices=best_practices,
            remaining_gaps=remaining_gaps,
            expansion_summary=summary,
        )

    def _apply_auto_fixes(
        self, spec: ConcretizedRequirement, gaps: List[RequirementGap]
    ) -> AutoFixResult:
        """자동 수정 가능한 갭 해결"""
        auto_fixable = [g for g in gaps if g.auto_fixable]

        if not auto_fixable:
            return AutoFixResult()

        # LLM을 사용하여 자동 확장
        result = AutoFixResult()

        for gap in auto_fixable:
            if gap.gap_type == GapType.MISSING_DATA_MODEL:
                # 데이터 모델 생성
                new_models = self._generate_data_models(spec, gap)
                result.data_models.extend(new_models)

            elif gap.gap_type == GapType.MISSING_ACCEPTANCE:
                # 인수 기준 생성
                criteria = self._generate_acceptance_criteria(spec, gap)
                # 기존 기능에 추가
                features = spec.features if spec.features else []
                for feature in features:
                    if feature.id == gap.related_feature_id:
                        result.features.append(
                            FeatureSpec(
                                id=feature.id,
                                name=feature.name,
                                description=feature.description,
                                priority=feature.priority,
                                acceptance_criteria=criteria,
                            )
                        )

            elif gap.gap_type == GapType.MISSING_UI_SPEC:
                # UI 컴포넌트 생성
                ui_comps = self._generate_ui_components(spec)
                result.ui_components.extend(ui_comps)

            elif gap.gap_type in [
                GapType.MISSING_PERFORMANCE,
                GapType.MISSING_NFR,
                GapType.MISSING_ERROR_HANDLING,
            ]:
                # NFR 생성
                nfr_updates = self._generate_nfr(spec, gap)
                result.nfr_updates.update(nfr_updates)

            result.fixed_gap_count += 1

        return result

    def _generate_data_models(
        self, spec: ConcretizedRequirement, gap: RequirementGap
    ) -> List[DataModel]:
        """데이터 모델 자동 생성"""
        if not self.llm:
            return []

        prompt = f"""
도메인: {spec.domain}
프로젝트: {spec.project_name}
설명: {spec.description}

기능 목록:
{self._format_features(spec.features)}

위 프로젝트에 필요한 데이터 모델을 생성하세요.
각 데이터 모델은 다음 형식으로:

{{
  "entity_name": "엔티티명",
  "attributes": ["속성1", "속성2", ...],
  "relationships": ["관계 설명"]
}}

응답은 JSON 배열로:
[{{...}}, {{...}}]
"""

        try:
            response = self.llm.invoke(prompt)
            # JSON 파싱
            models_data = JsonExtractor.safe_parse(response, default=[])

            return [
                DataModel(
                    entity_name=m["entity_name"],
                    attributes=m.get("attributes", []),
                    relationships=m.get("relationships", []),
                )
                for m in models_data
            ]
        except Exception:
            # LLM 실패 시 기본값
            return [
                DataModel(
                    entity_name=spec.project_name.replace(" ", ""),
                    attributes=["id", "created_at", "updated_at"],
                    relationships=[],
                )
            ]

    def _generate_acceptance_criteria(
        self, spec: ConcretizedRequirement, gap: RequirementGap
    ) -> List[str]:
        """인수 기준 자동 생성"""
        if not self.llm:
            return ["기능이 정상적으로 동작함", "에러 없이 완료됨"]

        # 관련 기능 찾기
        features = spec.features if spec.features else []
        feature = next((f for f in features if f.id == gap.related_feature_id), None)
        if not feature:
            return []

        prompt = f"""
기능명: {feature.name}
설명: {feature.description}

이 기능의 인수 기준(Acceptance Criteria)을 생성하세요.
- 측정 가능해야 함
- Given-When-Then 형식 권장
- 3~5개 항목

응답은 JSON 배열로:
["기준1", "기준2", ...]
"""

        try:
            response = self.llm.invoke(prompt)
            criteria = JsonExtractor.safe_parse(response, default=[])
            return criteria if isinstance(criteria, list) else []
        except Exception:
            return [
                f"{feature.name} 기능이 정상적으로 동작함",
                "예상된 결과가 반환됨",
                "에러 없이 완료됨",
            ]

    def _generate_ui_components(
        self, spec: ConcretizedRequirement
    ) -> List[UIComponent]:
        """UI 컴포넌트 자동 생성"""
        if not self.llm:
            return []

        prompt = f"""
도메인: {spec.domain}
프로젝트: {spec.project_name}

기능 목록:
{self._format_features(spec.features)}

이 프로젝트에 필요한 UI 페이지/컴포넌트를 생성하세요.

응답은 JSON 배열로:
[
  {{
    "page_name": "페이지명",
    "component_type": "form|table|chart|dashboard",
    "description": "설명"
  }}
]
"""

        try:
            response = self.llm.invoke(prompt)
            comps_data = JsonExtractor.safe_parse(response, default=[])

            return [
                UIComponent(
                    page_name=c["page_name"],
                    component_type=c["component_type"],
                    description=c["description"],
                )
                for c in comps_data
            ]
        except Exception:
            # 기본 UI
            return [
                UIComponent(
                    page_name="홈",
                    component_type="dashboard",
                    description="메인 대시보드",
                ),
                UIComponent(
                    page_name="목록",
                    component_type="table",
                    description="데이터 목록 조회",
                ),
            ]

    def _generate_nfr(
        self, spec: ConcretizedRequirement, gap: RequirementGap
    ) -> Dict[str, str]:
        """비기능 요구사항 생성"""
        nfr_updates = {}

        if gap.gap_type == GapType.MISSING_PERFORMANCE:
            nfr_updates["performance"] = self._get_default_performance_nfr(spec.domain)

        elif gap.gap_type == GapType.MISSING_NFR:
            if "확장성" in gap.description:
                nfr_updates["scalability"] = "수평 확장 가능한 아키텍처"
            if "신뢰성" in gap.description:
                nfr_updates["reliability"] = "99.9% 가용성 목표"

        elif gap.gap_type == GapType.MISSING_ERROR_HANDLING:
            nfr_updates[
                "reliability"
            ] = "모든 에러를 로깅하고 사용자 친화적 메시지 제공"

        return nfr_updates

    def _get_default_performance_nfr(self, domain: str) -> str:
        """도메인별 기본 성능 NFR"""
        defaults = {
            "E_COMMERCE": "페이지 로드 2초 이내, 1000명 동시 사용자 지원",
            "TASK_MANAGEMENT": "응답 시간 1초 이내, 100명 동시 사용자 지원",
            "HEALTHCARE": "실시간 처리, 99.99% 가용성",
            "FINANCE": "트랜잭션 처리 1초 이내, 99.99% 가용성",
        }
        return defaults.get(domain, "응답 시간 3초 이내, 100명 동시 사용자 지원")

    def _apply_best_practices(self, spec: ConcretizedRequirement) -> List[BestPractice]:
        """도메인별 모범 사례 적용"""
        practices = []

        domain_practices = {
            "TASK_MANAGEMENT": [
                BestPractice(
                    domain="TASK_MANAGEMENT",
                    category="UX",
                    recommendation="드래그 앤 드롭으로 할일 우선순위 변경 기능 추가",
                    reasoning="사용자 경험 향상",
                ),
                BestPractice(
                    domain="TASK_MANAGEMENT",
                    category="기능",
                    recommendation="할일 필터링 및 검색 기능 추가",
                    reasoning="생산성 향상",
                ),
            ],
            "E_COMMERCE": [
                BestPractice(
                    domain="E_COMMERCE",
                    category="보안",
                    recommendation="PCI DSS 준수 결제 시스템 구현",
                    reasoning="신용카드 정보 보안",
                ),
                BestPractice(
                    domain="E_COMMERCE",
                    category="UX",
                    recommendation="장바구니 저장 및 복구 기능",
                    reasoning="구매 전환율 향상",
                ),
            ],
            "FINANCE": [
                BestPractice(
                    domain="FINANCE",
                    category="보안",
                    recommendation="2FA(이중 인증) 필수 적용",
                    reasoning="계정 보안 강화",
                ),
                BestPractice(
                    domain="FINANCE",
                    category="감사",
                    recommendation="모든 거래 내역 불변 로그 저장",
                    reasoning="감사 추적 및 규제 준수",
                ),
            ],
        }

        return domain_practices.get(spec.domain, [])

    def _build_nfr_from_fixes(
        self, original: ConcretizedRequirement, fixes: AutoFixResult
    ) -> NonFunctionalRequirements:
        """수정 사항을 반영한 NFR 생성"""
        nfr = original.non_functional_requirements

        # 기존 NFR에 업데이트 적용
        security = ObjectAccessor.get_value(nfr, "security") or fixes.nfr_updates.get(
            "security"
        )
        performance = ObjectAccessor.get_value(
            nfr, "performance"
        ) or fixes.nfr_updates.get("performance")
        scalability = ObjectAccessor.get_value(
            nfr, "scalability"
        ) or fixes.nfr_updates.get("scalability")
        reliability = ObjectAccessor.get_value(
            nfr, "reliability"
        ) or fixes.nfr_updates.get("reliability")

        return NonFunctionalRequirements(
            security=security,
            performance=performance,
            scalability=scalability,
            reliability=reliability,
        )

    def _generate_expansion_summary(
        self, fixes: AutoFixResult, practices: List[BestPractice]
    ) -> str:
        """확장 요약 생성"""
        summary_parts = []

        if fixes.fixed_gap_count > 0:
            summary_parts.append(f"✅ {fixes.fixed_gap_count}개 항목 자동 보완")

        if fixes.features:
            summary_parts.append(f"📋 {len(fixes.features)}개 기능 인수 기준 추가")

        if fixes.data_models:
            summary_parts.append(f"💾 {len(fixes.data_models)}개 데이터 모델 생성")

        if fixes.ui_components:
            summary_parts.append(f"🎨 {len(fixes.ui_components)}개 UI 컴포넌트 추가")

        if practices:
            summary_parts.append(f"💡 {len(practices)}개 모범 사례 제안")

        return "\n".join(summary_parts) if summary_parts else "확장 사항 없음"

    def _format_features(self, features: List[FeatureSpec]) -> str:
        """기능 목록 포맷팅"""
        return "\n".join([f"- {f.name}: {f.description}" for f in features])


def expand_requirement(
    requirement: str,
    concretized: ConcretizedRequirement,
    gaps: List[RequirementGap],
    llm_client,
) -> ExpandedRequirement:
    """
    Helper function - 요구사항 확장

    Args:
        requirement: 원본 요구사항
        concretized: 구체화된 요구사항
        gaps: 탐지된 갭
        llm_client: LLM 클라이언트

    Returns:
        ExpandedRequirement
    """
    expander = RequirementExpander(llm_client=llm_client)
    return expander.expand_requirement(requirement, concretized, gaps)
