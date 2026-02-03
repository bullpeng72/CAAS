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
from caas_framework.utils import PromptBuilder


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

        # Enhance with Golden Data traceability
        if self.golden_data:
            analysis = self._enhance_with_golden_data(analysis)

        return analysis

    def _build_analysis_prompt(self, requirement: str, context: str) -> str:
        """Build LLM prompt for requirement analysis."""

        builder = (
            PromptBuilder(
                "analyze the following requirement and provide comprehensive analysis"
            )
            .add_task("You are an expert Requirements Analyst.")
            .add_input(requirement=requirement)
        )

        # Add golden data if available
        if self.golden_data:
            builder.add_golden_data(
                self.golden_data,
                fields=["domain", "project_name", "features", "data_models"],
            )

        # Add context if provided
        if context:
            builder.add_context("Additional Context", context)

        # Add output format
        builder.add_output_format(
            {
                "functional_requirements": [
                    {
                        "id": "FR1",
                        "description": "functional requirement description",
                        "priority": "high|medium|low",
                        "source": "derived from which feature or requirement",
                        "acceptance_criteria": ["criterion 1", "criterion 2"],
                    }
                ],
                "non_functional_requirements": {
                    "performance": ["requirement 1", "requirement 2"],
                    "security": ["requirement 1", "requirement 2"],
                    "scalability": ["requirement 1", "requirement 2"],
                    "usability": ["requirement 1", "requirement 2"],
                    "reliability": ["requirement 1", "requirement 2"],
                },
                "success_criteria": [
                    "Measurable success criterion 1",
                    "Measurable success criterion 2",
                ],
                "constraints": ["Technical constraint 1", "Business constraint 2"],
                "risks": [
                    {
                        "risk": "risk description",
                        "impact": "high|medium|low",
                        "mitigation": "mitigation strategy",
                    }
                ],
                "assumptions": ["Assumption 1", "Assumption 2"],
                "dependencies": ["External dependency 1", "External dependency 2"],
                "boundaries": {
                    "always_allowed": [
                        "Read files in project directory",
                        "Write to project directory",
                        "Install packages from requirements.txt",
                    ],
                    "ask_first": [
                        "Make API calls to external services",
                        "Modify system configuration",
                        "Delete files or directories",
                    ],
                    "never_allowed": [
                        "Execute shell commands with sudo",
                        "Modify files outside project directory",
                        "Disable security features",
                    ],
                },
            },
            "Provide detailed requirements analysis in JSON format:",
        )

        builder.add_guidelines(
            [
                "Be thorough and align with Golden Data features when provided",
                "Ensure all functional requirements have clear acceptance criteria",
                "Identify both technical and business constraints",
                "CRITICAL: Define security boundaries based on the requirement's needs",
                "Always set 'never_allowed' to prevent dangerous operations",
                "Use 'ask_first' for operations that could be risky or costly",
            ]
        )

        return builder.build()

    def _create_fallback_analysis(self, requirement: str) -> Dict[str, Any]:
        """Create basic analysis structure when LLM fails."""
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
