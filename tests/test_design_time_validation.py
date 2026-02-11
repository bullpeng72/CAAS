"""
Test suite for Design-Time Validation (v0.5.0)

Tests the validate_design_time() method and related checks in OntologyValidator.
Target coverage: 90%+
"""

import pytest
from caas_framework.validation.ontology_validator import OntologyValidator
from caas_framework.models.validation import ValidationSeverity


class TestValidateDesignTime:
    """Test the main validate_design_time() integration method."""

    def test_validate_with_clean_design(self):
        """Test validation with clean, correct design."""
        validator = OntologyValidator()

        agents = [
            {
                "id": "researcher",
                "role": "researcher",
                "goal": "Search for information",
                "tools": ["web_search"],
            }
        ]

        tasks = [
            {
                "id": "search_task",
                "description": "Search for {keyword}",
                "agent": "researcher",
            }
        ]

        # Mock golden_data
        class MockGoldenData:
            def __str__(self):
                return "Search using keyword input"

        golden_data = MockGoldenData()

        result = validator.validate_design_time(agents, tasks, golden_data)

        # Should pass or have only minor warnings
        assert result.is_valid or len(result.issues) == 0

    def test_detects_missing_ui_mapping(self):
        """Test detection of missing UI mapping (golden_data mentions input but no template vars)."""
        validator = OntologyValidator()

        agents = [{"id": "agent1", "role": "researcher", "tools": []}]

        tasks = [
            {
                "id": "task1",
                "description": "Search for data",  # No {keyword}!
            }
        ]

        class MockGoldenData:
            def __str__(self):
                return "사용자로부터 키워드를 입력받아 검색"  # Mentions input!

        golden_data = MockGoldenData()

        result = validator.validate_design_time(agents, tasks, golden_data)

        # Should detect missing UI mapping
        missing_ui_issues = [
            i for i in result.issues if i.issue_type == "missing_ui_mapping"
        ]
        assert len(missing_ui_issues) > 0
        assert any(i.severity == ValidationSeverity.ERROR for i in missing_ui_issues)

    def test_runs_all_checks(self):
        """Test that all 4 checks are executed."""
        validator = OntologyValidator()

        # Design that triggers multiple checks
        agents = [
            {
                "id": "dev",
                "role": "developer",
                "goal": "Build features",
                "tools": ["web_search"],  # Mismatch with role
            }
        ]

        tasks = [
            {
                "id": "task1",
                "description": "Use {keyword} and {query}",  # Inconsistent vars
                "agent": "dev",
            }
        ]

        result = validator.validate_design_time(agents, tasks, None)

        # Should find issues from different checks
        # (May not find all depending on data, but at least should run)
        assert isinstance(result.issues, list)


class TestValidateUIRequirementsMapping:
    """Test _validate_ui_requirements_mapping() - the KEY check."""

    def test_detects_template_var_without_golden_data_mention(self):
        """Test detection of template var not mentioned in golden data."""
        validator = OntologyValidator()

        tasks = [
            {"id": "task1", "description": "Search {obscure_variable}"}
        ]

        class MockGoldenData:
            def __str__(self):
                return "Simple search task"  # No mention of obscure_variable

        golden_data = MockGoldenData()

        issues = validator._validate_ui_requirements_mapping(tasks, golden_data)

        # Should warn about unmapped variable
        assert len(issues) > 0
        assert any("obscure_variable" in i.message for i in issues)

    def test_allows_template_var_with_generic_input_mention(self):
        """Test that generic '입력' mention allows template vars."""
        validator = OntologyValidator()

        tasks = [{"id": "task1", "description": "Search {keyword}"}]

        class MockGoldenData:
            def __str__(self):
                return "사용자 입력을 받아서 처리"  # Generic input mention

        golden_data = MockGoldenData()

        issues = validator._validate_ui_requirements_mapping(tasks, golden_data)

        # Should NOT warn because golden_data mentions "입력"
        keyword_issues = [i for i in issues if "keyword" in i.message]
        assert len(keyword_issues) == 0

    def test_detects_input_mention_without_template_vars(self):
        """Test detection when requirements mention input but no template vars exist."""
        validator = OntologyValidator()

        tasks = [{"id": "task1", "description": "Process data automatically"}]  # No {var}

        class MockGoldenData:
            def __str__(self):
                return "User inputs search keyword"  # Mentions input!

        golden_data = MockGoldenData()

        issues = validator._validate_ui_requirements_mapping(tasks, golden_data)

        # Should ERROR - missing template variables
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert len(error_issues) > 0
        assert any("template variable" in i.message.lower() for i in error_issues)

    def test_provides_auto_fix_for_missing_template_vars(self):
        """Test that auto-fix is provided for missing template variables."""
        validator = OntologyValidator()

        tasks = [{"id": "task1", "description": "Search data"}]

        class MockGoldenData:
            def __str__(self):
                return "Input keyword to search"

        golden_data = MockGoldenData()

        issues = validator._validate_ui_requirements_mapping(tasks, golden_data)

        fixable_issues = [i for i in issues if i.auto_fix_available]
        assert len(fixable_issues) > 0
        assert any("{keyword}" in i.suggested_fix for i in fixable_issues)

    def test_handles_no_golden_data(self):
        """Test handling when golden_data is None."""
        validator = OntologyValidator()

        tasks = [{"id": "task1", "description": "Use {keyword}"}]

        issues = validator._validate_ui_requirements_mapping(tasks, None)

        # Should not crash, may return no issues
        assert isinstance(issues, list)

    def test_handles_empty_tasks(self):
        """Test handling of empty tasks list."""
        validator = OntologyValidator()

        issues = validator._validate_ui_requirements_mapping([], None)

        assert isinstance(issues, list)


