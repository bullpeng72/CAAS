"""
Tests for Critic Agent Pattern

Tests the Producer-Critic pattern implementation.
"""

from typing import Any

import pytest

from caas_framework.agents.critic_pattern import (
    CriticAgentPattern,
    Critique,
    CritiqueResponse,
    SimpleSyncCriticPattern,
    create_critic_pattern,
)


# Mock Producer Agent (async)
class MockProducerAgent:
    """Mock producer that improves output based on critiques."""

    def __init__(self, initial_quality: int = 5):
        self.initial_quality = initial_quality
        self.execution_count = 0
        self.refinement_count = 0

    async def execute(self, task: str) -> dict:
        """Generate initial output."""
        self.execution_count += 1
        return {
            'task': task,
            'quality': self.initial_quality,
            'iteration': 0,
            'content': f"Initial solution for: {task}"
        }

    async def refine(
        self,
        task: str,
        previous_output: Any,
        critique: Critique
    ) -> dict:
        """Refine output based on critique."""
        self.refinement_count += 1

        # Simulate improvement
        new_quality = min(10, previous_output['quality'] + 2)

        return {
            'task': task,
            'quality': new_quality,
            'iteration': previous_output['iteration'] + 1,
            'content': f"Refined solution (v{previous_output['iteration'] + 1}) for: {task}",
            'addressed_issues': critique.issues[:],
            'applied_suggestions': critique.suggestions[:]
        }


# Mock Critic Agent (async)
class MockCriticAgent:
    """Mock critic that reviews output quality."""

    def __init__(self, approval_threshold: int = 8):
        self.approval_threshold = approval_threshold
        self.review_count = 0

    async def review(self, output: dict) -> Critique:
        """Review output and provide critique."""
        self.review_count += 1

        quality = output.get('quality', 0)
        approved = quality >= self.approval_threshold

        issues = []
        suggestions = []

        if quality < 6:
            issues.append("Quality is below acceptable level")
            suggestions.append("Improve overall quality")

        if quality < 8:
            issues.append("Some aspects need refinement")
            suggestions.append("Add more details")
            suggestions.append("Improve clarity")

        feedback = f"Quality level: {quality}/10"
        if approved:
            feedback += " - Approved!"
        else:
            feedback += f" - Needs improvement to reach {self.approval_threshold}"

        return Critique(
            approved=approved,
            score=quality,
            feedback=feedback,
            suggestions=suggestions,
            issues=issues
        )


# Sync versions for SimpleSyncCriticPattern tests
class SyncMockProducerAgent:
    """Synchronous mock producer."""

    def __init__(self, initial_quality: int = 5):
        self.initial_quality = initial_quality
        self.execution_count = 0
        self.refinement_count = 0

    def execute(self, task: str) -> dict:
        """Generate initial output."""
        self.execution_count += 1
        return {
            'task': task,
            'quality': self.initial_quality,
            'iteration': 0,
            'content': f"Initial solution for: {task}"
        }

    def refine(
        self,
        task: str,
        previous_output: Any,
        critique: Critique
    ) -> dict:
        """Refine output based on critique."""
        self.refinement_count += 1
        new_quality = min(10, previous_output['quality'] + 2)

        return {
            'task': task,
            'quality': new_quality,
            'iteration': previous_output['iteration'] + 1,
            'content': f"Refined solution (v{previous_output['iteration'] + 1}) for: {task}"
        }


class SyncMockCriticAgent:
    """Synchronous mock critic."""

    def __init__(self, approval_threshold: int = 8):
        self.approval_threshold = approval_threshold
        self.review_count = 0

    def review(self, output: dict) -> Critique:
        """Review output and provide critique."""
        self.review_count += 1

        quality = output.get('quality', 0)
        approved = quality >= self.approval_threshold

        issues = []
        suggestions = []

        if quality < 6:
            issues.append("Quality is below acceptable level")

        if quality < 8:
            suggestions.append("Improve overall quality")

        return Critique(
            approved=approved,
            score=quality,
            feedback=f"Quality: {quality}/10",
            suggestions=suggestions,
            issues=issues
        )


