"""
Test Requirement Examples and Interactive Guide

Tests the example requirement system and interactive guide functionality.
"""

from caas_framework.examples.interactive_guide import InteractiveGuide
from caas_framework.examples.requirement_examples import (
    REQUIREMENT_EXAMPLES,
    Complexity,
    Domain,
    RequirementExample,
    get_example_summary,
    get_examples_by_complexity,
    get_examples_by_domain,
    get_examples_by_tag,
    search_examples,
    suggest_examples,
)


def test_requirement_example_creation():
    """Test RequirementExample dataclass"""
    example = RequirementExample(
        title="Test App",
        domain=Domain.WEB_APP,
        complexity=Complexity.SIMPLE,
        description="A test application",
        requirement_text="Build a test app",
        key_features=["Feature 1", "Feature 2"],
        tags=["test", "simple"]
    )

    assert example.title == "Test App"
    assert example.domain == Domain.WEB_APP
    assert example.complexity == Complexity.SIMPLE
    assert len(example.key_features) == 2
    assert len(example.tags) == 2


def test_requirement_example_format():
    """Test formatted display of example"""
    example = RequirementExample(
        title="Test App",
        domain=Domain.WEB_APP,
        complexity=Complexity.SIMPLE,
        description="A test application",
        requirement_text="Build a test app",
        key_features=["Feature 1"],
        tags=["test"]
    )

    formatted = example.format_for_display()
    assert "Test App" in formatted
    assert "web_app" in formatted
    assert "simple" in formatted
    assert "Feature 1" in formatted


def test_examples_exist():
    """Test that examples database is not empty"""
    assert len(REQUIREMENT_EXAMPLES) > 0
    assert len(REQUIREMENT_EXAMPLES) >= 10  # Should have at least 10 examples


def test_all_domains_represented():
    """Test that examples cover multiple domains"""
    domains_in_examples = set(ex.domain for ex in REQUIREMENT_EXAMPLES)
    assert len(domains_in_examples) >= 5  # At least 5 different domains


def test_all_complexity_levels_represented():
    """Test that examples cover all complexity levels"""
    complexities_in_examples = set(ex.complexity for ex in REQUIREMENT_EXAMPLES)
    assert Complexity.SIMPLE in complexities_in_examples
    assert Complexity.MODERATE in complexities_in_examples
    assert Complexity.COMPLEX in complexities_in_examples


def test_get_examples_by_domain():
    """Test filtering examples by domain"""
    web_examples = get_examples_by_domain(Domain.WEB_APP)
    assert all(ex.domain == Domain.WEB_APP for ex in web_examples)

    api_examples = get_examples_by_domain(Domain.API)
    assert all(ex.domain == Domain.API for ex in api_examples)


def test_get_examples_by_complexity():
    """Test filtering examples by complexity"""
    simple_examples = get_examples_by_complexity(Complexity.SIMPLE)
    assert all(ex.complexity == Complexity.SIMPLE for ex in simple_examples)
    assert len(simple_examples) > 0

    complex_examples = get_examples_by_complexity(Complexity.COMPLEX)
    assert all(ex.complexity == Complexity.COMPLEX for ex in complex_examples)
    assert len(complex_examples) > 0


def test_get_examples_by_tag():
    """Test filtering examples by tag"""
    # Test common tags
    api_examples = get_examples_by_tag("api")
    assert all("api" in [t.lower() for t in ex.tags] for ex in api_examples)

    simple_examples = get_examples_by_tag("simple")
    assert all("simple" in [t.lower() for t in ex.tags] for ex in simple_examples)


def test_search_examples():
    """Test searching examples by keyword"""
    # Search by common keywords
    blog_results = search_examples("blog")
    assert len(blog_results) > 0
    assert any("blog" in ex.title.lower() or "blog" in ex.description.lower()
               for ex in blog_results)

    chatbot_results = search_examples("chatbot")
    assert len(chatbot_results) > 0

    # Search should be case-insensitive
    results_lower = search_examples("api")
    results_upper = search_examples("API")
    assert len(results_lower) == len(results_upper)


def test_search_examples_no_results():
    """Test search with no matching results"""
    results = search_examples("xyzabc123nonexistent")
    assert len(results) == 0


def test_get_example_summary():
    """Test getting summary statistics"""
    summary = get_example_summary()

    assert "total" in summary
    assert "by_domain" in summary
    assert "by_complexity" in summary

    assert summary["total"] == len(REQUIREMENT_EXAMPLES)
    assert summary["total"] > 0

    # Check domain counts
    for domain in Domain:
        assert domain.value in summary["by_domain"]
        expected_count = len(get_examples_by_domain(domain))
        assert summary["by_domain"][domain.value] == expected_count

    # Check complexity counts
    for complexity in Complexity:
        assert complexity.value in summary["by_complexity"]
        expected_count = len(get_examples_by_complexity(complexity))
        assert summary["by_complexity"][complexity.value] == expected_count


def test_suggest_examples():
    """Test getting suggestions based on user input"""
    # Test with different inputs
    suggestions = suggest_examples("blog", limit=3)
    assert len(suggestions) <= 3
    assert all(isinstance(ex, RequirementExample) for ex in suggestions)

    # Test limit parameter
    suggestions_1 = suggest_examples("app", limit=1)
    assert len(suggestions_1) <= 1

    suggestions_5 = suggest_examples("app", limit=5)
    assert len(suggestions_5) <= 5


