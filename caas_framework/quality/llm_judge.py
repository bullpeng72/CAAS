"""
LLM-as-a-Judge Quality Evaluation

LLM을 judge로 사용하여 생성된 코드의 품질을 자동으로 평가합니다.
다차원 평가 기준을 통해 코드의 정확성, 가독성, 보안성, 성능 등을 검증합니다.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from caas_framework.config.settings import LLMConstants
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils import PromptBuilder, ResponseParser


class EvaluationCategory(str, Enum):
    """평가 카테고리"""

    CORRECTNESS = "correctness"  # 정확성
    READABILITY = "readability"  # 가독성
    SECURITY = "security"  # 보안성
    PERFORMANCE = "performance"  # 성능
    BEST_PRACTICES = "best_practices"  # 모범 사례
    MAINTAINABILITY = "maintainability"  # 유지보수성


@dataclass
class CriterionScore:
    """개별 평가 기준 점수"""

    criterion: str  # 평가 기준
    category: EvaluationCategory  # 카테고리
    score: float  # 점수 (0-10)
    reasoning: str  # 점수 이유
    suggestions: str  # 개선 제안
    weight: float = 1.0  # 가중치


@dataclass
class EvaluationResult:
    """평가 결과"""

    overall_score: float  # 전체 점수 (0-10)
    criteria_scores: List[CriterionScore]  # 개별 기준 점수들
    passed: bool  # 통과 여부 (overall_score >= 7.0)
    summary: str  # 평가 요약
    issues: List[str]  # 발견된 문제점
    recommendations: List[str]  # 개선 권장사항

    def get_category_score(self, category: EvaluationCategory) -> float:
        """특정 카테고리의 평균 점수"""
        category_scores = [cs.score for cs in self.criteria_scores if cs.category == category]
        return sum(category_scores) / len(category_scores) if category_scores else 0.0

    def get_weighted_score(self) -> float:
        """가중 평균 점수"""
        total_weight = sum(cs.weight for cs in self.criteria_scores)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(cs.score * cs.weight for cs in self.criteria_scores)
        return weighted_sum / total_weight


class CodeQualityCriteria:
    """코드 품질 평가 기준"""

    @staticmethod
    def get_crewai_code_criteria() -> List[Dict[str, Any]]:
        """CrewAI 코드 품질 평가 기준"""
        return [
            {
                "criterion": "CrewAI framework usage is correct",
                "category": EvaluationCategory.CORRECTNESS,
                "description": "Uses proper CrewAI imports and follows framework patterns",
                "weight": 2.0,
            },
            {
                "criterion": "Agent definitions are complete and clear",
                "category": EvaluationCategory.CORRECTNESS,
                "description": "All agents have role, goal, backstory, and appropriate tools",
                "weight": 1.5,
            },
            {
                "criterion": "Task definitions have clear objectives",
                "category": EvaluationCategory.CORRECTNESS,
                "description": "Tasks have description, expected_output, and assigned agent",
                "weight": 1.5,
            },
            {
                "criterion": "Code is readable and well-structured",
                "category": EvaluationCategory.READABILITY,
                "description": "Clear variable names, proper formatting, and good organization",
                "weight": 1.0,
            },
            {
                "criterion": "No security vulnerabilities",
                "category": EvaluationCategory.SECURITY,
                "description": "No hardcoded credentials, SQL injection risks, or unsafe operations",
                "weight": 1.5,
            },
            {
                "criterion": "Follows Python best practices",
                "category": EvaluationCategory.BEST_PRACTICES,
                "description": "PEP 8 compliance, proper error handling, and Pythonic patterns",
                "weight": 1.0,
            },
            {
                "criterion": "Code is maintainable",
                "category": EvaluationCategory.MAINTAINABILITY,
                "description": "Easy to understand, modify, and extend",
                "weight": 1.0,
            },
            {
                "criterion": "Efficient resource usage",
                "category": EvaluationCategory.PERFORMANCE,
                "description": "No obvious performance issues or resource leaks",
                "weight": 0.8,
            },
        ]


class LLMJudge:
    """
    LLM-as-a-Judge 평가 엔진

    LLM을 사용하여 생성된 코드의 품질을 다차원으로 평가합니다.
    """

    def __init__(self, llm_plugin: LLMPlugin, passing_score: float = 7.0):
        """
        Args:
            llm_plugin: LLM 플러그인
            passing_score: 통과 기준 점수 (기본: 7.0/10)
        """
        self.llm = llm_plugin
        self.passing_score = passing_score

    async def evaluate_code_quality(
        self, code_files: Dict[str, str], context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """
        생성된 코드의 품질을 평가

        Args:
            code_files: 파일명 -> 코드 내용 매핑
            context: 추가 컨텍스트 (agents, tasks 등)

        Returns:
            EvaluationResult: 평가 결과
        """
        # 평가 기준 가져오기
        criteria_specs = CodeQualityCriteria.get_crewai_code_criteria()

        # 평가 프롬프트 생성
        prompt = self._build_evaluation_prompt(code_files, criteria_specs, context)

        # LLM 호출
        response = await self.llm.ainvoke(
            messages=[{"role": "user", "content": prompt}],
            response_format=LLMConstants.RESPONSE_FORMAT_JSON,
            temperature=LLMConstants.TEMPERATURE_PRECISE,
            max_tokens=2000,
        )

        # 응답 파싱
        evaluation_data = ResponseParser.parse_structured_response(
            response,
            expected_fields=["criteria_scores", "issues", "recommendations"],
            fallback_factory=lambda: self._create_fallback_evaluation(criteria_specs),
        )

        # EvaluationResult 생성
        return self._parse_evaluation_result(evaluation_data, criteria_specs)

    def _build_evaluation_prompt(
        self,
        code_files: Dict[str, str],
        criteria_specs: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """평가 프롬프트 생성"""

        builder = PromptBuilder("evaluate CrewAI code quality")

        # Task 설명
        builder.add_task(
            """You are an expert code reviewer evaluating the quality of generated CrewAI code.