class TestCritique:
    """Test Critique dataclass."""

    def test_critique_creation(self):
        """Test creating a critique."""
        critique = Critique(
            approved=True,
            score=9,
            feedback="Excellent work",
            suggestions=["Add more tests"],
            issues=[],
            iteration=1
        )

        assert critique.approved is True
        assert critique.score == 9
        assert critique.feedback == "Excellent work"
        assert len(critique.suggestions) == 1
        assert critique.iteration == 1

    def test_critique_default_values(self):
        """Test critique default values."""
        critique = Critique(
            approved=False,
            score=5,
            feedback="Needs work"
        )

        assert critique.suggestions == []
        assert critique.issues == []
        assert critique.iteration == 0


class TestCritiqueResponse:
    """Test CritiqueResponse Pydantic model."""

    def test_critique_response_creation(self):
        """Test creating critique response."""
        response = CritiqueResponse(
            approved=True,
            score=8,
            feedback="Good quality",
            suggestions=["Add comments"],
            issues=[]
        )

        assert response.approved is True
        assert response.score == 8

    def test_critique_response_validation(self):
        """Test score validation."""
        with pytest.raises(Exception):  # Pydantic validation error
            CritiqueResponse(
                approved=False,
                score=11,  # > 10
                feedback="Invalid"
            )

        with pytest.raises(Exception):
            CritiqueResponse(
                approved=False,
                score=0,  # < 1
                feedback="Invalid"
            )


class TestCriticAgentPattern:
    """Test async CriticAgentPattern."""

    @pytest.mark.asyncio
    async def test_pattern_initialization(self):
        """Test creating critic pattern."""
        producer = MockProducerAgent()
        critic = MockCriticAgent()

        pattern = CriticAgentPattern(
            producer=producer,
            critic=critic,
            max_iterations=3
        )

        assert pattern.producer == producer
        assert pattern.critic == critic
        assert pattern.max_iterations == 3

    @pytest.mark.asyncio
    async def test_single_iteration_approval(self):
        """Test approval on first iteration."""
        # Producer starts with quality 9, critic approves at 8+
        producer = MockProducerAgent(initial_quality=9)
        critic = MockCriticAgent(approval_threshold=8)

        pattern = CriticAgentPattern(producer, critic, max_iterations=3)

        output, critiques = await pattern.produce_with_critique(
            "Create a simple function",
            verbose=False
        )

        # Should approve on first iteration
        assert len(critiques) == 1
        assert critiques[0].approved is True
        assert critiques[0].score == 9
        assert producer.execution_count == 1
        assert producer.refinement_count == 0

    @pytest.mark.asyncio
    async def test_multiple_iterations_until_approval(self):
        """Test iterative improvement until approval."""
        # Producer starts at 5, improves by 2 each iteration
        # Iteration 1: 5 (not approved)
        # Iteration 2: 7 (not approved)
        # Iteration 3: 9 (approved)
        producer = MockProducerAgent(initial_quality=5)
        critic = MockCriticAgent(approval_threshold=8)

        pattern = CriticAgentPattern(
            producer,
            critic,
            max_iterations=5,
            min_score_threshold=10  # Prevent early stopping at score 7
        )

        output, critiques = await pattern.produce_with_critique(
            "Create a complex system",
            verbose=False
        )

        # Should take 3 iterations
        assert len(critiques) == 3
        assert critiques[0].score == 5
        assert critiques[1].score == 7
        assert critiques[2].score == 9
        assert critiques[2].approved is True

        # Producer should refine twice (after 1st and 2nd critique)
        assert producer.refinement_count == 2

    @pytest.mark.asyncio
    async def test_max_iterations_reached(self):
        """Test when max iterations reached without approval."""
        # Producer starts at 3, can't reach 8 in 2 iterations
        producer = MockProducerAgent(initial_quality=3)
        critic = MockCriticAgent(approval_threshold=8)

        pattern = CriticAgentPattern(producer, critic, max_iterations=2)

        output, critiques = await pattern.produce_with_critique(
            "Create something",
            verbose=False
        )

        # Should stop at max iterations
        assert len(critiques) == 2
        assert critiques[-1].approved is False
        assert critiques[-1].score < 8

    @pytest.mark.asyncio
    async def test_score_threshold_approval(self):
        """Test approval via score threshold."""
        # Producer reaches score 7, which meets min_score_threshold
        producer = MockProducerAgent(initial_quality=5)
        critic = MockCriticAgent(approval_threshold=10)  # Never approves

        pattern = CriticAgentPattern(
            producer,
            critic,
            max_iterations=5,
            min_score_threshold=7  # But auto-approve at 7+
        )

        output, critiques = await pattern.produce_with_critique(
            "Create something",
            verbose=False
        )

        # Should stop when score reaches 7
        assert len(critiques) == 2  # Iterations: 5->7
        assert critiques[-1].score >= 7
        # Critic didn't approve but score threshold met
        assert critiques[-1].approved is False

    @pytest.mark.asyncio
    async def test_get_improvement_summary(self):
        """Test improvement summary generation."""
        producer = MockProducerAgent(initial_quality=4)
        critic = MockCriticAgent(approval_threshold=8)

        pattern = CriticAgentPattern(producer, critic, max_iterations=5)

        output, critiques = await pattern.produce_with_critique(
            "Create something",
            verbose=False
        )

        summary = pattern.get_improvement_summary(critiques)

        assert summary['iterations'] > 0
        assert summary['initial_score'] == 4
        assert summary['final_score'] > 4
        assert summary['improvement'] > 0
        assert 'improvement_percent' in summary
        assert 'total_issues_found' in summary

    @pytest.mark.asyncio
    async def test_empty_critiques_summary(self):
        """Test summary with no critiques."""
        producer = MockProducerAgent()
        critic = MockCriticAgent()

        pattern = CriticAgentPattern(producer, critic)

        summary = pattern.get_improvement_summary([])

        assert summary['iterations'] == 0
        assert summary['initial_score'] == 0
        assert summary['final_score'] == 0
        assert summary['improvement'] == 0