def test_suggest_examples_empty_input():
    """Test suggestions with empty input"""
    suggestions = suggest_examples("", limit=3)
    # Empty search returns top matches (up to limit)
    assert len(suggestions) <= 3


def test_example_required_fields():
    """Test that all examples have required fields"""
    for ex in REQUIREMENT_EXAMPLES:
        # Check required fields are not empty
        assert ex.title
        assert ex.domain
        assert ex.complexity
        assert ex.description
        assert ex.requirement_text
        assert len(ex.key_features) > 0
        assert len(ex.tags) > 0


def test_example_quality():
    """Test that examples meet quality standards"""
    for ex in REQUIREMENT_EXAMPLES:
        # Title should be reasonable length
        assert 10 <= len(ex.title) <= 100

        # Description should be substantial
        assert len(ex.description) >= 20

        # Requirement text should be detailed
        assert len(ex.requirement_text) >= 50

        # Should have multiple key features
        assert len(ex.key_features) >= 3

        # Should have multiple tags
        assert len(ex.tags) >= 2


def test_domain_enum_values():
    """Test Domain enum values"""
    assert Domain.WEB_APP.value == "web_app"
    assert Domain.API.value == "api"
    assert Domain.CHATBOT.value == "chatbot"


def test_complexity_enum_values():
    """Test Complexity enum values"""
    assert Complexity.SIMPLE.value == "simple"
    assert Complexity.MODERATE.value == "moderate"
    assert Complexity.COMPLEX.value == "complex"


def test_interactive_guide_creation():
    """Test InteractiveGuide creation"""
    guide = InteractiveGuide(use_rich=False)
    assert guide is not None
    assert guide.use_rich is False

    guide_rich = InteractiveGuide(use_rich=True)
    assert guide_rich is not None


def test_interactive_guide_show_example():
    """Test showing an example"""
    import io
    from unittest.mock import patch

    guide = InteractiveGuide(use_rich=False)
    example = REQUIREMENT_EXAMPLES[0]

    # Capture output
    output = io.StringIO()
    with patch('sys.stdout', output):
        guide.show_example(example)

    output_text = output.getvalue()
    assert example.title in output_text
    # Domain is formatted with title case and spaces (e.g., "Web App" instead of "web_app")
    assert example.domain.value.replace('_', ' ').title() in output_text or example.domain.value in output_text


def test_interactive_guide_get_suggestions():
    """Test getting suggestions through guide"""
    guide = InteractiveGuide(use_rich=False)

    suggestions = guide.get_suggestions("blog", limit=2)
    assert len(suggestions) <= 2
    assert all(isinstance(ex, RequirementExample) for ex in suggestions)


def test_examples_cover_common_use_cases():
    """Test that examples cover common use cases"""
    # Check for common domains
    common_domains = [
        Domain.WEB_APP,
        Domain.API,
        Domain.CHATBOT,
        Domain.AUTOMATION
    ]

    for domain in common_domains:
        examples = get_examples_by_domain(domain)
        assert len(examples) > 0, f"No examples for common domain: {domain.value}"


def test_examples_progression():
    """Test that examples show progression from simple to complex"""
    # Get examples for a domain that has multiple complexity levels
    web_examples = get_examples_by_domain(Domain.WEB_APP)

    if len(web_examples) >= 2:
        # Find simple and complex examples
        simple = [ex for ex in web_examples if ex.complexity == Complexity.SIMPLE]
        complex_ex = [ex for ex in web_examples if ex.complexity == Complexity.COMPLEX]

        if simple and complex_ex:
            # Complex examples should have more features
            assert len(complex_ex[0].key_features) >= len(simple[0].key_features)


def test_tag_consistency():
    """Test that tags are consistent and useful"""
    all_tags = set()
    for ex in REQUIREMENT_EXAMPLES:
        for tag in ex.tags:
            all_tags.add(tag.lower())

    # Should have a reasonable number of unique tags
    assert len(all_tags) >= 10
    assert len(all_tags) <= 100  # Not too many

    # Common tags should exist
    assert "api" in all_tags or "simple" in all_tags


def test_search_finds_relevant_examples():
    """Test that search returns relevant results"""
    # Search for "todo" should find todo examples
    results = search_examples("todo")
    if results:
        assert any("todo" in ex.title.lower() or "todo" in ex.description.lower() or
                   any("todo" in tag.lower() for tag in ex.tags)
                   for ex in results)

    # Search for "app" should find app-related examples (more general term)
    results = search_examples("app")
    # Should find at least some results
    assert len(results) > 0


if __name__ == "__main__":
    # Run tests
    test_requirement_example_creation()
    test_requirement_example_format()
    test_examples_exist()
    test_all_domains_represented()
    test_all_complexity_levels_represented()
    test_get_examples_by_domain()
    test_get_examples_by_complexity()
    test_get_examples_by_tag()
    test_search_examples()
    test_search_examples_no_results()
    test_get_example_summary()
    test_suggest_examples()
    test_suggest_examples_empty_input()
    test_example_required_fields()
    test_example_quality()
    test_domain_enum_values()
    test_complexity_enum_values()
    test_interactive_guide_creation()
    test_interactive_guide_show_example()
    test_interactive_guide_get_suggestions()
    test_examples_cover_common_use_cases()
    test_examples_progression()
    test_tag_consistency()
    test_search_finds_relevant_examples()

    print("\n" + "="*70)
    print("✅ All Requirement Examples tests passed!")
    print("="*70)
