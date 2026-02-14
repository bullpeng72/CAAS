"""
Tests for Party Mode Coordinator (CAAS-E Week 2)

Tests the multi-agent collaborative review system.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from caas_framework.agents.party_mode_coordinator import (
    PartyModeCoordinator,
    ReviewPerspective,
    ReviewDimension,
    ReviewScore,
    AgentReview,
    PartyModeResult
)


class TestPartyModeCoordinator:
    """Test suite for PartyModeCoordinator"""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM plugin"""
        llm = Mock()
        llm.ainvoke = AsyncMock()
        return llm

    @pytest.fixture
    def coordinator(self, mock_llm):
        """Create PartyModeCoordinator instance"""
        return PartyModeCoordinator(
            llm_plugin=mock_llm,
            party_size=5,
            approval_threshold=6.0,
            consensus_threshold=0.6  # 3/5 = 60%
        )

    @pytest.mark.asyncio
    async def test_review_with_high_approval(self, coordinator, mock_llm):
        """Test review where majority approves (>60%)"""
        # Mock LLM responses (4/5 approve with scores >= 6.0)
        mock_responses = [
            # Agent 1: Approve (8.0)
            Mock(content='''{
                "dimension_scores": [
                    {"dimension": "completeness", "score": 8.0, "reasoning": "Good"},
                    {"dimension": "feasibility", "score": 8.0, "reasoning": "Good"},
                    {"dimension": "scalability", "score": 8.0, "reasoning": "Good"},
                    {"dimension": "maintainability", "score": 8.0, "reasoning": "Good"},
                    {"dimension": "security", "score": 8.0, "reasoning": "Good"}
                ],
                "feedback": "Looks good overall",
                "critical_issues": [],
                "warnings": []
            }'''),
            # Agent 2: Approve (7.0)
            Mock(content='''{
                "dimension_scores": [
                    {"dimension": "completeness", "score": 7.0, "reasoning": "Acceptable"},
                    {"dimension": "feasibility", "score": 7.0, "reasoning": "Acceptable"},
                    {"dimension": "scalability", "score": 7.0, "reasoning": "Acceptable"},
                    {"dimension": "maintainability", "score": 7.0, "reasoning": "Acceptable"},
                    {"dimension": "security", "score": 7.0, "reasoning": "Acceptable"}
                ],
                "feedback": "Acceptable quality",
                "critical_issues": [],
                "warnings": ["Minor concern"]
            }'''),
            # Agent 3: Approve (9.0)
            Mock(content='''{
                "dimension_scores": [
                    {"dimension": "completeness", "score": 9.0, "reasoning": "Excellent"},
                    {"dimension": "feasibility", "score": 9.0, "reasoning": "Excellent"},
                    {"dimension": "scalability", "score": 9.0, "reasoning": "Excellent"},
                    {"dimension": "maintainability", "score": 9.0, "reasoning": "Excellent"},
                    {"dimension": "security", "score": 9.0, "reasoning": "Excellent"}
                ],
                "feedback": "Excellent design",
                "critical_issues": [],
                "warnings": []
            }'''),
            # Agent 4: Reject (5.0)
            Mock(content='''{
                "dimension_scores": [
                    {"dimension": "completeness", "score": 5.0, "reasoning": "Missing elements"},
                    {"dimension": "feasibility", "score": 5.0, "reasoning": "Challenges"},
                    {"dimension": "scalability", "score": 5.0, "reasoning": "Concerns"},
                    {"dimension": "maintainability", "score": 5.0, "reasoning": "Issues"},
                    {"dimension": "security", "score": 5.0, "reasoning": "Risks"}
                ],
                "feedback": "Needs improvement",
                "critical_issues": ["Issue 1"],
                "warnings": []
            }'''),
            # Agent 5: Approve (6.5)
            Mock(content='''{
                "dimension_scores": [
                    {"dimension": "completeness", "score": 6.5, "reasoning": "Adequate"},
                    {"dimension": "feasibility", "score": 6.5, "reasoning": "Adequate"},
                    {"dimension": "scalability", "score": 6.5, "reasoning": "Adequate"},
                    {"dimension": "maintainability", "score": 6.5, "reasoning": "Adequate"},
                    {"dimension": "security", "score": 6.5, "reasoning": "Adequate"}
                ],
                "feedback": "Adequate quality",
                "critical_issues": [],
                "warnings": []
            }''')
        ]

        mock_llm.ainvoke.side_effect = mock_responses

        # Run review
        result = await coordinator.review_artifact(
            artifact={"test": "artifact"},
            artifact_type="architecture",
            phase="phase_2"
        )

        # Assert: 4/5 approved = 80% >= 60% threshold
        assert result.approved is True
        assert result.approval_rate == 0.8  # 4/5
        assert len(result.reviews) == 5
        assert result.consensus_score > 6.0

    @pytest.mark.asyncio
    async def test_review_with_low_approval(self, coordinator, mock_llm):
        """Test review where majority rejects (<60%)"""
        # Mock LLM responses (2/5 approve with scores >= 6.0)
        mock_responses = [
            # Agent 1: Approve (7.0)
            Mock(content='''{
                "dimension_scores": [
                    {"dimension": "completeness", "score": 7.0, "reasoning": "Good"},
                    {"dimension": "feasibility", "score": 7.0, "reasoning": "Good"},
                    {"dimension": "scalability", "score": 7.0, "reasoning": "Good"},
                    {"dimension": "maintainability", "score": 7.0, "reasoning": "Good"},
                    {"dimension": "security", "score": 7.0, "reasoning": "Good"}
                ],
                "feedback": "Acceptable",
                "critical_issues": [],
                "warnings": []
            }'''),
            # Agent 2: Reject (4.0)
            Mock(content='''{
                "dimension_scores": [
                    {"dimension": "completeness", "score": 4.0, "reasoning": "Incomplete"},
                    {"dimension": "feasibility", "score": 4.0, "reasoning": "Difficult"},
                    {"dimension": "scalability", "score": 4.0, "reasoning": "Limited"},
                    {"dimension": "maintainability", "score": 4.0, "reasoning": "Poor"},
                    {"dimension": "security", "score": 4.0, "reasoning": "Vulnerable"}
                ],
                "feedback": "Major issues",
                "critical_issues": ["Critical issue 1", "Critical issue 2"],
                "warnings": []
            }'''),
            # Agent 3: Reject (3.0)
            Mock(content='''{
                "dimension_scores": [
                    {"dimension": "completeness", "score": 3.0, "reasoning": "Major gaps"},
                    {"dimension": "feasibility", "score": 3.0, "reasoning": "Not feasible"},
                    {"dimension": "scalability", "score": 3.0, "reasoning": "Won't scale"},
                    {"dimension": "maintainability", "score": 3.0, "reasoning": "Brittle"},
                    {"dimension": "security", "score": 3.0, "reasoning": "Insecure"}
                ],
                "feedback": "Fundamental problems",
                "critical_issues": ["Critical issue 3"],
                "warnings": []
            }'''),
            # Agent 4: Reject (5.0)
            Mock(content='''{
                "dimension_scores": [
                    {"dimension": "completeness", "score": 5.0, "reasoning": "Below standard"},
                    {"dimension": "feasibility", "score": 5.0, "reasoning": "Questionable"},
                    {"dimension": "scalability", "score": 5.0, "reasoning": "Limited"},
                    {"dimension": "maintainability", "score": 5.0, "reasoning": "Difficult"},
                    {"dimension": "security", "score": 5.0, "reasoning": "Risks"}
                ],
                "feedback": "Below expectations",
                "critical_issues": [],
                "warnings": ["Warning 1"]
            }'''),
            # Agent 5: Approve (6.0)
            Mock(content='''{
                "dimension_scores": [
                    {"dimension": "completeness", "score": 6.0, "reasoning": "Minimum"},
                    {"dimension": "feasibility", "score": 6.0, "reasoning": "Minimum"},
                    {"dimension": "scalability", "score": 6.0, "reasoning": "Minimum"},
                    {"dimension": "maintainability", "score": 6.0, "reasoning": "Minimum"},
                    {"dimension": "security", "score": 6.0, "reasoning": "Minimum"}
                ],
                "feedback": "Barely acceptable",
                "critical_issues": [],
                "warnings": []
            }''')
        ]

        mock_llm.ainvoke.side_effect = mock_responses

        # Run review
        result = await coordinator.review_artifact(
            artifact={"test": "artifact"},
            artifact_type="design",
            phase="phase_3"
        )

        # Assert: 2/5 approved = 40% < 60% threshold
        assert result.approved is False
        assert result.approval_rate == 0.4  # 2/5
        assert len(result.critical_issues) >= 3
        assert len(result.recommendations) > 0


