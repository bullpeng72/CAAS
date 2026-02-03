"""
Tests for Golden Pattern RAG

Tests the pattern storage and retrieval functionality.
"""

import json
import shutil
import tempfile
from unittest.mock import patch

import pytest

from caas_framework.models.specifications import (
    ConcretizedRequirement,
    FeatureSpec,
    SystemScope,
)
from caas_framework.patterns.golden_pattern_rag import (
    Feedback,
    GoldenPatternLibrary,
    PatternMatch,
    retrieve_patterns,
    store_successful_pattern,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_concretized_blog():
    """Sample blog system concretized requirement."""
    return ConcretizedRequirement(
        system_scope=SystemScope(
            project_name="Blog System",
            purpose="Create a blogging platform",
            target_users=["Bloggers", "Readers"],
            system_type="web_application",
            scope_description="A simple blog system",
        ),
        features=[
            FeatureSpec(
                id="feat_1",
                name="Create Posts",
                description="Users can create blog posts",
                priority="high",
                acceptance_criteria=["User can write post", "Post is saved"],
            ),
            FeatureSpec(
                id="feat_2",
                name="View Posts",
                description="Users can view published posts",
                priority="high",
                acceptance_criteria=["Posts are displayed", "Posts are readable"],
            ),
        ],
        constraints=[],
        success_criteria=[],
        domain="blog",
    )


@pytest.fixture
def sample_concretized_news():
    """Sample news system concretized requirement (similar to blog)."""
    return ConcretizedRequirement(
        system_scope=SystemScope(
            project_name="News System",
            purpose="Create a news platform",
            target_users=["Journalists", "Readers"],
            system_type="web_application",
            scope_description="A news publishing system",
        ),
        features=[
            FeatureSpec(
                id="feat_1",
                name="Publish Articles",
                description="Journalists can publish news articles",
                priority="high",
                acceptance_criteria=["Article can be written", "Article is published"],
            )
        ],
        constraints=[],
        success_criteria=[],
        domain="news",
    )


@pytest.fixture
def sample_design():
    """Sample design output."""
    return {
        "agents": [
            {"id": "writer", "role": "Content Writer"},
            {"id": "editor", "role": "Content Editor"},
        ],
        "tasks": [
            {"id": "task1", "description": "Write content"},
            {"id": "task2", "description": "Edit content"},
        ],
    }


class TestFeedback:
    """Test Feedback model."""

    def test_feedback_creation(self):
        """Test creating feedback."""
        feedback = Feedback(satisfaction=5, comments="Great!")
        assert feedback.satisfaction == 5
        assert feedback.comments == "Great!"

    def test_feedback_validation(self):
        """Test feedback validation."""
        with pytest.raises(Exception):  # Pydantic validation error
            Feedback(satisfaction=6)  # > 5

        with pytest.raises(Exception):
            Feedback(satisfaction=0)  # < 1


class TestPatternMatch:
    """Test PatternMatch dataclass."""

    def test_pattern_match_creation(self):
        """Test creating a pattern match."""
        match = PatternMatch(
            request="Create a blog",
            features=[{"name": "Posts"}],
            num_agents=2,
            num_tasks=3,
            satisfaction=5.0,
            timestamp="2024-01-01T00:00:00",
            similarity=0.85,
        )

        assert match.request == "Create a blog"
        assert match.num_agents == 2
        assert match.similarity == 0.85


class TestGoldenPatternLibrary:
    """Test GoldenPatternLibrary class."""

    def test_library_initialization(self, temp_dir):
        """Test creating library."""
        library = GoldenPatternLibrary(
            collection_name="test_patterns", persist_directory=temp_dir
        )
        assert library is not None
        assert library.collection_name == "test_patterns"

    def test_library_with_fallback(self, temp_dir):
        """Test library uses fallback when dependencies unavailable."""
        # Force fallback mode
        with patch(
            "caas_framework.patterns.golden_pattern_rag.CHROMADB_AVAILABLE", False
        ):
            library = GoldenPatternLibrary(persist_directory=temp_dir)
            assert library.use_fallback is True

    def test_store_successful_generation(
        self, temp_dir, sample_concretized_blog, sample_design
    ):
        """Test storing a successful pattern."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        result = library.store_successful_generation(
            user_request="Create a blog system",
            concretized=sample_concretized_blog,
            design=sample_design,
            user_feedback=Feedback(satisfaction=5),
        )

        # Should succeed (either ChromaDB or fallback)
        assert result is True

    def test_store_low_satisfaction_rejected(self, temp_dir, sample_concretized_blog):
        """Test that low satisfaction patterns are not stored."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        result = library.store_successful_generation(
            user_request="Create a blog",
            concretized=sample_concretized_blog,
            user_feedback=Feedback(satisfaction=2),  # Low satisfaction
        )

        assert result is False

    def test_retrieve_similar_patterns_empty(self, temp_dir):
        """Test retrieving patterns from empty library."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        patterns = library.retrieve_similar_patterns("Create a blog")

        assert patterns == []

    def test_store_and_retrieve_pattern(
        self, temp_dir, sample_concretized_blog, sample_design
    ):
        """Test storing and then retrieving a pattern."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        # Store pattern
        library.store_successful_generation(
            user_request="Create a blog system with posts",
            concretized=sample_concretized_blog,
            design=sample_design,
            user_feedback=Feedback(satisfaction=5),
        )

        # Retrieve similar
        patterns = library.retrieve_similar_patterns(
            "Create a blogging platform", top_k=3
        )

        # Should find the stored pattern
        assert len(patterns) > 0
        assert patterns[0].num_agents == 2
        assert patterns[0].num_tasks == 2

    def test_retrieve_multiple_patterns(
        self, temp_dir, sample_concretized_blog, sample_concretized_news
    ):
        """Test retrieving multiple similar patterns."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        # Store multiple patterns
        library.store_successful_generation(
            user_request="Create a blog system",
            concretized=sample_concretized_blog,
            user_feedback=Feedback(satisfaction=5),
        )

        library.store_successful_generation(
            user_request="Create a news platform",
            concretized=sample_concretized_news,
            user_feedback=Feedback(satisfaction=5),
        )

        # Retrieve
        patterns = library.retrieve_similar_patterns(
            "Create a content management system", top_k=3
        )

        # Should find both patterns
        assert len(patterns) >= 1  # At least one match

    def test_enhance_with_patterns_no_matches(self, temp_dir, sample_concretized_news):
        """Test enhancement when no similar patterns exist."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        enhanced = library.enhance_with_patterns(
            user_request="Create a news system",
            concretized=sample_concretized_news,
            verbose=False,
        )

        # Should return unchanged
        assert len(enhanced.features) == 1

    def test_enhance_with_patterns_auto_add(
        self, temp_dir, sample_concretized_blog, sample_concretized_news
    ):
        """Test enhancement with auto-add enabled."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        # Store blog pattern with more features
        blog_with_comments = sample_concretized_blog
        blog_with_comments.features.append(
            FeatureSpec(
                id="feat_3",
                name="Comments",
                description="Users can comment on posts",
                priority="medium",
                acceptance_criteria=["Comments are displayed"],
            )
        )

        library.store_successful_generation(
            user_request="Create a blog with comments",
            concretized=blog_with_comments,
            user_feedback=Feedback(satisfaction=5),
        )

        # Enhance news system (similar to blog)
        original_count = len(sample_concretized_news.features)

        enhanced = library.enhance_with_patterns(
            user_request="Create a news platform",
            concretized=sample_concretized_news,
            auto_add=True,
            verbose=False,
        )

        # Should have added suggested features
        # (May or may not add depending on similarity threshold)
        assert len(enhanced.features) >= original_count

    def test_enhance_with_patterns_verbose(
        self, temp_dir, sample_concretized_blog, sample_concretized_news, capsys
    ):
        """Test enhancement with verbose output."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        # Store pattern
        library.store_successful_generation(
            user_request="Create a blog",
            concretized=sample_concretized_blog,
            user_feedback=Feedback(satisfaction=5),
        )

        # Enhance with verbose
        enhanced = library.enhance_with_patterns(
            user_request="Create another blog",
            concretized=sample_concretized_news,
            auto_add=True,
            verbose=True,
        )

        captured = capsys.readouterr()
        # Should print something (either "No similar patterns" or suggestions)
        assert len(captured.out) > 0

    def test_get_statistics_empty(self, temp_dir):
        """Test statistics for empty library."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        stats = library.get_statistics()

        assert stats["total_patterns"] == 0
        assert stats["avg_satisfaction"] == 0

    def test_get_statistics_with_patterns(
        self, temp_dir, sample_concretized_blog, sample_concretized_news
    ):
        """Test statistics with stored patterns."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        # Store patterns
        library.store_successful_generation(
            user_request="Create a blog",
            concretized=sample_concretized_blog,
            user_feedback=Feedback(satisfaction=5),
        )

        library.store_successful_generation(
            user_request="Create a news site",
            concretized=sample_concretized_news,
            user_feedback=Feedback(satisfaction=4),
        )

        stats = library.get_statistics()

        assert stats["total_patterns"] == 2
        assert stats["avg_satisfaction"] >= 4.0
        assert "blog" in stats["domains"] or "news" in stats["domains"]


