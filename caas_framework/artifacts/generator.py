"""
Artifact Generator

Generates project artifacts (documents) from BMAD outputs using Jinja2 templates.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from caas_framework.models.artifact_types import (
    Artifact,
    ArtifactGenerationConfig,
    ArtifactMetadata,
    ArtifactType,
    get_artifact_template_name,
)
from caas_framework.utils.logger import get_logger

logger = get_logger()


class ArtifactGenerator:
    """
    Artifact Generator

    Generates various project artifacts (documents) from BMAD pipeline outputs.
    Supports multiple artifact types and formats (Markdown, HTML, PDF).
    """

    def __init__(self, config: ArtifactGenerationConfig):
        """
        Initialize artifact generator.

        Args:
            config: Artifact generation configuration
        """
        self.config = config
        self.logger = get_logger()

        # Setup Jinja2 environment
        template_dir = (
            Path(__file__).parent.parent.parent / "data" / "templates" / "artifacts"
        )

        if not template_dir.exists():
            self.logger.warning(
                f"Artifact template directory not found: {template_dir}"
            )
            self.template_env = None
        else:
            self.template_env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                trim_blocks=True,
                lstrip_blocks=True,
            )

            # Add custom filters
            self.template_env.filters["datetime"] = (
                lambda dt, fmt="%Y-%m-%d %H:%M:%S": (
                    dt.strftime(fmt) if hasattr(dt, "strftime") else str(dt)
                )
            )
            self.template_env.filters["default"] = (
                lambda val, default="": val if val else default
            )
            self.template_env.filters["length"] = lambda val: len(val) if val else 0

            self.logger.info(f"Loaded artifact templates from: {template_dir}")

        # Output directory
        self.output_dir = Path(self.config.output_directory)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(self, bmad_data: Dict[str, Any]) -> List[Artifact]:
        """
        Generate all enabled artifacts.

        Args:
            bmad_data: Complete BMAD pipeline data containing:
                - requirement: Original requirement text
                - golden_data: Concretized requirement
                - requirement_analysis: Discovery phase output
                - architecture: Architecture phase output
                - agents: Agent specifications
                - tasks: Task specifications
                - code: Generated code

        Returns:
            List of generated artifacts
        """
        if not self.config.enabled:
            self.logger.info("Artifact generation is disabled")
            return []

        artifacts = []
        enabled_types = self.config.get_enabled_artifact_types()

        self.logger.info(f"Generating {len(enabled_types)} artifact types...")

        for artifact_type in enabled_types:
            try:
                artifact = self.generate_artifact(artifact_type, bmad_data)
                if artifact:
                    artifacts.append(artifact)
                    self.logger.info(f"✅ Generated: {artifact_type.value}")
            except Exception as e:
                self.logger.error(f"❌ Failed to generate {artifact_type.value}: {e}")

        self.logger.info(f"Generated {len(artifacts)} artifacts total")
        return artifacts

    def generate_artifact(
        self, artifact_type: ArtifactType, bmad_data: Dict[str, Any]
    ) -> Optional[Artifact]:
        """
        Generate a single artifact.

        Args:
            artifact_type: Type of artifact to generate
            bmad_data: BMAD pipeline data

        Returns:
            Generated artifact or None if failed
        """
        if not self.template_env:
            self.logger.error("Template environment not initialized")
            return None

        try:
            # Get template
            template_name = get_artifact_template_name(artifact_type)
            template = self.template_env.get_template(template_name)

            # Prepare context data
            context = self._prepare_context(artifact_type, bmad_data)

            # Render template
            content = template.render(**context)

            # Create metadata
            metadata = ArtifactMetadata(
                artifact_type=artifact_type,
                format=self.config.output_format,
                title=context.get("title", artifact_type.value),
                version="1.0.0",
                created_at=datetime.now(),
                created_by="CAAS",
                project_name=context.get("project_name"),
                description=context.get("description"),
            )

            # Save to file
            file_path = self._save_artifact(artifact_type, content)

            # Create artifact object
            artifact = Artifact(
                metadata=metadata,
                content=content,
                file_path=str(file_path) if file_path else None,
            )

            return artifact

        except TemplateNotFound:
            self.logger.error(f"Template not found for {artifact_type.value}")
            return None
        except Exception as e:
            self.logger.error(f"Error generating {artifact_type.value}: {e}")
            import traceback

            self.logger.debug(traceback.format_exc())
            return None

    def _prepare_context(
        self, artifact_type: ArtifactType, bmad_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare template context data for specific artifact type.

        Args:
            artifact_type: Type of artifact
            bmad_data: BMAD pipeline data

        Returns:
            Context dictionary for template rendering
        """
        # Common context for all artifacts
        now = datetime.now()
        context = {
            "timestamp": now.strftime("%Y년 %m월 %d일"),
            "year": now.year,
            "requirement": bmad_data.get("requirement", ""),
            "project_name": self._extract_project_name(bmad_data),
            "metadata": {
                "version": "1.0.0",
                "created_at": now,
                "created_by": "CAAS",
            },
        }

        # Add type-specific context
        if artifact_type == ArtifactType.PROJECT_PROPOSAL:
            context.update(self._prepare_project_proposal_context(bmad_data))
        elif artifact_type == ArtifactType.REQUIREMENTS_SPEC:
            context.update(self._prepare_requirements_spec_context(bmad_data))
        elif artifact_type == ArtifactType.ARCHITECTURE_DESIGN:
            context.update(self._prepare_architecture_design_context(bmad_data))
        elif artifact_type == ArtifactType.DATA_DESIGN:
            context.update(self._prepare_data_design_context(bmad_data))
        elif artifact_type == ArtifactType.AGENT_DESIGN:
            context.update(self._prepare_agent_design_context(bmad_data))
        elif artifact_type == ArtifactType.API_DESIGN:
            context.update(self._prepare_api_design_context(bmad_data))
        # Add more types as needed

        return context

    def _prepare_project_proposal_context(
        self, bmad_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare context for project proposal"""
        golden_data = bmad_data.get("golden_data", {})

        return {
            "title": "프로젝트 기획서",
            "description": "프로젝트 목적, 범위, 목표를 정의한 기획서",
            "system_scope": golden_data.get("system_scope", {}),
            "features": golden_data.get("features", []),
            "domain": golden_data.get("domain", "GENERAL"),
        }

    def _prepare_requirements_spec_context(
        self, bmad_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare context for requirements specification"""
        golden_data = bmad_data.get("golden_data", {})

        return {
            "title": "요구사항 명세서",
            "description": "기능/비기능 요구사항 상세 정의",
            "features": golden_data.get("features", []),
            "data_models": golden_data.get("data_models", []),
            "ui_components": golden_data.get("ui_components", []),
            "non_functional_requirements": golden_data.get(
                "non_functional_requirements", {}
            ),
            "constraints": golden_data.get("constraints", []),
            "assumptions": golden_data.get("assumptions", []),
        }

    def _prepare_architecture_design_context(
        self, bmad_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare context for architecture design"""
        architecture = bmad_data.get("architecture", {})

        return {
            "title": "아키텍처 설계서",
            "description": "시스템 구조 및 컴포넌트 설계",
            "architecture": architecture,
            "components": architecture.get("components", []),
            "dependencies": architecture.get("dependencies", []),
        }

    def _prepare_data_design_context(self, bmad_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context for data design"""
        golden_data = bmad_data.get("golden_data", {})

        return {
            "title": "데이터 설계서",
            "description": "데이터 모델 및 스키마 정의",
            "data_models": golden_data.get("data_models", []),
            "relationships": self._extract_relationships(golden_data),
        }

    def _prepare_agent_design_context(
        self, bmad_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare context for agent design"""
        agents = bmad_data.get("agents", [])
        tasks = bmad_data.get("tasks", [])

        return {
            "title": "에이전트 설계서",
            "description": "AI 에이전트 역할 및 태스크 상세",
            "agents": agents,
            "tasks": tasks,
            "agent_count": len(agents),
            "task_count": len(tasks),
        }

    def _prepare_api_design_context(self, bmad_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context for API design"""
        return {
            "title": "API 설계서",
            "description": "REST API 엔드포인트 및 인터페이스 정의",
            "endpoints": bmad_data.get("endpoints", []),
        }

    def _extract_project_name(self, bmad_data: Dict[str, Any]) -> str:
        """Extract project name from BMAD data"""
        golden_data = bmad_data.get("golden_data", {})
        system_scope = golden_data.get("system_scope", {})

        if isinstance(system_scope, dict):
            return system_scope.get("project_name", "AI Agent System")

        return "AI Agent System"

    def _extract_relationships(
        self, golden_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract data model relationships"""
        relationships = []
        data_models = golden_data.get("data_models", [])

        for model in data_models:
            if isinstance(model, dict):
                model_relationships = model.get("relationships", [])
                for rel in model_relationships:
                    relationships.append(
                        {
                            "source": model.get("entity_name", "Unknown"),
                            "target": rel.get("target", "Unknown"),
                            "type": rel.get("type", "unknown"),
                        }
                    )

        return relationships

    def _save_artifact(
        self, artifact_type: ArtifactType, content: str
    ) -> Optional[Path]:
        """
        Save artifact to file.

        Args:
            artifact_type: Type of artifact
            content: Artifact content

        Returns:
            Path to saved file or None if failed
        """
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = (
                f"{artifact_type.value}_{timestamp}.{self.config.output_format.value}"
            )
            file_path = self.output_dir / filename

            # Write content
            file_path.write_text(content, encoding="utf-8")

            self.logger.debug(f"Saved artifact to: {file_path}")
            return file_path

        except Exception as e:
            self.logger.error(f"Failed to save artifact: {e}")
            return None