class TestReviewDataClasses:
    """Test dataclasses"""

    def test_review_score_to_dict(self):
        """Test ReviewScore.to_dict()"""
        score = ReviewScore(
            dimension=ReviewDimension.COMPLETENESS,
            score=8.5,
            reasoning="Good coverage"
        )

        data = score.to_dict()

        assert data["dimension"] == "completeness"
        assert data["score"] == 8.5
        assert data["reasoning"] == "Good coverage"

    def test_agent_review_to_dict(self):
        """Test AgentReview.to_dict()"""
        review = AgentReview(
            agent_name="test_reviewer",
            perspective=ReviewPerspective.QUALITY,
            dimension_scores=[
                ReviewScore(ReviewDimension.COMPLETENESS, 7.0, "Good")
            ],
            overall_score=7.0,
            approved=True,
            feedback="Looks good",
            critical_issues=[],
            warnings=["Warning 1"]
        )

        data = review.to_dict()

        assert data["agent_name"] == "test_reviewer"
        assert data["perspective"] == "quality"
        assert data["overall_score"] == 7.0
        assert data["approved"] is True

    def test_party_mode_result_to_dict(self):
        """Test PartyModeResult.to_dict()"""
        result = PartyModeResult(
            artifact_type="architecture",
            reviews=[],
            consensus_score=7.5,
            approval_rate=0.8,
            approved=True,
            aggregated_feedback="Good work",
            critical_issues=[],
            warnings=[],
            recommendations=["Deploy it"]
        )

        data = result.to_dict()

        assert data["artifact_type"] == "architecture"
        assert data["consensus_score"] == 7.5
        assert data["approval_rate"] == 0.8
        assert data["approved"] is True


