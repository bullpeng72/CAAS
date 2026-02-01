"""
Async Workflow Runner

비동기로 BMAD 워크플로우를 실행하고 프로젝트 상태를 업데이트합니다.
"""

import asyncio
from typing import Dict, Optional, List
from datetime import datetime

from app.core.bmad import BMADEngine, BMADContext
from app.workflow.project_service import get_project_service
from app.utils.logger import get_logger
from app.utils.config import get_settings
from app.artifacts.generator import ArtifactGenerator
from app.models.artifact_types import ArtifactType
from app.core.sdd.multi_spec import UIPage, UIComponent, UIComponentType

logger = get_logger("workflow_runner")
settings = get_settings()

# Global registry of running workflows
_running_workflows: Dict[str, asyncio.Task] = {}


class WorkflowRunner:
    """
    비동기 워크플로우 실행기

    BMAD 엔진을 백그라운드에서 실행하고 프로젝트 상태를 실시간으로 업데이트합니다.
    """

    def __init__(self):
        self.engine = BMADEngine()
        self.project_service = get_project_service()

        # Initialize artifact generator if enabled
        self.artifact_generator = None
        if settings.artifacts.enabled:
            from app.models.artifact_types import ArtifactGenerationConfig
            config = ArtifactGenerationConfig(
                enabled=settings.artifacts.enabled,
                output_format=settings.artifacts.output_format,
                output_directory=settings.artifacts.output_directory,
                include_diagrams=settings.artifacts.include_diagrams,
                include_code_samples=settings.artifacts.include_code_samples,
                language=settings.artifacts.language,
            )
            self.artifact_generator = ArtifactGenerator(config=config)
            logger.info("Artifact generation enabled")

    async def run_workflow(
        self,
        project_id: str,
        requirement: str,
        project_name: str = "Generated Project",
        domain: Optional[str] = None,
        enable_adaptive: bool = True,
        enable_frontend: bool = False,
        frontend_framework: str = "streamlit"
    ) -> BMADContext:
        """
        워크플로우 비동기 실행

        Args:
            project_id: 프로젝트 ID
            requirement: 요구사항
            project_name: 프로젝트 이름
            domain: 도메인
            enable_adaptive: Scale-Adaptive Intelligence 활성화
            enable_frontend: Frontend 생성 활성화
            frontend_framework: Frontend 프레임워크 (streamlit, gradio)

        Returns:
            BMADContext: 완료된 컨텍스트
        """
        try:
            logger.info(f"Starting workflow for project {project_id} (frontend: {enable_frontend})")

            # Update status to generating
            self.project_service.update_project(project_id, {
                "status": "generating",
                "progress": 5,
                "current_phase": 0
            })

            # Run BMAD pipeline in executor (to avoid blocking)
            loop = asyncio.get_event_loop()
            context = await loop.run_in_executor(
                None,
                self._run_bmad_sync,
                project_name,
                requirement,
                enable_adaptive,
                project_id
            )

            # Extract generated files
            files = {}
            if context.generated_code:
                files = context.generated_code

            # Generate frontend if enabled
            if enable_frontend:
                logger.info(f"[{project_id}] Generating frontend ({frontend_framework})...")
                self.project_service.update_project(project_id, {
                    "progress": 0.95,
                    "current_phase": 5
                })

                frontend_files = await loop.run_in_executor(
                    None,
                    self._generate_frontend_sync,
                    frontend_framework,
                    context
                )

                # Add frontend files with prefix
                for filepath, content in frontend_files.items():
                    files[f"frontend/{filepath}"] = content

                logger.info(f"[{project_id}] Frontend generated: {len(frontend_files)} files")

            # Calculate generation time
            generation_time = (datetime.now() - datetime.fromisoformat(
                self.project_service.get_project(project_id)["created_at"]
            )).total_seconds()

            # Extract phases completed
            phases_completed = [
                phase["phase"] for phase in context.phase_history
                if phase.get("status") == "completed"
            ]

            # Mark project as completed
            self.project_service.complete_project(
                project_id=project_id,
                files=files,
                generation_time=generation_time,
                phases_completed=phases_completed
            )

            logger.info(f"Workflow completed for project {project_id}")
            return context

        except Exception as e:
            logger.error(f"Workflow failed for project {project_id}: {e}", exc_info=True)

            # Mark project as failed
            self.project_service.fail_project(
                project_id=project_id,
                error_message=str(e)
            )

            raise
        finally:
            # Remove from running workflows
            if project_id in _running_workflows:
                del _running_workflows[project_id]

    def _run_bmad_sync(
        self,
        project_name: str,
        requirement: str,
        enable_adaptive: bool,
        project_id: str
    ) -> BMADContext:
        """
        BMAD 파이프라인 동기 실행 (with progress updates)

        이 메서드는 executor에서 실행되어 메인 이벤트 루프를 블로킹하지 않습니다.
        """
        # Create context
        context = self.engine.create_context(project_name, requirement)

        try:
            # Phase 0: Concretization (10%)
            logger.info(f"[{project_id}] Phase 0: Concretization")
            self.project_service.update_project(project_id, {
                "progress": 10,
                "current_phase": 0
            })
            context = self.engine.execute_concretization(context)

            # Generate project proposal artifact
            if self.artifact_generator and settings.artifacts.generate_project_proposal:
                self._generate_and_save_artifact(
                    project_id,
                    ArtifactType.PROJECT_PROPOSAL,
                    context,
                    project_name
                )

            # Phase 1: Discovery (30%)
            logger.info(f"[{project_id}] Phase 1: Discovery")
            self.project_service.update_project(project_id, {
                "progress": 30,
                "current_phase": 1
            })
            context = self.engine.execute_discovery(context, enable_sharding=True)

            # Generate requirements specification artifact
            if self.artifact_generator and settings.artifacts.generate_requirements_spec:
                self._generate_and_save_artifact(
                    project_id,
                    ArtifactType.REQUIREMENTS_SPEC,
                    context,
                    project_name
                )

            # Phase 2: Architecture (50%)
            logger.info(f"[{project_id}] Phase 2: Architecture")
            self.project_service.update_project(project_id, {
                "progress": 50,
                "current_phase": 2
            })
            context = self.engine.execute_architecture(context)

            # Generate architecture design artifact
            if self.artifact_generator and settings.artifacts.generate_architecture_design:
                self._generate_and_save_artifact(
                    project_id,
                    ArtifactType.ARCHITECTURE_DESIGN,
                    context,
                    project_name
                )

            # Generate data design artifact
            if self.artifact_generator and settings.artifacts.generate_data_design:
                self._generate_and_save_artifact(
                    project_id,
                    ArtifactType.DATA_DESIGN,
                    context,
                    project_name
                )

            # Phase 3: Design (70%)
            logger.info(f"[{project_id}] Phase 3: Design")
            self.project_service.update_project(project_id, {
                "progress": 70,
                "current_phase": 3
            })
            context = self.engine.execute_design(context)

            # Generate agent design artifact
            if self.artifact_generator and settings.artifacts.generate_agent_design:
                self._generate_and_save_artifact(
                    project_id,
                    ArtifactType.AGENT_DESIGN,
                    context,
                    project_name
                )

            # Phase 4: Development (85%)
            logger.info(f"[{project_id}] Phase 4: Development")
            self.project_service.update_project(project_id, {
                "progress": 85,
                "current_phase": 4
            })
            context = self.engine.execute_development(context)

            # Generate test plan artifact
            if self.artifact_generator and settings.artifacts.generate_test_plan:
                self._generate_and_save_artifact(
                    project_id,
                    ArtifactType.TEST_PLAN,
                    context,
                    project_name
                )

            # Generate API design artifact
            if self.artifact_generator and settings.artifacts.generate_api_design:
                self._generate_and_save_artifact(
                    project_id,
                    ArtifactType.API_DESIGN,
                    context,
                    project_name
                )

            # Phase 5: Delivery (95%)
            logger.info(f"[{project_id}] Phase 5: Delivery")
            self.project_service.update_project(project_id, {
                "progress": 95,
                "current_phase": 5
            })
            context = self.engine.execute_delivery(context)

            # Generate code review artifact (after code generation)
            if self.artifact_generator and settings.artifacts.generate_code_review:
                self._generate_and_save_artifact(
                    project_id,
                    ArtifactType.CODE_REVIEW,
                    context,
                    project_name
                )

            # Generate test report artifact (after testing)
            if self.artifact_generator and settings.artifacts.generate_test_report:
                self._generate_and_save_artifact(
                    project_id,
                    ArtifactType.TEST_REPORT,
                    context,
                    project_name
                )

            # Generate deployment guide artifact
            if self.artifact_generator and settings.artifacts.generate_deployment_guide:
                self._generate_and_save_artifact(
                    project_id,
                    ArtifactType.DEPLOYMENT_GUIDE,
                    context,
                    project_name
                )

            logger.info(f"[{project_id}] All phases completed")
            return context

        except Exception as e:
            logger.error(f"[{project_id}] Phase execution failed: {e}")
            raise

    def _generate_and_save_artifact(
        self,
        project_id: str,
        artifact_type: ArtifactType,
        context: BMADContext,
        project_name: str
    ):
        """
        산출물을 생성하고 저장합니다.

        Args:
            project_id: 프로젝트 ID
            artifact_type: 산출물 타입
            context: BMAD Context
            project_name: 프로젝트 이름
        """
        try:
            from pathlib import Path

            logger.info(f"[{project_id}] Generating {artifact_type} artifact")

            # Prepare context for artifact generation
            artifact_context = {
                "project_name": project_name,
                "requirement": context.requirement,
                "golden_data": context.concretized_requirement,
                "analysis": context.analysis,
                "architecture": context.architecture_design,
                "agents": context.agent_specs,
                "tasks": context.task_specs,
            }

            # Add code files for CODE_REVIEW artifact
            if artifact_type == ArtifactType.CODE_REVIEW and context.generated_code:
                code_files = []
                for file_path, file_content in context.generated_code.items():
                    code_files.append({
                        "path": file_path,
                        "content": file_content,
                        "lines": len(file_content.splitlines())
                    })
                artifact_context["code_files"] = code_files
                artifact_context["validation_result"] = context.validation_result or {}
                # TODO: Add code_metrics, security_issues, performance_issues when available
                artifact_context["code_metrics"] = {}
                artifact_context["security_issues"] = {}
                artifact_context["performance_issues"] = []

            # Add test data for TEST_REPORT artifact
            if artifact_type == ArtifactType.TEST_REPORT:
                # TODO: Extract actual test results when test execution is implemented
                artifact_context["test_summary"] = {}
                artifact_context["test_results"] = {}
                artifact_context["coverage"] = {}
                artifact_context["validation_result"] = context.validation_result or {}

            # Generate artifact
            artifact = self.artifact_generator.generate_artifact(
                artifact_type=artifact_type,
                context=artifact_context,
                project_name=project_name
            )

            # Save to file
            output_dir = Path(settings.artifacts.output_directory) / project_id
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{artifact.metadata.artifact_type.value}.{artifact.metadata.format.value}"
            output_file = output_dir / filename
            output_file.write_text(artifact.content, encoding='utf-8')

            logger.info(f"[{project_id}] Saved {artifact_type} to {output_file}")

        except Exception as e:
            logger.error(f"[{project_id}] Failed to generate {artifact_type}: {e}", exc_info=True)
            # Don't fail the workflow if artifact generation fails

    def _generate_frontend_sync(
        self,
        frontend_framework: str,
        context: BMADContext
    ) -> Dict[str, str]:
        """
        Frontend 코드 동기 생성

        Args:
            frontend_framework: Frontend 프레임워크 (streamlit, gradio)
            context: BMAD Context

        Returns:
            Dict[str, str]: 생성된 frontend 파일들
        """
        try:
            from app.codegen.multi_generator import MultiArtifactGenerator, FrontendSpec, FrontendFramework

            generator = MultiArtifactGenerator()

            # Determine framework
            if frontend_framework.lower() == "gradio":
                framework = FrontendFramework.GRADIO
                port = 7860
            else:  # Default to streamlit
                framework = FrontendFramework.STREAMLIT
                port = 8502

            # Create UI pages from analysis result (요구사항 기반)
            pages = []
            if context.analysis_result:
                pages = self._create_ui_pages_from_analysis(
                    context.analysis_result,
                    context.agents,
                    context.tasks
                )
                logger.info(f"Created {len(pages)} domain-specific UI pages from analysis")

            # Create frontend spec
            frontend_spec = FrontendSpec(
                framework=framework,
                pages=pages,
                port=port,
                api_client={'base_url': 'http://localhost:8001'}  # 생성된 프로젝트 포트
            )

            # Determine if backend exists
            has_backend = bool(context.generated_code)

            # Generate frontend
            frontend_files = generator._generate_frontend(frontend_spec, has_backend=has_backend)

            return frontend_files

        except Exception as e:
            logger.error(f"Frontend generation failed: {e}")
            raise

    def _create_ui_pages_from_analysis(
        self,
        analysis,
        agents: List[Dict],
        tasks: List[Dict]
    ) -> List[UIPage]:
        """
        요구사항 분석 결과에서 도메인 특화 UI 페이지 생성

        Args:
            analysis: AnalysisResult 객체
            agents: 에이전트 리스트
            tasks: 태스크 리스트

        Returns:
            List[UIPage]: 생성된 UI 페이지들
        """
        try:
            pages = []

            # 도메인 타입 확인
            domain_type = None
            if hasattr(analysis, 'domain_classification') and analysis.domain_classification:
                domain_type = analysis.domain_classification.domain_type
                logger.info(f"Creating UI for domain type: {domain_type}")

            # 도메인별 특화 UI 생성
            if domain_type in ["data_analysis", "analytics", "monitoring"]:
                # 데이터 분석/대시보드형 UI
                pages.append(self._create_dashboard_page(analysis, tasks))
            elif domain_type in ["content_generation", "content_creator"]:
                # 컨텐츠 생성형 UI
                pages.append(self._create_content_generation_page(analysis, agents))
            else:
                # 기본 UI (하지만 요구사항 반영)
                pages.append(self._create_default_page(analysis, agents, tasks))

            return pages

        except Exception as e:
            logger.error(f"Failed to create UI pages from analysis: {e}")
            # 실패 시 빈 리스트 반환 (fallback to generic UI)
            return []

    def _create_dashboard_page(self, analysis, tasks: List[Dict]) -> UIPage:
        """
        데이터 분석/대시보드형 UI 페이지 생성

        뉴스 수집, 감성 분석, 모니터링 등 데이터 처리 시스템에 적합
        """
        # 요구사항에서 핵심 키워드 추출
        requirement = analysis.raw_requirement.lower()

        components = []

        # 1. 입력 섹션
        if "뉴스" in requirement or "news" in requirement:
            components.append(UIComponent(
                component_id="stock_symbol",
                component_type=UIComponentType.TEXT_INPUT,
                label="주식 심볼",
                description="분석할 주식 심볼을 입력하세요 (예: AAPL, TSLA)",
                props={"placeholder": "AAPL"}
            ))
            components.append(UIComponent(
                component_id="news_sources",
                component_type=UIComponentType.SELECT,
                label="뉴스 소스 선택",
                description="뉴스를 수집할 소스를 선택하세요",
                props={"options": ["All Sources", "RSS Feeds", "Financial News Sites", "Social Media"]}
            ))
        else:
            # 일반 데이터 입력
            components.append(UIComponent(
                component_id="input_query",
                component_type=UIComponentType.TEXT_INPUT,
                label="검색 쿼리",
                description="분석할 데이터 검색 쿼리를 입력하세요"
            ))

        # 2. 실행 버튼
        components.append(UIComponent(
            component_id="start_analysis",
            component_type=UIComponentType.BUTTON,
            label="분석 시작"
        ))

        # 3. 결과 표시 섹션
        if "감성" in requirement or "sentiment" in requirement:
            components.append(UIComponent(
                component_id="sentiment_chart",
                component_type=UIComponentType.CHART,
                label="감성 분석 결과",
                description="시간에 따른 감성 점수 변화"
            ))

        if "뉴스" in requirement or "news" in requirement or "article" in requirement:
            components.append(UIComponent(
                component_id="news_table",
                component_type=UIComponentType.TABLE,
                label="수집된 뉴스",
                description="최근 수집된 뉴스 목록 (제목, 출처, 감성 점수)"
            ))

        if "인사이트" in requirement or "insight" in requirement:
            components.append(UIComponent(
                component_id="insights_display",
                component_type=UIComponentType.MARKDOWN,
                label="AI 인사이트",
                description="GPT가 생성한 투자 인사이트 및 요약"
            ))

        # 4. 알림 설정
        if "알림" in requirement or "notification" in requirement or "이메일" in requirement or "슬랙" in requirement:
            components.append(UIComponent(
                component_id="notification_settings",
                component_type=UIComponentType.MARKDOWN,
                label="알림 설정",
                description="이메일 및 슬랙 알림 구성"
            ))

        return UIPage(
            name="dashboard",
            title="실시간 분석 대시보드",
            description="데이터를 실시간으로 수집하고 분석 결과를 시각화합니다",
            components=components,
            layout="single_column"
        )

    def _create_content_generation_page(self, analysis, agents: List[Dict]) -> UIPage:
        """
        컨텐츠 생성형 UI 페이지 생성

        블로그 작성, 코드 생성 등 컨텐츠 생성 시스템에 적합
        """
        requirement = analysis.raw_requirement.lower()

        components = [
            UIComponent(
                component_id="content_topic",
                component_type=UIComponentType.TEXT_INPUT,
                label="주제",
                description="생성할 컨텐츠의 주제를 입력하세요"
            ),
            UIComponent(
                component_id="content_details",
                component_type=UIComponentType.TEXT_AREA,
                label="상세 요구사항",
                description="컨텐츠 생성을 위한 구체적인 요구사항을 입력하세요",
                props={"height": 150}
            ),
            UIComponent(
                component_id="generate_button",
                component_type=UIComponentType.BUTTON,
                label="생성 시작"
            ),
            UIComponent(
                component_id="generated_content",
                component_type=UIComponentType.MARKDOWN,
                label="생성된 컨텐츠",
                description="AI가 생성한 컨텐츠가 여기에 표시됩니다"
            )
        ]

        return UIPage(
            name="content_generator",
            title="컨텐츠 생성기",
            description="AI를 활용하여 고품질 컨텐츠를 자동 생성합니다",
            components=components,
            layout="single_column"
        )

    def _create_default_page(self, analysis, agents: List[Dict], tasks: List[Dict]) -> UIPage:
        """
        기본 UI 페이지 생성 (요구사항 반영)

        범용 에이전트 실행 인터페이스 + 요구사항 특화
        """
        requirement = analysis.raw_requirement

        # 기본 컴포넌트
        components = [
            UIComponent(
                component_id="user_input",
                component_type=UIComponentType.TEXT_AREA,
                label="입력",
                description=f"요청 내용을 입력하세요. 시스템: {requirement[:100]}...",
                props={"height": 150, "placeholder": "작업 내용을 입력하세요..."}
            ),
            UIComponent(
                component_id="execute_button",
                component_type=UIComponentType.BUTTON,
                label="실행"
            ),
            UIComponent(
                component_id="result_display",
                component_type=UIComponentType.MARKDOWN,
                label="실행 결과",
                description="에이전트 실행 결과가 여기에 표시됩니다"
            )
        ]

        # 에이전트 정보 표시
        if agents:
            agent_info = f"**사용 가능한 에이전트:** {len(agents)}개\n\n"
            for agent in agents[:5]:  # 최대 5개만
                role = agent.get('role', 'Unknown')
                goal = agent.get('goal', '')
                agent_info += f"- **{role}**: {goal[:100]}...\n"

            components.insert(0, UIComponent(
                component_id="agent_info",
                component_type=UIComponentType.MARKDOWN,
                label="시스템 정보",
                description=agent_info
            ))

        return UIPage(
            name="main",
            title="멀티 에이전트 시스템",
            description=f"AI 에이전트를 활용한 작업 실행 시스템",
            components=components,
            layout="single_column"
        )

    async def cancel_workflow(self, project_id: str) -> bool:
        """
        실행 중인 워크플로우 취소

        Args:
            project_id: 프로젝트 ID

        Returns:
            bool: 취소 성공 여부
        """
        if project_id not in _running_workflows:
            logger.warning(f"No running workflow found for project {project_id}")
            return False

        task = _running_workflows[project_id]

        if not task.done():
            task.cancel()
            logger.info(f"Cancelled workflow for project {project_id}")

            # Update project status
            self.project_service.fail_project(
                project_id=project_id,
                error_message="Cancelled by user"
            )

            return True

        return False


