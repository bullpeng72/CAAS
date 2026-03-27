"""
LLM-as-a-Judge Pattern

Uses LLM to evaluate quality of agent outputs with multi-dimensional criteria.
Goes beyond schema validation to assess semantic quality and design coherence.
"""

import asyncio
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
            "phase": self.phase.value
            if isinstance(self.phase, AgentPhase)
            else self.phase,
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

    ✅ v0.4.0 (P1-3): Lightweight mode with Claude Haiku for 70% faster evaluation
    - use_fast_model=True (default): ~1 second evaluation time
    - use_fast_model=False: ~3 seconds with more detailed feedback
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        approval_threshold: float = 7.0,
        phase_thresholds: Optional[Dict[AgentPhase, float]] = None,
        use_fast_model: bool = False,  # ✅ Changed default to False for better accuracy
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize LLM Judge.

        Args:
            llm_plugin: LLM plugin for evaluation
            approval_threshold: Default minimum score for approval (0-10)
            phase_thresholds: Optional phase-specific thresholds (overrides default)
            use_fast_model: If True, use optimized prompt (faster but less detailed)
                           Changed default to False in v0.4.1 for better evaluation accuracy
            logger: Optional logger
        """
        self.llm = llm_plugin
        self.approval_threshold = approval_threshold
        self.phase_thresholds = phase_thresholds or {}
        self.use_fast_model = use_fast_model

        # FIX: Use llm_plugin's model instead of hardcoded Claude models
        # This allows LLM Judge to work with OpenAI, Ollama, and other providers
        self.fast_model = getattr(llm_plugin, 'model', "claude-3-5-haiku-20241022")
        self.standard_model = getattr(llm_plugin, 'model', "claude-3-5-sonnet-20241022")

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
        self,
        output: Dict[str, Any],
        phase: AgentPhase,
        context: Optional[Dict[str, Any]] = None,
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

            # Build evaluation prompt (optimized for fast model if enabled)
            prompt = self._build_evaluation_prompt(
                output, phase, criteria, context, optimized=self.use_fast_model
            )

            # Get LLM evaluation with appropriate model
            messages = [{"role": "user", "content": prompt}]
            llm_kwargs = {
                "messages": messages,
                "temperature": 0.3,  # Lower temperature for consistent evaluation
                "max_tokens": 1000 if self.use_fast_model else 2000,  # Shorter for fast model
            }

            # NOTE: Model override not supported via ainvoke() kwargs due to build_request_params() signature
            # The LLM plugin uses its configured model (self.model) which is set at initialization
            # TODO (v0.4.1): Implement proper fast model support by creating separate LLM plugin instance

            # ✅ P0 FIX #3: Add timeout protection (belt-and-suspenders approach)
            # Note: TimeoutManager already wraps this in collaboration.py, but this provides
            # defensive protection directly in LLM Judge for edge cases
            try:
                response = await asyncio.wait_for(
                    self.llm.ainvoke(**llm_kwargs),
                    timeout=60.0,  # 60s timeout for LLM calls (can be slow)
                )
            except asyncio.TimeoutError:
                self.logger.error(f"LLM Judge timed out after 60s for {phase.name}")
                raise TimeoutError(
                    f"LLM Judge evaluation timed out after 60 seconds for {phase.name}"
                )

            # Extract content from response
            response_content = (
                response.get("content", "")
                if isinstance(response, dict)
                else str(response)
            )

            # Check if response is empty
            if not response_content or not response_content.strip():
                self.logger.error(
                    f"LLM returned empty response. Full response object: {response}"
                )
                raise ValueError(
                    f"Empty response from LLM. Response type: {type(response)}"
                )

            # Parse evaluation response
            evaluation = self._parse_evaluation_response(
                response_content, phase, criteria
            )

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
        optimized: bool = False,
    ) -> str:
        """
        Build evaluation prompt for LLM

        Args:
            optimized: If True, use concise prompt for faster evaluation (v0.4.0)
        """

        # Format context if provided
        context_section = ""
        if context:
            requirement = context.get("requirement", "")
            if requirement:
                context_section = f"\n## Original Requirement\n{requirement}\n"

        # Format criteria
        criteria_section = "\n".join(
            [
                f"{i+1}. **{c['dimension']}**: {c['description']}"
                for i, c in enumerate(criteria)
            ]
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
        output_json = json.dumps(
            serializable_output, indent=2, ensure_ascii=False, default=str
        )

        # ✅ v0.4.0: Optimized prompt for fast evaluation (Haiku model)
        if optimized:
            return self._build_optimized_prompt(
                output_json, phase, criteria, context_section
            )

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

    def _build_optimized_prompt(
        self,
        output_json: str,
        phase: AgentPhase,
        criteria: List[Dict[str, str]],
        context_section: str,
    ) -> str:
        """
        Build optimized, concise prompt for fast evaluation (v0.4.0)

        Target: 70% faster evaluation (1s vs 3s) using Claude Haiku
        """
        # Format criteria concisely
        criteria_list = ", ".join([c["dimension"] for c in criteria])

        prompt = f"""Evaluate {phase.name} output quality. Score each: {criteria_list} (0-10).

