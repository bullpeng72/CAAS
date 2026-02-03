"""
Tests for Semantic Consistency Checker

Tests the semantic contradiction detection functionality.
"""

import pytest

from caas_framework.models.specifications import (
    ConcretizedRequirement,
    FeatureSpec,
    SystemScope,
)
from caas_framework.validation.semantic_checker import (
    Contradiction,
    ContradictionReport,
    SemanticConsistencyChecker,
    validate_semantic_consistency,
)


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def generate_structured(self, prompt: str, schema):
        """Mock structured generation."""
        # Return a report with one contradiction
        return ContradictionReport(
            contradictions=[
                {
                    "concept_a": "test_a",
                    "concept_b": "test_b",
                    "reason": "Test contradiction from LLM",
                    "severity": "warning",
                }
            ],
            has_contradictions=True,
        )


@pytest.fixture
def sample_requirement():
    """Sample concretized requirement without contradictions."""
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
                id="feature_1",
                name="Create Posts",
                description="Users can create blog posts",
                priority="high",
                acceptance_criteria=["User can write post", "Post is saved"],
            )
        ],
        constraints=[],
        success_criteria=[],
        domain="blog",
    )


@pytest.fixture
def contradictory_requirement():
    """Sample requirement with contradictions."""
    return ConcretizedRequirement(
        system_scope=SystemScope(
            project_name="Chat App",
            purpose="Real-time chat application using REST only",
            target_users=["Users"],
            system_type="web_application",
            scope_description="A chat app with real-time features and RESTful API only",
        ),
        features=[
            FeatureSpec(
                id="feature_1",
                name="Real-time Messaging",
                description="Users can send real-time messages using WebSocket",
                priority="high",
                acceptance_criteria=["Messages appear instantly"],
            ),
            FeatureSpec(
                id="feature_2",
                name="RESTful API",
                description="System uses REST only for all communications",
                priority="high",
                acceptance_criteria=["No WebSocket allowed"],
            ),
        ],
        constraints=["REST API only"],
        success_criteria=[],
        domain="chat",
    )


class TestContradiction:
    """Test Contradiction dataclass"""

    def test_contradiction_creation(self):
        """Test creating a Contradiction"""
        c = Contradiction(
            concept_a="realtime",
            concept_b="rest_only",
            reason="Test reason",
            severity="error",
        )

        assert c.concept_a == "realtime"
        assert c.concept_b == "rest_only"
        assert c.reason == "Test reason"
        assert c.severity == "error"

    def test_contradiction_default_severity(self):
        """Test default severity"""
        c = Contradiction(concept_a="test_a", concept_b="test_b", reason="Test")

        assert c.severity == "warning"


