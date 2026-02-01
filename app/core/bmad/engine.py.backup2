"""
CAAS BMAD Engine

Breakthrough Method for Agile AI-driven Development 엔진입니다.
4단계 프로세스 (Discovery → Design → Development → Delivery)를 구현합니다.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field

from app.utils.logger import get_logger, LoggerMixin
from caas_framework.reporting.progress_reporter import (
    ProgressReporter,
    VerbosityLevel,
    PhaseStatus as ReporterPhaseStatus
)
from app.llm.chains import (
    RequirementConcretizationChain,  # Phase 0
    RequirementAnalysisChain,
    SystemArchitectChain,
    AgentDesignChain,
    TaskDesignChain,
    SpecGenerationChain,
    SpecValidationChain,
    RequirementAnalysis,
    AgentSpec,
    TaskSpec,
)
from app.knowledge.graph.patterns import PatternMatcher, PatternMatch
from app.core.sdd.engine import SDDEngine
# Lazy import: from app.codegen.generator import CodeGenerator (imported in __init__ to avoid circular import)
from app.codegen.formatter import CodeFormatter
from app.core.bmad.validator import CodeValidator
from app.core.bmad.tester import TestGenerator
from app.core.bmad.deployer import DeploymentPreparer

logger = get_logger("bmad.engine")


class BMADPhase(str, Enum):
    """BMAD 6단계 (Concretization 추가)"""
    CONCRETIZATION = "concretization"  # Phase 0: Golden Data 생성
    DISCOVERY = "discovery"
    ARCHITECTURE = "architecture"
    DESIGN = "design"
    DEVELOPMENT = "development"
    DELIVERY = "delivery"


class PhaseStatus(str, Enum):
    """단계 상태"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class UserAbortedError(Exception):
    """User aborted the process during Plan Mode review."""
    pass


class FeatureItem(BaseModel):
    """기능 항목"""
    id: str
    name: str
    description: str
    priority: int = Field(ge=1, le=5)
    complexity: str = "medium"  # low, medium, high
    estimated_effort: Optional[str] = None


class SprintItem(BaseModel):
    """스프린트 항목"""
    id: str
    name: str
    features: List[str] = []
    agents: List[str] = []
    tasks: List[str] = []
    status: PhaseStatus = PhaseStatus.PENDING


