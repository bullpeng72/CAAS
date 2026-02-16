"""
Requirement Analyst Agent

Expert agent responsible for Phase 1 (Discovery):
- Analyzes natural language requirements
- Validates against Golden Data
- Identifies functional and non-functional requirements
- Extracts success criteria and constraints
"""

from typing import Any, Dict, List, Optional

from caas_framework.agents.base import AgentPhase, BaseExpertAgent, ValidationIssue
from caas_framework.agents.executors import GoldenDataEnhancer, RefinementExecutor
from caas_framework.agents.registry import register_agent
from caas_framework.models.specifications import ConcretizedRequirement
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils.logger import get_logger

logger = get_logger()


@register_agent(phase=AgentPhase.DISCOVERY)
class RequirementAnalystAgent(BaseExpertAgent):
    """
    Requirement Analyst Agent

    Specializes in analyzing requirements and ensuring alignment
    with Golden Data features and acceptance criteria.
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        golden_data: Optional[ConcretizedRequirement] = None,
    ):
        super().__init__(llm_plugin, golden_data, AgentPhase.DISCOVERY)

    @property
    def agent_name(self) -> str:
        return "RequirementAnalyst"

    @property
    def agent_role(self) -> str:
        return "Expert Requirements Analyst"

    @property
    def agent_expertise(self) -> List[str]:
        return [
            "Requirements elicitation",
            "Functional requirement analysis",
            "Non-functional requirement analysis",
            "Acceptance criteria definition",
            "Constraint identification",
            "Traceability matrix creation",
        ]

    async def _do_work(
        self,
        requirement: Optional[str],
        context: Optional[Dict[str, Any]],
        previous_outputs: Optional[Dict[AgentPhase, Any]],
    ) -> Dict[str, Any]:
        """
        Analyze requirements and produce structured analysis.

        Returns:
            Dict with:
            - functional_requirements: List[Dict]
            - non_functional_requirements: Dict
            - success_criteria: List[str]
            - constraints: List[str]
            - risks: List[Dict]
            - traceability_map: Dict (feature_id -> requirements)
        """
        context_summary = self._build_context_summary(context, previous_outputs)

        prompt = self._build_analysis_prompt(requirement, context_summary)

        # Use unified LLM helper
        analysis = await self._invoke_llm_structured(
            prompt=prompt,
            expected_fields=[
                "functional_requirements",
                "non_functional_requirements",
                "constraints",
                "success_criteria",
            ],
            fallback_factory=lambda: self._create_fallback_analysis(requirement),
        )

        # ✅ P0 Fix (Bug 1): Deduplicate features before enhancement
        if "functional_requirements" in analysis and analysis["functional_requirements"]:
            original_count = len(analysis["functional_requirements"])
            analysis["functional_requirements"] = self._deduplicate_features(
                analysis["functional_requirements"]
            )
            deduplicated_count = len(analysis["functional_requirements"])

            if deduplicated_count < original_count:
                logger.info(
                    f"[RequirementAnalyst] Feature deduplication: "
                    f"{original_count} → {deduplicated_count} features "
                    f"(-{original_count - deduplicated_count} duplicates)"
                )

        # Enhance with Golden Data traceability
        if self.golden_data:
            analysis = self._enhance_with_golden_data(analysis)

        return analysis

    def _build_analysis_prompt(self, requirement: str, context: str) -> str:
        """Build LLM prompt for requirement analysis."""
        # ✅ v0.5.0: 한국어 출력 강제 (P0 수정)
        # Use base class template method with custom output format
        output_format = {
            "functional_requirements": [
                {
                    "id": "FR1",
                    "description": "기능 요구사항 상세 설명",
                    "priority": "high|medium|low (높음|중간|낮음)",
                    "source": "어떤 기능이나 요구사항에서 도출되었는지",
                    "acceptance_criteria": ["수용 기준 1", "수용 기준 2"],
                }
            ],
            "non_functional_requirements": {
                "performance": ["성능 요구사항 1", "성능 요구사항 2"],
                "security": ["보안 요구사항 1", "보안 요구사항 2"],
                "scalability": ["확장성 요구사항 1", "확장성 요구사항 2"],
                "usability": ["사용성 요구사항 1", "사용성 요구사항 2"],
                "reliability": ["신뢰성 요구사항 1", "신뢰성 요구사항 2"],
            },
            "success_criteria": [
                "측정 가능한 성공 기준 1",
                "측정 가능한 성공 기준 2",
            ],
            "constraints": ["기술적 제약사항 1", "비즈니스 제약사항 2"],
            "risks": [
                {
                    "risk": "위험 설명",
                    "impact": "high|medium|low (높음|중간|낮음)",
                    "mitigation": "완화 전략",
                }
            ],
            "assumptions": ["가정사항 1", "가정사항 2"],
            "dependencies": ["외부 의존성 1", "외부 의존성 2"],
            "boundaries": {
                "always_allowed": [
                    "프로젝트 디렉토리의 파일 읽기",
                    "프로젝트 디렉토리에 쓰기",
                    "requirements.txt에서 패키지 설치",
                ],
                "ask_first": [
                    "외부 서비스에 API 호출",
                    "시스템 설정 변경",
                    "파일이나 디렉토리 삭제",
                ],
                "never_allowed": [
                    "sudo로 셸 명령 실행",
                    "프로젝트 외부 파일 수정",
                    "보안 기능 비활성화",
                ],
            },
        }

        guidelines = [
            "**중요: 모든 텍스트 값(description, acceptance_criteria, risk, mitigation 등)을 한국어로 작성하세요**",
            "JSON 키(key)는 영어로 유지하되, 값(value)은 반드시 한국어로 작성하세요",
            "Golden Data의 기능들과 철저히 정렬하세요",
            "모든 기능 요구사항에 명확한 수용 기준을 포함하세요",
            "기술적 제약사항과 비즈니스 제약사항을 모두 식별하세요",
            "중요: 요구사항의 필요에 따라 보안 경계를 정의하세요",
            "위험한 작업을 방지하기 위해 'never_allowed'를 항상 설정하세요",
            "위험하거나 비용이 많이 드는 작업에는 'ask_first'를 사용하세요",
        ]

        # Use standardized template method from base class
        return self._build_standard_prompt(
            requirement=requirement,
            output_format=output_format,
            guidelines=guidelines,
            context={"additional_context": context} if context else None,
        )

    def _create_fallback_analysis(self, requirement: str) -> Dict[str, Any]:
        """Create basic analysis structure when LLM fails."""
        # ✅ Week 2-1: Use base helper for consistent fallback logging
        self._log_fallback_usage(
            reason="LLM generation failed - using basic analysis structure",
            fallback_type="requirement_analysis_fallback"
        )

        return {
            "functional_requirements": [
                {
                    "id": "FR1",
                    "description": requirement[:200],
                    "priority": "high",
                    "source": "Original requirement",
                    "acceptance_criteria": ["System should fulfill the requirement"],
                }
            ],
            "non_functional_requirements": {
                "performance": [],
                "security": [],
                "scalability": [],
                "usability": [],
                "reliability": [],
            },
            "success_criteria": ["System is operational"],
            "constraints": [],
            "risks": [],
            "assumptions": [],
            "dependencies": [],
        }

    def _deduplicate_features(self, features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate features based on semantic similarity.

        Deduplication strategy:
        1. Exact name match → Remove duplicates
        2. Semantic similarity (name + description) → Keep highest priority
        3. If features have similar acceptance criteria → Merge

        Args:
            features: List of feature dictionaries

        Returns:
            Deduplicated list of features

        Example:
            Input: [{"name": "Keyword Input", "priority": "high"},
                    {"name": "Keyword Input", "priority": "medium"}]
            Output: [{"name": "Keyword Input", "priority": "high"}]
        """
        if not features:
            return []

        from difflib import SequenceMatcher

        def calculate_similarity(str1: str, str2: str) -> float:
            """Calculate string similarity using SequenceMatcher."""
            return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

        unique_features = []
        duplicate_count = 0

        for feature in features:
            # Check for exact name match
            exact_match = next(
                (f for f in unique_features if f.get("name") == feature.get("name")),
                None
            )

            if exact_match:
                # Exact duplicate found - merge or skip
                duplicate_count += 1
                logger.debug(
                    f"[RequirementAnalyst] Duplicate feature '{feature.get('name')}' - "
                    f"keeping higher priority"
                )

                # Keep higher priority feature
                priority_map = {"high": 3, "medium": 2, "low": 1}
                current_priority = priority_map.get(feature.get("priority", "medium"), 2)
                existing_priority = priority_map.get(exact_match.get("priority", "medium"), 2)

                if current_priority > existing_priority:
                    # Replace with higher priority
                    unique_features.remove(exact_match)
                    unique_features.append(feature)
                continue

            # Check for semantic similarity (name + description)
            is_duplicate = False
            feature_name = feature.get("name", "")
            feature_desc = feature.get("description", "")

            for existing in unique_features:
                existing_name = existing.get("name", "")
                existing_desc = existing.get("description", "")

                # Calculate similarity
                name_similarity = calculate_similarity(feature_name, existing_name)
                desc_similarity = calculate_similarity(feature_desc, existing_desc)

                # Combined similarity (weighted: name 60%, description 40%)
                combined_similarity = (name_similarity * 0.6) + (desc_similarity * 0.4)

                # 85% threshold for semantic duplicates
                if combined_similarity > 0.85:
                    is_duplicate = True
                    duplicate_count += 1
                    logger.debug(
                        f"[RequirementAnalyst] Semantic duplicate detected: "
                        f"'{feature_name}' similar to '{existing_name}' "
                        f"(similarity: {combined_similarity:.2f})"
                    )
                    break

            if not is_duplicate:
                unique_features.append(feature)

        if duplicate_count > 0:
            logger.info(
                f"[RequirementAnalyst] Removed {duplicate_count} duplicate features "
                f"({len(features)} → {len(unique_features)})"
            )

        return unique_features

    def _enhance_with_golden_data(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance analysis with Golden Data traceability."""
        enhancer = GoldenDataEnhancer(self.golden_data)
        return enhancer.enhance_with_traceability(
            output=analysis,
            items_key="functional_requirements",
            item_text_keys=["description"],
            item_id_key="id",
        )

    async def _refine_implementation(
        self,
        output: Dict[str, Any],
        issues: List[ValidationIssue],
        context: Optional[Dict[str, Any]],
        iteration: int,
    ) -> Dict[str, Any]:
        """
        Refine analysis based on validation feedback.

        Uses RefinementExecutor for standardized refinement workflow.
        """
        executor = RefinementExecutor.create_for_agent(
            agent=self,
            agent_role="Expert Requirements Analyst",
            output_type="requirements analysis",
        )

        return await executor.refine_output(
            output=output,
            issues=issues,
            iteration=iteration,
            guidelines=[
                "Address each issue specifically",
                "Maintain consistency with Golden Data features",
                "Ensure all functional requirements have acceptance criteria",
                "Verify traceability to Golden Data features",
            ],
        )
