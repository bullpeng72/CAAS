"""
Artifact Generator

개발 산출물 자동 생성
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

from caas_framework.models.artifact_types import (
    Artifact,
    ArtifactType,
    ArtifactFormat,
    ArtifactMetadata,
    ArtifactGenerationConfig,
    get_artifact_template_name,
)
from caas_app.artifacts.context import ArtifactGenerationContext
from caas_framework.utils.logger import get_logger
from caas_app.utils.config import PROJECT_ROOT

logger = get_logger("artifacts.generator")


class ArtifactGenerator:
    """산출물 생성기"""

    def __init__(
        self,
        config: Optional[ArtifactGenerationConfig] = None,
        template_dir: Optional[Path] = None,
    ):
        """
        Args:
            config: 산출물 생성 설정
            template_dir: 템플릿 디렉토리 (기본: data/templates/artifacts)
        """
        self.config = config or ArtifactGenerationConfig()

        # 템플릿 디렉토리 설정
        if template_dir is None:
            template_dir = PROJECT_ROOT / "data" / "templates" / "artifacts"

        template_dir.mkdir(parents=True, exist_ok=True)

        # Jinja2 환경 설정
        self.template_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # 커스텀 필터 추가
        self.template_env.filters['datetime'] = self._format_datetime
        self.template_env.filters['markdown_escape'] = self._markdown_escape

        logger.info(f"ArtifactGenerator initialized with template_dir={template_dir}")

    def _format_datetime(self, dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        """datetime 포맷팅"""
        return dt.strftime(format)

    def _markdown_escape(self, text: str) -> str:
        """Markdown 특수문자 이스케이프"""
        return text.replace('|', '\\|').replace('\n', '<br>')

    def generate_artifact(
        self,
        artifact_type: ArtifactType,
        context: Dict[str, Any],
        project_name: Optional[str] = None,
    ) -> Artifact:
        """
        산출물 생성

        Args:
            artifact_type: 산출물 타입
            context: 산출물 생성에 필요한 컨텍스트
            project_name: 프로젝트 이름

        Returns:
            Artifact: 생성된 산출물
        """
        logger.info(f"Generating artifact: {artifact_type}")

        # 메타데이터 생성
        metadata = ArtifactMetadata(
            artifact_type=artifact_type,
            format=self.config.output_format,
            title=self._get_artifact_title(artifact_type, project_name),
            project_name=project_name,
            description=context.get("description", ""),
            tags=context.get("tags", []),
        )

        # 템플릿 기반 산출물 생성
        content = self._render_template(artifact_type, context, metadata)

        # Artifact 객체 생성
        artifact = Artifact(
            metadata=metadata,
            content=content,
            related_artifacts=context.get("related_artifacts", []),
        )

        # 파일로 저장 (옵션)
        if self.config.enabled:
            file_path = self._save_artifact(artifact)
            artifact.file_path = str(file_path)
            logger.info(f"Artifact saved to: {file_path}")

        return artifact

    def _get_artifact_title(self, artifact_type: ArtifactType, project_name: Optional[str]) -> str:
        """산출물 제목 생성"""
        titles = {
            ArtifactType.PROJECT_PROPOSAL: "프로젝트 기획서",
            ArtifactType.REQUIREMENTS_SPEC: "요구사항 명세서",
            ArtifactType.ARCHITECTURE_DESIGN: "아키텍처 설계서",
            ArtifactType.DATA_DESIGN: "데이터 설계서",
            ArtifactType.API_DESIGN: "API 설계서",
            ArtifactType.AGENT_DESIGN: "에이전트 설계서",
            ArtifactType.TEST_PLAN: "테스트 계획서",
            ArtifactType.TEST_REPORT: "테스트 결과 리포트",
            ArtifactType.CODE_REVIEW: "코드 리뷰 리포트",
            ArtifactType.DEPLOYMENT_GUIDE: "배포 가이드",
        }

        base_title = titles.get(artifact_type, "산출물")

        if project_name:
            return f"{project_name} - {base_title}"
        return base_title

    def _render_template(
        self,
        artifact_type: ArtifactType,
        context: Dict[str, Any],
        metadata: ArtifactMetadata,
    ) -> str:
        """템플릿 렌더링"""
        template_name = get_artifact_template_name(artifact_type)

        try:
            template = self.template_env.get_template(template_name)

            # 컨텍스트에 메타데이터 추가
            render_context = {
                **context,
                "metadata": metadata,
                "config": self.config,
                "generated_at": datetime.now(),
            }

            content = template.render(**render_context)
            return content

        except Exception as e:
            logger.warning(f"Template rendering failed for {artifact_type}: {e}")
            # Fallback: 기본 템플릿 사용
            return self._generate_fallback_content(artifact_type, context, metadata)

    def _generate_fallback_content(
        self,
        artifact_type: ArtifactType,
        context: Dict[str, Any],
        metadata: ArtifactMetadata,
    ) -> str:
        """Fallback 산출물 생성 (템플릿 없을 때)"""
        lines = [
            f"# {metadata.title}",
            "",
            f"**버전**: {metadata.version}",
            f"**생성일**: {metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**생성자**: {metadata.created_by}",
            "",
            "---",
            "",
            "## 개요",
            "",
            f"{metadata.description or '설명 없음'}",
            "",
            "## 상세 내용",
            "",
            "※ 템플릿을 찾을 수 없어 기본 산출물로 생성되었습니다.",
            "",
            f"**타입**: {artifact_type.value}",
            "",
        ]

        # 컨텍스트 정보 추가
        if context:
            lines.append("## 컨텍스트 정보")
            lines.append("")
            for key, value in context.items():
                if key not in ["description", "tags", "related_artifacts"]:
                    lines.append(f"- **{key}**: {value}")
            lines.append("")

        return "\n".join(lines)

    def _save_artifact(self, artifact: Artifact) -> Path:
        """산출물을 파일로 저장"""
        # 출력 디렉토리 생성
        output_dir = Path(self.config.output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 프로젝트별 디렉토리 생성
        if artifact.metadata.project_name:
            output_dir = output_dir / artifact.metadata.project_name
            output_dir.mkdir(parents=True, exist_ok=True)

        # 파일명 생성
        timestamp = artifact.metadata.created_at.strftime("%Y%m%d_%H%M%S")
        artifact_type = artifact.metadata.artifact_type.value
        extension = self._get_file_extension(artifact.metadata.format)

        filename = f"{artifact_type}_{timestamp}{extension}"
        file_path = output_dir / filename

        # 파일 저장
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(artifact.content)

        return file_path

    def _get_file_extension(self, format: ArtifactFormat) -> str:
        """포맷에 따른 파일 확장자 반환"""
        extensions = {
            ArtifactFormat.MARKDOWN: ".md",
            ArtifactFormat.HTML: ".html",
            ArtifactFormat.PDF: ".pdf",
            ArtifactFormat.JSON: ".json",
        }
        return extensions.get(format, ".txt")

    def generate_all_artifacts(
        self,
        context: ArtifactGenerationContext,
    ) -> List[Artifact]:
        """
        모든 활성화된 산출물 생성 (Refactored P1.3: 1 parameter vs 15 parameters)

        Before:
            generate_all_artifacts(project_name, requirement, golden_data, bmad_mapping,
                                   agents, tasks, test_summary, test_results, coverage,
                                   validation_result, code_files, code_metrics,
                                   security_issues, performance_issues)

        After:
            generate_all_artifacts(context)

        Args:
            context: Artifact generation context with all required data

        Returns:
            List[Artifact]: 생성된 산출물 목록
        """
        if not self.config.enabled:
            logger.info("Artifact generation is disabled")
            return []

        artifacts = []
        enabled_types = self.config.get_enabled_artifact_types()

        logger.info(
            f"Generating {len(enabled_types)} artifacts for project: {context.project_name}"
        )

        for artifact_type in enabled_types:
            try:
                render_context = self._build_context(artifact_type, context)

                artifact = self.generate_artifact(
                    artifact_type=artifact_type,
                    context=render_context,
                    project_name=context.project_name,
                )

                artifacts.append(artifact)

            except Exception as e:
                logger.error(f"Failed to generate {artifact_type}: {e}")
                continue

        logger.info(f"Successfully generated {len(artifacts)} artifacts")
        return artifacts

    def _build_context(
        self,
        artifact_type: ArtifactType,
        context: ArtifactGenerationContext,
    ) -> Dict[str, Any]:
        """
        산출물 타입에 맞는 컨텍스트 구성 (Refactored P1.3: 2 parameters vs 14 parameters)

        Before:
            _build_context(artifact_type, requirement, golden_data, bmad_mapping,
                          agents, tasks, test_summary, test_results, coverage,
                          validation_result, code_files, code_metrics,
                          security_issues, performance_issues)

        After:
            _build_context(artifact_type, context)

        Args:
            artifact_type: 산출물 타입
            context: Artifact generation context

        Returns:
            Dict with artifact-specific context data
        """
        base_context = {
            "requirement": context.requirement,
            "include_diagrams": self.config.include_diagrams,
            "include_code_samples": self.config.include_code_samples,
            "language": self.config.language,
        }

        if artifact_type == ArtifactType.PROJECT_PROPOSAL:
            # 프로젝트 기획서는 원본 요구사항만 필요
            return {
                **base_context,
                "description": "프로젝트의 목적과 범위를 정의합니다.",
            }

        elif artifact_type == ArtifactType.REQUIREMENTS_SPEC:
            # 요구사항 명세서는 Golden Data 필요
            return {
                **base_context,
                "golden_data": context.golden_data,
                "description": "상세 요구사항을 명세합니다.",
            }

        elif artifact_type == ArtifactType.ARCHITECTURE_DESIGN:
            # 아키텍처 설계서는 BMAD 매핑 필요
            return {
                **base_context,
                "golden_data": context.golden_data,
                "bmad_mapping": context.bmad_mapping,
                "description": "시스템 아키텍처를 설계합니다.",
            }

        elif artifact_type == ArtifactType.AGENT_DESIGN:
            # 에이전트 설계서는 Agent/Task 정보 필요
            return {
                **base_context,
                "agents": context.agents or [],
                "tasks": context.tasks or [],
                "description": "AI 에이전트와 태스크를 설계합니다.",
            }

        elif artifact_type == ArtifactType.DATA_DESIGN:
            # 데이터 설계서
            return {
                **base_context,
                "golden_data": context.golden_data,
                "agents": context.agents or [],
                "description": "데이터 모델과 스키마를 설계합니다.",
            }

        elif artifact_type == ArtifactType.API_DESIGN:
            # API 설계서
            return {
                **base_context,
                "agents": context.agents or [],
                "tasks": context.tasks or [],
                "description": "REST API를 설계합니다.",
            }

        elif artifact_type == ArtifactType.TEST_PLAN:
            # 테스트 계획서
            return {
                **base_context,
                "agents": context.agents or [],
                "tasks": context.tasks or [],
                "description": "테스트 전략과 시나리오를 계획합니다.",
            }

        elif artifact_type == ArtifactType.TEST_REPORT:
            # 테스트 결과 리포트
            return {
                **base_context,
                "test_summary": context.test_summary or {},
                "test_results": context.test_results or {},
                "coverage": context.coverage or {},
                "validation_result": context.validation_result or {},
                "description": "테스트 실행 결과 및 커버리지를 리포트합니다.",
            }

        elif artifact_type == ArtifactType.CODE_REVIEW:
            # 코드 리뷰 리포트
            return {
                **base_context,
                "code_files": context.code_files or [],
                "validation_result": context.validation_result or {},
                "code_metrics": context.code_metrics or {},
                "security_issues": context.security_issues or {},
                "performance_issues": context.performance_issues or [],
                "description": "코드 품질, 보안, 성능을 분석합니다.",
            }

        elif artifact_type == ArtifactType.DEPLOYMENT_GUIDE:
            # 배포 가이드
            return {
                **base_context,
                "agents": context.agents or [],
                "description": "배포 절차를 안내합니다.",
            }

        return base_context
