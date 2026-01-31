"""
Test Scenario Generator

기능 명세에서 테스트 시나리오 자동 생성 (BDD 스타일)
"""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..models.specifications import FeatureSpec, ConcretizedRequirement
from ..utils import JsonExtractor


class BDDScenario(BaseModel):
    """BDD (Given-When-Then) 시나리오"""

    scenario_id: str
    scenario_name: str
    given: List[str] = Field(default_factory=list, description="사전 조건")
    when: List[str] = Field(default_factory=list, description="사용자 행동")
    then: List[str] = Field(default_factory=list, description="예상 결과")


class TestScenario(BaseModel):
    """테스트 시나리오"""

    scenario_id: str
    feature_id: str
    feature_name: str
    description: str
    bdd: BDDScenario
    test_type: str = "functional"  # functional, integration, e2e
    priority: str = "medium"  # low, medium, high, critical
    test_data: Dict[str, Any] = Field(default_factory=dict)


class TestScenarioGenerator:
    """테스트 시나리오 생성기"""

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: LLM 클라이언트 (선택적)
        """
        self.llm = llm_client

    def generate_scenarios(
        self, features: List[FeatureSpec], golden_data: Optional[ConcretizedRequirement] = None
    ) -> List[TestScenario]:
        """
        기능 목록에서 테스트 시나리오 생성

        Args:
            features: 기능 목록
            golden_data: Golden Data (선택적, 추가 컨텍스트 제공)

        Returns:
            List[TestScenario]
        """
        scenarios = []

        for feature in features:
            # 1. Acceptance Criteria → Test Scenario
            for i, criterion in enumerate(feature.acceptance_criteria, 1):
                scenario = self._criterion_to_scenario(feature, criterion, i)
                scenarios.append(scenario)

            # 2. 추가 엣지 케이스 생성
            edge_cases = self._generate_edge_cases(feature)
            scenarios.extend(edge_cases)

        return scenarios

    def _criterion_to_scenario(
        self, feature: FeatureSpec, criterion: str, index: int
    ) -> TestScenario:
        """인수 기준을 테스트 시나리오로 변환"""

        scenario_id = f"{feature.id}_test_{index}"

        # LLM으로 BDD 시나리오 생성
        if self.llm:
            bdd = self._generate_bdd_with_llm(feature, criterion)
        else:
            bdd = self._generate_bdd_heuristic(feature, criterion)

        return TestScenario(
            scenario_id=scenario_id,
            feature_id=feature.id,
            feature_name=feature.name,
            description=f"Test: {criterion}",
            bdd=bdd,
            test_type=self._infer_test_type(criterion),
            priority=feature.priority,
        )

    def _generate_bdd_with_llm(
        self, feature: FeatureSpec, criterion: str
    ) -> BDDScenario:
        """LLM을 사용하여 BDD 시나리오 생성"""

        prompt = f"""
기능명: {feature.name}
설명: {feature.description}
인수 기준: {criterion}

이를 BDD (Given-When-Then) 시나리오로 변환하세요:

응답 형식 (JSON):
{{
  "scenario_name": "시나리오명",
  "given": ["사전 조건1", "사전 조건2"],
  "when": ["사용자 행동1", "사용자 행동2"],
  "then": ["예상 결과1", "예상 결과2"]
}}
"""

        try:
            response = self.llm.invoke(prompt)
            data = JsonExtractor.safe_parse(response, default={})

            return BDDScenario(
                scenario_id=f"bdd_{feature.id}",
                scenario_name=data.get("scenario_name", criterion),
                given=data.get("given", []),
                when=data.get("when", []),
                then=data.get("then", []),
            )
        except Exception:
            # Fallback
            return self._generate_bdd_heuristic(feature, criterion)

    def _generate_bdd_heuristic(
        self, feature: FeatureSpec, criterion: str
    ) -> BDDScenario:
        """휴리스틱 기반 BDD 시나리오 생성"""

        # 간단한 규칙 기반 생성
        given = [f"{feature.name} 기능이 준비됨"]
        when = [f"사용자가 {criterion}을 수행"]
        then = [f"{criterion} 결과가 정상적으로 반환됨"]

        return BDDScenario(
            scenario_id=f"bdd_{feature.id}",
            scenario_name=criterion,
            given=given,
            when=when,
            then=then,
        )

    def _generate_edge_cases(self, feature: FeatureSpec) -> List[TestScenario]:
        """엣지 케이스 테스트 시나리오 생성"""

        edge_cases = []

        # 일반적인 엣지 케이스 패턴
        edge_case_templates = [
            {
                "name": "빈 입력 처리",
                "given": ["시스템이 준비됨"],
                "when": ["빈 입력을 제공함"],
                "then": ["적절한 에러 메시지가 반환됨"],
            },
            {
                "name": "잘못된 입력 처리",
                "given": ["시스템이 준비됨"],
                "when": ["잘못된 형식의 입력을 제공함"],
                "then": ["입력 검증 에러가 발생함"],
            },
            {
                "name": "중복 처리",
                "given": ["동일한 데이터가 이미 존재함"],
                "when": ["중복 생성을 시도함"],
                "then": ["중복 에러가 반환됨"],
            },
        ]

        for i, template in enumerate(edge_case_templates, 1):
            scenario_id = f"{feature.id}_edge_{i}"
            bdd = BDDScenario(
                scenario_id=scenario_id,
                scenario_name=template["name"],
                given=template["given"],
                when=template["when"],
                then=template["then"],
            )

            edge_cases.append(
                TestScenario(
                    scenario_id=scenario_id,
                    feature_id=feature.id,
                    feature_name=feature.name,
                    description=f"Edge Case: {template['name']}",
                    bdd=bdd,
                    test_type="functional",
                    priority="low",
                )
            )

        return edge_cases

    def _infer_test_type(self, criterion: str) -> str:
        """인수 기준에서 테스트 타입 추론"""

        criterion_lower = criterion.lower()

        # 키워드 기반 분류
        if any(
            keyword in criterion_lower
            for keyword in ["통합", "integration", "api", "연동"]
        ):
            return "integration"
        elif any(
            keyword in criterion_lower for keyword in ["e2e", "전체", "사용자 시나리오"]
        ):
            return "e2e"
        else:
            return "functional"


def generate_test_scenarios(
    features: List[FeatureSpec],
    golden_data: Optional[ConcretizedRequirement] = None,
    llm_client=None,
) -> List[TestScenario]:
    """
    Helper function - 테스트 시나리오 생성

    Args:
        features: 기능 목록
        golden_data: Golden Data
        llm_client: LLM 클라이언트

    Returns:
        List[TestScenario]
    """
    generator = TestScenarioGenerator(llm_client=llm_client)
    return generator.generate_scenarios(features, golden_data)
