"""
Domain-Specific Code Generation Strategy

Determines code generation approach based on domain type.
"""

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class CodeGenStrategy(str, Enum):
    """Code generation strategy"""
    AGENT_BASED = "agent_based"  # Agent-centric
    CRUD_BASED = "crud_based"    # CRUD-centric (minimal agents)
    HYBRID = "hybrid"            # Agent + CRUD combined


class DomainStrategyConfig(BaseModel):
    """Domain strategy configuration"""

    strategy: CodeGenStrategy = Field(description="Code generation strategy")
    requires_agents: bool = Field(description="Whether agents are required")
    requires_crud: bool = Field(description="Whether CRUD API is required")
    requires_database: bool = Field(description="Whether database is required")
    primary_artifact: str = Field(description="Primary artifact type")
    agent_purpose: Optional[str] = Field(
        default=None,
        description="Purpose of agents"
    )
    recommended_architecture: str = Field(
        description="Recommended architecture description"
    )


class DomainStrategy:
    """
    Domain-based Code Generation Strategy

    Maps domain types to optimal code generation strategies.
    """

    # Domain → Strategy mapping
    STRATEGY_MAP: Dict[str, DomainStrategyConfig] = {
        # CRUD-centric domains (minimize agents)
        "TASK_MANAGEMENT": DomainStrategyConfig(
            strategy=CodeGenStrategy.CRUD_BASED,
            requires_agents=False,
            requires_crud=True,
            requires_database=True,
            primary_artifact="backend",
            agent_purpose="reminder_notifications",
            recommended_architecture=(
                "FastAPI REST API + Database + Streamlit UI. "
                "Optional: Agent for background reminders."
            )
        ),

        "E_COMMERCE": DomainStrategyConfig(
            strategy=CodeGenStrategy.CRUD_BASED,
            requires_agents=False,
            requires_crud=True,
            requires_database=True,
            primary_artifact="backend",
            agent_purpose="order_processing",
            recommended_architecture=(
                "FastAPI REST API + Database + Streamlit UI. "
                "Optional: Agent for order notifications."
            )
        ),

        "PROJECT_MANAGEMENT": DomainStrategyConfig(
            strategy=CodeGenStrategy.CRUD_BASED,
            requires_agents=False,
            requires_crud=True,
            requires_database=True,
            primary_artifact="backend",
            agent_purpose="project_notifications",
            recommended_architecture=(
                "FastAPI REST API + Database + Streamlit UI. "
                "Optional: Agent for project notifications."
            )
        ),

        # Agent-centric domains
        "CONVERSATIONAL_AI": DomainStrategyConfig(
            strategy=CodeGenStrategy.AGENT_BASED,
            requires_agents=True,
            requires_crud=False,
            requires_database=False,
            primary_artifact="agents",
            agent_purpose="conversation_management",
            recommended_architecture=(
                "CrewAI Agents for conversation + Streamlit Chat UI."
            )
        ),

        "CUSTOMER_SUPPORT": DomainStrategyConfig(
            strategy=CodeGenStrategy.AGENT_BASED,
            requires_agents=True,
            requires_crud=False,
            requires_database=False,
            primary_artifact="agents",
            agent_purpose="support_automation",
            recommended_architecture=(
                "CrewAI Agents for support + Streamlit UI."
            )
        ),

        "CONTENT_CREATION": DomainStrategyConfig(
            strategy=CodeGenStrategy.AGENT_BASED,
            requires_agents=True,
            requires_crud=False,
            requires_database=False,
            primary_artifact="agents",
            agent_purpose="content_generation",
            recommended_architecture=(
                "CrewAI Agents for content creation + Streamlit UI."
            )
        ),

        # Hybrid domains
        "WORKFLOW_AUTOMATION": DomainStrategyConfig(
            strategy=CodeGenStrategy.HYBRID,
            requires_agents=True,
            requires_crud=True,
            requires_database=True,
            primary_artifact="agents",
            agent_purpose="workflow_orchestration",
            recommended_architecture=(
                "CrewAI Agents + FastAPI + Database. "
                "Agents execute workflows, API manages state."
            )
        ),

        "DATA_ANALYSIS": DomainStrategyConfig(
            strategy=CodeGenStrategy.HYBRID,
            requires_agents=True,
            requires_crud=True,
            requires_database=True,
            primary_artifact="agents",
            agent_purpose="data_processing",
            recommended_architecture=(
                "CrewAI Agents + FastAPI + Database. "
                "Agents perform analysis, API serves results."
            )
        ),
    }

    @classmethod
    def get_strategy_config(cls, domain: Optional[str]) -> DomainStrategyConfig:
        """
        Get strategy configuration for domain.

        Args:
            domain: Domain type

        Returns:
            DomainStrategyConfig: Strategy configuration
        """
        if not domain:
            # Default: Agent-based
            return DomainStrategyConfig(
                strategy=CodeGenStrategy.AGENT_BASED,
                requires_agents=True,
                requires_crud=False,
                requires_database=False,
                primary_artifact="agents",
                agent_purpose="general_purpose",
                recommended_architecture="CrewAI Agents with custom logic"
            )

        config = cls.STRATEGY_MAP.get(domain.upper())

        if config is None:
            # Default for unknown domains
            return DomainStrategyConfig(
                strategy=CodeGenStrategy.AGENT_BASED,
                requires_agents=True,
                requires_crud=False,
                requires_database=False,
                primary_artifact="agents",
                agent_purpose="general_purpose",
                recommended_architecture="CrewAI Agents with custom logic"
            )

        return config

    @classmethod
    def get_strategy(cls, domain: Optional[str]) -> CodeGenStrategy:
        """Get code generation strategy for domain"""
        config = cls.get_strategy_config(domain)
        return config.strategy

    @classmethod
    def requires_agents(cls, domain: Optional[str]) -> bool:
        """Check if domain requires agents"""
        config = cls.get_strategy_config(domain)
        return config.requires_agents

    @classmethod
    def requires_crud(cls, domain: Optional[str]) -> bool:
        """Check if domain requires CRUD"""
        config = cls.get_strategy_config(domain)
        return config.requires_crud

    @classmethod
    def requires_database(cls, domain: Optional[str]) -> bool:
        """Check if domain requires database"""
        config = cls.get_strategy_config(domain)
        return config.requires_database