class TestSimpleSyncCriticPattern:
    """Test synchronous SimpleSyncCriticPattern."""

    def test_sync_pattern_initialization(self):
        """Test creating sync critic pattern."""
        producer = SyncMockProducerAgent()
        critic = SyncMockCriticAgent()

        pattern = SimpleSyncCriticPattern(
            producer=producer,
            critic=critic,
            max_iterations=3
        )

        assert pattern.producer == producer
        assert pattern.critic == critic

    def test_sync_single_iteration_approval(self):
        """Test sync approval on first iteration."""
        producer = SyncMockProducerAgent(initial_quality=9)
        critic = SyncMockCriticAgent(approval_threshold=8)

        pattern = SimpleSyncCriticPattern(producer, critic)

        output, critiques = pattern.produce_with_critique(
            "Create a function",
            verbose=False
        )

        assert len(critiques) == 1
        assert critiques[0].approved is True
        assert producer.execution_count == 1

    def test_sync_multiple_iterations(self):
        """Test sync iterative improvement."""
        producer = SyncMockProducerAgent(initial_quality=5)
        critic = SyncMockCriticAgent(approval_threshold=8)

        pattern = SimpleSyncCriticPattern(producer, critic, max_iterations=5)

        output, critiques = pattern.produce_with_critique(
            "Create something",
            verbose=False
        )

        # Should improve over iterations
        assert len(critiques) >= 2
        assert critiques[-1].score > critiques[0].score

    def test_sync_max_iterations(self):
        """Test sync max iterations."""
        producer = SyncMockProducerAgent(initial_quality=2)
        critic = SyncMockCriticAgent(approval_threshold=8)

        pattern = SimpleSyncCriticPattern(producer, critic, max_iterations=2)

        output, critiques = pattern.produce_with_critique(
            "Create something",
            verbose=False
        )

        assert len(critiques) == 2

    def test_sync_get_improvement_summary(self):
        """Test sync improvement summary."""
        producer = SyncMockProducerAgent(initial_quality=4)
        critic = SyncMockCriticAgent(approval_threshold=8)

        pattern = SimpleSyncCriticPattern(producer, critic, max_iterations=5)

        output, critiques = pattern.produce_with_critique(
            "Create something",
            verbose=False
        )

        summary = pattern.get_improvement_summary(critiques)

        assert summary['iterations'] > 0
        assert summary['final_score'] >= summary['initial_score']