{context_section if context_section else ""}
Output:
```json
{output_json}
```

Return JSON:
{{
  "dimension_scores": [{{"dimension": "clarity", "score": 8.5, "reasoning": "brief reason", "suggestions": ["fix1"]}}],
  "overall_score": 8.2,
  "feedback": "brief summary",
  "critical_issues": [],
  "warnings": []
}}"""

        return prompt

    def _parse_evaluation_response(
        self, response: str, phase: AgentPhase, criteria: List[Dict[str, str]]
    ) -> EvaluationResult:
        """
        Parse LLM evaluation response into EvaluationResult

        ✅ IMPROVED (P1): Multi-strategy JSON extraction with fallback
        """

        import json
        import re
        import ast as _ast

        def _extract_json_with_brace_matching(text: str):
            """
            Extract the first complete JSON object using brace counting.
            This correctly handles nested objects unlike regex-based approaches.
            Returns parsed dict or None.
            """
            brace_count = 0
            start_idx = None
            in_string = False
            escape_next = False

            for i, char in enumerate(text):
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\' and in_string:
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue

                if char == '{':
                    if start_idx is None:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx is not None:
                        candidate = text[start_idx:i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            # Try fixing single quotes and re-parse
                            try:
                                fixed = re.sub(r"'([^']*)'", r'"\1"', candidate)
                                return json.loads(fixed)
                            except json.JSONDecodeError:
                                try:
                                    return _ast.literal_eval(candidate)
                                except (ValueError, SyntaxError):
                                    pass
                            # Continue searching for next candidate
                            start_idx = None
                            brace_count = 0
            return None

        try:
            # Check for empty response
            if not response or not response.strip():
                self.logger.warning("LLM returned empty response for evaluation")
                raise ValueError("Empty response from LLM")

            # ✅ Strategy 1: Try direct JSON parse (LLM already returned valid JSON)
            data = None
            try:
                data = json.loads(response.strip())
                if not isinstance(data, dict):
                    data = None
            except json.JSONDecodeError:
                pass

            # ✅ Strategy 2: Try ast.literal_eval (handles Python-style dicts with single quotes)
            if data is None:
                try:
                    data = _ast.literal_eval(response.strip())
                    if not isinstance(data, dict):
                        data = None
                except (ValueError, SyntaxError):
                    pass

            # ✅ Strategy 3: Extract from markdown code block, then parse with brace matching
            if data is None:
                # Strip markdown fences to get the content inside ```json ... ```
                fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
                if fence_match:
                    block_content = fence_match.group(1).strip()
                    # Try direct parse first
                    try:
                        data = json.loads(block_content)
                        if not isinstance(data, dict):
                            data = None
                    except json.JSONDecodeError:
                        data = _extract_json_with_brace_matching(block_content)

            # ✅ Strategy 4: Brace-matching on full response (handles JSON buried in text)
            if data is None:
                data = _extract_json_with_brace_matching(response)

            if data is None:
                last_err = "No valid JSON object found in LLM response"
                self.logger.warning(f"JSON parsing failed: {last_err}")
                raise ValueError(last_err)

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
            {
                "dimension": "clarity",
                "description": "Are agent roles clear and non-overlapping?",
            },
            {
                "dimension": "completeness",
                "description": "Are all necessary agents and tasks defined?",
            },
            {
                "dimension": "coherence",
                "description": "Are task dependencies logical and acyclic?",
            },
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
            {
                "dimension": "clarity",
                "description": "Is code readable and well-documented?",
            },
            {
                "dimension": "completeness",
                "description": "Are all required features implemented?",
            },
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
            {
                "dimension": "completeness",
                "description": "Are all critical aspects tested?",
            },
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
    use_fast_model: bool = True,
) -> EvaluationResult:
    """
    Convenience function to evaluate output with LLM Judge.

    Args:
        output: Agent output to evaluate
        phase: Current phase
        llm_plugin: LLM plugin for evaluation
        context: Optional context
        approval_threshold: Minimum score for approval (0-10)
        use_fast_model: Use Claude Haiku for 70% faster evaluation (v0.4.0)

    Returns:
        EvaluationResult
    """
    judge = LLMJudge(
        llm_plugin, approval_threshold=approval_threshold, use_fast_model=use_fast_model
    )
    return await judge.evaluate_quality(output, phase, context)
