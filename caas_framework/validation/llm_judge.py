"""
LLM-as-a-Judge Pattern

Uses LLM to evaluate quality of agent outputs with multi-dimensional criteria.
Goes beyond schema validation to assess semantic quality and design coherence.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from caas_framework.agents.base import AgentPhase
from caas_framework.plugins.llm.base import LLMPlugin


class EvaluationDimension(str, Enum):
    """Quality evaluation dimensions"""

    CLARITY = "clarity"
    COMPLETENESS = "completeness"
    COHERENCE = "coherence"
    APPROPRIATENESS = "appropriateness"
    CORRECTNESS = "correctness"


@dataclass
class DimensionScore:
    """Score for a single evaluation dimension"""

    dimension: EvaluationDimension
    score: float  # 0.0 to 10.0
    reasoning: str
    suggestions: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Result of LLM quality evaluation"""

    phase: AgentPhase
    overall_score: float  # 0.0 to 10.0
    dimension_scores: List[DimensionScore]
    approved: bool  # True if overall_score >= threshold
    feedback: str
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def needs_improvement(self) -> bool:
        """Check if output needs improvement"""
        return not self.approved or len(self.critical_issues) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "phase": self.phase.value if isinstance(self.phase, AgentPhase) else self.phase,
            "overall_score": self.overall_score,
            "dimension_scores": [
                {
                    "dimension": score.dimension.value,
                    "score": score.score,
                    "reasoning": score.reasoning,
                    "suggestions": score.suggestions,
                }
                for score in self.dimension_scores
            ],
            "approved": self.approved,
            "feedback": self.feedback,
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
        }


