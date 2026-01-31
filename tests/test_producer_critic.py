"""
Tests for Producer-Critic Pattern

Tests the Producer-Critic collaboration pattern for iterative refinement.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json

from caas_framework.patterns.producer_critic import (
    ProducerCriticPattern,
    CriticAgent,
    CriticRole,
    CriticReview,
    ProducerCriticResult,
    collaborate_with_critic
)
from caas_framework.agents.base import AgentPhase, AgentWorkResult


class TestCriticReview:
    """Test CriticReview dataclass"""

    def test_critic_review_creation(self):
        """Test creating a CriticReview"""
        review = CriticReview(
            approved=True,
            overall_score=8.5,
            strengths=["Clear design"],
            weaknesses=[],
            suggestions=["Add error handling"],
            critical_issues=[],
            feedback="Good work"
        )

        assert review.approved is True
        assert review.overall_score == 8.5
        assert len(review.strengths) == 1
        assert review.needs_revision is False

    def test_critic_review_needs_revision(self):
        """Test needs_revision property"""
        # Approved without issues
        review1 = CriticReview(approved=True, overall_score=8.0)
        assert review1.needs_revision is False

        # Not approved
        review2 = CriticReview(approved=False, overall_score=6.0)
        assert review2.needs_revision is True

        # Approved but has critical issues
        review3 = CriticReview(
            approved=True,
            overall_score=8.0,
            critical_issues=["Something wrong"]
        )
        assert review3.needs_revision is True


class TestCriticAgent:
    """Test Critic Agent"""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM plugin"""
        llm = MagicMock()
        llm.generate = AsyncMock()
        return llm

    @pytest.fixture
    def sample_llm_response_approved(self):
        """Sample LLM response for approved review"""
        return json.dumps({
            "dimension_scores": [
                {"dimension": "clarity", "score": 9.0, "reasoning": "Clear", "suggestions": []},
                {"dimension": "completeness", "score": 8.5, "reasoning": "Complete", "suggestions": []},
                {"dimension": "coherence", "score": 9.0, "reasoning": "Coherent", "suggestions": []}
            ],
            "overall_score": 8.8,
            "feedback": "Excellent work",
            "critical_issues": [],
            "warnings": []
        })

    @pytest.fixture
    def sample_llm_response_rejected(self):
        """Sample LLM response for rejected review"""
        return json.dumps({
            "dimension_scores": [
                {"dimension": "clarity", "score": 5.0, "reasoning": "Unclear", "suggestions": ["Clarify roles"]},
                {"dimension": "completeness", "score": 6.0, "reasoning": "Incomplete", "suggestions": ["Add missing"]},
            ],
            "overall_score": 5.5,
            "feedback": "Needs improvement",
            "critical_issues": ["Missing key elements"],
            "warnings": []
        })

    @pytest.mark.asyncio
    async def test_critic_agent_creation(self, mock_llm):
        """Test creating a Critic Agent"""
        critic = CriticAgent(
            llm_plugin=mock_llm,
            role=CriticRole.DESIGN_REVIEWER,
            approval_threshold=7.0
        )

        assert critic.llm == mock_llm
        assert critic.role == CriticRole.DESIGN_REVIEWER
        assert critic.approval_threshold == 7.0

    @pytest.mark.asyncio
    async def test_critic_approves_good_output(
        self,
        mock_llm,
        sample_llm_response_approved
    ):
        """Test critic approves high-quality output"""
        mock_llm.generate.return_value = sample_llm_response_approved

        critic = CriticAgent(mock_llm, approval_threshold=7.0)
        review = await critic.review(
            output={"agents": [], "tasks": []},
            phase=AgentPhase.DESIGN
        )

        assert isinstance(review, CriticReview)
        assert review.approved is True
        assert review.overall_score == 8.8
        assert len(review.strengths) > 0  # High scores become strengths

    @pytest.mark.asyncio
    async def test_critic_rejects_poor_output(
        self,
        mock_llm,
        sample_llm_response_rejected
    ):
        """Test critic rejects low-quality output"""
        mock_llm.generate.return_value = sample_llm_response_rejected

        critic = CriticAgent(mock_llm, approval_threshold=7.0)
        review = await critic.review(
            output={"agents": [], "tasks": []},
            phase=AgentPhase.DESIGN
        )

        assert review.approved is False
        assert review.overall_score == 5.5
        assert len(review.critical_issues) > 0
        assert len(review.suggestions) > 0

    @pytest.mark.asyncio
    async def test_critic_error_handling(self, mock_llm):
        """Test critic handles errors gracefully"""
        mock_llm.generate.side_effect = Exception("LLM error")

        critic = CriticAgent(mock_llm)
        review = await critic.review(
            output={"test": "data"},
            phase=AgentPhase.DESIGN
        )

        # Should return rejection on error
        assert review.approved is False
        assert review.overall_score == 0.0
        assert len(review.critical_issues) > 0


