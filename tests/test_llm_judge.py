"""
Tests for LLM-as-a-Judge Quality Evaluation

Tests the LLM Judge system that evaluates generated code quality.
"""

import json

import pytest

from caas_framework.quality.llm_judge import (
    CodeQualityCriteria,
    CriterionScore,
    EvaluationCategory,
    EvaluationResult,
    LLMJudge,
)


# Mock LLM for testing
class MockLLM:
    """Mock LLM that returns predefined evaluation"""

    def __init__(self, return_data=None):
        self.return_data = return_data or self._default_evaluation()

    def _default_evaluation(self):
        """Default mock evaluation"""
        return {
            "criteria_scores": [
                {
                    "criterion": "CrewAI framework usage is correct",
                    "score": 9.0,
                    "reasoning": "Correct imports and proper usage",
                    "suggestions": "None"
                },
                {
                    "criterion": "Agent definitions are complete and clear",
                    "score": 8.5,
                    "reasoning": "All required fields present",
                    "suggestions": "Add more detailed backstories"
                },
                {
                    "criterion": "Task definitions have clear objectives",
                    "score": 9.0,
                    "reasoning": "Clear descriptions",
                    "suggestions": "None"
                },
                {
                    "criterion": "Code is readable and well-structured",
                    "score": 8.0,
                    "reasoning": "Well-formatted",
                    "suggestions": "Add comments"
                },
                {
                    "criterion": "No security vulnerabilities",
                    "score": 10.0,
                    "reasoning": "No issues detected",
                    "suggestions": "None"
                },
                {
                    "criterion": "Follows Python best practices",
                    "score": 8.5,
                    "reasoning": "PEP 8 compliant",
                    "suggestions": "None"
                },
                {
                    "criterion": "Code is maintainable",
                    "score": 8.0,
                    "reasoning": "Easy to understand",
                    "suggestions": "Add docstrings"
                },
                {
                    "criterion": "Efficient resource usage",
                    "score": 9.0,
                    "reasoning": "No performance issues",
                    "suggestions": "None"
                }
            ],
            "issues": [],
            "recommendations": ["Add type hints", "Add docstrings"],
            "summary": "High-quality code with minor improvements suggested."
        }

    async def ainvoke(self, messages, **kwargs):
        """Return mock evaluation response"""

        class MockResponse:
            def __init__(self, content):
                self.content = json.dumps(content)

        return MockResponse(self.return_data)


class TestCodeQualityCriteria:
    """Test code quality criteria definitions"""

    def test_get_crewai_code_criteria(self):
        """Test CrewAI code criteria"""
        criteria = CodeQualityCriteria.get_crewai_code_criteria()

        assert len(criteria) > 0
        assert all("criterion" in c for c in criteria)
        assert all("category" in c for c in criteria)
        assert all("weight" in c for c in criteria)

    def test_criteria_categories(self):
        """Test that criteria cover all important categories"""
        criteria = CodeQualityCriteria.get_crewai_code_criteria()

        categories = set(c["category"] for c in criteria)

        # Should have multiple categories
        assert EvaluationCategory.CORRECTNESS in categories
        assert EvaluationCategory.SECURITY in categories
        assert EvaluationCategory.READABILITY in categories

    def test_criteria_weights(self):
        """Test that criteria have reasonable weights"""
        criteria = CodeQualityCriteria.get_crewai_code_criteria()

        for c in criteria:
            weight = c["weight"]
            assert 0.1 <= weight <= 3.0, f"Weight {weight} out of reasonable range"


class TestCriterionScore:
    """Test CriterionScore dataclass"""

    def test_criterion_score_creation(self):
        """Test creating a CriterionScore"""
        score = CriterionScore(
            criterion="Test criterion",
            category=EvaluationCategory.CORRECTNESS,
            score=8.5,
            reasoning="Good implementation",
            suggestions="Add tests",
            weight=1.5
        )

        assert score.criterion == "Test criterion"
        assert score.category == EvaluationCategory.CORRECTNESS
        assert score.score == 8.5
        assert score.weight == 1.5