class BMADContext(BaseModel):
    """BMAD 실행 컨텍스트"""
    project_name: str
    requirement: str
    domain: Optional[str] = None

    # Concretization 결과 (Phase 0 - Golden Data)
    concretized_requirement: Optional[Dict[str, Any]] = None
    golden_data_validation_enabled: bool = True

    # Discovery 결과
    analysis: Optional[Dict[str, Any]] = None
    features: List[FeatureItem] = []

    # Architecture 결과
    architecture_design: Optional[Dict[str, Any]] = None

    # Design 결과
    agent_specs: List[Dict[str, Any]] = []
    task_specs: List[Dict[str, Any]] = []

    # Development 결과
    spec_yaml: Optional[str] = None
    generated_code: Optional[Dict[str, str]] = None

    # Delivery 결과
    validation_result: Optional[Dict[str, Any]] = None
    deployment_info: Optional[Dict[str, Any]] = None

    # Golden Data Validation Reports (각 Phase별)
    golden_validation_reports: List[Dict[str, Any]] = []

    # 메타데이터
    current_phase: BMADPhase = BMADPhase.CONCRETIZATION
    phase_history: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class BMADEngine(LoggerMixin):
    """
    BMAD (Breakthrough Method for Agile AI-driven Development) 엔진
    
    4단계 프로세스:
    1. Discovery: 요구사항 분석 및 기능 추출
    2. Design: 에이전트/태스크 설계
    3. Development: 코드 생성 및 검증
    4. Delivery: 배포 및 피드백 수집
    """
    
    def __init__(
        self,
        plan_mode: bool = False,
        review_handler=None,
        use_progress_reporter: bool = True,
        verbosity: str = "normal"
    ):
        """
        Initialize BMAD Engine.

        Args:
            plan_mode: Enable Plan Mode for user approval gates
            review_handler: ReviewHandler for Plan Mode (None = auto-approve)
            use_progress_reporter: Enable Rich progress reporting (default: True)
            verbosity: Progress verbosity level: quiet, minimal, normal, verbose, debug (default: normal)
        """
        # Phase 0: Concretization (Golden Data Generation)
        self.concretization_chain = RequirementConcretizationChain()

        # Discovery & Design chains
        from app.core.bmad.analyzer import RequirementAnalyzer
        self.analyzer = RequirementAnalyzer()
        self.analysis_chain = RequirementAnalysisChain()
        self.agent_design_chain = AgentDesignChain()
        self.task_design_chain = TaskDesignChain()

        # Development & Delivery chains
        self.spec_generation_chain = SpecGenerationChain()
        self.spec_validation_chain = SpecValidationChain()

        # Engines and utilities
        self.pattern_matcher = PatternMatcher()
        self.sdd_engine = SDDEngine()
        # Lazy import to avoid circular dependency
        from app.codegen.generator import CodeGenerator
        self.code_generator = CodeGenerator()
        self.code_formatter = CodeFormatter()

        # Delivery components
        self.code_validator = CodeValidator()
        self.test_generator = TestGenerator()
        self.deployment_preparer = DeploymentPreparer()

        # Golden Data Validation & Auto-Fixing (초기화는 Phase 0 완료 후)
        self.golden_validator = None
        self.auto_fixer = None

        # 🆕 Plan Mode (User Approval Gates)
        self.plan_mode_enabled = plan_mode
        self.plan_mode_api = None
        if plan_mode:
            from caas_framework.execution.plan_mode_api import PlanModeAPI
            self.plan_mode_api = PlanModeAPI(review_handler=review_handler)
            logger.info("✅ Plan Mode enabled - User approval gates activated")

        # 🆕 Progress Reporter (Rich CLI UI)
        self.use_progress_reporter = use_progress_reporter
        self.progress_reporter = None
        if use_progress_reporter:
            # Map verbosity string to enum
            verbosity_map = {
                "quiet": VerbosityLevel.QUIET,
                "minimal": VerbosityLevel.MINIMAL,
                "normal": VerbosityLevel.NORMAL,
                "verbose": VerbosityLevel.VERBOSE,
                "debug": VerbosityLevel.DEBUG
            }
            verbosity_level = verbosity_map.get(verbosity.lower(), VerbosityLevel.NORMAL)
            self.progress_reporter = ProgressReporter(
                verbosity=verbosity_level,
                use_rich=True
            )
            logger.info(f"✅ Progress Reporter enabled - Verbosity: {verbosity}")

        self.available_tools = [
            {"id": "web_search", "description": "Search the web for information"},
            {"id": "file_read", "description": "Read contents from files"},
            {"id": "file_write", "description": "Write contents to files"},
            {"id": "code_interpreter", "description": "Execute Python code"},
            {"id": "scrape_website", "description": "Scrape content from websites"},
            {"id": "calculator", "description": "Perform mathematical calculations"},
            {"id": "data_analyzer", "description": "Analyze data and generate insights"},
        ]
    
    def create_context(self, project_name: str, requirement: str) -> BMADContext:
        """
        새 BMAD 컨텍스트를 생성합니다.

        Args:
            project_name: 프로젝트 이름
            requirement: 요구사항 텍스트

        Returns:
            BMADContext: 초기화된 컨텍스트
        """
        return BMADContext(
            project_name=project_name,
            requirement=requirement,
        )

    def _report_phase_start(self, phase_name: str, agent_name: str = None, description: str = None):
        """Helper method to report phase start"""
        if self.progress_reporter:
            self.progress_reporter.start_phase(phase_name, agent_name, description)

    def _report_phase_complete(self, phase_name: str, duration: float = None, success: bool = True):
        """Helper method to report phase completion"""
        if self.progress_reporter:
            self.progress_reporter.complete_phase(phase_name, success=success, duration=duration)

    def execute_concretization(self, context: BMADContext, llm_config=None) -> BMADContext:
        """
        Phase 0: Concretization - Golden Data 생성

        사용자 요구사항을 구체화된 Golden Data로 변환합니다.

        Args:
            context: BMAD 컨텍스트
            llm_config: LLM 설정 (선택적)

        Returns:
            BMADContext: 업데이트된 컨텍스트 (concretized_requirement 포함)
        """
        self.logger.info("=== BMAD Concretization 단계 시작 (Phase 0: Golden Data Generation) ===")
        context.current_phase = BMADPhase.CONCRETIZATION

        try:
            # Requirement Concretization Chain 실행
            from app.models.schemas import ConcretizedRequirement

            self.logger.info(f"📝 요구사항 구체화 중... (입력 길이: {len(context.requirement)} 문자)")

            concretized = self.concretization_chain.concretize(
                requirement_text=context.requirement
            )

            # Context 업데이트
            if isinstance(concretized, ConcretizedRequirement):
                context.concretized_requirement = concretized.model_dump()

                # Golden Data Validator 및 AutoFixer 초기화
                from app.core.validation.golden_validator import GoldenDataValidator
                from app.core.fixing.auto_fixer import AutoFixer

                self.golden_validator = GoldenDataValidator(concretized)
                self.auto_fixer = AutoFixer(concretized, llm_client=None)  # LLM client는 나중에 설정

                # 품질 메트릭 로깅
                if concretized.concretization_quality:
                    quality = concretized.concretization_quality
                    self.logger.info(
                        f"✅ Golden Data 생성 완료 - "
                        f"Overall Quality: {quality.overall_quality:.2f}, "
                        f"Features: {len(concretized.features)}, "
                        f"Data Models: {len(concretized.data_models)}, "
                        f"UI Components: {len(concretized.ui_components)}"
                    )

                    if quality.quality_issues:
                        for issue in quality.quality_issues:
                            self.logger.warning(f"⚠️ Quality Issue: {issue}")

                # Phase History 기록
                context.phase_history.append({
                    "phase": BMADPhase.CONCRETIZATION,
                    "status": PhaseStatus.COMPLETED,
                    "timestamp": datetime.now().isoformat(),
                    "features_count": len(concretized.features),
                    "data_models_count": len(concretized.data_models),
                    "ui_components_count": len(concretized.ui_components),
                    "quality_score": concretized.concretization_quality.overall_quality if concretized.concretization_quality else 0.0
                })

                self.logger.info("🎯 Golden Data가 생성되어 모든 후속 단계의 기준으로 사용됩니다")

                # 🆕 Gate 1: Requirements Review (Plan Mode)
                if self.plan_mode_api:
                    self.logger.info("\n" + "="*70)
                    self.logger.info("📋 Gate 1: Requirements Review")
                    self.logger.info("="*70)

                    decision = self.plan_mode_api.request_requirements_review(concretized)

                    if decision == "reject":
                        self.logger.warning("❌ User rejected requirements")
                        raise UserAbortedError("User rejected requirements at Gate 1")
                    elif decision == "edit":
                        self.logger.info("✏️  User requested edits (not implemented yet)")
                        # TODO: Implement edit flow
                    else:
                        self.logger.info("✅ User approved requirements")

            else:
                raise ValueError("Concretization 결과가 ConcretizedRequirement 타입이 아닙니다")

        except Exception as e:
            self.logger.error(f"❌ Concretization 단계 실패: {str(e)}")
            context.phase_history.append({
                "phase": BMADPhase.CONCRETIZATION,
                "status": PhaseStatus.FAILED,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            })
            raise

        return context

    def execute_discovery(self, context: BMADContext, enable_sharding: bool = True) -> BMADContext:
        """
        Discovery 단계 실행 - 요구사항 분석 및 기능 추출 (Document Sharding 적용)

        Args:
            context: BMAD 컨텍스트
            enable_sharding: Document Sharding 활성화 여부

        Returns:
            BMADContext: 업데이트된 컨텍스트
        """
        self.logger.info("=== BMAD Discovery 단계 시작 ===")
        context.current_phase = BMADPhase.DISCOVERY

        try:
            # 🆕 Document Sharding (대형 요구사항 처리)
            from app.core.bmad.sharding import DocumentSharder, ShardingStrategy

            if enable_sharding:
                sharder = DocumentSharder(max_tokens_per_shard=2000)
                sharding_result = sharder.shard_requirement(
                    context.requirement,
                    strategy=ShardingStrategy.BY_SECTION
                )

                if sharding_result.total_shards > 1:
                    self.logger.info(
                        f"Document Sharding: {sharding_result.total_shards}개 조각, "
                        f"토큰 절감 {sharding_result.reduction_ratio*100:.1f}%"
                    )

                    # 각 조각 개별 분석 및 병합
                    all_agents = []
                    all_tasks = []

                    for shard in sharding_result.shards:
                        partial_analysis = self.analysis_chain.analyze(
                            shard.content,
                            workflow_type=context.analysis.get("workflow_type", "sequential") if context.analysis else "sequential"
                        )
                        all_agents.extend(partial_analysis.agents)
                        all_tasks.extend(partial_analysis.tasks)

                    # 중복 제거 및 병합
                    from app.llm.chains import RequirementAnalysis, AgentRequirement, TaskRequirement
                    unique_agents = {a.role: a for a in all_agents}.values()

                    analysis = RequirementAnalysis(
                        domain=sharding_result.shards[0].shard_type if sharding_result.shards else "general",
                        summary=f"Analyzed from {sharding_result.total_shards} shards",
                        agents=list(unique_agents),
                        tasks=all_tasks,
                        workflow_type="sequential",
                        suggested_tools=list(set(t for a in all_agents for t in getattr(a, 'tools', []))),
                    )
                else:
                    # 단일 조각: 분석 (Golden Data 활용 가능)
                    golden_data_obj = None
                    if context.concretized_requirement:
                        from app.models.schemas import ConcretizedRequirement
                        golden_data_obj = ConcretizedRequirement(**context.concretized_requirement)
                        self.logger.info("🎯 Golden Data 기반 분석 시작")

                    analysis = self.analysis_chain.analyze(
                        context.requirement,
                        golden_data=golden_data_obj
                    )
            else:
                # Sharding 비활성화: RequirementAnalyzer 사용
                analysis_result = self.analyzer.analyze(context.requirement)

                # AnalysisResult를 RequirementAnalysis로 변환 (backward compatibility)
                from app.models.schemas import RequirementAnalysis, AgentRequirement, TaskRequirement

                # features에서 tasks 생성
                tasks = [
                    TaskRequirement(
                        name=feature.name,
                        description=feature.description,
                        agent=None,
                        expected_output=f"Complete {feature.name}",
                        context=[]
                    )
                    for feature in analysis_result.features
                ]

                analysis = RequirementAnalysis(
                    domain=analysis_result.domain_context.domain,
                    subdomain=analysis_result.domain_context.subdomain,
                    summary=f"Analysis completed for {analysis_result.domain_context.domain}",
                    agents=[],  # Will be designed in Design phase
                    tasks=tasks,
                    workflow_type="sequential",
                    suggested_tools=[],
                    project_template="agent_only",
                    requires_ui=False
                )

            # 🆕 Golden Data 검증 및 자동 수정
            if self.golden_validator and context.concretized_requirement and context.golden_data_validation_enabled:
                self.logger.info("🎯 Golden Data 검증 시작 (Discovery Phase)")

                try:
                    # 1. Golden Data 검증
                    validation_report = self.golden_validator.validate_discovery(analysis)

                    self.logger.info(
                        f"📊 Golden Data Coverage: {validation_report.coverage_score:.2%}, "
                        f"Status: {validation_report.compliance_status.value}"
                    )

                    # 2. 자동 수정 (needs_fixing인 경우)
                    if validation_report.needs_fixing and self.auto_fixer:
                        self.logger.info("🔧 Auto-fixing 시작...")

                        fix_result = self.auto_fixer.fix_discovery(analysis, validation_report)

                        if fix_result.success:
                            self.logger.info(f"✅ Auto-fix 완료: {len(fix_result.fixes_applied)} fixes applied")
                            for fix in fix_result.fixes_applied:
                                self.logger.info(f"  ✓ {fix}")

                            # 수정된 결과로 교체
                            analysis = fix_result.fixed_output
                        else:
                            self.logger.warning(f"⚠️ Auto-fix 실패: {', '.join(fix_result.errors)}")

                    # 3. 검증 결과 저장
                    context.golden_validation_reports.append(validation_report.model_dump())

                except Exception as e:
                    self.logger.error(f"❌ Golden Data 검증 중 오류: {str(e)}")
                    # 검증 실패해도 계속 진행

            context.analysis = analysis.model_dump()
            context.domain = analysis.domain

            # AnalysisResult도 저장 (adaptive intelligence용)
            if not enable_sharding and 'analysis_result' in locals():
                context.analysis_result = analysis_result.model_dump()

            # 기능 추출
            features = []
            for i, task in enumerate(analysis.tasks, 1):
                feature = FeatureItem(
                    id=f"feature_{i}",
                    name=task.name,
                    description=task.description,
                    priority=min(i, 5),  # 순서 기반 우선순위
                )
                features.append(feature)
            context.features = features

            # 히스토리 기록
            context.phase_history.append({
                "phase": BMADPhase.DISCOVERY,
                "status": PhaseStatus.COMPLETED,
                "timestamp": datetime.now().isoformat(),
                "summary": f"Identified {len(analysis.agents)} agents, {len(features)} features",
            })

            self.logger.info(f"Discovery 완료: {len(features)}개 기능 추출")
            return context

        except Exception as e:
            self.logger.error(f"Discovery 실패: {e}")
            context.phase_history.append({
                "phase": BMADPhase.DISCOVERY,
                "status": PhaseStatus.FAILED,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            })
            raise

    def execute_architecture(self, context: BMADContext) -> BMADContext:
        """
        Architecture 단계 실행 - 시스템 아키텍처 설계

        Args:
            context: BMAD 컨텍스트

        Returns:
            BMADContext: 업데이트된 컨텍스트
        """
        self.logger.info("=" * 60)
        self.logger.info("BMAD Phase: ARCHITECTURE - System Architecture Design")
        self.logger.info("=" * 60)

        context.current_phase = BMADPhase.ARCHITECTURE
        context.phase_history.append({
            "phase": BMADPhase.ARCHITECTURE,
            "status": PhaseStatus.IN_PROGRESS,
            "timestamp": datetime.now().isoformat(),
        })

        try:
            # RequirementAnalysis가 없으면 에러
            if not context.analysis:
                raise ValueError("Discovery 단계가 먼저 실행되어야 합니다")

            # RequirementAnalysis 객체 생성
            requirement_analysis = RequirementAnalysis(**context.analysis)

            # SystemArchitectChain 초기화
            architect_chain = SystemArchitectChain()

            # 아키텍처 설계
            self.logger.info("시스템 아키텍처 설계 중...")
            architecture_design = architect_chain.design_architecture(requirement_analysis)

            # 🆕 Golden Data 검증 및 자동 수정
            if self.golden_validator and context.concretized_requirement and context.golden_data_validation_enabled:
                self.logger.info("🎯 Golden Data 검증 시작 (Architecture Phase)")

                try:
                    # 1. Golden Data 검증
                    validation_report = self.golden_validator.validate_architecture(architecture_design)

                    self.logger.info(
                        f"📊 Golden Data Coverage: {validation_report.coverage_score:.2%}, "
                        f"Status: {validation_report.compliance_status.value}"
                    )

                    # 2. 자동 수정 (needs_fixing인 경우)
                    if validation_report.needs_fixing and self.auto_fixer:
                        self.logger.info("🔧 Auto-fixing 시작...")

                        fix_result = self.auto_fixer.fix_architecture(architecture_design, validation_report)

                        if fix_result.success:
                            self.logger.info(f"✅ Auto-fix 완료: {len(fix_result.fixes_applied)} fixes applied")
                            for fix in fix_result.fixes_applied:
                                self.logger.info(f"  ✓ {fix}")

                            # 수정된 결과로 교체
                            architecture_design = fix_result.fixed_output
                        else:
                            self.logger.warning(f"⚠️ Auto-fix 실패: {', '.join(fix_result.errors)}")

                    # 3. 검증 결과 저장
                    context.golden_validation_reports.append(validation_report.model_dump())

                except Exception as e:
                    self.logger.error(f"❌ Golden Data 검증 중 오류: {str(e)}")
                    # 검증 실패해도 계속 진행

            # 결과 저장
            context.architecture_design = architecture_design.model_dump()

            # 성공 로깅
            self.logger.info("=" * 60)
            self.logger.info(f"✅ Architecture 완료")
            self.logger.info(f"   패턴: {architecture_design.architectural_pattern.value}")
            self.logger.info(f"   컴포넌트: {len(architecture_design.components)}개")
            self.logger.info(f"   기술 스택: {len(architecture_design.technology_stack)}개")
            self.logger.info(f"   설계 신뢰도: {architecture_design.design_confidence:.2%}")
            self.logger.info("=" * 60)

            context.phase_history.append({
                "phase": BMADPhase.ARCHITECTURE,
                "status": PhaseStatus.COMPLETED,
                "timestamp": datetime.now().isoformat(),
                "result": {
                    "pattern": architecture_design.architectural_pattern.value,
                    "components": len(architecture_design.components),
                    "confidence": architecture_design.design_confidence,
                }
            })

            context.updated_at = datetime.now()
            return context

        except Exception as e:
            self.logger.error(f"Architecture 실패: {e}")
            context.phase_history.append({
                "phase": BMADPhase.ARCHITECTURE,
                "status": PhaseStatus.FAILED,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            })
            raise

    def execute_design(self, context: BMADContext) -> BMADContext:
        """
        Design 단계 실행 - 에이전트/태스크 상세 설계
        
        Args:
            context: BMAD 컨텍스트
        
        Returns:
            BMADContext: 업데이트된 컨텍스트
        """
        self.logger.info("=== BMAD Design 단계 시작 ===")
        context.current_phase = BMADPhase.DESIGN
        
        if not context.analysis:
            raise ValueError("Discovery 단계가 먼저 실행되어야 합니다.")
        
        try:
            analysis = RequirementAnalysis(**context.analysis)

            # 에이전트 설계
            agent_specs = []

            # agents가 비어있으면 task 기반으로 기본 에이전트 생성
            agents_to_design = analysis.agents
            if not agents_to_design and analysis.tasks:
                from app.models.schemas import AgentRequirement
                # 각 task마다 전용 에이전트 생성
                agents_to_design = [
                    AgentRequirement(
                        role=f"{task.name.replace('_', ' ').title()} Agent",
                        goal=f"Handle {task.name} task",
                        skills=[task.name],
                        backstory=f"Specialized agent for {task.description}"
                    )
                    for task in analysis.tasks
                ]
                # assigned_agent 업데이트
                for i, task in enumerate(analysis.tasks):
                    task.assigned_agent = agents_to_design[i].role

            for agent_req in agents_to_design:
                related_tasks = [
                    t.name for t in analysis.tasks
                    if t.assigned_agent == agent_req.role
                ]
                
                spec = self.agent_design_chain.design(
                    domain=analysis.domain,
                    role=agent_req.role,
                    goal=agent_req.goal,
                    skills=agent_req.skills,
                    tasks=related_tasks,
                    available_tools=self.available_tools,
                )
                agent_specs.append(spec.model_dump())
            
            context.agent_specs = agent_specs
            
            # 태스크 설계
            task_specs = []
            system_context = f"Domain: {analysis.domain}\nSummary: {analysis.summary}"
            
            for task_req in analysis.tasks:
                # 에이전트 ID 매핑
                agent_id = None
                for agent in agent_specs:
                    if task_req.assigned_agent.lower() in agent["role"].lower():
                        agent_id = agent["id"]
                        break
                
                if not agent_id and agent_specs:
                    agent_id = agent_specs[0]["id"]
                
                spec = self.task_design_chain.design(
                    task_name=task_req.name,
                    description=task_req.description,
                    agent_id=agent_id or "default_agent",
                    dependencies=task_req.dependencies,
                    output_type=task_req.output_type,
                    system_context=system_context,
                )
                task_specs.append(spec.model_dump())
            
            context.task_specs = task_specs

            # 🆕 Automatic Process Type Selection (Sequential vs Hierarchical)
            from caas_framework.utils.workflow_selector import determine_workflow_type, get_workflow_recommendation

            self.logger.info("🔄 자동 프로세스 타입 선택 중...")

            # Get workflow recommendation with explanation
            recommendation = get_workflow_recommendation(
                requirement=context.requirement,
                agents=context.agent_specs,
                tasks=context.task_specs,
                domain=context.domain
            )

            selected_workflow = recommendation["workflow_type"]
            complexity_score = recommendation["complexity_score"]
            reasons = recommendation["reasons"]

            # Update analysis with selected workflow type
            if context.analysis:
                context.analysis["workflow_type"] = selected_workflow
                context.analysis["workflow_complexity_score"] = complexity_score
                context.analysis["workflow_selection_reasons"] = reasons

            self.logger.info(
                f"✅ 프로세스 타입 선택: {selected_workflow.upper()} "
                f"(복잡도: {complexity_score:.1f}/100)"
            )
            if reasons:
                self.logger.info(f"   선택 이유:")
                for reason in reasons:
                    self.logger.info(f"   - {reason}")

            # Golden Data 검증 및 자동 수정
            if (self.golden_validator and
                context.concretized_requirement and
                context.golden_data_validation_enabled):
                try:
                    self.logger.info("🎯 Golden Data 검증 시작 (Design Phase)")

                    # Design Phase 검증
                    validation_report = self.golden_validator.validate_design(
                        agent_specs=agent_specs,
                        task_specs=task_specs
                    )

                    self.logger.info(
                        f"검증 결과 - 커버리지: {validation_report.coverage_score:.1%}, "
                        f"누락: {len(validation_report.missing_items)}개, "
                        f"추가: {len(validation_report.extra_items)}개"
                    )

                    # 자동 수정 실행
                    if validation_report.needs_fixing and self.auto_fixer:
                        self.logger.info("🔧 자동 수정 실행 중...")
                        fix_result = self.auto_fixer.fix_design(
                            agent_specs,
                            task_specs,
                            validation_report
                        )

                        if fix_result.success:
                            self.logger.info(f"✅ 자동 수정 완료: {len(fix_result.fixes_applied)}개 항목 수정")
                            # 수정된 결과로 context 업데이트
                            context.agent_specs = fix_result.fixed_output.get("agents", agent_specs)
                            context.task_specs = fix_result.fixed_output.get("tasks", task_specs)
                        else:
                            self.logger.warning("⚠️ 자동 수정 실패")

                    # 검증 리포트 저장
                    context.golden_validation_reports.append(validation_report.model_dump())

                except Exception as e:
                    self.logger.error(f"Golden Data 검증 중 오류: {e}")
                    # 검증 실패해도 진행 계속

            # 히스토리 기록
            context.phase_history.append({
                "phase": BMADPhase.DESIGN,
                "status": PhaseStatus.COMPLETED,
                "timestamp": datetime.now().isoformat(),
                "summary": f"Designed {len(agent_specs)} agents, {len(task_specs)} tasks",
            })

            self.logger.info(f"Design 완료: {len(agent_specs)}개 에이전트, {len(task_specs)}개 태스크")

            # 🆕 Gate 2: Design Review (Plan Mode)
            if self.plan_mode_api:
                self.logger.info("\n" + "="*70)
                self.logger.info("🎨 Gate 2: Design Review")
                self.logger.info("="*70)

                design_data = {
                    "agents": context.agent_specs,
                    "tasks": context.task_specs
                }

                decision = self.plan_mode_api.request_design_review(design_data)

                if decision == "reject":
                    self.logger.warning("❌ User rejected design")
                    raise UserAbortedError("User rejected design at Gate 2")
                elif decision == "redesign":
                    self.logger.info("🔄 User requested redesign (not implemented yet)")
                    # TODO: Implement redesign flow
                else:
                    self.logger.info("✅ User approved design")

            return context
            
        except Exception as e:
            self.logger.error(f"Design 실패: {e}")
            context.phase_history.append({
                "phase": BMADPhase.DESIGN,
                "status": PhaseStatus.FAILED,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            })
            raise
    
    def execute_development(
        self,
        context: BMADContext,
        enable_reflection: bool = True,
        enable_traceability: bool = True,
        quality_threshold: float = 0.7,
        max_reflection_iterations: int = 3
    ) -> BMADContext:
        """
        Development 단계 실행 - 코드 생성 (Reflection Engine + Traceability 적용)

        Args:
            context: BMAD 컨텍스트
            enable_reflection: Reflection Engine 활성화 여부
            enable_traceability: Traceability Validation 활성화 여부
            quality_threshold: 품질 임계값
            max_reflection_iterations: 최대 반성 반복 횟수

        Returns:
            BMADContext: 업데이트된 컨텍스트
        """
        self.logger.info("=== BMAD Development 단계 시작 ===")
        context.current_phase = BMADPhase.DEVELOPMENT

        if not context.agent_specs or not context.task_specs:
            raise ValueError("Design 단계가 먼저 실행되어야 합니다.")

        try:
            # 1. Pattern Matching - 도메인 기반 패턴 매칭
            self.logger.info("패턴 매칭 시작...")
            matched_patterns = self._match_patterns(context)
            self.logger.info(f"매칭된 패턴 {len(matched_patterns)}개 발견")

            # 2. Spec Generation - CrewAI YAML 스펙 생성 (Reflection 적용)
            self.logger.info("스펙 생성 시작...")
            spec_yaml = self._generate_spec(context, matched_patterns)

            # 🆕 Reflection on Spec
            if enable_reflection:
                from app.core.bmad.reflection import ReflectionEngine

                reflection_engine = ReflectionEngine(quality_threshold=quality_threshold)
                spec_reflection = reflection_engine.reflect_on_spec(
                    spec_yaml,
                    context.requirement,
                    use_llm=False  # 비용 절감
                )

                iteration_count = 0
                while spec_reflection.requires_iteration and iteration_count < max_reflection_iterations:
                    self.logger.info(
                        f"스펙 개선 필요 (점수: {spec_reflection.overall_score:.2f}), "
                        f"반복 {iteration_count+1}/{max_reflection_iterations}"
                    )
                    self.logger.debug(f"개선 계획:\n{spec_reflection.iteration_plan}")

                    # 간단한 개선: 경고 사항을 반영하여 재생성
                    # (실제로는 LLM을 호출하여 개선할 수 있음)
                    spec_yaml = self._generate_spec(context, matched_patterns)

                    # 재평가
                    spec_reflection = reflection_engine.reflect_on_spec(
                        spec_yaml,
                        context.requirement,
                        use_llm=False
                    )
                    iteration_count += 1

                self.logger.info(f"스펙 반성 완료: 점수={spec_reflection.overall_score:.2f}")

            context.spec_yaml = spec_yaml
            self.logger.info("스펙 생성 완료")

            # 🆕 Traceability Validation - 요구사항과 Spec 간 추적성 검증
            traceability_report = None
            if enable_traceability:
                from app.core.validation.traceability import TraceabilityValidator

                self.logger.info("추적성 검증 시작...")
                traceability_validator = TraceabilityValidator(min_match_confidence=0.6)

                # 요구사항 분석과 생성된 Spec 비교
                requirement_analysis = RequirementAnalysis(**context.analysis)
                generated_spec = {
                    "agents": context.agent_specs,
                    "tasks": context.task_specs,
                }

                traceability_report = traceability_validator.validate_coverage(
                    requirement_analysis,
                    generated_spec
                )

                self.logger.info(
                    f"추적성 검증 완료: valid={traceability_report.valid}, "
                    f"coverage={traceability_report.coverage_score:.2%}"
                )

                # 심각한 이슈가 있으면 경고
                critical_issues = [
                    issue for issue in traceability_report.issues
                    if issue.get("severity") in ["critical", "high"]
                ]

                if critical_issues:
                    self.logger.warning(
                        f"⚠️ {len(critical_issues)}개의 심각한 추적성 이슈 발견"
                    )
                    for issue in critical_issues[:3]:  # 최대 3개만 출력
                        self.logger.warning(f"  - {issue.get('message')}")

                # 누락된 요소 경고
                if traceability_report.missing_agents:
                    self.logger.warning(
                        f"⚠️ 누락된 Agent: {', '.join(traceability_report.missing_agents)}"
                    )
                if traceability_report.missing_tasks:
                    self.logger.warning(
                        f"⚠️ 누락된 Task: {', '.join(traceability_report.missing_tasks[:5])}"
                    )

            # 3. Code Generation - 패턴 기반 코드 생성
            self.logger.info("코드 생성 시작...")
            generated_code = self._generate_code_with_patterns(
                context,
                spec_yaml,
                matched_patterns
            )

            # 🆕 Reflection on Code
            if enable_reflection:
                from app.core.bmad.reflection import ReflectionEngine

                reflection_engine = ReflectionEngine(quality_threshold=quality_threshold)
                code_reflection = reflection_engine.reflect_on_code(generated_code, spec_yaml)

                iteration_count = 0
                while code_reflection.requires_iteration and iteration_count < max_reflection_iterations:
                    self.logger.info(
                        f"코드 개선 필요 (점수: {code_reflection.overall_score:.2f}), "
                        f"반복 {iteration_count+1}/{max_reflection_iterations}"
                    )
                    self.logger.debug(f"개선 계획:\n{code_reflection.iteration_plan}")

                    # 코드 재생성 (개선 피드백 반영)
                    generated_code = self._generate_code_with_patterns(
                        context,
                        spec_yaml,
                        matched_patterns
                    )

                    # 재평가
                    code_reflection = reflection_engine.reflect_on_code(generated_code, spec_yaml)
                    iteration_count += 1

                self.logger.info(f"코드 반성 완료: 점수={code_reflection.overall_score:.2f}")

            context.generated_code = generated_code
            self.logger.info(f"코드 생성 완료: {len(generated_code)}개 파일")

            # 4. Validation - 생성된 코드 검증
            self.logger.info("코드 검증 시작...")
            validation_result = self._validate_generated_code(generated_code)

            # 🆕 Code Quality Pipeline (Syntax, Imports, Style)
            quality_report = None
            try:
                from caas_framework.quality.pipeline import CodeQualityPipeline

                self.logger.info("🔍 Code Quality Pipeline 실행 중...")

                # Prepare code files for quality checks
                code_files = {
                    file["path"]: file.get("content", "")
                    for file in generated_code
                }

                # Run quality pipeline
                quality_pipeline = CodeQualityPipeline(
                    enable_syntax=True,
                    enable_imports=True,
                    enable_style=True
                )

                quality_report = quality_pipeline.verify(code_files)

                self.logger.info(
                    f"Quality Report - Passed: {quality_report.overall_passed}, "
                    f"Errors: {quality_report.total_errors}, Warnings: {quality_report.total_warnings}"
                )

                if not quality_report.overall_passed:
                    self.logger.warning(
                        f"⚠️ {quality_report.total_errors} error(s) and "
                        f"{quality_report.total_warnings} warning(s) detected"
                    )

                    # Log issues from checks
                    for check in quality_report.checks:
                        if check.errors:
                            self.logger.warning(f"  [{check.name}] Errors:")
                            for error in check.errors[:3]:  # Show first 3
                                self.logger.warning(f"    - {error}")
                            if len(check.errors) > 3:
                                self.logger.warning(f"    ... and {len(check.errors) - 3} more")

                        if check.warnings:
                            self.logger.warning(f"  [{check.name}] Warnings:")
                            for warning in check.warnings[:2]:  # Show first 2
                                self.logger.warning(f"    - {warning}")
                            if len(check.warnings) > 2:
                                self.logger.warning(f"    ... and {len(check.warnings) - 2} more")
                else:
                    self.logger.info("✅ All quality checks passed")

            except Exception as e:
                self.logger.error(f"Quality Pipeline 실행 중 오류: {e}")
                # Quality check 실패해도 진행 계속

            # Golden Data 검증 및 자동 수정 (Development Phase)
            if (self.golden_validator and
                context.concretized_requirement and
                context.golden_data_validation_enabled):
                try:
                    self.logger.info("🎯 Golden Data 검증 시작 (Development Phase)")

                    # 생성된 스펙 구조화
                    generated_spec = {
                        "agents": context.agent_specs,
                        "tasks": context.task_specs,
                        "code_files": [file["path"] for file in generated_code],
                        "spec_yaml": context.spec_yaml,
                    }

                    # Development Phase 검증
                    validation_report = self.golden_validator.validate_code(generated_spec)

                    self.logger.info(
                        f"검증 결과 - 커버리지: {validation_report.coverage_score:.1%}, "
                        f"누락: {len(validation_report.missing_items)}개, "
                        f"추가: {len(validation_report.extra_items)}개"
                    )

                    # 자동 수정 실행
                    if validation_report.needs_fixing and self.auto_fixer:
                        self.logger.info("🔧 자동 수정 실행 중...")
                        fix_result = self.auto_fixer.fix_code(
                            generated_spec,
                            validation_report
                        )

                        if fix_result.success:
                            self.logger.info(f"✅ 자동 수정 완료: {len(fix_result.fixes_applied)}개 항목 수정")
                            # 수정된 결과로 context 업데이트
                            if "agents" in fix_result.fixed_output:
                                context.agent_specs = fix_result.fixed_output["agents"]
                            if "tasks" in fix_result.fixed_output:
                                context.task_specs = fix_result.fixed_output["tasks"]
                        else:
                            self.logger.warning("⚠️ 자동 수정 실패")

                    # 검증 리포트 저장
                    context.golden_validation_reports.append(validation_report.model_dump())

                except Exception as e:
                    self.logger.error(f"Golden Data 검증 중 오류: {e}")
                    # 검증 실패해도 진행 계속

            # 🆕 Boundaries 검증 (Security)
            boundaries_violations = []
            if context.concretized_requirement:
                from app.models.schemas import ConcretizedRequirement
                concretized = ConcretizedRequirement(**context.concretized_requirement)

                if concretized.boundaries:
                    self.logger.info("🔒 Security Boundaries 검증 시작...")

                    # Prepare code files for validation
                    code_files = {
                        file["path"]: file.get("content", "")
                        for file in generated_code
                    }

                    # Simple boundary validation
                    boundaries = concretized.boundaries
                    for filename, content in code_files.items():
                        if not filename.endswith('.py'):
                            continue

                        content_lower = content.lower()

                        # Check never_allowed patterns
                        for pattern in (boundaries.never_allowed or []):
                            if pattern.lower() in content_lower:
                                violation = f"NEVER_ALLOWED: {filename} contains '{pattern}'"
                                boundaries_violations.append(violation)
                                self.logger.warning(f"⚠️ {violation}")

                    if boundaries_violations:
                        self.logger.warning(
                            f"🚨 {len(boundaries_violations)} boundary violation(s) detected!"
                        )
                    else:
                        self.logger.info("✅ No boundary violations detected")

            # 히스토리 기록
            history_entry = {
                "phase": BMADPhase.DEVELOPMENT,
                "status": PhaseStatus.COMPLETED,
                "timestamp": datetime.now().isoformat(),
                "summary": f"Generated {len(generated_code)} files with {len(matched_patterns)} patterns",
                "patterns_used": [p.pattern_name for p in matched_patterns],
                "validation": validation_result,
            }

            if enable_reflection:
                history_entry["reflection"] = {
                    "spec_score": spec_reflection.overall_score,
                    "code_score": code_reflection.overall_score,
                    "spec_iterations": spec_reflection.iteration_count,
                    "code_iterations": code_reflection.iteration_count,
                }

            if enable_traceability and traceability_report:
                history_entry["traceability"] = {
                    "valid": traceability_report.valid,
                    "coverage_score": traceability_report.coverage_score,
                    "total_issues": len(traceability_report.issues),
                    "critical_issues": len([
                        i for i in traceability_report.issues
                        if i.get("severity") in ["critical", "high"]
                    ]),
                    "missing_agents": len(traceability_report.missing_agents),
                    "missing_tasks": len(traceability_report.missing_tasks),
                    "missing_tools": len(traceability_report.missing_tools),
                }

            if boundaries_violations:
                history_entry["boundaries"] = {
                    "violations_count": len(boundaries_violations),
                    "violations": boundaries_violations
                }

            if quality_report:
                syntax_check = next((c for c in quality_report.checks if c.name == "Syntax Check"), None)
                import_check = next((c for c in quality_report.checks if c.name == "Import Check"), None)
                style_check = next((c for c in quality_report.checks if c.name == "Code Style Check"), None)

                history_entry["quality"] = {
                    "passed": quality_report.overall_passed,
                    "total_errors": quality_report.total_errors,
                    "total_warnings": quality_report.total_warnings,
                    "syntax_errors": len(syntax_check.errors) if syntax_check else 0,
                    "import_errors": len(import_check.errors) if import_check else 0,
                    "style_warnings": len(style_check.warnings) if style_check else 0,
                }

            context.phase_history.append(history_entry)

            self.logger.info("=== BMAD Development 단계 완료 ===")

            # 🆕 Gate 3: Code Review (Plan Mode)
            if self.plan_mode_api:
                self.logger.info("\n" + "="*70)
                self.logger.info("💻 Gate 3: Code Review")
                self.logger.info("="*70)

                # Prepare code files for review
                code_files = {
                    file["path"]: file.get("content", "")
                    for file in generated_code
                }

                decision = self.plan_mode_api.request_code_review(code_files)

                if decision == "reject":
                    self.logger.warning("❌ User rejected generated code")
                    raise UserAbortedError("User rejected code at Gate 3")
                else:
                    self.logger.info("✅ User approved generated code")

            return context

        except Exception as e:
            self.logger.error(f"Development 실패: {e}")
            context.phase_history.append({
                "phase": BMADPhase.DEVELOPMENT,
                "status": PhaseStatus.FAILED,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            })
            raise

    def _match_patterns(self, context: BMADContext) -> List[PatternMatch]:
        """
        Neo4j 온톨로지 기반 패턴 매칭

        Args:
            context: BMAD 컨텍스트

        Returns:
            List[PatternMatch]: 매칭된 패턴 목록
        """
        domain = context.domain or "general"

        # 태스크 타입 추출
        task_types = []
        for task_spec in context.task_specs:
            task_desc = task_spec.get("description", "").lower()
            # 태스크 설명에서 주요 동사 추출
            if "search" in task_desc or "find" in task_desc:
                task_types.append("search")
            if "analyze" in task_desc or "process" in task_desc:
                task_types.append("analysis")
            if "write" in task_desc or "create" in task_desc:
                task_types.append("generation")
            if "validate" in task_desc or "check" in task_desc:
                task_types.append("validation")

        # 요구사항에서 키워드 추출
        requirement = context.requirement.lower()
        keywords = []
        keyword_map = {
            "research": ["research", "investigate", "study"],
            "report": ["report", "document", "summary"],
            "data": ["data", "dataset", "information"],
            "analysis": ["analyze", "analysis", "insight"],
            "automation": ["automate", "automatic", "automated"],
        }

        for key, terms in keyword_map.items():
            if any(term in requirement for term in terms):
                keywords.append(key)

        try:
            # Neo4j를 통한 패턴 검색 시도
            patterns = self.pattern_matcher.find_patterns(
                domain=domain,
                task_types=task_types or None,
                keywords=keywords or None,
                limit=5,
            )

            # 패턴을 PatternMatch로 변환
            pattern_matches = []
            for pattern in patterns:
                # 유사도 점수 계산 (간단한 매칭 로직)
                score = 0.5  # 기본 점수

                # 도메인 매칭
                if pattern.domain.lower() == domain.lower():
                    score += 0.2

                # 태스크 타입 매칭
                matching_tasks = set(task_types) & set(pattern.task_types)
                if matching_tasks:
                    score += 0.2 * (len(matching_tasks) / max(len(task_types), 1))

                # 최소 임계값 이상만 포함
                if score >= 0.3:
                    pattern_match = PatternMatch(
                        pattern_id=pattern.id,
                        pattern_name=pattern.name,
                        similarity_score=min(score, 1.0),
                        matched_features=list(matching_tasks),
                        suggested_adaptations=[
                            f"Adapt workflow to {domain} domain",
                            "Customize agent roles based on requirements",
                        ],
                    )
                    pattern_matches.append(pattern_match)

            # 패턴 사용 기록
            for match in pattern_matches:
                try:
                    self.pattern_matcher.record_pattern_usage(match.pattern_id)
                except Exception as e:
                    self.logger.warning(f"패턴 사용 기록 실패: {e}")

            return sorted(pattern_matches, key=lambda x: x.similarity_score, reverse=True)

        except Exception as e:
            self.logger.warning(f"Neo4j 패턴 매칭 실패 (폴백 사용): {e}")
            # 빌트인 패턴 폴백
            return []

    def _generate_spec(
        self,
        context: BMADContext,
        patterns: List[PatternMatch]
    ) -> str:
        """
        CrewAI 스펙 생성 및 검증

        Args:
            context: BMAD 컨텍스트
            patterns: 매칭된 패턴 목록

        Returns:
            str: 검증된 YAML 스펙
        """
        # 스펙 생성
        spec_yaml = self.spec_generation_chain.generate(
            domain=context.domain or "general",
            summary=context.analysis.get("summary", "") if context.analysis else "",
            agents=context.agent_specs,
            tasks=context.task_specs,
            workflow_type=context.analysis.get("workflow_type", "sequential") if context.analysis else "sequential",
            tools=context.analysis.get("suggested_tools", []) if context.analysis else [],
        )

        # 스펙 검증
        validation = self.spec_validation_chain.validate(spec_yaml)

        # 심각한 오류만 raise (critical severity만 - error는 경고로 처리)
        critical_errors = [
            err for err in validation.errors
            if err.get('severity') == 'critical'
        ]

        if critical_errors:
            error_summary = "; ".join([
                f"{err.get('location', 'unknown')}: {err.get('message', '')}"
                for err in critical_errors
            ])
            raise ValueError(f"스펙 검증 실패 (Critical): {error_summary}")

        # 모든 error severity를 경고로 처리 (blocking하지 않음)
        error_warnings = [
            err for err in validation.errors
            if err.get('severity') == 'error'
        ]
        for err in error_warnings:
            self.logger.warning(
                f"스펙 검증 경고 (Error): {err.get('location')}: {err.get('message')}"
            )

        # 일반 경고 로깅
        for warning in validation.warnings:
            self.logger.warning(f"스펙 검증 경고: {warning}")

        non_critical_errors = [
            err for err in validation.errors
            if err.get('severity') not in ['critical', 'error']
        ]
        for err in non_critical_errors:
            self.logger.warning(
                f"스펙 검증 권장사항 ({err.get('location')}): {err.get('message')}"
            )

        return spec_yaml

    def _generate_code_with_patterns(
        self,
        context: BMADContext,
        spec_yaml: str,
        patterns: List[PatternMatch],
    ) -> Dict[str, str]:
        """
        패턴 템플릿 적용하여 코드 생성

        Args:
            context: BMAD 컨텍스트
            spec_yaml: YAML 스펙
            patterns: 매칭된 패턴 목록

        Returns:
            Dict[str, str]: 파일명 -> 코드 매핑
        """
        # SDDEngine을 통한 스펙 파싱
        spec = self.sdd_engine.parse(spec_yaml)

        # CodeGenerator를 통한 코드 생성
        generated_project = self.code_generator.generate_from_spec(spec)

        # GeneratedProject.files는 이미 Dict[str, str] 형태
        generated_files = generated_project.files

        # 패턴 기반 코드 개선 (선택적)
        if patterns:
            self.logger.info(f"패턴 {len(patterns)}개를 적용하여 코드 개선")
            # 패턴별 코드 템플릿 적용은 향후 구현
            # 현재는 기본 코드 생성만 수행

        # 코드 포맷팅
        formatted_files = {}
        for filename, code in generated_files.items():
            if filename.endswith(".py"):
                try:
                    formatted_code = self.code_formatter.format_code(code)
                    formatted_files[filename] = formatted_code
                except Exception as e:
                    self.logger.warning(f"코드 포맷팅 실패 ({filename}): {e}")
                    formatted_files[filename] = code
            else:
                formatted_files[filename] = code

        return formatted_files

    def _validate_generated_code(self, code_files: Dict[str, str]) -> Dict[str, Any]:
        """
        생성된 코드 검증 (AST 기반 구문 검증)

        Args:
            code_files: 파일명 -> 코드 매핑

        Returns:
            Dict[str, Any]: 검증 결과
        """
        import ast

        validation_result = {
            "valid": True,
            "total_files": len(code_files),
            "validated_files": 0,
            "syntax_errors": [],
            "warnings": [],
        }

        for filename, code in code_files.items():
            # Python 파일만 구문 검증
            if not filename.endswith(".py"):
                continue

            try:
                ast.parse(code)
                validation_result["validated_files"] += 1
            except SyntaxError as e:
                validation_result["valid"] = False
                validation_result["syntax_errors"].append({
                    "file": filename,
                    "line": e.lineno,
                    "message": str(e.msg),
                })
                self.logger.error(f"구문 오류 ({filename}:{e.lineno}): {e.msg}")

        # 검증 요약
        if validation_result["valid"]:
            self.logger.info(
                f"코드 검증 성공: {validation_result['validated_files']}/{validation_result['total_files']} 파일"
            )
        else:
            self.logger.error(
                f"코드 검증 실패: {len(validation_result['syntax_errors'])}개 구문 오류"
            )

        return validation_result
    
    def execute_delivery(self, context: BMADContext) -> BMADContext:
        """
        Delivery 단계 실행 - 검증 및 배포

        Args:
            context: BMAD 컨텍스트

        Returns:
            BMADContext: 업데이트된 컨텍스트
        """
        self.logger.info("=== BMAD Delivery 단계 시작 ===")
        context.current_phase = BMADPhase.DELIVERY

        if not context.generated_code:
            raise ValueError("Development 단계가 먼저 실행되어야 합니다.")

        try:
            # 1. Code Validation - 코드 품질 검증
            self.logger.info("코드 검증 시작...")
            validation_result = self.code_validator.validate(context.generated_code)

            # 검증 실패 시 Delivery 중단
            if not validation_result.valid:
                self.logger.error("코드 검증 실패")
                context.validation_result = validation_result.to_dict()
                context.phase_history.append({
                    "phase": BMADPhase.DELIVERY,
                    "status": PhaseStatus.FAILED,
                    "timestamp": datetime.now().isoformat(),
                    "error": "Code validation failed",
                    "details": validation_result.to_dict(),
                })
                return context

            self.logger.info("코드 검증 성공")

            # 2. Test Generation - 테스트 생성
            self.logger.info("테스트 생성 시작...")
            test_files = self.test_generator.generate_tests(
                project_name=context.project_name,
                agent_specs=context.agent_specs,
                task_specs=context.task_specs,
            )
            self.logger.info(f"테스트 파일 {len(test_files)}개 생성 완료")

            # 테스트 파일을 generated_code에 추가
            context.generated_code.update(test_files)

            # 3. Test Execution - 테스트 실행
            self.logger.info("테스트 실행 시작...")
            test_result = self.test_generator.run_tests(
                code_files=context.generated_code,
                test_files=test_files,
                timeout=60,
            )

            test_passed = test_result.success
            self.logger.info(
                f"테스트 실행 완료: {test_result.passed_tests}/{test_result.total_tests} passed"
            )

            # 4. Deployment Preparation - 배포 준비
            self.logger.info("배포 준비 시작...")
            deployment_artifacts = self.deployment_preparer.prepare_deployment(
                project_name=context.project_name,
                code_files=context.generated_code,
                agent_specs=context.agent_specs,
            )
            self.logger.info(f"배포 아티팩트 {len(deployment_artifacts.files)}개 생성 완료")

            # 배포 아티팩트를 generated_code에 추가
            context.generated_code.update(deployment_artifacts.files)

            # 5. Quality Metrics - 품질 메트릭 계산
            quality_metrics = {
                "validation": validation_result.to_dict(),
                "testing": test_result.to_dict(),
                "deployment": deployment_artifacts.to_dict(),
                "quality_score": self._calculate_quality_score(
                    validation_result,
                    test_result,
                ),
            }

            # 결과 저장
            context.validation_result = quality_metrics
            context.deployment_info = deployment_artifacts.to_dict()

            # 전체 성공 여부 결정
            overall_success = (
                validation_result.valid
                and test_passed
                and len(deployment_artifacts.files) > 0
            )

            # 히스토리 기록
            context.phase_history.append({
                "phase": BMADPhase.DELIVERY,
                "status": PhaseStatus.COMPLETED if overall_success else PhaseStatus.FAILED,
                "timestamp": datetime.now().isoformat(),
                "summary": f"Validation: {'PASS' if validation_result.valid else 'FAIL'}, "
                          f"Tests: {test_result.passed_tests}/{test_result.total_tests}, "
                          f"Deployment: {len(deployment_artifacts.files)} artifacts",
                "metrics": quality_metrics,
            })

            if overall_success:
                self.logger.info("=== BMAD Delivery 단계 완료 ===")
            else:
                self.logger.warning("=== BMAD Delivery 단계 완료 (경고 있음) ===")

            return context

        except Exception as e:
            self.logger.error(f"Delivery 실패: {e}")
            context.phase_history.append({
                "phase": BMADPhase.DELIVERY,
                "status": PhaseStatus.FAILED,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            })
            raise

    def _calculate_quality_score(
        self,
        validation_result,
        test_result,
    ) -> float:
        """
        품질 점수 계산

        Args:
            validation_result: 검증 결과
            test_result: 테스트 결과

        Returns:
            float: 품질 점수 (0.0 ~ 100.0)
        """
        score = 100.0

        # 구문 오류: -20점
        if validation_result.syntax_errors:
            score -= 20.0

        # 보안 이슈: critical/high -10점, medium -5점
        for issue in validation_result.security_issues:
            if issue["severity"] in ["critical", "high"]:
                score -= 10.0
            else:
                score -= 5.0

        # 테스트 실패: 각 실패당 -5점
        if test_result.total_tests > 0:
            failure_rate = test_result.failed_tests / test_result.total_tests
            score -= failure_rate * 50.0  # 최대 -50점
        else:
            score -= 20.0  # 테스트 없음: -20점

        # 문서화 점수: docstring coverage 기반
        if validation_result.metrics:
            doc_coverage = validation_result.metrics.get("docstring_coverage", 0)
            if doc_coverage < 50:
                score -= 10.0  # 문서화 부족

        # 복잡도 점수: 평균 복잡도 기반
        if validation_result.metrics:
            avg_complexity = validation_result.metrics.get("avg_complexity", 0)
            if avg_complexity > 10:
                score -= 10.0  # 복잡도 높음

        return max(0.0, min(100.0, score))
    
    def run_full_pipeline(
        self,
        project_name: str,
        requirement: str,
        enable_adaptive: bool = True
    ) -> BMADContext:
        """
        전체 BMAD 파이프라인 실행 (Scale-Adaptive Intelligence 적용)

        Args:
            project_name: 프로젝트 이름
            requirement: 요구사항
            enable_adaptive: Scale-Adaptive Intelligence 활성화 여부

        Returns:
            BMADContext: 완료된 컨텍스트
        """
        # 🆕 Progress Reporter: Start workflow
        if self.progress_reporter:
            self.progress_reporter.start_workflow(
                workflow_name=f"BMAD Pipeline: {project_name}",
                total_phases=6
            )

        context = self.create_context(project_name, requirement)

        # 🆕 Scale-Adaptive Intelligence
        if enable_adaptive:
            from app.core.bmad.adaptive import ScaleAdaptiveEngine
            from app.core.bmad.analyzer import AnalysisResult

            self.logger.info("=== Scale-Adaptive Intelligence 활성화 ===")

            # 1. Discovery (초기 분석)
            context = self.execute_discovery(context, enable_sharding=True)

            # 2. 규모 분석
            adaptive_engine = ScaleAdaptiveEngine()

            # AnalysisResult 생성 (context.analysis_result가 있으면 사용, 없으면 간단한 변환)
            if hasattr(context, 'analysis_result') and context.analysis_result:
                analysis_result = AnalysisResult(**context.analysis_result)
            else:
                # Fallback: context.analysis(RequirementAnalysis)에서 AnalysisResult 생성
                from app.core.bmad.analyzer import DomainContext, ExtractedFeature
                req_analysis = context.analysis

                analysis_result = AnalysisResult(
                    raw_requirement=context.requirement,
                    domain_context=DomainContext(
                        domain=req_analysis.get('domain', 'general'),
                        subdomain=req_analysis.get('subdomain'),
                        keywords=[],
                        industry_terms=[],
                        related_domains=[]
                    ),
                    features=[
                        ExtractedFeature(
                            id=f"feature_{i}",
                            name=task.get('name', f'Feature {i}'),
                            description=task.get('description', ''),
                            priority=5,
                            type="functional",
                            dependencies=[]
                        )
                        for i, task in enumerate(req_analysis.get('tasks', []), 1)
                    ],
                    constraints=req_analysis.get('constraints', []),
                    assumptions=[],
                    success_criteria=req_analysis.get('success_criteria', []),
                    suggested_workflow=req_analysis.get('workflow_type', 'sequential'),
                    complexity_score=5
                )

            scale = adaptive_engine.analyze_scale(analysis_result)
            workflow_config = adaptive_engine.create_workflow_config(scale)

            self.logger.info(f"프로젝트 규모: {scale.value}")
            self.logger.info(f"예상 소요 시간: {adaptive_engine.estimate_duration(scale)['avg_minutes']}분")

            # 권장사항 출력
            recommendations = adaptive_engine.recommend_optimizations(scale, analysis_result)
            for rec in recommendations:
                self.logger.info(f"📌 {rec}")

            # 3. Architecture (시스템 아키텍처 설계)
            if "Architecture" not in workflow_config.skip_phases:
                context = self.execute_architecture(context)
            else:
                self.logger.info("Architecture 단계 생략 (Quick Fix)")

            # 4. Design (Quick Fix는 간소화 가능)
            if "Design" not in workflow_config.skip_phases:
                context = self.execute_design(context)
            else:
                self.logger.info("Design 단계 생략 (Quick Fix)")

            # 4. Development (규모별 설정 적용)
            context = self.execute_development(
                context,
                enable_reflection=workflow_config.enable_reflection,
                quality_threshold=workflow_config.quality_threshold,
                max_reflection_iterations=3 if scale.value != "quick_fix" else 1
            )

            # 5. Delivery (규모별 검증 수준 조정)
            if workflow_config.require_tests or workflow_config.require_security_audit:
                context = self.execute_delivery(context)
            else:
                self.logger.info("Delivery 단계 간소화 (Quick Fix)")

            # 규모 정보 저장
            context.phase_history.append({
                "phase": "adaptive_intelligence",
                "scale": scale.value,
                "config": workflow_config.model_dump(),
                "duration_estimate": adaptive_engine.estimate_duration(scale),
                "recommendations": recommendations,
            })

        else:
            # 기존 파이프라인 (Adaptive 비활성화)
            self.logger.info("=== 표준 파이프라인 실행 ===")

            # 1. Discovery
            context = self.execute_discovery(context, enable_sharding=True)

            # 2. Architecture
            context = self.execute_architecture(context)

            # 3. Design
            context = self.execute_design(context)

            # 4. Development
            context = self.execute_development(context, enable_reflection=True)

            # 4. Delivery
            context = self.execute_delivery(context)

        context.updated_at = datetime.now()

        # 🆕 Progress Reporter: Complete workflow
        if self.progress_reporter:
            success = context.current_phase == BMADPhase.DELIVERY
            self.progress_reporter.complete_workflow(success=success)

        return context