class TestProducerCriticPattern:
    """Test Producer-Critic Pattern"""

    @pytest.fixture
    def mock_producer(self):
        """Create mock producer agent"""
        producer = MagicMock()
        producer.work = AsyncMock()
        producer.refine = AsyncMock()
        return producer

    @pytest.fixture
    def mock_critic(self):
        """Create mock critic agent"""
        critic = MagicMock()
        critic.review = AsyncMock()
        return critic

    @pytest.mark.asyncio
    async def test_producer_critic_pattern_creation(self):
        """Test creating Producer-Critic pattern"""
        pattern = ProducerCriticPattern(
            max_iterations=3,
            timeout_per_iteration=120
        )

        assert pattern.max_iterations == 3
        assert pattern.timeout_per_iteration == 120

    @pytest.mark.asyncio
    async def test_first_iteration_approval(self, mock_producer, mock_critic):
        """Test approval on first iteration"""
        # Producer creates good output
        mock_producer.work.return_value = AgentWorkResult(
            success=True,
            output={"agents": [], "tasks": []},
            phase=AgentPhase.DESIGN,
            agent_name="test_producer",
            errors=[],
            duration=1.0
        )

        # Critic approves immediately
        mock_critic.review.return_value = CriticReview(
            approved=True,
            overall_score=9.0,
            feedback="Excellent"
        )

        pattern = ProducerCriticPattern(max_iterations=3)
        result = await pattern.produce_with_critique(
            producer=mock_producer,
            critic=mock_critic,
            requirement="Test requirement",
            phase=AgentPhase.DESIGN
        )

        # Should complete in 1 iteration
        assert result.success is True
        assert result.iterations == 1
        assert len(result.reviews) == 1
        assert result.reviews[0].approved is True
        assert mock_producer.work.called
        assert not mock_producer.refine.called  # No refinement needed

    @pytest.mark.asyncio
    async def test_multiple_iterations_until_approval(
        self,
        mock_producer,
        mock_critic
    ):
        """Test multiple refinement iterations"""
        # Producer work
        mock_producer.work.return_value = AgentWorkResult(
            success=True,
            output={"agents": [], "tasks": []},
            phase=AgentPhase.DESIGN,
            agent_name="test_producer",
            errors=[],
            duration=1.0
        )

        # Refinement
        mock_producer.refine.return_value = AgentWorkResult(
            success=True,
            output={"agents": ["fixed"], "tasks": []},
            phase=AgentPhase.DESIGN,
            agent_name="test_producer",
            errors=[],
            duration=1.0
        )

        # Critic rejects first, approves second
        mock_critic.review.side_effect = [
            CriticReview(approved=False, overall_score=6.0, suggestions=["Fix this"]),
            CriticReview(approved=True, overall_score=8.5, feedback="Good")
        ]

        pattern = ProducerCriticPattern(max_iterations=3)
        result = await pattern.produce_with_critique(
            producer=mock_producer,
            critic=mock_critic,
            requirement="Test requirement",
            phase=AgentPhase.DESIGN
        )

        # Should complete in 2 iterations
        assert result.success is True
        assert result.iterations == 2
        assert len(result.reviews) == 2
        assert result.reviews[0].approved is False
        assert result.reviews[1].approved is True
        assert mock_producer.refine.called

    @pytest.mark.asyncio
    async def test_max_iterations_reached(self, mock_producer, mock_critic):
        """Test max iterations without approval"""
        # Producer always succeeds
        mock_producer.work.return_value = AgentWorkResult(
            success=True,
            output={"agents": [], "tasks": []},
            phase=AgentPhase.DESIGN,
            agent_name="test_producer",
            errors=[],
            duration=1.0
        )

        mock_producer.refine.return_value = AgentWorkResult(
            success=True,
            output={"agents": [], "tasks": []},
            phase=AgentPhase.DESIGN,
            agent_name="test_producer",
            errors=[],
            duration=1.0
        )

        # Critic always rejects
        mock_critic.review.return_value = CriticReview(
            approved=False,
            overall_score=5.0,
            critical_issues=["Always wrong"]
        )

        pattern = ProducerCriticPattern(max_iterations=3)
        result = await pattern.produce_with_critique(
            producer=mock_producer,
            critic=mock_critic,
            requirement="Test requirement",
            phase=AgentPhase.DESIGN
        )

        # Should reach max iterations
        assert result.success is False
        assert result.iterations == 3
        assert all(not r.approved for r in result.reviews)

    @pytest.mark.asyncio
    async def test_producer_failure_stops_collaboration(
        self,
        mock_producer,
        mock_critic
    ):
        """Test collaboration stops if producer fails"""
        # Producer fails
        mock_producer.work.return_value = AgentWorkResult(
            success=False,
            output={},
            phase=AgentPhase.DESIGN,
            agent_name="test_producer",
            errors=["Producer error"],
            duration=1.0
        )

        pattern = ProducerCriticPattern(max_iterations=3)
        result = await pattern.produce_with_critique(
            producer=mock_producer,
            critic=mock_critic,
            requirement="Test requirement",
            phase=AgentPhase.DESIGN
        )

        # Should stop immediately
        assert result.success is False
        assert result.iterations == 0  # No reviews
        assert not mock_critic.review.called

    @pytest.mark.asyncio
    async def test_improvement_trajectory(self, mock_producer, mock_critic):
        """Test improvement trajectory tracking"""
        mock_producer.work.return_value = AgentWorkResult(
            success=True,
            output={},
            phase=AgentPhase.DESIGN,
            agent_name="test_producer",
            errors=[],
            duration=1.0
        )

        mock_producer.refine.return_value = AgentWorkResult(
            success=True,
            output={},
            phase=AgentPhase.DESIGN,
            agent_name="test_producer",
            errors=[],
            duration=1.0
        )

        # Scores improve over iterations
        mock_critic.review.side_effect = [
            CriticReview(approved=False, overall_score=6.0),
            CriticReview(approved=False, overall_score=7.5),
            CriticReview(approved=True, overall_score=8.5)
        ]

        pattern = ProducerCriticPattern(max_iterations=3)
        result = await pattern.produce_with_critique(
            producer=mock_producer,
            critic=mock_critic,
            requirement="Test requirement",
            phase=AgentPhase.DESIGN
        )

        # Check improvement trajectory
        trajectory = result.improvement_trajectory
        assert len(trajectory) == 3
        assert trajectory == [6.0, 7.5, 8.5]
        assert trajectory[-1] > trajectory[0]  # Improved


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