class TestEvaluationResult:
    """Test EvaluationResult dataclass"""

    def test_evaluation_result_creation(self):
        """Test creating an EvaluationResult"""
        criteria_scores = [
            CriterionScore(
                criterion="Test 1",
                category=EvaluationCategory.CORRECTNESS,
                score=8.0,
                reasoning="Good",
                suggestions="None",
                weight=1.0
            ),
            CriterionScore(
                criterion="Test 2",
                category=EvaluationCategory.SECURITY,
                score=9.0,
                reasoning="Excellent",
                suggestions="None",
                weight=1.5
            )
        ]

        result = EvaluationResult(
            overall_score=8.5,
            criteria_scores=criteria_scores,
            passed=True,
            summary="Good quality",
            issues=[],
            recommendations=["Add docs"]
        )

        assert result.overall_score == 8.5
        assert result.passed is True
        assert len(result.criteria_scores) == 2

    def test_get_category_score(self):
        """Test getting score for a specific category"""
        criteria_scores = [
            CriterionScore("C1", EvaluationCategory.CORRECTNESS, 8.0, "Good", "None"),
            CriterionScore("C2", EvaluationCategory.CORRECTNESS, 9.0, "Great", "None"),
            CriterionScore("C3", EvaluationCategory.SECURITY, 10.0, "Perfect", "None")
        ]

        result = EvaluationResult(
            overall_score=8.5,
            criteria_scores=criteria_scores,
            passed=True,
            summary="Test",
            issues=[],
            recommendations=[]
        )

        # Average of 8.0 and 9.0
        correctness_score = result.get_category_score(EvaluationCategory.CORRECTNESS)
        assert correctness_score == 8.5

        # Only one security criterion
        security_score = result.get_category_score(EvaluationCategory.SECURITY)
        assert security_score == 10.0

    def test_get_weighted_score(self):
        """Test calculating weighted average score"""
        criteria_scores = [
            CriterionScore("C1", EvaluationCategory.CORRECTNESS, 8.0, "Good", "None", weight=2.0),
            CriterionScore("C2", EvaluationCategory.SECURITY, 10.0, "Perfect", "None", weight=1.0)
        ]

        result = EvaluationResult(
            overall_score=8.5,
            criteria_scores=criteria_scores,
            passed=True,
            summary="Test",
            issues=[],
            recommendations=[]
        )

        # (8.0 * 2.0 + 10.0 * 1.0) / (2.0 + 1.0) = 26 / 3 = 8.67
        weighted_score = result.get_weighted_score()
        assert abs(weighted_score - 8.67) < 0.01


class TestLLMJudge:
    """Test LLM Judge evaluation engine"""

    @pytest.mark.asyncio
    async def test_llm_judge_creation(self):
        """Test creating LLM Judge"""
        mock_llm = MockLLM()
        judge = LLMJudge(llm_plugin=mock_llm, passing_score=7.0)

        assert judge.llm == mock_llm
        assert judge.passing_score == 7.0

    @pytest.mark.asyncio
    async def test_evaluate_code_quality_basic(self):
        """Test basic code quality evaluation"""
        mock_llm = MockLLM()
        judge = LLMJudge(llm_plugin=mock_llm)

        code_files = {
            "main.py": "from crewai import Crew\n\ndef main():\n    pass"
        }

        result = await judge.evaluate_code_quality(code_files)

        assert result is not None
        assert result.overall_score > 0
        assert len(result.criteria_scores) > 0
        assert result.passed is not None

    @pytest.mark.asyncio
    async def test_evaluate_code_quality_with_context(self):
        """Test evaluation with additional context"""
        mock_llm = MockLLM()
        judge = LLMJudge(llm_plugin=mock_llm)

        code_files = {"main.py": "from crewai import Crew"}
        context = {
            "agents_count": 2,
            "tasks_count": 3
        }

        result = await judge.evaluate_code_quality(code_files, context)

        assert result is not None
        assert result.overall_score > 0

    @pytest.mark.asyncio
    async def test_passing_threshold(self):
        """Test that passing_score threshold works"""
        # High scores - should pass
        high_score_data = MockLLM()._default_evaluation()
        mock_llm_pass = MockLLM(return_data=high_score_data)
        judge_pass = LLMJudge(llm_plugin=mock_llm_pass, passing_score=7.0)

        result_pass = await judge_pass.evaluate_code_quality({"main.py": "code"})
        assert result_pass.passed is True

        # Low scores - should fail
        low_score_data = {
            **high_score_data,
            "criteria_scores": [
                {**s, "score": 5.0} for s in high_score_data["criteria_scores"]
            ]
        }
        mock_llm_fail = MockLLM(return_data=low_score_data)
        judge_fail = LLMJudge(llm_plugin=mock_llm_fail, passing_score=7.0)

        result_fail = await judge_fail.evaluate_code_quality({"main.py": "code"})
        assert result_fail.passed is False

    @pytest.mark.asyncio
    async def test_evaluation_result_structure(self):
        """Test that evaluation result has correct structure"""
        mock_llm = MockLLM()
        judge = LLMJudge(llm_plugin=mock_llm)

        result = await judge.evaluate_code_quality({"main.py": "code"})

        # Check required fields
        assert hasattr(result, 'overall_score')
        assert hasattr(result, 'criteria_scores')
        assert hasattr(result, 'passed')
        assert hasattr(result, 'summary')
        assert hasattr(result, 'issues')
        assert hasattr(result, 'recommendations')

        # Check types
        assert isinstance(result.overall_score, float)
        assert isinstance(result.criteria_scores, list)
        assert isinstance(result.passed, bool)
        assert isinstance(result.summary, str)
        assert isinstance(result.issues, list)
        assert isinstance(result.recommendations, list)

    @pytest.mark.asyncio
    async def test_criteria_score_structure(self):
        """Test that each criterion score has correct structure"""
        mock_llm = MockLLM()
        judge = LLMJudge(llm_plugin=mock_llm)

        result = await judge.evaluate_code_quality({"main.py": "code"})

        assert len(result.criteria_scores) > 0

        for cs in result.criteria_scores:
            assert isinstance(cs, CriterionScore)
            assert isinstance(cs.criterion, str)
            assert isinstance(cs.category, EvaluationCategory)
            assert isinstance(cs.score, float)
            assert 0 <= cs.score <= 10
            assert isinstance(cs.reasoning, str)
            assert isinstance(cs.suggestions, str)
            assert isinstance(cs.weight, float)
            assert cs.weight > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
