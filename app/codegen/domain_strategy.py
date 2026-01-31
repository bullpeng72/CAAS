"""
Domain-based Code Generation Strategy

도메인 타입에 따라 코드 생성 전략을 결정합니다.

핵심 개념:
- CRUD_BASED: Agent 최소화, CRUD 중심 (Todo 앱, E-commerce)
- AGENT_BASED: Agent 중심 (Chatbot, Customer Support)
- HYBRID: Agent + CRUD 결합 (Workflow Automation, Data Analysis)
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.domain_types import DomainType, ExecutionPattern
from app.utils.logger import get_logger

logger = get_logger("codegen.strategy")


class CodeGenStrategy(str, Enum):
    """코드 생성 전략"""

    AGENT_BASED = "agent_based"
    """Agent 중심: CrewAI Agents가 핵심 로직 수행"""

    CRUD_BASED = "crud_based"
    """CRUD 중심: FastAPI + DB 모델이 핵심, Agent는 최소화 또는 제외"""

    HYBRID = "hybrid"
    """Hybrid: Agent (비동기 작업) + CRUD (데이터 관리) 결합"""


class DomainStrategyConfig(BaseModel):
    """도메인 전략 설정"""

    strategy: CodeGenStrategy = Field(
        description="코드 생성 전략"
    )

    requires_agents: bool = Field(
        description="Agent 생성 필요 여부"
    )

    requires_crud: bool = Field(
        description="CRUD API 생성 필요 여부"
    )

    requires_database: bool = Field(
        description="Database 생성 필요 여부"
    )

    primary_artifact: str = Field(
        description="주요 아티팩트 (agents, backend, frontend)"
    )

    agent_purpose: Optional[str] = Field(
        default=None,
        description="Agent의 목적 (background tasks, business logic, conversation, etc.)"
    )

    recommended_architecture: str = Field(
        description="권장 아키텍처 설명"
    )


class DomainCodeStrategy:
    """
    도메인별 코드 생성 전략

    도메인 타입에 따라 최적의 코드 생성 전략을 결정합니다.
    """

    # 도메인별 전략 매핑
    STRATEGY_MAP: Dict[DomainType, DomainStrategyConfig] = {
        # ================================================================
        # CRUD 중심 도메인 (Agent 최소화)
        # ================================================================

        DomainType.TASK_MANAGEMENT: DomainStrategyConfig(
            strategy=CodeGenStrategy.CRUD_BASED,
            requires_agents=False,
            requires_crud=True,
            requires_database=True,
            primary_artifact="backend",
            agent_purpose="reminder_notifications",  # 선택적
            recommended_architecture=(
                "FastAPI REST API + Database (CRUD operations) + "
                "Streamlit UI for task management. "
                "Optional: Agent for background reminders."
            )
        ),

        DomainType.E_COMMERCE: DomainStrategyConfig(
            strategy=CodeGenStrategy.CRUD_BASED,
            requires_agents=False,
            requires_crud=True,
            requires_database=True,
            primary_artifact="backend",
            agent_purpose="order_processing",  # 선택적
            recommended_architecture=(
                "FastAPI REST API + Database (products, orders, users) + "
                "Streamlit UI for e-commerce. "
                "Optional: Agent for order notifications."
            )
        ),

        DomainType.DASHBOARD: DomainStrategyConfig(
            strategy=CodeGenStrategy.CRUD_BASED,
            requires_agents=False,
            requires_crud=True,
            requires_database=True,
            primary_artifact="frontend",
            agent_purpose="data_refresh",  # 선택적
            recommended_architecture=(
                "Streamlit Dashboard + FastAPI for data API + "
                "Database for metrics storage. "
                "Optional: Agent for scheduled data updates."
            )
        ),

        DomainType.KNOWLEDGE_BASE: DomainStrategyConfig(
            strategy=CodeGenStrategy.CRUD_BASED,
            requires_agents=False,
            requires_crud=True,
            requires_database=True,
            primary_artifact="backend",
            agent_purpose="document_indexing",  # 선택적
            recommended_architecture=(
                "FastAPI + Vector Database (embeddings) + "
                "Streamlit UI for search interface. "
                "Optional: Agent for document processing."
            )
        ),

        # ================================================================
        # Agent 중심 도메인
        # ================================================================

        DomainType.CONVERSATIONAL_AI: DomainStrategyConfig(
            strategy=CodeGenStrategy.AGENT_BASED,
            requires_agents=True,
            requires_crud=False,
            requires_database=False,
            primary_artifact="agents",
            agent_purpose="conversation_management",
            recommended_architecture=(
                "CrewAI Agents (conversation_assistant, context_manager, intent_classifier) + "
                "Streamlit Chat UI. "
                "Agents handle all conversation logic."
            )
        ),

        DomainType.CUSTOMER_SUPPORT: DomainStrategyConfig(
            strategy=CodeGenStrategy.AGENT_BASED,
            requires_agents=True,
            requires_crud=False,
            requires_database=False,
            primary_artifact="agents",
            agent_purpose="support_automation",
            recommended_architecture=(
                "CrewAI Agents (support_agent, ticket_manager) + "
                "Streamlit UI for customer interactions. "
                "Agents handle ticket routing and responses."
            )
        ),

        DomainType.CONTENT_CREATION: DomainStrategyConfig(
            strategy=CodeGenStrategy.AGENT_BASED,
            requires_agents=True,
            requires_crud=False,
            requires_database=False,
            primary_artifact="agents",
            agent_purpose="content_generation",
            recommended_architecture=(
                "CrewAI Agents (content_writer, content_editor) + "
                "Streamlit UI for content management. "
                "Agents handle writing and editing."
            )
        ),

        DomainType.REPORT_GENERATION: DomainStrategyConfig(
            strategy=CodeGenStrategy.AGENT_BASED,
            requires_agents=True,
            requires_crud=False,
            requires_database=False,
            primary_artifact="agents",
            agent_purpose="report_automation",
            recommended_architecture=(
                "CrewAI Agents (report_generator, data_collector) + "
                "Streamlit UI for report parameters. "
                "Agents handle data collection and report creation."
            )
        ),

        # ================================================================
        # Hybrid 도메인 (Agent + CRUD)
        # ================================================================

        DomainType.WORKFLOW_AUTOMATION: DomainStrategyConfig(
            strategy=CodeGenStrategy.HYBRID,
            requires_agents=True,
            requires_crud=True,
            requires_database=True,
            primary_artifact="agents",
            agent_purpose="workflow_orchestration",
            recommended_architecture=(
                "CrewAI Agents (workflow_orchestrator, notification_agent) + "
                "FastAPI for workflow state management + Database. "
                "Agents execute workflows, API manages state."
            )
        ),

        DomainType.DATA_ANALYSIS: DomainStrategyConfig(
            strategy=CodeGenStrategy.HYBRID,
            requires_agents=True,
            requires_crud=True,
            requires_database=True,
            primary_artifact="agents",
            agent_purpose="data_processing",
            recommended_architecture=(
                "CrewAI Agents (data_analyst, visualization_expert) + "
                "FastAPI for data upload/download + Database. "
                "Agents perform analysis, API serves results."
            )
        ),

        DomainType.DOCUMENT_PROCESSING: DomainStrategyConfig(
            strategy=CodeGenStrategy.HYBRID,
            requires_agents=True,
            requires_crud=True,
            requires_database=True,
            primary_artifact="agents",
            agent_purpose="document_transformation",
            recommended_architecture=(
                "CrewAI Agents (document_processor, document_analyzer) + "
                "FastAPI for file upload + Database for results. "
                "Agents process documents, API manages files."
            )
        ),

        DomainType.API_INTEGRATION: DomainStrategyConfig(
            strategy=CodeGenStrategy.HYBRID,
            requires_agents=True,
            requires_crud=True,
            requires_database=False,
            primary_artifact="backend",
            agent_purpose="api_orchestration",
            recommended_architecture=(
                "CrewAI Agents (api_connector, data_transformer) + "
                "FastAPI for integration endpoints. "
                "Agents handle external API calls, FastAPI exposes unified interface."
            )
        ),
    }

    @classmethod
    def get_strategy_config(cls, domain_type: DomainType) -> DomainStrategyConfig:
        """
        도메인 타입에서 전략 설정 반환

        Args:
            domain_type: 도메인 타입

        Returns:
            DomainStrategyConfig: 전략 설정
        """
        config = cls.STRATEGY_MAP.get(domain_type)

        if config is None:
            # 기본값: Agent 기반 (가장 범용적)
            logger.warning(f"도메인 {domain_type}에 대한 전략이 정의되지 않음. Agent 기반 사용.")
            config = DomainStrategyConfig(
                strategy=CodeGenStrategy.AGENT_BASED,
                requires_agents=True,
                requires_crud=False,
                requires_database=False,
                primary_artifact="agents",
                agent_purpose="general_purpose",
                recommended_architecture="CrewAI Agents with custom logic"
            )

        logger.info(
            f"도메인 {domain_type} → 전략: {config.strategy}, "
            f"Agent 필요: {config.requires_agents}, CRUD 필요: {config.requires_crud}"
        )

        return config

    @classmethod
    def get_strategy(cls, domain_type: DomainType) -> CodeGenStrategy:
        """도메인 타입에서 코드 생성 전략 반환 (간단 버전)"""
        config = cls.get_strategy_config(domain_type)
        return config.strategy

    @classmethod
    def requires_agents(cls, domain_type: DomainType) -> bool:
        """Agent 생성 필요 여부"""
        config = cls.get_strategy_config(domain_type)
        return config.requires_agents

    @classmethod
    def requires_crud(cls, domain_type: DomainType) -> bool:
        """CRUD 생성 필요 여부"""
        config = cls.get_strategy_config(domain_type)
        return config.requires_crud

    @classmethod
    def requires_database(cls, domain_type: DomainType) -> bool:
        """Database 생성 필요 여부"""
        config = cls.get_strategy_config(domain_type)
        return config.requires_database

    @classmethod
    def get_primary_artifact(cls, domain_type: DomainType) -> str:
        """주요 아티팩트 반환 (agents, backend, frontend)"""
        config = cls.get_strategy_config(domain_type)
        return config.primary_artifact

    @classmethod
    def get_recommendation(cls, domain_type: DomainType) -> str:
        """아키텍처 권장사항 반환"""
        config = cls.get_strategy_config(domain_type)
        return config.recommended_architecture

    @classmethod
    def should_minimize_agents(cls, domain_type: DomainType) -> bool:
        """
        Agent를 최소화해야 하는지 여부

        CRUD 중심 도메인에서는 Agent를 최소화하거나 제외합니다.
        """
        strategy = cls.get_strategy(domain_type)
        return strategy == CodeGenStrategy.CRUD_BASED

    @classmethod
    def get_agent_role_suggestion(cls, domain_type: DomainType) -> str:
        """
        Agent 역할 제안

        CRUD 중심 도메인의 경우 선택적 Agent 역할을 제안합니다.
        """
        config = cls.get_strategy_config(domain_type)

        if config.agent_purpose:
            return (
                f"선택사항: Agent를 백그라운드 작업용으로 사용할 수 있습니다 "
                f"(목적: {config.agent_purpose}). "
                f"하지만 핵심 CRUD 로직은 FastAPI에 구현하세요."
            )
        else:
            return "이 도메인은 Agent가 핵심 로직을 수행합니다."