# Global singleton instance
_workflow_runner: Optional[WorkflowRunner] = None


def get_workflow_runner() -> WorkflowRunner:
    """Get or create global workflow runner instance"""
    global _workflow_runner

    if _workflow_runner is None:
        _workflow_runner = WorkflowRunner()

    return _workflow_runner


async def start_workflow(
    project_id: str,
    requirement: str,
    project_name: str = "Generated Project",
    domain: Optional[str] = None,
    enable_frontend: bool = False,
    frontend_framework: str = "streamlit"
) -> asyncio.Task:
    """
    워크플로우를 백그라운드 태스크로 시작

    Args:
        project_id: 프로젝트 ID
        requirement: 요구사항
        project_name: 프로젝트 이름
        domain: 도메인
        enable_frontend: Frontend 생성 활성화
        frontend_framework: Frontend 프레임워크 (streamlit, gradio)

    Returns:
        asyncio.Task: 실행 중인 태스크
    """
    runner = get_workflow_runner()

    # Create background task
    task = asyncio.create_task(
        runner.run_workflow(
            project_id=project_id,
            requirement=requirement,
            project_name=project_name,
            domain=domain,
            enable_frontend=enable_frontend,
            frontend_framework=frontend_framework
        )
    )

    # Register in global registry
    _running_workflows[project_id] = task

    logger.info(f"Started background workflow for project {project_id} (frontend: {enable_frontend})")

    return task


async def cancel_workflow(project_id: str) -> bool:
    """
    실행 중인 워크플로우 취소

    Args:
        project_id: 프로젝트 ID

    Returns:
        bool: 취소 성공 여부
    """
    runner = get_workflow_runner()
    return await runner.cancel_workflow(project_id)


def is_workflow_running(project_id: str) -> bool:
    """
    워크플로우가 실행 중인지 확인

    Args:
        project_id: 프로젝트 ID

    Returns:
        bool: 실행 중 여부
    """
    if project_id not in _running_workflows:
        return False

    task = _running_workflows[project_id]
    return not task.done()
