"""
Tests for LLM-as-a-Judge Pattern (Validation)

Tests the LLM-based quality evaluation system for agent phase outputs.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from caas_framework.agents.base import AgentPhase
from caas_framework.validation.llm_judge import (
    DimensionScore,
    EvaluationDimension,
    EvaluationResult,
    LLMJudge,
    evaluate_with_llm_judge,
)


class TestLLMJudgeValidation:
    """Test LLM Judge quality evaluation for phase outputs"""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM plugin"""
        llm = MagicMock()
        llm.generate = AsyncMock()
        return llm

    @pytest.fixture
    def sample_design_output(self):
        """Sample design phase output"""
        return {
            "agents": [
                {
                    "id": "user_agent",
                    "role": "User Management",
                    "goal": "Handle user registration and authentication",
                    "backstory": "Expert in user management",
                    "tools": ["database", "auth"]
                }
            ],
            "tasks": [
                {
                    "id": "register_user",
                    "description": "Register new user",
                    "expected_output": "User registration confirmation",
                    "agent": "user_agent"
                }
            ]
        }

    @pytest.fixture
    def sample_llm_response_approved(self):
        """Sample LLM response for approved output"""
        return json.dumps({
            "dimension_scores": [
                {
                    "dimension": "clarity",
                    "score": 9.0,
                    "reasoning": "Agent roles are clearly defined and well-scoped",
                    "suggestions": []
                },
                {
                    "dimension": "completeness",
                    "score": 8.5,
                    "reasoning": "All necessary agents and tasks are present",
                    "suggestions": ["Consider adding error handling tasks"]
                },
                {
                    "dimension": "coherence",
                    "score": 9.0,
                    "reasoning": "Task dependencies are logical and well-structured",
                    "suggestions": []
                },
                {
                    "dimension": "appropriateness",
                    "score": 8.5,
                    "reasoning": "Tools are well-matched to agent roles",
                    "suggestions": []
                },
                {
                    "dimension": "correctness",
                    "score": 9.0,
                    "reasoning": "No logical errors detected",
                    "suggestions": []
                }
            ],
            "overall_score": 8.8,
            "feedback": "Excellent design with clear agent roles and logical task structure. Minor improvements could include additional error handling tasks.",
            "critical_issues": [],
            "warnings": []
        })

    @pytest.fixture
    def sample_llm_response_rejected(self):
        """Sample LLM response for rejected output"""
        return json.dumps({
            "dimension_scores": [
                {
                    "dimension": "clarity",
                    "score": 5.0,
                    "reasoning": "Agent roles overlap significantly",
                    "suggestions": ["Separate concerns", "Define clear boundaries"]
                },
                {
                    "dimension": "completeness",
                    "score": 6.0,
                    "reasoning": "Missing critical error handling",
                    "suggestions": ["Add error handling tasks"]
                },
                {
                    "dimension": "coherence",
                    "score": 4.0,
                    "reasoning": "Task dependencies create cycles",
                    "suggestions": ["Remove circular dependencies"]
                }
            ],
            "overall_score": 5.0,
            "feedback": "Design needs significant improvements. Major issues with role clarity and task dependencies.",
            "critical_issues": [
                "Circular task dependencies detected",
                "Agent role overlap will cause conflicts"
            ],
            "warnings": [
                "Consider restructuring agent responsibilities"
            ]
        })

    @pytest.mark.asyncio
    async def test_llm_judge_creation(self, mock_llm):
        """Test that LLM Judge can be created"""
        judge = LLMJudge(
            llm_plugin=mock_llm,
            approval_threshold=7.0
        )

        assert judge.llm == mock_llm
        assert judge.approval_threshold == 7.0
        assert judge.logger is not None

    @pytest.mark.asyncio
    async def test_llm_judge_approved_evaluation(
        self,
        mock_llm,
        sample_design_output,
        sample_llm_response_approved
    ):
        """Test LLM Judge approves high-quality output"""
        mock_llm.generate.return_value = sample_llm_response_approved

        judge = LLMJudge(mock_llm, approval_threshold=7.0)
        result = await judge.evaluate_quality(
            output=sample_design_output,
            phase=AgentPhase.DESIGN
        )

        # Verify evaluation
        assert isinstance(result, EvaluationResult)
        assert result.phase == AgentPhase.DESIGN
        assert result.overall_score == 8.8
        assert result.approved is True  # Score >= 7.0
        assert len(result.dimension_scores) == 5
        assert len(result.critical_issues) == 0

        # Verify LLM was called
        assert mock_llm.generate.called
        call_args = mock_llm.generate.call_args
        assert "Evaluate" in call_args.kwargs["prompt"]
        assert call_args.kwargs["temperature"] == 0.3  # Low temp for consistency

    @pytest.mark.asyncio
    async def test_llm_judge_rejected_evaluation(
        self,
        mock_llm,
        sample_design_output,
        sample_llm_response_rejected
    ):
        """Test LLM Judge rejects low-quality output"""
        mock_llm.generate.return_value = sample_llm_response_rejected

        judge = LLMJudge(mock_llm, approval_threshold=7.0)
        result = await judge.evaluate_quality(
            output=sample_design_output,
            phase=AgentPhase.DESIGN
        )

        # Verify rejection
        assert result.overall_score == 5.0
        assert result.approved is False  # Score < 7.0
        assert len(result.critical_issues) == 2
        assert len(result.warnings) == 1
        assert result.needs_improvement is True

        # Verify low scores have suggestions
        low_scores = [s for s in result.dimension_scores if s.score < 7.0]
        assert len(low_scores) == 3
        for score in low_scores:
            assert len(score.suggestions) > 0

    @pytest.mark.asyncio
    async def test_llm_judge_dimension_scores(
        self,
        mock_llm,
        sample_design_output,
        sample_llm_response_approved
    ):
        """Test LLM Judge dimension scoring"""
        mock_llm.generate.return_value = sample_llm_response_approved

        judge = LLMJudge(mock_llm)
        result = await judge.evaluate_quality(
            output=sample_design_output,
            phase=AgentPhase.DESIGN
        )

        # Verify dimension scores
        assert len(result.dimension_scores) == 5

        dimensions = {s.dimension for s in result.dimension_scores}
        assert EvaluationDimension.CLARITY in dimensions
        assert EvaluationDimension.COMPLETENESS in dimensions
        assert EvaluationDimension.COHERENCE in dimensions
        assert EvaluationDimension.APPROPRIATENESS in dimensions
        assert EvaluationDimension.CORRECTNESS in dimensions

        # Verify each score has reasoning
        for score in result.dimension_scores:
            assert isinstance(score, DimensionScore)
            assert 0.0 <= score.score <= 10.0
            assert len(score.reasoning) > 0

    @pytest.mark.asyncio
    async def test_llm_judge_with_context(self, mock_llm, sample_design_output):
        """Test LLM Judge with context (requirement)"""
        mock_llm.generate.return_value = json.dumps({
            "dimension_scores": [],
            "overall_score": 8.0,
            "feedback": "Good",
            "critical_issues": [],
            "warnings": []
        })

        judge = LLMJudge(mock_llm)
        context = {
            "requirement": "Build a user management system"
        }

        result = await judge.evaluate_quality(
            output=sample_design_output,
            phase=AgentPhase.DESIGN,
            context=context
        )

        # Verify context was included in prompt
        call_args = mock_llm.generate.call_args
        prompt = call_args.kwargs["prompt"]
        assert "Build a user management system" in prompt
        assert "Original Requirement" in prompt

    @pytest.mark.asyncio
    async def test_llm_judge_phase_specific_criteria(self, mock_llm):
        """Test that each phase has specific criteria"""
        judge = LLMJudge(mock_llm)

        # Test criteria methods exist for all phases
        assert judge._get_discovery_criteria() is not None
        assert judge._get_architecture_criteria() is not None
        assert judge._get_design_criteria() is not None
        assert judge._get_delivery_criteria() is not None
        assert judge._get_qa_criteria() is not None

        # Verify Design phase has 5 criteria
        design_criteria = judge._get_design_criteria()
        assert len(design_criteria) == 5

        # Verify all criteria have required fields
        for criterion in design_criteria:
            assert "dimension" in criterion
            assert "description" in criterion

    @pytest.mark.asyncio
    async def test_evaluate_with_llm_judge_convenience(
        self,
        mock_llm,
        sample_design_output,
        sample_llm_response_approved
    ):
        """Test convenience function"""
        mock_llm.generate.return_value = sample_llm_response_approved

        result = await evaluate_with_llm_judge(
            output=sample_design_output,
            phase=AgentPhase.DESIGN,
            llm_plugin=mock_llm,
            approval_threshold=8.0
        )

        assert isinstance(result, EvaluationResult)
        assert result.overall_score == 8.8
        assert result.approved is True  # 8.8 >= 8.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