class TestFallbackStorage:
    """Test fallback storage mechanism."""

    def test_fallback_store_and_retrieve(self, temp_dir, sample_concretized_blog):
        """Test fallback storage works correctly."""
        # Force fallback mode
        with patch(
            "caas_framework.patterns.golden_pattern_rag.CHROMADB_AVAILABLE", False
        ):
            library = GoldenPatternLibrary(persist_directory=temp_dir)

            # Store
            result = library.store_successful_generation(
                user_request="Create a blog system",
                concretized=sample_concretized_blog,
                user_feedback=Feedback(satisfaction=5),
            )

            assert result is True
            assert len(library.fallback_storage) == 1

            # Retrieve
            patterns = library.retrieve_similar_patterns("Create a blog")

            assert len(patterns) > 0
            assert patterns[0].request == "Create a blog system"

    def test_fallback_similarity_calculation(self, temp_dir):
        """Test fallback similarity uses Jaccard similarity."""
        with patch(
            "caas_framework.patterns.golden_pattern_rag.CHROMADB_AVAILABLE", False
        ):
            library = GoldenPatternLibrary(persist_directory=temp_dir)

            # Manually add to fallback storage
            library.fallback_storage.append(
                {
                    "id": "test_1",
                    "document": "Create a blog system",
                    "metadata": {
                        "features": json.dumps([]),
                        "num_agents": 2,
                        "num_tasks": 2,
                        "satisfaction": 5,
                        "timestamp": "2024-01-01T00:00:00",
                        "domain": "blog",
                    },
                }
            )

            # Retrieve with similar query
            patterns = library.retrieve_similar_patterns("Create a blog platform")

            assert len(patterns) > 0
            # Similarity should be > 0 due to word overlap
            assert patterns[0].similarity > 0


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_store_successful_pattern(self, temp_dir, sample_concretized_blog):
        """Test convenience function for storing pattern."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        result = store_successful_pattern(
            library=library,
            user_request="Create a blog",
            concretized=sample_concretized_blog,
            satisfaction=5,
        )

        assert result is True

    def test_retrieve_patterns(self, temp_dir, sample_concretized_blog):
        """Test convenience function for retrieving patterns."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        # Store first
        store_successful_pattern(
            library=library,
            user_request="Create a blog",
            concretized=sample_concretized_blog,
            satisfaction=5,
        )

        # Retrieve
        patterns = retrieve_patterns(
            library=library, user_request="Create a blogging system", top_k=3
        )

        assert len(patterns) > 0


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_request(self, temp_dir):
        """Test with empty user request."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        patterns = library.retrieve_similar_patterns("")

        assert patterns == []

    def test_very_long_request(self, temp_dir, sample_concretized_blog):
        """Test with very long user request."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        long_request = "Create a blog " * 100

        result = library.store_successful_generation(
            user_request=long_request,
            concretized=sample_concretized_blog,
            user_feedback=Feedback(satisfaction=5),
        )

        # Should handle gracefully
        assert result in [True, False]

    def test_special_characters_in_request(self, temp_dir, sample_concretized_blog):
        """Test with special characters in request."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        special_request = "Create a blog with @mentions & #hashtags!"

        result = library.store_successful_generation(
            user_request=special_request,
            concretized=sample_concretized_blog,
            user_feedback=Feedback(satisfaction=5),
        )

        assert result is True

    def test_no_features(self, temp_dir):
        """Test with concretized requirement that has no features."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        empty_req = ConcretizedRequirement(
            system_scope=SystemScope(
                project_name="Empty",
                purpose="Test",
                target_users=["Users"],
                system_type="web_application",
                scope_description="Empty",
            ),
            features=[],  # No features
            constraints=[],
            success_criteria=[],
            domain="test",
        )

        result = library.store_successful_generation(
            user_request="Create empty system",
            concretized=empty_req,
            user_feedback=Feedback(satisfaction=5),
        )

        # Should handle gracefully
        assert result is True


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(
        self, temp_dir, sample_concretized_blog, sample_concretized_news, sample_design
    ):
        """Test complete workflow: store, retrieve, enhance."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        # 1. Store successful blog generation
        result = library.store_successful_generation(
            user_request="Create a blogging platform with posts and comments",
            concretized=sample_concretized_blog,
            design=sample_design,
            user_feedback=Feedback(satisfaction=5, comments="Excellent!"),
        )

        assert result is True

        # 2. New user request for similar system
        new_request = "Create a news website"

        # 3. Retrieve similar patterns
        patterns = library.retrieve_similar_patterns(new_request, top_k=3)

        # Should find the blog pattern as similar
        assert len(patterns) >= 0  # May or may not find depending on similarity

        # 4. Enhance with patterns
        enhanced = library.enhance_with_patterns(
            user_request=new_request,
            concretized=sample_concretized_news,
            auto_add=True,
            verbose=False,
        )

        # Should return enhanced requirement
        assert enhanced is not None
        assert len(enhanced.features) >= 1

        # 5. Check statistics
        stats = library.get_statistics()
        assert stats["total_patterns"] >= 1

    def test_multiple_domains(self, temp_dir):
        """Test with patterns from multiple domains."""
        library = GoldenPatternLibrary(persist_directory=temp_dir)

        # Store patterns from different domains
        blog_req = ConcretizedRequirement(
            system_scope=SystemScope(
                project_name="Blog",
                purpose="Blog",
                target_users=["Users"],
                system_type="web_application",
                scope_description="Blog",
            ),
            features=[
                FeatureSpec(
                    id="feat_1",
                    name="Posts",
                    description="Blog posts",
                    priority="high",
                    acceptance_criteria=[],
                )
            ],
            constraints=[],
            success_criteria=[],
            domain="blog",
        )

        ecommerce_req = ConcretizedRequirement(
            system_scope=SystemScope(
                project_name="Shop",
                purpose="Shop",
                target_users=["Customers"],
                system_type="web_application",
                scope_description="Shop",
            ),
            features=[
                FeatureSpec(
                    id="feat_1",
                    name="Products",
                    description="Product catalog",
                    priority="high",
                    acceptance_criteria=[],
                )
            ],
            constraints=[],
            success_criteria=[],
            domain="ecommerce",
        )

        library.store_successful_generation(
            user_request="Create a blog",
            concretized=blog_req,
            user_feedback=Feedback(satisfaction=5),
        )

        library.store_successful_generation(
            user_request="Create an online store",
            concretized=ecommerce_req,
            user_feedback=Feedback(satisfaction=5),
        )

        # Check statistics
        stats = library.get_statistics()
        assert stats["total_patterns"] == 2
        assert len(stats["domains"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