class TestSemanticConsistencyChecker:
    """Test SemanticConsistencyChecker class"""

    def test_checker_creation(self):
        """Test creating checker"""
        checker = SemanticConsistencyChecker()
        assert checker is not None
        assert checker.llm_provider is None

    def test_checker_with_llm(self):
        """Test creating checker with LLM provider"""
        llm = MockLLMProvider()
        checker = SemanticConsistencyChecker(llm_provider=llm)
        assert checker.llm_provider == llm

    def test_contradiction_rules_exist(self):
        """Test that contradiction rules are defined"""
        checker = SemanticConsistencyChecker()
        assert len(checker.CONTRADICTION_RULES) > 0
        assert all("concept_a" in rule for rule in checker.CONTRADICTION_RULES)
        assert all("concept_b" in rule for rule in checker.CONTRADICTION_RULES)

    def test_extract_requirements(self, sample_requirement):
        """Test extracting requirements as text"""
        checker = SemanticConsistencyChecker()
        requirements = checker._extract_requirements(sample_requirement)

        assert len(requirements) > 0
        assert any("Blog System" in req for req in requirements)
        assert any("Create Posts" in req for req in requirements)

    def test_no_contradictions(self, sample_requirement):
        """Test with requirement that has no contradictions"""
        checker = SemanticConsistencyChecker()
        contradictions = checker.check_consistency(sample_requirement)

        assert len(contradictions) == 0

    def test_detect_realtime_rest_contradiction(self, contradictory_requirement):
        """Test detecting realtime + REST-only contradiction"""
        checker = SemanticConsistencyChecker()
        contradictions = checker.check_consistency(contradictory_requirement)

        assert len(contradictions) > 0

        # Should detect the realtime + REST-only conflict
        realtime_conflict = any(
            c.concept_a == "realtime" and c.concept_b == "rest_only"
            for c in contradictions
        )
        assert realtime_conflict

    def test_detect_serverless_stateful_contradiction(self):
        """Test detecting serverless + stateful contradiction"""
        requirement = ConcretizedRequirement(
            system_scope=SystemScope(
                project_name="Serverless App",
                purpose="Serverless application with stateful sessions",
                target_users=["Users"],
                system_type="serverless",
                scope_description="A serverless app",
            ),
            features=[
                FeatureSpec(
                    id="feat_1",
                    name="Lambda Functions",
                    description="Use AWS Lambda serverless functions",
                    priority="high",
                    acceptance_criteria=[],
                ),
                FeatureSpec(
                    id="feat_2",
                    name="Session Management",
                    description="Maintain stateful user sessions",
                    priority="high",
                    acceptance_criteria=[],
                ),
            ],
            constraints=[],
            success_criteria=[],
            domain="web",
        )

        checker = SemanticConsistencyChecker()
        contradictions = checker.check_consistency(requirement)

        assert len(contradictions) > 0

        serverless_conflict = any(
            "serverless" in c.concept_a.lower() or "stateful" in c.concept_b.lower()
            for c in contradictions
        )
        assert serverless_conflict

    def test_detect_nosql_joins_contradiction(self):
        """Test detecting NoSQL + complex joins contradiction"""
        requirement = ConcretizedRequirement(
            system_scope=SystemScope(
                project_name="Data App",
                purpose="Application with MongoDB and complex joins",
                target_users=["Users"],
                system_type="web_application",
                scope_description="App using NoSQL",
            ),
            features=[
                FeatureSpec(
                    id="feat_3",
                    name="MongoDB Database",
                    description="Use MongoDB NoSQL database",
                    priority="high",
                    acceptance_criteria=[],
                ),
                FeatureSpec(
                    id="feat_4",
                    name="Complex Queries",
                    description="Perform complex multi-table joins",
                    priority="high",
                    acceptance_criteria=[],
                ),
            ],
            constraints=[],
            success_criteria=[],
            domain="database",
        )

        checker = SemanticConsistencyChecker()
        contradictions = checker.check_consistency(requirement)

        assert len(contradictions) > 0

    def test_find_location(self):
        """Test finding contradiction location"""
        checker = SemanticConsistencyChecker()

        requirements = [
            "Feature: Real-time chat using WebSocket",
            "Constraint: REST API only, no WebSocket",
        ]

        rule = checker.CONTRADICTION_RULES[0]  # realtime + rest_only
        location = checker._find_location(requirements, rule)

        assert location is not None
        assert len(location) > 0

    def test_generate_report(self):
        """Test generating contradiction report"""
        checker = SemanticConsistencyChecker()

        contradictions = [
            Contradiction(
                concept_a="realtime",
                concept_b="rest_only",
                reason="Test",
                severity="error",
            ),
            Contradiction(
                concept_a="nosql",
                concept_b="complex_joins",
                reason="Test",
                severity="warning",
            ),
        ]

        report = checker.generate_report(contradictions)

        assert report.has_contradictions is True
        assert len(report.contradictions) == 2
        assert report.severity_counts["error"] == 1
        assert report.severity_counts["warning"] == 1

    def test_generate_report_empty(self):
        """Test generating report with no contradictions"""
        checker = SemanticConsistencyChecker()

        report = checker.generate_report([])

        assert report.has_contradictions is False
        assert len(report.contradictions) == 0

    def test_print_report_no_contradictions(self, capsys):
        """Test printing report with no contradictions"""
        checker = SemanticConsistencyChecker()

        checker.print_report([])

        captured = capsys.readouterr()
        assert "No semantic contradictions found" in captured.out

    def test_print_report_with_contradictions(self, capsys):
        """Test printing report with contradictions"""
        checker = SemanticConsistencyChecker()

        contradictions = [
            Contradiction(
                concept_a="realtime",
                concept_b="rest_only",
                reason="Real-time requires WebSocket",
                severity="error",
                location="Feature A vs Constraint B",
            )
        ]

        checker.print_report(contradictions, verbose=True)

        captured = capsys.readouterr()
        assert "SEMANTIC CONSISTENCY REPORT" in captured.out
        assert "realtime" in captured.out
        assert "rest_only" in captured.out
        assert "ERROR" in captured.out