class TestFactoryFunction:
    """Test create_critic_pattern factory function."""

    @pytest.mark.asyncio
    async def test_create_async_pattern(self):
        """Test creating async pattern via factory."""
        producer = MockProducerAgent()
        critic = MockCriticAgent()

        pattern = create_critic_pattern(
            producer=producer,
            critic=critic,
            async_mode=True
        )

        assert isinstance(pattern, CriticAgentPattern)

    def test_create_sync_pattern(self):
        """Test creating sync pattern via factory."""
        producer = SyncMockProducerAgent()
        critic = SyncMockCriticAgent()

        pattern = create_critic_pattern(
            producer=producer,
            critic=critic,
            async_mode=False
        )

        assert isinstance(pattern, SimpleSyncCriticPattern)


class TestEdgeCases:
    """Test edge cases."""

    @pytest.mark.asyncio
    async def test_empty_task(self):
        """Test with empty task string."""
        producer = MockProducerAgent()
        critic = MockCriticAgent()

        pattern = CriticAgentPattern(producer, critic)

        output, critiques = await pattern.produce_with_critique(
            "",
            verbose=False
        )

        # Should still work
        assert len(critiques) > 0

    @pytest.mark.asyncio
    async def test_very_low_initial_quality(self):
        """Test with very low initial quality."""
        producer = MockProducerAgent(initial_quality=1)
        critic = MockCriticAgent(approval_threshold=8)

        pattern = CriticAgentPattern(producer, critic, max_iterations=10)

        output, critiques = await pattern.produce_with_critique(
            "Create something",
            verbose=False
        )

        # Should eventually approve or hit max iterations
        assert len(critiques) > 0

    @pytest.mark.asyncio
    async def test_perfect_initial_quality(self):
        """Test with perfect initial quality."""
        producer = MockProducerAgent(initial_quality=10)
        critic = MockCriticAgent(approval_threshold=8)

        pattern = CriticAgentPattern(producer, critic)

        output, critiques = await pattern.produce_with_critique(
            "Create something",
            verbose=False
        )

        # Should approve immediately
        assert len(critiques) == 1
        assert critiques[0].approved is True

    def test_sync_edge_cases(self):
        """Test sync pattern with edge cases."""
        producer = SyncMockProducerAgent(initial_quality=1)
        critic = SyncMockCriticAgent(approval_threshold=10)

        pattern = SimpleSyncCriticPattern(producer, critic, max_iterations=3)

        output, critiques = pattern.produce_with_critique(
            "Difficult task",
            verbose=False
        )

        # Should reach max iterations
        assert len(critiques) == 3


class TestIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_improvement(self):
        """Test complete producer-critic workflow."""
        producer = MockProducerAgent(initial_quality=5)
        critic = MockCriticAgent(approval_threshold=8)

        pattern = CriticAgentPattern(
            producer=producer,
            critic=critic,
            max_iterations=5,
            min_score_threshold=7
        )

        # Execute pattern
        output, critiques = await pattern.produce_with_critique(
            "Design a blog system with posts and comments",
            verbose=False
        )

        # Verify improvement
        assert len(critiques) >= 1
        assert critiques[-1].score >= critiques[0].score

        # Generate summary
        summary = pattern.get_improvement_summary(critiques)

        assert summary['iterations'] == len(critiques)
        assert summary['improvement'] >= 0

        # Verify output contains refinements
        if len(critiques) > 1:
            assert 'iteration' in output
            assert output['iteration'] > 0

    @pytest.mark.asyncio
    async def test_critic_catches_issues(self):
        """Test that critic properly identifies issues."""
        producer = MockProducerAgent(initial_quality=3)
        critic = MockCriticAgent(approval_threshold=8)

        pattern = CriticAgentPattern(producer, critic, max_iterations=5)

        output, critiques = await pattern.produce_with_critique(
            "Create something",
            verbose=False
        )

        # First critique should have issues
        assert len(critiques[0].issues) > 0
        assert len(critiques[0].suggestions) > 0

    @pytest.mark.asyncio
    async def test_producer_addresses_critique(self):
        """Test that producer addresses critique issues."""
        producer = MockProducerAgent(initial_quality=4)
        critic = MockCriticAgent(approval_threshold=8)

        pattern = CriticAgentPattern(producer, critic, max_iterations=5)

        output, critiques = await pattern.produce_with_critique(
            "Create something complex",
            verbose=False
        )

        # If multiple iterations, verify refinement happened
        if len(critiques) > 1:
            assert 'addressed_issues' in output
            assert 'applied_suggestions' in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
