"""
Integration tests for Producer-Critic Pattern in ExpertAgentCollaboration

Tests that Producer-Critic Pattern is properly integrated into the collaboration workflow.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from caas_framework.agents.collaboration import ExpertAgentCollaboration
from caas_framework.models.specifications import ConcretizedRequirement
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.patterns.producer_critic import (
    ProducerCriticPattern,
    CriticAgent,
    CriticRole
)


class TestCriticPatternIntegration:
    """Test Producer-Critic Pattern integration with ExpertAgentCollaboration"""

    def test_critic_pattern_disabled_by_default(self):
        """Test that critic pattern is disabled by default"""
        # Arrange - Use MockFactory for consistent test data
        from tests.helpers import MockFactory

        mock_llm = MockFactory.create_llm_plugin()
        mock_golden = MockFactory.create_golden_data()

        # Act
        collaboration = ExpertAgentCollaboration(
            llm_plugin=mock_llm,
            golden_data=mock_golden,
            enable_validation=True
            # enable_critic_pattern not specified (defaults to False)
        )

        # Assert
        assert collaboration.enable_critic_pattern is False
        assert collaboration.producer_critic_pattern is None
        assert collaboration.critic_agent is None

    def test_critic_pattern_enabled_initialization(self):
        """Test that critic pattern initializes when enabled"""
        # Arrange - Use MockFactory for consistent test data
        from tests.helpers import MockFactory

        mock_llm = MockFactory.create_llm_plugin()
        mock_golden = MockFactory.create_golden_data()

        # Act
        collaboration = ExpertAgentCollaboration(
            llm_plugin=mock_llm,
            golden_data=mock_golden,
            enable_validation=True,
            enable_critic_pattern=True  # Enable critic pattern
        )

        # Assert
        assert collaboration.enable_critic_pattern is True
        assert collaboration.producer_critic_pattern is not None
        assert isinstance(collaboration.producer_critic_pattern, ProducerCriticPattern)
        assert collaboration.critic_agent is not None
        assert isinstance(collaboration.critic_agent, CriticAgent)
        assert collaboration.critic_agent.role == CriticRole.GENERAL_CRITIC

    def test_critic_pattern_requires_validation(self):
        """Test that critic pattern requires validation to be enabled"""
        # Arrange
        mock_llm = Mock(spec=LLMPlugin)
        mock_golden = Mock(spec=ConcretizedRequirement)

        # Act
        collaboration = ExpertAgentCollaboration(
            llm_plugin=mock_llm,
            golden_data=mock_golden,
            enable_validation=False,  # Validation disabled
            enable_critic_pattern=True  # Try to enable critic pattern
        )

        # Assert - critic pattern should not initialize without validation
        assert collaboration.enable_critic_pattern is True
        assert collaboration.producer_critic_pattern is None
        assert collaboration.critic_agent is None

    def test_critic_pattern_configuration(self):
        """Test that critic pattern is configured correctly"""
        # Arrange - Use MockFactory for consistent test data
        from tests.helpers import MockFactory

        mock_llm = MockFactory.create_llm_plugin()
        mock_golden = MockFactory.create_golden_data()

        # Act
        collaboration = ExpertAgentCollaboration(
            llm_plugin=mock_llm,
            golden_data=mock_golden,
            enable_validation=True,
            enable_critic_pattern=True,
            max_feedback_loops=5  # Custom feedback loops
        )

        # Assert
        pattern = collaboration.producer_critic_pattern
        critic = collaboration.critic_agent

        # Check pattern configuration
        assert pattern.max_iterations == 3
        assert pattern.timeout_per_iteration == 120

        # Check critic configuration
        assert critic.approval_threshold == 7.0
        assert critic.role == CriticRole.GENERAL_CRITIC

    def test_imports_available(self):
        """Test that all necessary imports are available"""
        from caas_framework.agents.collaboration import ExpertAgentCollaboration
        from caas_framework.patterns.producer_critic import (
            ProducerCriticPattern,
            CriticAgent,
            CriticRole,
            ProducerCriticResult
        )

        # All imports should succeed without error
        assert ExpertAgentCollaboration is not None
        assert ProducerCriticPattern is not None
        assert CriticAgent is not None
        assert CriticRole is not None
        assert ProducerCriticResult is not None


class TestCriticPatternTestSuites:
    """Verify that critic pattern test suites exist and pass"""

    def test_critic_pattern_tests_exist(self):
        """Test that critic pattern test files exist"""
        import os

        # Check for test files
        assert os.path.exists("tests/test_critic_pattern.py")
        assert os.path.exists("tests/test_producer_critic.py")

    def test_can_run_critic_pattern_tests(self):
        """Test that we can run critic pattern tests"""
        import subprocess

        # Run tests and check they pass
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/test_critic_pattern.py", "-v"],
            capture_output=True,
            text=True
        )

        # Tests should pass (exit code 0)
        assert result.returncode == 0
        assert "passed" in result.stdout

    def test_can_run_producer_critic_tests(self):
        """Test that we can run producer-critic tests"""
        import subprocess

        # Run tests and check they pass
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/test_producer_critic.py", "-v"],
            capture_output=True,
            text=True
        )

        # Tests should pass (exit code 0)
        assert result.returncode == 0
        assert "passed" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