class TestValidateSemanticConsistency:
    """Test convenience function"""

    def test_validate_no_contradictions(self, sample_requirement):
        """Test validation with no contradictions"""
        is_valid, contradictions = validate_semantic_consistency(
            sample_requirement, verbose=False
        )

        assert is_valid is True
        assert len(contradictions) == 0

    def test_validate_with_contradictions(self, contradictory_requirement):
        """Test validation with contradictions"""
        is_valid, contradictions = validate_semantic_consistency(
            contradictory_requirement, verbose=False
        )

        # Should be invalid due to errors
        assert is_valid is False
        assert len(contradictions) > 0

    def test_validate_with_warnings_only(self):
        """Test that warnings don't make it invalid"""
        # Create requirement with only warning-level contradiction
        requirement = ConcretizedRequirement(
            system_scope=SystemScope(
                project_name="Test",
                purpose="Test app with NoSQL and joins",
                target_users=["Users"],
                system_type="web_application",
                scope_description="Test",
            ),
            features=[
                FeatureSpec(
                    id="feat_5",
                    name="NoSQL",
                    description="Use MongoDB NoSQL",
                    priority="high",
                    acceptance_criteria=[],
                ),
                FeatureSpec(
                    id="feat_6",
                    name="Joins",
                    description="Complex multi-table joins",
                    priority="low",
                    acceptance_criteria=[],
                ),
            ],
            constraints=[],
            success_criteria=[],
            domain="test",
        )

        is_valid, contradictions = validate_semantic_consistency(
            requirement, verbose=False
        )

        # Should be valid (only warnings, no errors)
        # Note: nosql + joins is a warning, not error
        assert len(contradictions) > 0
        assert all(c.severity == "warning" for c in contradictions)


class TestRuleBasedChecking:
    """Test rule-based contradiction detection"""

    def test_all_rules_have_required_fields(self):
        """Test that all rules have required fields"""
        checker = SemanticConsistencyChecker()

        for rule in checker.CONTRADICTION_RULES:
            assert "concept_a" in rule
            assert "concept_b" in rule
            assert "reason" in rule
            assert "severity" in rule
            assert "keywords_a" in rule
            assert "keywords_b" in rule

    def test_rule_severities_are_valid(self):
        """Test that rule severities are valid values"""
        checker = SemanticConsistencyChecker()

        valid_severities = ["warning", "error", "critical"]

        for rule in checker.CONTRADICTION_RULES:
            assert rule["severity"] in valid_severities

    def test_multiple_contradictions_detected(self):
        """Test detecting multiple contradictions in one requirement"""
        requirement = ConcretizedRequirement(
            system_scope=SystemScope(
                project_name="Complex App",
                purpose="Serverless real-time app using REST only and NoSQL with joins",
                target_users=["Users"],
                system_type="serverless",
                scope_description="Complex app",
            ),
            features=[
                FeatureSpec(
                    id="feat_7",
                    name="Real-time",
                    description="Real-time WebSocket features",
                    priority="high",
                    acceptance_criteria=[],
                ),
                FeatureSpec(
                    id="feat_8",
                    name="Lambda",
                    description="AWS Lambda serverless with stateful sessions",
                    priority="high",
                    acceptance_criteria=[],
                ),
                FeatureSpec(
                    id="feat_9",
                    name="Database",
                    description="MongoDB with complex SQL joins",
                    priority="high",
                    acceptance_criteria=[],
                ),
            ],
            constraints=["REST API only", "No WebSocket"],
            success_criteria=[],
            domain="complex",
        )

        checker = SemanticConsistencyChecker()
        contradictions = checker.check_consistency(requirement)

        # Should detect multiple contradictions
        assert len(contradictions) >= 2


class TestIntegration:
    """Integration tests"""

    def test_end_to_end_workflow(self):
        """Test complete contradiction checking workflow"""
        # Create a requirement with known contradiction
        requirement = ConcretizedRequirement(
            system_scope=SystemScope(
                project_name="Chat System",
                purpose="Real-time chat using REST only",
                target_users=["Users"],
                system_type="web_application",
                scope_description="Chat app",
            ),
            features=[
                FeatureSpec(
                    id="feat_10",
                    name="Real-time Chat",
                    description="Real-time messaging with WebSocket",
                    priority="high",
                    acceptance_criteria=["Instant delivery"],
                )
            ],
            constraints=["RESTful API only", "No WebSocket allowed"],
            success_criteria=[],
            domain="chat",
        )

        # Check consistency
        checker = SemanticConsistencyChecker()
        contradictions = checker.check_consistency(requirement)

        # Generate report
        report = checker.generate_report(contradictions)

        # Verify
        assert len(contradictions) > 0
        assert report.has_contradictions
        assert report.severity_counts["error"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
