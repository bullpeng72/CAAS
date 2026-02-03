"""
Tests for Self-Aware Agent

Tests the meta-cognitive capabilities and self-assessment functionality.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from caas_framework.agents.self_aware_agent import (
    AgentCapabilities,
    CapabilityAssessment,
    LLMBasedAssessment,
    RuleBasedAssessment,
    SelfAwareAgent,
    create_self_aware_agent,
)


class TestCapabilityAssessment:
    """Test CapabilityAssessment model."""

    def test_assessment_creation(self):
        """Test creating capability assessment."""
        assessment = CapabilityAssessment(
            confidence=0.8,
            reasoning="Agent has required tools",
            missing_capabilities=[],
            alternative_approach=None,
            estimated_difficulty="Easy",
        )

        assert assessment.confidence == 0.8
        assert assessment.reasoning == "Agent has required tools"
        assert assessment.missing_capabilities == []
        assert assessment.estimated_difficulty == "Easy"

    def test_assessment_validation(self):
        """Test confidence validation."""
        with pytest.raises(Exception):  # Pydantic validation error
            CapabilityAssessment(
                confidence=1.5,  # > 1.0
                reasoning="Invalid",
            )

        with pytest.raises(Exception):
            CapabilityAssessment(
                confidence=-0.1,  # < 0.0
                reasoning="Invalid",
            )


class TestAgentCapabilities:
    """Test AgentCapabilities dataclass."""

    def test_capabilities_creation(self):
        """Test creating agent capabilities."""
        caps = AgentCapabilities(
            role="Developer",
            tools=["file_read", "file_write", "git"],
            expertise="Python development",
            goal="Write clean code",
        )

        assert caps.role == "Developer"
        assert len(caps.tools) == 3
        assert caps.known_limitations == []

    def test_capabilities_with_limitations(self):
        """Test capabilities with known limitations."""
        caps = AgentCapabilities(
            role="Frontend Developer",
            tools=["file_write"],
            expertise="React and TypeScript",
            goal="Build UIs",
            known_limitations=["backend", "database"],
        )

        assert len(caps.known_limitations) == 2
        assert "backend" in caps.known_limitations


class TestRuleBasedAssessment:
    """Test rule-based assessment strategy."""

    def test_assessment_with_matching_tools(self):
        """Test assessment when agent has required tools."""
        strategy = RuleBasedAssessment()

        caps = AgentCapabilities(
            role="Developer",
            tools=["file_read", "file_write"],
            expertise="Coding",
            goal="Write code",
        )

        assessment = strategy.assess("Read a file and write code", caps)

        # Should have high confidence
        assert assessment.confidence >= 0.7
        assert "can perform" in assessment.reasoning.lower()

    def test_assessment_with_missing_tools(self):
        """Test assessment when agent lacks required tools."""
        strategy = RuleBasedAssessment()

        caps = AgentCapabilities(
            role="Developer", tools=["file_read"], expertise="Coding", goal="Write code"
        )

        assessment = strategy.assess("Search the web for information", caps)

        # Should have lower confidence
        assert assessment.confidence < 0.7
        assert len(assessment.missing_capabilities) > 0
        assert assessment.alternative_approach is not None

    def test_assessment_with_known_limitation(self):
        """Test assessment for task in known limitation."""
        strategy = RuleBasedAssessment()

        caps = AgentCapabilities(
            role="Frontend Developer",
            tools=["file_write"],
            expertise="React",
            goal="Build UIs",
            known_limitations=["database", "backend"],
        )

        assessment = strategy.assess("Design a database schema", caps)

        # Should have low confidence
        assert assessment.confidence < 0.7
        assert "database" in assessment.missing_capabilities

    def test_difficulty_estimation(self):
        """Test difficulty estimation based on confidence."""
        strategy = RuleBasedAssessment()

        caps_with_tools = AgentCapabilities(
            role="Dev",
            tools=["file_read", "file_write"],
            expertise="Coding",
            goal="Code",
        )

        caps_without_tools = AgentCapabilities(
            role="Dev", tools=[], expertise="Coding", goal="Code"
        )

        # Easy task with tools
        easy = strategy.assess("Write a file", caps_with_tools)
        assert easy.estimated_difficulty in ["Easy", "Medium"]

        # Hard/Impossible task without tools
        hard = strategy.assess("Search web and access database", caps_without_tools)
        assert hard.estimated_difficulty in ["Hard", "Impossible"]


class TestLLMBasedAssessment:
    """Test LLM-based assessment strategy."""

    def test_llm_assessment_success(self):
        """Test LLM assessment when LLM succeeds."""
        # Mock LLM provider
        mock_llm = Mock()
        mock_llm.generate_structured.return_value = CapabilityAssessment(
            confidence=0.9,
            reasoning="LLM assessed high capability",
            missing_capabilities=[],
            alternative_approach=None,
            estimated_difficulty="Easy",
        )

        strategy = LLMBasedAssessment(mock_llm)

        caps = AgentCapabilities(
            role="Developer", tools=["file_read"], expertise="Coding", goal="Code"
        )

        assessment = strategy.assess("Read a file", caps)

        assert assessment.confidence == 0.9
        assert mock_llm.generate_structured.called

    def test_llm_assessment_fallback(self):
        """Test fallback to rule-based when LLM fails."""
        # Mock LLM that raises exception
        mock_llm = Mock()
        mock_llm.generate_structured.side_effect = Exception("LLM error")

        strategy = LLMBasedAssessment(mock_llm)

        caps = AgentCapabilities(
            role="Developer", tools=["file_read"], expertise="Coding", goal="Code"
        )

        assessment = strategy.assess("Read a file", caps)

        # Should still return assessment (from fallback)
        assert assessment is not None
        assert isinstance(assessment, CapabilityAssessment)


class TestSelfAwareAgent:
    """Test SelfAwareAgent class."""

    def test_agent_initialization(self):
        """Test creating self-aware agent."""
        caps = AgentCapabilities(
            role="Developer", tools=["file_read"], expertise="Coding", goal="Code"
        )

        agent = SelfAwareAgent(capabilities=caps, confidence_threshold=0.7)

        assert agent.capabilities == caps
        assert agent.confidence_threshold == 0.7
        assert len(agent.assessment_history) == 0

    def test_can_perform_within_capability(self):
        """Test can_perform for task within capability."""
        caps = AgentCapabilities(
            role="Developer",
            tools=["file_read", "file_write"],
            expertise="Python coding",
            goal="Write code",
        )

        agent = SelfAwareAgent(capabilities=caps)

        assessment = agent.can_perform("Read and write files")

        assert assessment.confidence >= 0.7
        assert len(agent.assessment_history) == 1

    def test_can_perform_outside_capability(self):
        """Test can_perform for task outside capability."""
        caps = AgentCapabilities(
            role="Developer",
            tools=["file_read"],
            expertise="Reading code",
            goal="Analyze code",
        )

        agent = SelfAwareAgent(capabilities=caps)

        assessment = agent.can_perform("Search the web for solutions")

        assert assessment.confidence < 0.7
        assert len(assessment.missing_capabilities) > 0

    def test_execute_or_delegate_sync_executes(self):
        """Test sync execute when confident."""
        caps = AgentCapabilities(
            role="Developer",
            tools=["file_read"],
            expertise="Reading",
            goal="Read files",
        )

        agent = SelfAwareAgent(capabilities=caps, confidence_threshold=0.7)

        # Mock executor
        mock_executor = Mock(return_value="Task completed")

        result, assessment = agent.execute_or_delegate_sync(
            "Read a file", executor=mock_executor, verbose=False
        )

        assert assessment.confidence >= 0.7
        assert mock_executor.called
        assert result == "Task completed"

    def test_execute_or_delegate_sync_delegates(self):
        """Test sync delegate when not confident."""
        caps = AgentCapabilities(
            role="Developer",
            tools=["file_read"],
            expertise="Reading",
            goal="Read files",
        )

        agent = SelfAwareAgent(capabilities=caps, confidence_threshold=0.7)

        result, assessment = agent.execute_or_delegate_sync(
            "Search the web", verbose=False
        )

        assert assessment.confidence < 0.7
        assert result["status"] == "needs_delegation"

    def test_execute_or_delegate_sync_with_delegate_handler(self):
        """Test sync delegation with custom handler."""
        caps = AgentCapabilities(
            role="Developer",
            tools=["file_read"],
            expertise="Reading",
            goal="Read files",
        )

        # Mock delegate handler
        mock_delegate = Mock(return_value="Delegated successfully")

        agent = SelfAwareAgent(
            capabilities=caps, confidence_threshold=0.7, delegate_handler=mock_delegate
        )

        result, assessment = agent.execute_or_delegate_sync(
            "Search the web", verbose=False
        )

        assert assessment.confidence < 0.7
        assert mock_delegate.called
        assert result == "Delegated successfully"

    @pytest.mark.asyncio
    async def test_execute_or_delegate_async_executes(self):
        """Test async execute when confident."""
        caps = AgentCapabilities(
            role="Developer",
            tools=["file_read", "file_write"],
            expertise="Coding",
            goal="Write code",
        )

        agent = SelfAwareAgent(capabilities=caps)

        # Mock async executor
        mock_executor = AsyncMock(return_value="Async task completed")

        result, assessment = await agent.execute_or_delegate(
            "Read and write files", executor=mock_executor, verbose=False
        )

        assert assessment.confidence >= 0.7
        assert mock_executor.called
        assert result == "Async task completed"

    @pytest.mark.asyncio
    async def test_execute_or_delegate_async_delegates(self):
        """Test async delegate when not confident."""
        caps = AgentCapabilities(
            role="Developer",
            tools=["file_read"],
            expertise="Reading",
            goal="Read files",
        )

        # Mock async delegate handler
        mock_delegate = AsyncMock(return_value="Delegated to expert")

        agent = SelfAwareAgent(capabilities=caps, delegate_handler=mock_delegate)

        result, assessment = await agent.execute_or_delegate(
            "Build a complex web application with database", verbose=False
        )

        assert assessment.confidence < 0.7
        assert mock_delegate.called
        assert result == "Delegated to expert"

    def test_get_assessment_statistics_empty(self):
        """Test statistics with no assessments."""
        caps = AgentCapabilities(
            role="Developer", tools=["file_read"], expertise="Reading", goal="Read"
        )

        agent = SelfAwareAgent(capabilities=caps)

        stats = agent.get_assessment_statistics()

        assert stats["total_assessments"] == 0
        assert stats["avg_confidence"] == 0.0

    def test_get_assessment_statistics_with_history(self):
        """Test statistics with assessment history."""
        caps = AgentCapabilities(
            role="Developer",
            tools=["file_read", "file_write"],
            expertise="Coding",
            goal="Code",
        )

        agent = SelfAwareAgent(capabilities=caps, confidence_threshold=0.7)

        # Perform several assessments
        agent.can_perform("Read a file")  # Should be confident
        agent.can_perform("Search the web")  # Should not be confident
        agent.can_perform("Write code")  # Should be confident

        stats = agent.get_assessment_statistics()

        assert stats["total_assessments"] == 3
        assert stats["avg_confidence"] > 0.0
        assert stats["tasks_within_capability"] >= 2
        assert stats["tasks_requiring_delegation"] >= 1


class TestFactoryFunction:
    """Test create_self_aware_agent factory."""

    def test_create_with_rule_based(self):
        """Test creating agent with rule-based strategy."""
        agent = create_self_aware_agent(
            role="Developer",
            tools=["file_read", "file_write"],
            expertise="Python development",
            goal="Write clean code",
            confidence_threshold=0.7,
        )

        assert isinstance(agent, SelfAwareAgent)
        assert agent.capabilities.role == "Developer"
        assert isinstance(agent.assessment_strategy, RuleBasedAssessment)

    def test_create_with_llm(self):
        """Test creating agent with LLM strategy."""
        mock_llm = Mock()

        agent = create_self_aware_agent(
            role="Developer",
            tools=["file_read"],
            expertise="Coding",
            goal="Code",
            llm_provider=mock_llm,
        )

        assert isinstance(agent, SelfAwareAgent)
        assert isinstance(agent.assessment_strategy, LLMBasedAssessment)

    def test_create_with_limitations(self):
        """Test creating agent with known limitations."""
        agent = create_self_aware_agent(
            role="Frontend Dev",
            tools=["file_write"],
            expertise="React",
            goal="Build UIs",
            known_limitations=["backend", "database"],
        )

        assert len(agent.capabilities.known_limitations) == 2


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_task(self):
        """Test with empty task string."""
        caps = AgentCapabilities(
            role="Developer", tools=["file_read"], expertise="Coding", goal="Code"
        )

        agent = SelfAwareAgent(capabilities=caps)

        assessment = agent.can_perform("")

        # Should still return assessment
        assert assessment is not None

    def test_agent_with_no_tools(self):
        """Test agent with no tools."""
        caps = AgentCapabilities(
            role="Thinker", tools=[], expertise="Thinking", goal="Think"
        )

        agent = SelfAwareAgent(capabilities=caps)

        assessment = agent.can_perform("Perform complex task requiring tools")

        # Should have low confidence
        assert assessment.confidence < 0.7

    def test_very_high_confidence_threshold(self):
        """Test with very high confidence threshold."""
        caps = AgentCapabilities(
            role="Developer",
            tools=["file_read", "file_write"],
            expertise="Expert coder",
            goal="Perfect code",
        )

        agent = SelfAwareAgent(
            capabilities=caps,
            confidence_threshold=0.95,  # Very high
        )

        result, assessment = agent.execute_or_delegate_sync(
            "Read a file", verbose=False
        )

        # Even simple tasks might not meet threshold
        # Result could be execution or delegation depending on exact confidence


class TestIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_confidence(self):
        """Test complete workflow with confident agent."""
        caps = AgentCapabilities(
            role="File Manager",
            tools=["file_read", "file_write"],
            expertise="File operations",
            goal="Manage files efficiently",
        )

        # Mock executor
        async def mock_execute(task):
            return f"Executed: {task}"

        agent = SelfAwareAgent(capabilities=caps, confidence_threshold=0.7)

        # Execute task within capability
        result, assessment = await agent.execute_or_delegate(
            "Read configuration file", executor=mock_execute, verbose=False
        )

        assert assessment.confidence >= 0.7
        assert "Executed" in result

        # Check statistics
        stats = agent.get_assessment_statistics()
        assert stats["total_assessments"] == 1
        assert stats["tasks_within_capability"] == 1

    @pytest.mark.asyncio
    async def test_full_workflow_with_delegation(self):
        """Test complete workflow with task requiring delegation."""
        caps = AgentCapabilities(
            role="File Manager",
            tools=["file_read"],
            expertise="Reading files",
            goal="Read files",
            known_limitations=["database", "web"],
        )

        # Mock delegate handler
        async def mock_delegate(task, reason, missing_capabilities):
            return {"delegated_to": "specialist", "task": task, "reason": reason}

        agent = SelfAwareAgent(
            capabilities=caps, confidence_threshold=0.7, delegate_handler=mock_delegate
        )

        # Task outside capability
        result, assessment = await agent.execute_or_delegate(
            "Search the web and query database", verbose=False
        )

        assert assessment.confidence < 0.7
        assert "delegated_to" in result
        assert result["delegated_to"] == "specialist"

        # Check statistics
        stats = agent.get_assessment_statistics()
        assert stats["tasks_requiring_delegation"] == 1

    def test_assessment_history_tracking(self):
        """Test that assessment history is properly tracked."""
        caps = AgentCapabilities(
            role="Developer",
            tools=["file_read", "file_write", "git"],
            expertise="Software development",
            goal="Develop software",
        )

        agent = SelfAwareAgent(capabilities=caps)

        # Perform various assessments
        tasks = [
            "Read source code",
            "Search the web",
            "Write code",
            "Query database",
            "Commit changes with git",
        ]

        for task in tasks:
            agent.can_perform(task)

        # Check history
        assert len(agent.assessment_history) == 5

        # Get statistics
        stats = agent.get_assessment_statistics()
        assert stats["total_assessments"] == 5
        assert stats["avg_confidence"] > 0.0
        assert 0.0 <= stats["delegation_rate"] <= 1.0

    def test_multiple_agents_different_capabilities(self):
        """Test multiple agents with different capabilities."""
        # Frontend developer
        frontend = create_self_aware_agent(
            role="Frontend Developer",
            tools=["file_write"],
            expertise="React and TypeScript",
            goal="Build user interfaces",
            known_limitations=["backend", "database"],
        )

        # Backend developer
        backend = create_self_aware_agent(
            role="Backend Developer",
            tools=["database", "http_client"],
            expertise="API development and databases",
            goal="Build robust backends",
            known_limitations=["frontend", "UI design"],
        )

        # Assess same task with both
        task = "Build a REST API with database"

        frontend_assessment = frontend.can_perform(task)
        backend_assessment = backend.can_perform(task)

        # Backend should be more confident
        assert backend_assessment.confidence > frontend_assessment.confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