class TestPerspectiveSelection:
    """Test perspective selection logic"""

    @pytest.fixture
    def mock_llm(self):
        llm = Mock()
        llm.ainvoke = AsyncMock()
        return llm

    @pytest.fixture
    def coordinator(self, mock_llm):
        return PartyModeCoordinator(llm_plugin=mock_llm)

    def test_select_perspectives_for_discovery(self, coordinator):
        """Test perspective selection for discovery phase"""
        perspectives = coordinator._select_default_perspectives("discovery")

        assert len(perspectives) == 5
        assert ReviewPerspective.REQUIREMENTS in perspectives
        assert ReviewPerspective.ARCHITECTURE in perspectives

    def test_select_perspectives_for_architecture(self, coordinator):
        """Test perspective selection for architecture phase"""
        perspectives = coordinator._select_default_perspectives("architecture")

        assert len(perspectives) == 5
        # Architecture perspective should be prioritized
        assert perspectives[0] == ReviewPerspective.ARCHITECTURE

    def test_select_perspectives_for_refactor(self, coordinator):
        """Test perspective selection for refactor phase"""
        perspectives = coordinator._select_default_perspectives("refactor")

        assert len(perspectives) == 5
        # Security and Quality should be prioritized for refactor
        assert perspectives[0] == ReviewPerspective.SECURITY
        assert perspectives[1] == ReviewPerspective.QUALITY