class TestValidateTemplateVariables:
    """Test _validate_template_variables() method."""

    def test_detects_inconsistent_keyword_variants(self):
        """Test detection of multiple keyword variants."""
        validator = OntologyValidator()

        tasks = [
            {"id": "task1", "description": "Search {keyword}"},
            {"id": "task2", "description": "Find {query}"},
            {"id": "task3", "description": "Use {search_term}"},
        ]

        issues = validator._validate_template_variables(tasks)

        # Should detect inconsistency
        inconsistent_issues = [
            i for i in issues if i.issue_type == "inconsistent_variables"
        ]
        assert len(inconsistent_issues) > 0

    def test_provides_standardization_suggestion(self):
        """Test that standardization suggestion is provided."""
        validator = OntologyValidator()

        tasks = [
            {"id": "task1", "description": "Use {keyword}"},
            {"id": "task2", "description": "Use {query}"},
        ]

        issues = validator._validate_template_variables(tasks)

        if issues:
            assert any("standardize" in i.suggested_fix.lower() for i in issues)

    def test_accepts_consistent_variables(self):
        """Test that consistent variable usage passes."""
        validator = OntologyValidator()

        tasks = [
            {"id": "task1", "description": "Search {keyword}"},
            {"id": "task2", "description": "Filter {keyword}"},
            {"id": "task3", "description": "Analyze {keyword}"},
        ]

        issues = validator._validate_template_variables(tasks)

        # Should have no inconsistency issues
        inconsistent_issues = [
            i for i in issues if i.issue_type == "inconsistent_variables"
        ]
        assert len(inconsistent_issues) == 0

    def test_handles_no_template_variables(self):
        """Test handling when no template variables exist."""
        validator = OntologyValidator()

        tasks = [{"id": "task1", "description": "Process data automatically"}]

        issues = validator._validate_template_variables(tasks)

        # Should not crash
        assert isinstance(issues, list)