class LLMJudge:
    """
    LLM-as-a-Judge Pattern Implementation

    Uses LLM to evaluate quality of agent outputs across multiple dimensions.
    Provides semantic quality assessment beyond structural validation.

    This complements Golden Data validation by assessing:
    - Clarity: Are definitions clear and unambiguous?
    - Completeness: Are all necessary elements present?
    - Coherence: Do elements work together logically?
    - Appropriateness: Are choices suitable for the context?
    - Correctness: Are there logical errors or inconsistencies?
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        approval_threshold: float = 7.0,
        phase_thresholds: Optional[Dict[AgentPhase, float]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize LLM Judge.

        Args:
            llm_plugin: LLM plugin for evaluation
            approval_threshold: Default minimum score for approval (0-10)
            phase_thresholds: Optional phase-specific thresholds (overrides default)
            logger: Optional logger
        """
        self.llm = llm_plugin
        self.approval_threshold = approval_threshold
        self.phase_thresholds = phase_thresholds or {}
        self.logger = logger or logging.getLogger(__name__)

        # Phase-specific evaluation criteria
        self.phase_criteria = {
            AgentPhase.DISCOVERY: self._get_discovery_criteria,
            AgentPhase.ARCHITECTURE: self._get_architecture_criteria,
            AgentPhase.DESIGN: self._get_design_criteria,
            AgentPhase.DELIVERY: self._get_delivery_criteria,
            AgentPhase.QUALITY_ASSURANCE: self._get_qa_criteria,
        }

    def get_threshold_for_phase(self, phase: AgentPhase) -> float:
        """Get approval threshold for a specific phase."""
        return self.phase_thresholds.get(phase, self.approval_threshold)

    async def evaluate_quality(
        self, output: Dict[str, Any], phase: AgentPhase, context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """
        Evaluate quality of agent output using LLM.

        Args:
            output: Agent output to evaluate
            phase: Current phase
            context: Optional context (requirement, previous outputs, etc.)

        Returns:
            EvaluationResult with scores and feedback
        """
        self.logger.info(f"🤖 LLM Judge evaluating {phase.name} output...")

        try:
            # Get phase-specific criteria
            criteria_fn = self.phase_criteria.get(phase)
            if not criteria_fn:
                self.logger.warning(f"No criteria defined for phase {phase.name}")
                return self._create_fallback_result(phase)

            criteria = criteria_fn()

            # Build evaluation prompt
            prompt = self._build_evaluation_prompt(output, phase, criteria, context)

            # Get LLM evaluation
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.ainvoke(
                messages=messages,
                temperature=0.3,  # Lower temperature for consistent evaluation
                max_tokens=2000,
            )

            # Extract content from response
            response_content = (
                response.get("content", "") if isinstance(response, dict) else str(response)
            )

            # Check if response is empty
            if not response_content or not response_content.strip():
                self.logger.error(f"LLM returned empty response. Full response object: {response}")
                raise ValueError(f"Empty response from LLM. Response type: {type(response)}")

            # Parse evaluation response
            evaluation = self._parse_evaluation_response(response_content, phase, criteria)

            self.logger.info(
                f"✅ LLM Judge completed: {evaluation.overall_score:.1f}/10.0 "
                f"({'APPROVED' if evaluation.approved else 'NEEDS IMPROVEMENT'})"
            )

            return evaluation

        except Exception as e:
            self.logger.error(f"❌ LLM Judge evaluation failed: {e}")
            return self._create_error_result(phase, str(e))

    def _build_evaluation_prompt(
        self,
        output: Dict[str, Any],
        phase: AgentPhase,
        criteria: List[Dict[str, str]],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Build evaluation prompt for LLM"""

        # Format context if provided
        context_section = ""
        if context:
            requirement = context.get("requirement", "")
            if requirement:
                context_section = f"\n## Original Requirement\n{requirement}\n"

        # Format criteria
        criteria_section = "\n".join(
            [f"{i+1}. **{c['dimension']}**: {c['description']}" for i, c in enumerate(criteria)]
        )

        # Format output for readability
        import json

        from pydantic import BaseModel

        # Convert Pydantic models to dicts for JSON serialization
        def convert_to_dict(obj):
            """Recursively convert Pydantic models and other objects to dicts"""
            if isinstance(obj, BaseModel):
                return obj.model_dump()
            elif isinstance(obj, dict):
                return {k: convert_to_dict(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_dict(item) for item in obj]
            else:
                return obj

        serializable_output = convert_to_dict(output)
        output_json = json.dumps(serializable_output, indent=2, ensure_ascii=False, default=str)

        prompt = f"""# Quality Evaluation Task

You are an expert software architect evaluating the quality of {phase.name} phase output.

{context_section}
## Output to Evaluate

```json
{output_json}
```

## Evaluation Criteria

{criteria_section}

## Instructions

For each criterion:
1. Assign a score from 0.0 to 10.0 (10.0 = excellent, 0.0 = very poor)
2. Provide clear reasoning for the score
3. Suggest specific improvements (if score < 8.0)

Then provide:
- Overall score (average of dimension scores)
- Summary feedback
- List of critical issues (if any)
- List of warnings (if any)

## Output Format

Return your evaluation in the following JSON format:

{{
  "dimension_scores": [
    {{
      "dimension": "clarity",
      "score": 8.5,
      "reasoning": "Agent roles are clearly defined but could be more specific...",
      "suggestions": ["Add more specific role descriptions", "Clarify boundaries"]
    }},
    ...
  ],
  "overall_score": 8.2,
  "feedback": "Overall assessment summary...",
  "critical_issues": ["Issue 1", "Issue 2"],
  "warnings": ["Warning 1", "Warning 2"]
}}

Evaluate now:"""

        return prompt

    def _parse_evaluation_response(
        self, response: str, phase: AgentPhase, criteria: List[Dict[str, str]]
    ) -> EvaluationResult:
        """Parse LLM evaluation response into EvaluationResult"""

        import json
        import re

        try:
            # Check for empty response
            if not response or not response.strip():
                self.logger.warning("LLM returned empty response for evaluation")
                raise ValueError("Empty response from LLM")

            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON
                json_str = response.strip()

                # Check if json_str is empty after stripping
                if not json_str:
                    self.logger.warning("No JSON content found in LLM response")
                    raise ValueError("No JSON content in response")

            data = json.loads(json_str)

            # Parse dimension scores
            dimension_scores = []
            for dim_data in data.get("dimension_scores", []):
                try:
                    dimension = EvaluationDimension(dim_data["dimension"])
                except (ValueError, KeyError):
                    # Skip invalid dimensions
                    continue

                dimension_scores.append(
                    DimensionScore(
                        dimension=dimension,
                        score=float(dim_data.get("score", 0.0)),
                        reasoning=dim_data.get("reasoning", ""),
                        suggestions=dim_data.get("suggestions", []),
                    )
                )

            overall_score = float(data.get("overall_score", 0.0))

            # If no dimension scores provided, calculate from criteria
            if not dimension_scores and overall_score == 0.0:
                overall_score = 5.0  # Neutral score as fallback

            # Check approval using phase-specific threshold
            threshold = self.get_threshold_for_phase(phase)
            approved = overall_score >= threshold

            return EvaluationResult(
                phase=phase,
                overall_score=overall_score,
                dimension_scores=dimension_scores,
                approved=approved,
                feedback=data.get("feedback", "No feedback provided"),
                critical_issues=data.get("critical_issues", []),
                warnings=data.get("warnings", []),
            )

        except Exception as e:
            self.logger.error(f"Failed to parse LLM evaluation response: {e}")
            # Return fallback result
            return EvaluationResult(
                phase=phase,
                overall_score=5.0,
                dimension_scores=[],
                approved=False,
                feedback=f"Failed to parse evaluation: {str(e)}\n\nRaw response: {response[:500]}",
                critical_issues=["Evaluation parsing failed"],
            )

    def _create_fallback_result(self, phase: AgentPhase) -> EvaluationResult:
        """Create fallback result when criteria not defined"""
        return EvaluationResult(
            phase=phase,
            overall_score=7.0,  # Neutral approval
            dimension_scores=[],
            approved=True,
            feedback="No specific criteria defined for this phase. Structural validation passed.",
            warnings=["LLM evaluation skipped - no criteria defined"],
        )

    def _create_error_result(self, phase: AgentPhase, error: str) -> EvaluationResult:
        """Create error result when evaluation fails"""
        return EvaluationResult(
            phase=phase,
            overall_score=0.0,
            dimension_scores=[],
            approved=False,
            feedback=f"Evaluation failed: {error}",
            critical_issues=[f"LLM evaluation error: {error}"],
        )

    # ==================== Phase-Specific Criteria ====================

    def _get_discovery_criteria(self) -> List[Dict[str, str]]:
        """Get evaluation criteria for Discovery phase (Requirements Analysis)"""
        return [
            {
                "dimension": "clarity",
                "description": "Are requirements clearly stated and unambiguous?",
            },
            {
                "dimension": "completeness",
                "description": "Are all necessary features and constraints identified?",
            },
            {
                "dimension": "coherence",
                "description": "Do requirements work together without conflicts?",
            },
        ]

    def _get_architecture_criteria(self) -> List[Dict[str, str]]:
        """Get evaluation criteria for Architecture phase (System Design)"""
        return [
            {
                "dimension": "clarity",
                "description": "Are component responsibilities clearly defined?",
            },
            {
                "dimension": "completeness",
                "description": "Are all necessary components and interfaces identified?",
            },
            {
                "dimension": "coherence",
                "description": "Do components interact logically and efficiently?",
            },
            {
                "dimension": "appropriateness",
                "description": "Are architectural choices suitable for requirements?",
            },
        ]

    def _get_design_criteria(self) -> List[Dict[str, str]]:
        """Get evaluation criteria for Design phase (Agent/Task Design)"""
        return [
            {"dimension": "clarity", "description": "Are agent roles clear and non-overlapping?"},
            {
                "dimension": "completeness",
                "description": "Are all necessary agents and tasks defined?",
            },
            {"dimension": "coherence", "description": "Are task dependencies logical and acyclic?"},
            {
                "dimension": "appropriateness",
                "description": "Are tools appropriate for each agent's role?",
            },
            {
                "dimension": "correctness",
                "description": "Are there any logical errors or inconsistencies?",
            },
        ]

    def _get_delivery_criteria(self) -> List[Dict[str, str]]:
        """Get evaluation criteria for Delivery phase (Code Generation)"""
        return [
            {"dimension": "clarity", "description": "Is code readable and well-documented?"},
            {"dimension": "completeness", "description": "Are all required features implemented?"},
            {
                "dimension": "correctness",
                "description": "Is code syntactically and logically correct?",
            },
            {
                "dimension": "appropriateness",
                "description": "Are implementation choices suitable and follow best practices?",
            },
        ]

    def _get_qa_criteria(self) -> List[Dict[str, str]]:
        """Get evaluation criteria for QA phase (Quality Assurance)"""
        return [
            {"dimension": "completeness", "description": "Are all critical aspects tested?"},
            {
                "dimension": "correctness",
                "description": "Are test assertions correct and comprehensive?",
            },
            {
                "dimension": "appropriateness",
                "description": "Are test strategies suitable for the codebase?",
            },
        ]


# ==================== Convenience Functions ====================


async def evaluate_with_llm_judge(
    output: Dict[str, Any],
    phase: AgentPhase,
    llm_plugin: LLMPlugin,
    context: Optional[Dict[str, Any]] = None,
    approval_threshold: float = 7.0,
) -> EvaluationResult:
    """
    Convenience function to evaluate output with LLM Judge.

    Args:
        output: Agent output to evaluate
        phase: Current phase
        llm_plugin: LLM plugin for evaluation
        context: Optional context
        approval_threshold: Minimum score for approval (0-10)

    Returns:
        EvaluationResult
    """
    judge = LLMJudge(llm_plugin, approval_threshold=approval_threshold)
    return await judge.evaluate_quality(output, phase, context)
