"""
Tests for Story Decomposition Engine (CAAS-E Week 1)

Tests the new story decomposition functionality for epic-level requirements.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from caas_framework.methodology.story_decomposer import (
    StoryDecomposer,
    Epic,
    Story,
    topological_sort
)


class TestStoryDecomposer:
    """Test suite for StoryDecomposer"""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM plugin"""
        llm = Mock()
        llm.ainvoke = AsyncMock()
        return llm

    @pytest.fixture
    def decomposer(self, mock_llm):
        """Create StoryDecomposer instance"""
        return StoryDecomposer(
            llm_plugin=mock_llm,
            max_features_per_story=5,
            max_stories_per_epic=10
        )

    @pytest.mark.asyncio
    async def test_small_requirement_single_story(self, decomposer, mock_llm):
        """Test that small requirements create single story"""
        # Mock feature count estimation (small)
        mock_llm.ainvoke.return_value = Mock(
            content='{"estimated_features": 3, "reasoning": "Small project"}'
        )

        epic = await decomposer.decompose_epic(
            "Build a simple user login system",
            domain_hint="authentication"
        )

        # Should create single story
        assert epic.recommended_stories == 1
        assert len(epic.stories) == 1
        assert epic.stories[0].id == "story_1"

    @pytest.mark.asyncio
    async def test_large_requirement_multiple_stories(self, decomposer, mock_llm):
        """Test that large requirements decompose into multiple stories"""
        # Mock responses in order
        responses = [
            # Feature count
            Mock(content='{"estimated_features": 20, "reasoning": "Large project"}'),

            # Feature extraction
            Mock(content='''[
                {"id": "feature_1", "name": "User Login", "description": "Login", "category": "authentication"},
                {"id": "feature_2", "name": "Product List", "description": "List", "category": "data"},
                {"id": "feature_3", "name": "Shopping Cart", "description": "Cart", "category": "business_logic"},
                {"id": "feature_4", "name": "Checkout", "description": "Pay", "category": "business_logic"},
                {"id": "feature_5", "name": "Order History", "description": "History", "category": "data"}
            ]'''),

            # Story clustering
            Mock(content='''{
                "stories": [
                    {
                        "id": "story_1",
                        "name": "User Authentication",
                        "description": "Login and signup",
                        "feature_ids": ["feature_1"],
                        "estimated_complexity": "low",
                        "business_value": "high"
                    },
                    {
                        "id": "story_2",
                        "name": "Product Catalog",
                        "description": "Browse products",
                        "feature_ids": ["feature_2"],
                        "estimated_complexity": "medium",
                        "business_value": "high"
                    },
                    {
                        "id": "story_3",
                        "name": "Shopping & Checkout",
                        "description": "Cart and payment",
                        "feature_ids": ["feature_3", "feature_4"],
                        "estimated_complexity": "high",
                        "business_value": "high"
                    }
                ]
            }'''),

            # Dependency detection
            Mock(content='''{
                "dependencies": [
                    {"story_id": "story_3", "depends_on": ["story_1", "story_2"]}
                ]
            }'''),

            # Epic name
            Mock(content='E-Commerce Platform')
        ]

        mock_llm.ainvoke.side_effect = responses

        epic = await decomposer.decompose_epic(
            "Build an e-commerce platform with product catalog, shopping cart, and checkout",
            domain_hint="e_commerce"
        )

        # Should create multiple stories
        assert epic.recommended_stories == 3
        assert len(epic.stories) == 3

        # Check dependencies
        story_3 = next(s for s in epic.stories if s.id == "story_3")
        assert "story_1" in story_3.dependencies
        assert "story_2" in story_3.dependencies


class TestTopologicalSort:
    """Test suite for topological sorting"""

    def test_sort_with_dependencies(self):
        """Test sorting stories by dependencies"""
        stories = [
            Story(
                id="story_1",
                name="Foundation",
                description="Base",
                dependencies=[]
            ),
            Story(
                id="story_2",
                name="Dependent",
                description="Depends on story_1",
                dependencies=["story_1"]
            ),
            Story(
                id="story_3",
                name="Complex",
                description="Depends on story_1 and story_2",
                dependencies=["story_1", "story_2"]
            )
        ]

        sorted_stories = topological_sort(stories)

        # story_1 should be first
        assert sorted_stories[0].id == "story_1"

        # story_2 should be before story_3
        story_2_index = next(i for i, s in enumerate(sorted_stories) if s.id == "story_2")
        story_3_index = next(i for i, s in enumerate(sorted_stories) if s.id == "story_3")
        assert story_2_index < story_3_index

    def test_sort_no_dependencies(self):
        """Test sorting stories with no dependencies"""
        stories = [
            Story(id="story_1", name="A", description="A", dependencies=[]),
            Story(id="story_2", name="B", description="B", dependencies=[]),
            Story(id="story_3", name="C", description="C", dependencies=[])
        ]

        sorted_stories = topological_sort(stories)

        # Should return in original order (all have same priority)
        assert len(sorted_stories) == 3

    def test_sort_circular_dependencies(self):
        """Test handling of circular dependencies"""
        stories = [
            Story(id="story_1", name="A", description="A", dependencies=["story_2"]),
            Story(id="story_2", name="B", description="B", dependencies=["story_1"])
        ]

        sorted_stories = topological_sort(stories)

        # Should still return all stories (with warning)
        assert len(sorted_stories) == 2


class TestStoryDataClasses:
    """Test Story and Epic dataclasses"""

    def test_story_to_dict(self):
        """Test Story.to_dict()"""
        story = Story(
            id="story_1",
            name="Test Story",
            description="Description",
            features=["f1", "f2"],
            dependencies=["story_0"],
            estimated_complexity="medium",
            acceptance_criteria=["AC1", "AC2"],
            business_value="high"
        )

        data = story.to_dict()

        assert data["id"] == "story_1"
        assert data["name"] == "Test Story"
        assert len(data["features"]) == 2
        assert data["estimated_complexity"] == "medium"

    def test_epic_to_dict(self):
        """Test Epic.to_dict()"""
        epic = Epic(
            name="Test Epic",
            description="Epic description",
            estimated_features=10,
            recommended_stories=2,
            stories=[
                Story(id="story_1", name="S1", description="D1"),
                Story(id="story_2", name="S2", description="D2")
            ],
            business_value="high"
        )

        data = epic.to_dict()

        assert data["epic"]["name"] == "Test Epic"
        assert data["epic"]["recommended_stories"] == 2
        assert len(data["stories"]) == 2