Analyze the code carefully and provide detailed, objective feedback based on the evaluation criteria.
Be thorough but fair - code doesn't need to be perfect, but should meet professional standards."""
        )

        # Code files 추가
        code_summary = {}
        for filename, content in code_files.items():
            # 긴 파일은 요약
            if len(content) > 500:
                code_summary[filename] = f"{content[:500]}...\n(Total: {len(content)} chars)"
            else:
                code_summary[filename] = content

        builder.add_context("Code Files", code_summary, format_as_json=True)

        # Context 추가
        if context:
            builder.add_context("Additional Context", context, format_as_json=True)

        # 평가 기준 추가
        criteria_list = []
        for i, spec in enumerate(criteria_specs, 1):
            criteria_list.append(
                f"{i}. {spec['criterion']} ({spec['category'].value})\n"
                f"   Description: {spec['description']}\n"
                f"   Weight: {spec['weight']}"
            )

        builder.add_context("Evaluation Criteria", "\n\n".join(criteria_list))

        # 출력 형식
        builder.add_output_format(
            {
                "criteria_scores": [
                    {
                        "criterion": "string (exact match from criteria)",
                        "score": "float (0-10, where 10 is excellent)",
                        "reasoning": "string (why you gave this score)",
                        "suggestions": "string (how to improve, or 'None' if score >= 8)",
                    }
                ],
                "issues": ["list of critical issues found"],
                "recommendations": ["list of improvement recommendations"],
                "summary": "string (overall assessment)",
            },
            "Provide your evaluation in JSON format:",
        )

        # Guidelines
        builder.add_guidelines(
            [
                "Evaluate each criterion independently on a 0-10 scale",
                "Score 10 = Excellent, 8-9 = Good, 6-7 = Acceptable, 4-5 = Needs work, 0-3 = Poor",
                "Provide specific, actionable feedback in your reasoning",
                "Be objective - focus on code quality, not personal preferences",
                "Consider the context - this is auto-generated code, not hand-written",
                "List critical issues separately from minor improvements",
                "Keep feedback constructive and professional",
            ]
        )

        return builder.build()

    def _parse_evaluation_result(
        self, evaluation_data: Dict[str, Any], criteria_specs: List[Dict[str, Any]]
    ) -> EvaluationResult:
        """평가 데이터를 EvaluationResult로 변환"""

        # CriterionScore 리스트 생성
        criteria_scores = []
        for score_data in evaluation_data.get("criteria_scores", []):
            # Find matching spec for category and weight
            criterion_name = score_data.get("criterion", "")
            matching_spec = next(
                (spec for spec in criteria_specs if spec["criterion"] == criterion_name), None
            )

            category = EvaluationCategory.CORRECTNESS  # default
            weight = 1.0  # default

            if matching_spec:
                category = matching_spec["category"]
                weight = matching_spec["weight"]

            criteria_scores.append(
                CriterionScore(
                    criterion=criterion_name,
                    category=category,
                    score=float(score_data.get("score", 0)),
                    reasoning=score_data.get("reasoning", ""),
                    suggestions=score_data.get("suggestions", ""),
                    weight=weight,
                )
            )

        # 가중 평균 계산
        if criteria_scores:
            total_weight = sum(cs.weight for cs in criteria_scores)
            overall_score = sum(cs.score * cs.weight for cs in criteria_scores) / total_weight
        else:
            overall_score = 0.0

        # 통과 여부
        passed = overall_score >= self.passing_score

        return EvaluationResult(
            overall_score=overall_score,
            criteria_scores=criteria_scores,
            passed=passed,
            summary=evaluation_data.get("summary", ""),
            issues=evaluation_data.get("issues", []),
            recommendations=evaluation_data.get("recommendations", []),
        )

    def _create_fallback_evaluation(self, criteria_specs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """LLM 호출 실패 시 fallback 평가"""

        return {
            "criteria_scores": [
                {
                    "criterion": spec["criterion"],
                    "score": 7.0,  # Neutral score
                    "reasoning": "Unable to evaluate - LLM evaluation failed",
                    "suggestions": "Manual review recommended",
                }
                for spec in criteria_specs
            ],
            "issues": ["LLM evaluation failed - manual review required"],
            "recommendations": ["Verify code manually before deployment"],
            "summary": "Automated evaluation unavailable. Code generated successfully but requires manual review.",
        }

    def evaluate_sync(
        self, code_files: Dict[str, str], context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """
        동기 버전 평가 (테스트용)

        Args:
            code_files: 파일명 -> 코드 내용 매핑
            context: 추가 컨텍스트

        Returns:
            EvaluationResult: 평가 결과
        """
        import asyncio

        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 이미 실행 중인 루프가 있으면 새 태스크 생성
            return asyncio.create_task(self.evaluate_code_quality(code_files, context))
        else:
            # 새 루프 실행
            return loop.run_until_complete(self.evaluate_code_quality(code_files, context))
