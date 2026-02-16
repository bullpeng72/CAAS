"""
Party Mode: Multi-Agent Collaborative Review

Implements BMAD Party Mode methodology:
- 5 agents review same artifact in parallel
- Each scores on 5 dimensions (0-10)
- Approval threshold: 3/5 agents must score ≥6.0
- Feedback aggregation for actionable insights

Author: CAAS Framework Team
Version: 0.6.0 (CAAS-E Week 2)
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import statistics
import json
import re

from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.exceptions import AgentExecutionError
import logging

logger = logging.getLogger(__name__)


class ReviewPerspective(Enum):
    """Different review perspectives for Party Mode"""
    REQUIREMENTS = "requirements"  # Requirement Analyst perspective
    ARCHITECTURE = "architecture"  # System Architect perspective
    DESIGN = "design"  # Agent Designer perspective
    QUALITY = "quality"  # QA Specialist perspective
    SECURITY = "security"  # Security Specialist perspective


class ReviewDimension(Enum):
    """Dimensions for multi-dimensional scoring"""
    COMPLETENESS = "completeness"
    FEASIBILITY = "feasibility"
    SCALABILITY = "scalability"
    MAINTAINABILITY = "maintainability"
    SECURITY = "security"


@dataclass
class ReviewScore:
    """Individual dimension score from one reviewer"""
    dimension: ReviewDimension
    score: float  # 0.0-10.0
    reasoning: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "dimension": self.dimension.value,
            "score": self.score,
            "reasoning": self.reasoning
        }


@dataclass
class AgentReview:
    """Review result from one agent"""
    agent_name: str
    perspective: ReviewPerspective
    dimension_scores: List[ReviewScore] = field(default_factory=list)
    overall_score: float = 0.0  # Average of dimension scores
    approved: bool = False  # True if overall_score >= approval_threshold
    feedback: str = ""
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "agent_name": self.agent_name,
            "perspective": self.perspective.value,
            "dimension_scores": [s.to_dict() for s in self.dimension_scores],
            "overall_score": self.overall_score,
            "approved": self.approved,
            "feedback": self.feedback,
            "critical_issues": self.critical_issues,
            "warnings": self.warnings
        }


@dataclass
class PartyModeResult:
    """Aggregated result from Party Mode review"""
    artifact_type: str  # "architecture", "design", etc.
    reviews: List[AgentReview] = field(default_factory=list)
    consensus_score: float = 0.0  # Average overall score
    approval_rate: float = 0.0  # Percentage of approving agents
    approved: bool = False  # True if approval_rate >= threshold
    aggregated_feedback: str = ""
    critical_issues: List[str] = field(default_factory=list)  # Union of all critical issues
    warnings: List[str] = field(default_factory=list)  # Union of all warnings
    recommendations: List[str] = field(default_factory=list)  # Synthesized recommendations

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "artifact_type": self.artifact_type,
            "reviews": [r.to_dict() for r in self.reviews],
            "consensus_score": self.consensus_score,
            "approval_rate": self.approval_rate,
            "approved": self.approved,
            "aggregated_feedback": self.aggregated_feedback,
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations
        }


class PartyModeCoordinator:
    """
    Coordinates Party Mode multi-agent review.

    Workflow:
    1. Select N reviewers based on review phase (default: 5)
    2. Run reviews in parallel (async)
    3. Collect scores on 5 dimensions each
    4. Calculate approval rate (% of agents scoring ≥6.0)
    5. Aggregate feedback into actionable insights
    6. Return consensus decision (approve/revise/reject)

    Example:
        coordinator = PartyModeCoordinator(
            llm_plugin=llm,
            party_size=5,
            approval_threshold=6.0,
            consensus_threshold=0.6  # 60% = 3/5 agents
        )

        result = await coordinator.review_artifact(
            artifact=architecture_design,
            artifact_type="architecture",
            phase="phase_2"
        )

        if result.approved:
            print("Architecture approved by Party Mode!")
        else:
            print(f"Revisions needed: {result.recommendations}")
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        party_size: int = 5,
        approval_threshold: float = 6.0,
        consensus_threshold: float = 0.6,  # 60% = 3/5 agents
        logger: Optional[logging.Logger] = None
    ):
        self.llm = llm_plugin
        self.party_size = party_size
        self.approval_threshold = approval_threshold
        self.consensus_threshold = consensus_threshold
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    async def review_artifact(
        self,
        artifact: Dict,
        artifact_type: str,
        phase: str,
        perspectives: Optional[List[ReviewPerspective]] = None
    ) -> PartyModeResult:
        """
        Main entry point for Party Mode review.

        Args:
            artifact: The artifact to review (Golden Data, Architecture, etc.)
            artifact_type: Type of artifact ("golden_data", "architecture", "design")
            phase: CAAS phase ("discovery", "architecture", "design", "refactor")
            perspectives: Optional list of perspectives to use

        Returns:
            PartyModeResult with consensus decision

        Raises:
            AgentExecutionError: If review process fails
        """
        try:
            # Step 1: Select reviewers
            if perspectives is None:
                perspectives = self._select_default_perspectives(phase)

            self.logger.info(
                f"Starting Party Mode review with {len(perspectives)} agents for {artifact_type}"
            )

            # Step 2: Run reviews in parallel
            review_tasks = [
                self._run_single_review(artifact, artifact_type, perspective)
                for perspective in perspectives
            ]

            reviews: List[AgentReview] = await asyncio.gather(*review_tasks)

            # Step 3: Calculate consensus
            result = self._calculate_consensus(reviews, artifact_type)

            # Step 4: Log result
            self.logger.info(
                f"Party Mode complete: {result.approval_rate*100:.1f}% approval "
                f"({'APPROVED' if result.approved else 'REVISE NEEDED'})"
            )

            return result

        except Exception as e:
            self.logger.error(f"Party Mode review failed: {e}")
            raise AgentExecutionError(
                f"Party Mode review failed for {artifact_type}: {e}",
                details={"phase": phase, "artifact_type": artifact_type}
            ) from e

    def _select_default_perspectives(self, phase: str) -> List[ReviewPerspective]:
        """Select default reviewers based on phase"""
        perspective_map = {
            "discovery": [
                ReviewPerspective.REQUIREMENTS,
                ReviewPerspective.ARCHITECTURE,
                ReviewPerspective.DESIGN,
                ReviewPerspective.QUALITY,
                ReviewPerspective.SECURITY,
            ],
            "phase_1": [
                ReviewPerspective.REQUIREMENTS,
                ReviewPerspective.ARCHITECTURE,
                ReviewPerspective.DESIGN,
                ReviewPerspective.QUALITY,
                ReviewPerspective.SECURITY,
            ],
            "architecture": [
                ReviewPerspective.ARCHITECTURE,
                ReviewPerspective.DESIGN,
                ReviewPerspective.QUALITY,
                ReviewPerspective.SECURITY,
                ReviewPerspective.REQUIREMENTS,
            ],
            "phase_2": [
                ReviewPerspective.ARCHITECTURE,
                ReviewPerspective.DESIGN,
                ReviewPerspective.QUALITY,
                ReviewPerspective.SECURITY,
                ReviewPerspective.REQUIREMENTS,
            ],
            "design": [
                ReviewPerspective.DESIGN,
                ReviewPerspective.ARCHITECTURE,
                ReviewPerspective.QUALITY,
                ReviewPerspective.SECURITY,
                ReviewPerspective.REQUIREMENTS,
            ],
            "phase_3": [
                ReviewPerspective.DESIGN,
                ReviewPerspective.ARCHITECTURE,
                ReviewPerspective.QUALITY,
                ReviewPerspective.SECURITY,
                ReviewPerspective.REQUIREMENTS,
            ],
            "refactor": [
                ReviewPerspective.SECURITY,
                ReviewPerspective.QUALITY,
                ReviewPerspective.DESIGN,
                ReviewPerspective.ARCHITECTURE,
                ReviewPerspective.REQUIREMENTS,
            ],
            "phase_5_5": [
                ReviewPerspective.SECURITY,
                ReviewPerspective.QUALITY,
                ReviewPerspective.DESIGN,
                ReviewPerspective.ARCHITECTURE,
                ReviewPerspective.REQUIREMENTS,
            ]
        }

        # Return perspectives for the phase, or default 5 if not found
        return perspective_map.get(phase, list(ReviewPerspective)[:5])

    async def _run_single_review(
        self,
        artifact: Dict,
        artifact_type: str,
        perspective: ReviewPerspective
    ) -> AgentReview:
        """Run a single agent review"""
        try:
            # Build review prompt
            prompt = self._build_review_prompt(artifact, artifact_type, perspective)

            # Get LLM review
            response = await self.llm.ainvoke(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=2000
            )

            # Parse response
            review_data = self._parse_review_response(response.content)

            # Calculate overall score
            dimension_scores = [
                ReviewScore(
                    dimension=ReviewDimension[d["dimension"].upper()],
                    score=float(d["score"]),
                    reasoning=d["reasoning"]
                )
                for d in review_data.get("dimension_scores", [])
            ]

            overall_score = (
                statistics.mean([s.score for s in dimension_scores])
                if dimension_scores else 0.0
            )

            return AgentReview(
                agent_name=f"{perspective.value}_reviewer",
                perspective=perspective,
                dimension_scores=dimension_scores,
                overall_score=overall_score,
                approved=overall_score >= self.approval_threshold,
                feedback=review_data.get("feedback", ""),
                critical_issues=review_data.get("critical_issues", []),
                warnings=review_data.get("warnings", [])
            )

        except Exception as e:
            self.logger.warning(f"Review from {perspective.value} failed: {e}")
            # Return default review with low score
            return AgentReview(
                agent_name=f"{perspective.value}_reviewer",
                perspective=perspective,
                dimension_scores=[],
                overall_score=0.0,
                approved=False,
                feedback=f"Review failed: {e}",
                critical_issues=[f"Review process error: {e}"],
                warnings=[]
            )

    def _build_review_prompt(
        self,
        artifact: Dict,
        artifact_type: str,
        perspective: ReviewPerspective
    ) -> str:
        """Build review prompt for specific perspective"""
        perspective_guidance = {
            ReviewPerspective.REQUIREMENTS: "Focus on: Requirements coverage, clarity, completeness, traceability",
            ReviewPerspective.ARCHITECTURE: "Focus on: System design, scalability, component boundaries, patterns",
            ReviewPerspective.DESIGN: "Focus on: Agent roles, task definitions, delegation patterns, interfaces",
            ReviewPerspective.QUALITY: "Focus on: Testability, maintainability, code quality, error handling",
            ReviewPerspective.SECURITY: "Focus on: Security risks, data privacy, authentication, vulnerabilities"
        }

        # Truncate artifact for prompt (avoid token limit)
        artifact_json = json.dumps(artifact, indent=2)
        if len(artifact_json) > 3000:
            artifact_json = artifact_json[:3000] + "\n... (truncated)"

        prompt = f"""You are a {perspective.value} expert reviewing a {artifact_type} artifact.

Artifact:
```json
{artifact_json}
```

Review Guidance:
{perspective_guidance.get(perspective, "")}

Score each dimension (0-10):
- **completeness**: All necessary elements present? (10 = fully complete, 0 = major gaps)
- **feasibility**: Can this be implemented realistically? (10 = very feasible, 0 = impossible)
- **scalability**: Will it handle growth? (10 = excellent scalability, 0 = not scalable)
- **maintainability**: Easy to modify/extend? (10 = very maintainable, 0 = brittle)
- **security**: Risks mitigated? (10 = very secure, 0 = major vulnerabilities)

Return JSON:
{{
  "dimension_scores": [
    {{"dimension": "completeness", "score": 8.5, "reasoning": "Most elements present, missing X"}},
    {{"dimension": "feasibility", "score": 7.0, "reasoning": "Feasible but Y is challenging"}},
    {{"dimension": "scalability", "score": 9.0, "reasoning": "Good scalability patterns"}},
    {{"dimension": "maintainability", "score": 8.0, "reasoning": "Clear structure, good separation"}},
    {{"dimension": "security", "score": 7.5, "reasoning": "Most risks addressed, consider Z"}}
  ],
  "feedback": "Overall assessment: [2-3 sentences]",
  "critical_issues": ["Issue 1", "Issue 2"],
  "warnings": ["Warning 1"]
}}

Be constructive and specific in your feedback."""

        return prompt

    def _parse_review_response(self, response: str) -> Dict:
        """Parse JSON review response with robust error handling"""
        # Strategy 1: Try to find JSON in markdown code blocks
        json_patterns = [
            r'```(?:json)?\s*(\{.*?\})\s*```',  # ```json {...} ```
            r'```\s*(\{.*?\})\s*```',            # ``` {...} ```
            r'(?:json)?\s*(\{.*?\})',            # json {...} or just {...}
        ]

        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

        # Strategy 2: Try to parse entire response as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Strategy 3: Extract brace-matched content
        brace_depth = 0
        start_idx = None
        for i, char in enumerate(response):
            if char == '{':
                if brace_depth == 0:
                    start_idx = i
                brace_depth += 1
            elif char == '}':
                brace_depth -= 1
                if brace_depth == 0 and start_idx is not None:
                    try:
                        return json.loads(response[start_idx:i+1])
                    except json.JSONDecodeError:
                        continue

        # Fallback: Return empty review with warning
        self.logger.warning(f"Failed to parse review JSON: {response[:200]}")
        return {
            "dimension_scores": [],
            "feedback": response[:500],  # Use raw response as feedback
            "critical_issues": ["Failed to parse review response"],
            "warnings": []
        }

    def _calculate_consensus(
        self,
        reviews: List[AgentReview],
        artifact_type: str
    ) -> PartyModeResult:
        """Calculate consensus from multiple reviews"""
        if not reviews:
            return PartyModeResult(
                artifact_type=artifact_type,
                approved=False,
                aggregated_feedback="No reviews available",
                critical_issues=["No reviews completed"]
            )

        # Approval rate
        approved_count = sum(1 for r in reviews if r.approved)
        approval_rate = approved_count / len(reviews)

        # Consensus score (average of all overall scores)
        consensus_score = statistics.mean([r.overall_score for r in reviews])

        # Aggregate issues
        all_critical = []
        all_warnings = []
        for review in reviews:
            all_critical.extend(review.critical_issues)
            all_warnings.extend(review.warnings)

        # Deduplicate
        critical_issues = list(dict.fromkeys(all_critical))  # Preserve order
        warnings = list(dict.fromkeys(all_warnings))

        # Synthesize feedback
        aggregated_feedback = self._synthesize_feedback(reviews)

        # Generate recommendations
        recommendations = self._generate_recommendations(reviews, approval_rate, consensus_score)

        return PartyModeResult(
            artifact_type=artifact_type,
            reviews=reviews,
            consensus_score=consensus_score,
            approval_rate=approval_rate,
            approved=approval_rate >= self.consensus_threshold,
            aggregated_feedback=aggregated_feedback,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=recommendations
        )

    def _synthesize_feedback(self, reviews: List[AgentReview]) -> str:
        """Synthesize feedback from multiple reviews"""
        feedback_parts = []

        # Overall consensus
        approved = sum(1 for r in reviews if r.approved)
        total = len(reviews)
        feedback_parts.append(
            f"**Consensus**: {approved}/{total} reviewers approved "
            f"({approved/total*100:.0f}%)"
        )

        # Dimension averages
        dimension_scores = {}
        for review in reviews:
            for score in review.dimension_scores:
                dim_name = score.dimension.value
                if dim_name not in dimension_scores:
                    dimension_scores[dim_name] = []
                dimension_scores[dim_name].append(score.score)

        if dimension_scores:
            feedback_parts.append("\n**Dimension Averages**:")
            for dim, scores in sorted(dimension_scores.items()):
                avg = statistics.mean(scores)
                feedback_parts.append(f"  - {dim.capitalize()}: {avg:.1f}/10")

        # Common themes from individual feedback
        all_feedback = " ".join([r.feedback for r in reviews])
        if len(all_feedback) > 300:
            all_feedback = all_feedback[:300] + "..."

        feedback_parts.append(f"\n**Key Feedback**:\n{all_feedback}")

        return "\n".join(feedback_parts)

    def _generate_recommendations(
        self,
        reviews: List[AgentReview],
        approval_rate: float,
        consensus_score: float
    ) -> List[str]:
        """Generate actionable recommendations"""
        recs = []

        # Overall decision
        if approval_rate < self.consensus_threshold:
            shortfall = (self.consensus_threshold - approval_rate) * 100
            recs.append(
                f"**Action Required**: Revise artifact to gain {shortfall:.0f}% more approval"
            )

        # Dimension-specific recommendations
        dim_scores = {}
        for review in reviews:
            for score in review.dimension_scores:
                dim_name = score.dimension.value
                if dim_name not in dim_scores:
                    dim_scores[dim_name] = []
                dim_scores[dim_name].append(score.score)

        for dim, scores in sorted(dim_scores.items()):
            avg_score = statistics.mean(scores)
            if avg_score < self.approval_threshold:
                recs.append(
                    f"**Improve {dim.capitalize()}**: Average score {avg_score:.1f}/10 "
                    f"(target: {self.approval_threshold:.1f}+)"
                )

        # Critical issues summary
        critical_count = sum(len(r.critical_issues) for r in reviews)
        if critical_count > 0:
            recs.append(f"**Address {critical_count} critical issue(s)** before proceeding")

        # If approved, provide positive feedback
        if approval_rate >= self.consensus_threshold:
            recs.append(f"✅ **Approved**: Consensus score {consensus_score:.1f}/10")

        return recs
