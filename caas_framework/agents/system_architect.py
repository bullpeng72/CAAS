"""
System Architect Agent

Expert agent responsible for Phase 2 (Architecture):
- Designs system architecture
- Identifies components and their relationships
- Defines data flow and integration points
- Selects appropriate technology stack
"""

from typing import Any, Dict, List, Optional

from caas_framework.agents.base import AgentPhase, BaseExpertAgent, ValidationIssue
from caas_framework.agents.executors import GoldenDataEnhancer, RefinementExecutor
from caas_framework.agents.registry import register_agent
from caas_framework.models.specifications import ConcretizedRequirement
from caas_framework.plugins.llm.base import LLMPlugin


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
        golden_data: Optional[ConcretizedRequirement] = None,
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
            "Architecture pattern application",
        ]

    async def _do_work(
        self,
        requirement: Optional[str],
        context: Optional[Dict[str, Any]],
        previous_outputs: Optional[Dict[AgentPhase, Any]],
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
            requirement, req_analysis, context_summary
        )

        # Use unified LLM helper (uses TEMPERATURE_CREATIVE by default for ARCHITECTURE phase)
        architecture = await self._invoke_llm_structured(
            prompt=prompt,
            expected_fields=[
                "components",
                "data_flow",
                "integration_points",
                "technology_stack",
            ],
            fallback_factory=self._create_fallback_architecture,
        )

        # Enhance with Golden Data alignment
        if self.golden_data:
            architecture = self._align_with_golden_data(architecture)

        return architecture

    def _build_architecture_prompt(
        self, requirement: str, req_analysis: Optional[Dict[str, Any]], context: str
    ) -> str:
        """Build LLM prompt for architecture design."""
        # ✅ v0.5.0: 한국어 출력 강제 (P0 수정)
        # Use base class template method
        output_format = {
            "components": [
                {
                    "id": "component_id",
                    "name": "컴포넌트 이름",
                    "type": "backend|frontend|database|service|api",
                    "responsibility": "이 컴포넌트가 수행하는 역할",
                    "interfaces": ["인터페이스1", "인터페이스2"],
                    "dependencies": ["component_id1", "component_id2"],
                }
            ],
            "data_flow": {
                "flows": [
                    {
                        "from": "component_id",
                        "to": "component_id",
                        "data": "전달되는 데이터",
                        "protocol": "REST|gRPC|WebSocket|etc",
                    }
                ]
            },
            "integration_points": [
                {
                    "name": "통합 이름",
                    "type": "external_api|database|service",
                    "purpose": "통합의 목적",
                    "protocol": "REST|GraphQL|etc",
                }
            ],
            "technology_stack": {
                "backend": ["프레임워크", "언어"],
                "frontend": ["프레임워크", "라이브러리"],
                "database": ["데이터베이스 타입"],
                "infrastructure": ["docker", "kubernetes"],
                "tools": ["도구1", "도구2"],
            },
            "architecture_patterns": [
                "마이크로서비스",
                "이벤트 기반",
                "CQRS",
                "기타 패턴",
            ],
            "deployment_architecture": {
                "environment": "cloud|on-premise|hybrid (클라우드|온프레미스|하이브리드)",
                "containers": ["컨테이너1", "컨테이너2"],
                "services": ["서비스1", "서비스2"],
                "scaling_strategy": "horizontal|vertical|auto (수평|수직|자동)",
            },
            "security_architecture": {
                "authentication": "인증 전략",
                "authorization": "권한 부여 전략",
                "data_protection": ["암호화", "기타 보호 방법"],
            },
        }

        guidelines = [
            "**중요: 모든 텍스트 값(name, responsibility, purpose 등)을 한국어로 작성하세요**",
            "JSON 키(key)는 영어로 유지하되, 값(value)은 반드시 한국어로 작성하세요",
            "모든 기능적/비기능적 요구사항을 지원하세요",
            "Golden Data 구조와 정렬하세요",
            "확장 가능하고 유지보수 가능하도록 설계하세요",
            "모범 사례와 패턴을 따르세요",
        ]

        # Prepare previous outputs
        previous_outputs = {}
        if req_analysis:
            previous_outputs["requirement_analysis"] = req_analysis

        return self._build_standard_prompt(
            requirement=requirement,
            output_format=output_format,
            guidelines=guidelines,
            context={"additional_context": context} if context else None,
            previous_outputs=previous_outputs,
        )

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
                    "dependencies": [],
                }
            ],
            "data_flow": {"flows": []},
            "integration_points": [],
            "technology_stack": {
                "backend": ["Python", "FastAPI"],
                "frontend": ["Streamlit"],
                "database": ["PostgreSQL"],
                "infrastructure": ["Docker"],
                "tools": [],
            },
            "architecture_patterns": ["Monolithic"],
            "deployment_architecture": {
                "environment": "cloud",
                "containers": ["app"],
                "services": ["app-service"],
                "scaling_strategy": "horizontal",
            },
            "security_architecture": {
                "authentication": "JWT",
                "authorization": "RBAC",
                "data_protection": ["TLS", "encryption-at-rest"],
            },
        }

    def _align_with_golden_data(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Align architecture with Golden Data."""
        if not self.golden_data:
            return architecture

        # Use GoldenDataEnhancer for data model alignment
        enhancer = GoldenDataEnhancer(self.golden_data)
        architecture = enhancer.enhance_with_data_models(
            output=architecture, components_key="components"
        )

        # Custom logic: Add database component if missing but data models exist
        components = architecture.get("components") or []
        if isinstance(components, list):
            db_components = [c for c in components if c.get("type") == "database"]

            if self.golden_data.data_models and not db_components:
                data_models = self.golden_data.data_models
                model_names = (
                    ", ".join(dm.entity_name for dm in data_models[:3])
                    if data_models
                    else "data entities"
                )

                architecture.setdefault("components", []).append(
                    {
                        "id": "database",
                        "name": "Data Layer",
                        "type": "database",
                        "responsibility": f"Stores {model_names}",
                        "interfaces": ["ORM"],
                        "dependencies": [],
                    }
                )

        return architecture

    async def _refine_implementation(
        self,
        output: Dict[str, Any],
        issues: List[ValidationIssue],
        context: Optional[Dict[str, Any]],
        iteration: int,
    ) -> Dict[str, Any]:
        """
        Refine architecture based on validation feedback.

        Uses RefinementExecutor for standardized refinement workflow.
        """
        executor = RefinementExecutor.create_for_agent(
            agent=self,
            agent_role="Expert System Architect",
            output_type="system architecture",
        )

        return await executor.refine_output(
            output=output,
            issues=issues,
            iteration=iteration,
            guidelines=[
                "Address component dependencies",
                "Ensure data flow covers all requirements",
                "Verify technology stack alignment",
                "Check scalability considerations",
            ],
        )
