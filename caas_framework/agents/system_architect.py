"""
System Architect Agent

Expert agent responsible for Phase 2 (Architecture):
- Designs system architecture
- Identifies components and their relationships
- Defines data flow and integration points
- Selects appropriate technology stack
"""

from typing import Any, Dict, List, Optional

from caas_framework.agents.base import (
    BaseExpertAgent,
    AgentPhase,
    ValidationIssue
)
from caas_framework.agents.registry import register_agent
from caas_framework.models.specifications import ConcretizedRequirement
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils import PromptBuilder


@register_agent(phase=AgentPhase.ARCHITECTURE)
class SystemArchitectAgent(BaseExpertAgent):
    """
    System Architect Agent

    Specializes in designing system architecture that supports
    all requirements and aligns with Golden Data structure.
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        golden_data: Optional[ConcretizedRequirement] = None
    ):
        super().__init__(llm_plugin, golden_data, AgentPhase.ARCHITECTURE)

    @property
    def agent_name(self) -> str:
        return "SystemArchitect"

    @property
    def agent_role(self) -> str:
        return "Expert System Architect"

    @property
    def agent_expertise(self) -> List[str]:
        return [
            "System architecture design",
            "Component decomposition",
            "Data flow modeling",
            "Technology stack selection",
            "Integration pattern design",
            "Scalability planning",
            "Architecture pattern application"
        ]

    async def _do_work(
        self,
        requirement: Optional[str],
        context: Optional[Dict[str, Any]],
        previous_outputs: Optional[Dict[AgentPhase, Any]]
    ) -> Dict[str, Any]:
        """
        Design system architecture.

        Returns:
            Dict with:
            - components: List[Dict] - System components
            - data_flow: Dict - Data flow between components
            - integration_points: List[Dict] - External integrations
            - technology_stack: Dict - Selected technologies
            - architecture_patterns: List[str] - Applied patterns
            - deployment_architecture: Dict - Deployment structure
        """
        context_summary = self._build_context_summary(context, previous_outputs)

        # Get requirement analysis from previous phase
        req_analysis = None
        if previous_outputs and AgentPhase.DISCOVERY in previous_outputs:
            req_analysis = previous_outputs[AgentPhase.DISCOVERY]

        prompt = self._build_architecture_prompt(
            requirement,
            req_analysis,
            context_summary
        )

        # Use unified LLM helper (uses TEMPERATURE_CREATIVE by default for ARCHITECTURE phase)
        architecture = await self._invoke_llm_structured(
            prompt=prompt,
            expected_fields=['components', 'data_flow', 'integration_points', 'technology_stack'],
            fallback_factory=self._create_fallback_architecture
        )

        # Enhance with Golden Data alignment
        if self.golden_data:
            architecture = self._align_with_golden_data(architecture)

        return architecture

    def _build_architecture_prompt(
        self,
        requirement: str,
        req_analysis: Optional[Dict[str, Any]],
        context: str
    ) -> str:
        """Build LLM prompt for architecture design."""

        builder = (
            PromptBuilder("design a comprehensive system architecture for the following requirement")
            .add_task("You are an expert System Architect.")
            .add_input(requirement=requirement)
        )

        # Add golden data if available
        if self.golden_data:
            builder.add_golden_data(
                self.golden_data,
                fields=['domain', 'data_models', 'ui_components', 'deployment_target']
            )

        # Add requirements analysis from previous phase
        if req_analysis:
            builder.add_previous_outputs(
                {"requirement_analysis": req_analysis},
                phases=["requirement_analysis"]
            )

        # Add context if provided
        if context:
            builder.add_context("Additional Context", context)

        # Add output format
        builder.add_output_format({
            "components": [
                {
                    "id": "component_id",
                    "name": "Component Name",
                    "type": "backend|frontend|database|service|api",
                    "responsibility": "What this component does",
                    "interfaces": ["interface1", "interface2"],
                    "dependencies": ["component_id1", "component_id2"]
                }
            ],
            "data_flow": {
                "flows": [
                    {
                        "from": "component_id",
                        "to": "component_id",
                        "data": "what data flows",
                        "protocol": "REST|gRPC|WebSocket|etc"
                    }
                ]
            },
            "integration_points": [
                {
                    "name": "Integration name",
                    "type": "external_api|database|service",
                    "purpose": "why this integration",
                    "protocol": "REST|GraphQL|etc"
                }
            ],
            "technology_stack": {
                "backend": ["framework", "language"],
                "frontend": ["framework", "library"],
                "database": ["database_type"],
                "infrastructure": ["docker", "kubernetes"],
                "tools": ["tool1", "tool2"]
            },
            "architecture_patterns": [
                "Microservices",
                "Event-driven",
                "CQRS",
                "etc"
            ],
            "deployment_architecture": {
                "environment": "cloud|on-premise|hybrid",
                "containers": ["container1", "container2"],
                "services": ["service1", "service2"],
                "scaling_strategy": "horizontal|vertical|auto"
            },
            "security_architecture": {
                "authentication": "strategy",
                "authorization": "strategy",
                "data_protection": ["encryption", "etc"]
            }
        }, "Design system architecture in JSON format:")

        builder.add_guidelines([
            "Support all functional and non-functional requirements",
            "Align with Golden Data structure",
            "Be scalable and maintainable",
            "Follow best practices and patterns"
        ])

        return builder.build()

    def _create_fallback_architecture(self) -> Dict[str, Any]:
        """Create basic architecture when LLM fails."""
        return {
            "components": [
                {
                    "id": "backend",
                    "name": "Backend Service",
                    "type": "backend",
                    "responsibility": "Core business logic",
                    "interfaces": ["REST API"],
                    "dependencies": []
                }
            ],
            "data_flow": {"flows": []},
            "integration_points": [],
            "technology_stack": {
                "backend": ["Python", "FastAPI"],
                "frontend": ["Streamlit"],
                "database": ["PostgreSQL"],
                "infrastructure": ["Docker"],
                "tools": []
            },
            "architecture_patterns": ["Monolithic"],
            "deployment_architecture": {
                "environment": "cloud",
                "containers": ["app"],
                "services": ["app-service"],
                "scaling_strategy": "horizontal"
            },
            "security_architecture": {
                "authentication": "JWT",
                "authorization": "RBAC",
                "data_protection": ["TLS", "encryption-at-rest"]
            }
        }

    def _align_with_golden_data(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Align architecture with Golden Data."""
        if not self.golden_data:
            return architecture

        # Ensure data models are reflected in components
        components = architecture.get("components") or []
        # Safety check: ensure components is a list
        if not isinstance(components, list):
            components = []

        db_components = [
            c for c in components
            if c.get("type") == "database"
        ]

        if self.golden_data.data_models and not db_components:
            # Add database component if missing
            data_models = self.golden_data.data_models if self.golden_data.data_models else []
            model_names = ', '.join(dm.entity_name for dm in data_models[:3]) if data_models else "data entities"

            architecture.setdefault("components", []).append({
                "id": "database",
                "name": "Data Layer",
                "type": "database",
                "responsibility": f"Stores {model_names}",
                "interfaces": ["ORM"],
                "dependencies": []
            })

        # Add alignment metadata
        data_models = self.golden_data.data_models if self.golden_data.data_models else []
        ui_components = self.golden_data.ui_components if self.golden_data.ui_components else []

        architecture["golden_data_alignment"] = {
            "data_models_covered": len(data_models),
            "ui_components_supported": len(ui_components),
            "deployment_target": self.golden_data.deployment_target
        }

        return architecture

    async def _refine_implementation(
        self,
        output: Dict[str, Any],
        issues: List[ValidationIssue],
        context: Optional[Dict[str, Any]],
        iteration: int
    ) -> Dict[str, Any]:
        """Refine architecture based on validation feedback."""

        issues_summary = self._format_validation_issues(issues)

        # Prepare Golden Data context if available
        golden_data_info = None
        if self.golden_data:
            data_models = self.golden_data.data_models if self.golden_data.data_models else []
            golden_data_info = {
                "data_models": [dm.entity_name for dm in data_models]
            }

        # Build refinement prompt using PromptBuilder
        prompt = PromptBuilder.build_refinement_prompt(
            agent_role="System Architect",
            output_type="architecture",
            current_output=output,
            issues_summary=issues_summary,
            golden_data=golden_data_info,
            golden_data_context="Golden Data Requirements",
            guidelines=[
                "Address component dependencies",
                "Ensure data flow covers all requirements",
                "Verify technology stack alignment",
                "Check scalability considerations"
            ],
            iteration=iteration
        )

        # Use unified LLM helper
        refined = await self._invoke_llm_structured(
            prompt=prompt,
            expected_fields=list(output.keys()),
            fallback_factory=lambda: output
        )

        # Use unified output merging helper
        return self._merge_outputs(refined, output)