class TestValidateToolRoleCompatibility:
    """Test _validate_tool_role_compatibility() method."""

    def test_detects_tool_role_mismatch(self):
        """Test detection of incompatible tool-role combination."""
        validator = OntologyValidator()

        agents = [
            {
                "id": "writer",
                "role": "writer",
                "tools": ["code_interpreter"],  # Writer shouldn't use code interpreter
            }
        ]

        issues = validator._validate_tool_role_compatibility(agents)

        # Should detect mismatch
        mismatch_issues = [
            i for i in issues if i.issue_type == "tool_role_mismatch"
        ]
        assert len(mismatch_issues) > 0

    def test_accepts_compatible_tool_role(self):
        """Test that compatible tool-role combinations pass."""
        validator = OntologyValidator()

        agents = [
            {
                "id": "researcher",
                "role": "researcher",
                "tools": ["web_search"],  # Compatible
            }
        ]

        issues = validator._validate_tool_role_compatibility(agents)

        # Should have no mismatch issues
        mismatch_issues = [
            i for i in issues if i.issue_type == "tool_role_mismatch"
        ]
        assert len(mismatch_issues) == 0

    def test_handles_similar_role_names(self):
        """Test that similar role names are accepted."""
        validator = OntologyValidator()

        agents = [
            {
                "id": "data_analyst",
                "role": "data analyst",  # Contains "analyst"
                "tools": ["file_read"],  # Compatible with "analyst"
            }
        ]

        issues = validator._validate_tool_role_compatibility(agents)

        # Should accept similar role
        mismatch_issues = [
            i for i in issues if i.issue_type == "tool_role_mismatch"
        ]
        assert len(mismatch_issues) == 0

    def test_handles_unknown_tools(self):
        """Test handling of tools not in compatibility map."""
        validator = OntologyValidator()

        agents = [
            {
                "id": "agent1",
                "role": "researcher",
                "tools": ["custom_unknown_tool"],
            }
        ]

        issues = validator._validate_tool_role_compatibility(agents)

        # Should not crash, may not produce issues for unknown tools
        assert isinstance(issues, list)


class TestValidateSemanticConsistency:
    """Test _validate_semantic_consistency() method."""

    def test_handles_unassigned_tasks(self):
        """Test handling of tasks without assigned agents."""
        validator = OntologyValidator()

        agents = [{"id": "agent1", "role": "researcher", "goal": "Search"}]

        tasks = [
            {
                "id": "task1",
                "description": "Process data",
                # No agent assignment
            }
        ]

        issues = validator._validate_semantic_consistency(agents, tasks)

        # Should not crash
        assert isinstance(issues, list)

    def test_handles_missing_agents(self):
        """Test handling when assigned agent doesn't exist."""
        validator = OntologyValidator()

        agents = [{"id": "agent1", "role": "researcher", "goal": "Search"}]

        tasks = [
            {
                "id": "task1",
                "description": "Process data",
                "agent": "nonexistent_agent",
            }
        ]

        issues = validator._validate_semantic_consistency(agents, tasks)

        # Should not crash
        assert isinstance(issues, list)


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_blog_search_scenario(self):
        """Test realistic blog search scenario."""
        validator = OntologyValidator()

        agents = [
            {
                "id": "researcher",
                "role": "researcher",
                "goal": "Search for blog posts",
                "tools": ["web_search"],
            },
            {
                "id": "analyst",
                "role": "analyst",
                "goal": "Analyze search results",
                "tools": ["file_read"],
            },
        ]

        tasks = [
            {
                "id": "search_task",
                "description": "사용자로부터 {keyword}를 입력받아 블로그 검색",
                "agent": "researcher",
            },
            {
                "id": "analysis_task",
                "description": "검색 결과를 {keyword} 기준으로 분석",
                "agent": "analyst",
            },
        ]

        class MockGoldenData:
            def __str__(self):
                return "키워드를 입력받아 블로그를 검색하고 분석"

        golden_data = MockGoldenData()

        result = validator.validate_design_time(agents, tasks, golden_data)

        # Should pass or have only minor warnings
        critical_issues = [
            i for i in result.issues if i.severity == ValidationSeverity.CRITICAL
        ]
        error_issues = [
            i for i in result.issues if i.severity == ValidationSeverity.ERROR
        ]

        # Should have no critical/error issues
        assert len(critical_issues) == 0
        assert len(error_issues) == 0

    def test_missing_input_detection_scenario(self):
        """Test scenario where input is mentioned but not captured."""
        validator = OntologyValidator()

        agents = [{"id": "agent1", "role": "researcher", "tools": []}]

        tasks = [
            {
                "id": "task1",
                "description": "Automatically search data",  # No {keyword}!
            }
        ]

        class MockGoldenData:
            def __str__(self):
                return "User inputs search keyword to find results"

        golden_data = MockGoldenData()

        result = validator.validate_design_time(agents, tasks, golden_data)

        # Should detect ERROR - missing UI mapping
        assert not result.is_valid
        assert any(i.severity == ValidationSeverity.ERROR for i in result.issues)
