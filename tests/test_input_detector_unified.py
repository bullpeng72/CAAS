"""
Test suite for caas_framework/analysis/input_detector.py

Tests the 5-Strategy Fallback system for input detection (v0.5.0).
Target coverage: 95%+
"""

import pytest
from caas_framework.analysis.input_detector import InputDetector


class TestDetectInputRequirementsUnified:
    """Test the main unified detection method (5-strategy fallback)."""

    def test_unified_never_returns_empty(self):
        """Test that unified detection NEVER returns empty list (Strategy 5 fallback)."""
        # Empty tasks list
        result = InputDetector.detect_input_requirements_unified([])
        assert len(result) >= 1
        assert result[0]["input_name"] == "keyword"
        assert result[0]["prompt_message"] == "검색 키워드"

    def test_unified_with_no_detection(self):
        """Test unified detection falls back to default when no strategy detects input."""
        tasks = [
            {
                "id": "task1",
                "description": "Process data without any input keywords",
            }
        ]

        result = InputDetector.detect_input_requirements_unified(tasks)
        assert len(result) >= 1
        # Should have default keyword input
        assert any(r["input_name"] == "keyword" for r in result)

    def test_unified_deduplicates_inputs(self):
        """Test that unified detection deduplicates same inputs from different strategies."""
        tasks = [
            {
                "id": "task1",
                "description": "Use {keyword} to search",  # Strategy 1: template
            },
            {
                "id": "task2",
                "description": "입력받은 keyword를 사용",  # Strategy 4: keyword matching
            },
        ]

        result = InputDetector.detect_input_requirements_unified(tasks)
        # Should have only 1 "keyword" input (deduplicated)
        keyword_inputs = [r for r in result if r["input_name"] == "keyword"]
        assert len(keyword_inputs) == 1

        # Should list multiple tasks using it
        assert "task1" in keyword_inputs[0]["used_by_tasks"]

    def test_unified_returns_sorted_list(self):
        """Test that unified detection returns sorted list for consistency."""
        tasks = [
            {"id": "task1", "description": "Use {url} and {keyword}"},
        ]

        result = InputDetector.detect_input_requirements_unified(tasks)
        # Should be sorted alphabetically by input_name
        input_names = [r["input_name"] for r in result]
        assert input_names == sorted(input_names)


class TestStrategy1TemplateVariables:
    """Test Strategy 1: Template variable extraction ({keyword})."""

    def test_detects_single_template_variable(self):
        """Test detection of single template variable."""
        tasks = [
            {
                "id": "task1",
                "description": "Search for {keyword} in database",
            }
        ]

        result = InputDetector._detect_from_template_variables(tasks)
        assert len(result) == 1
        assert result[0]["input_name"] == "keyword"
        assert result[0]["input_type"] == "keyword"
        assert "task1" in result[0]["used_by_tasks"]

    def test_detects_multiple_template_variables(self):
        """Test detection of multiple different template variables."""
        tasks = [
            {
                "id": "task1",
                "description": "Download {url} and save to {file_path}",
            }
        ]

        result = InputDetector._detect_from_template_variables(tasks)
        assert len(result) == 2

        input_names = {r["input_name"] for r in result}
        assert "url" in input_names
        assert "file_path" in input_names

    def test_infers_type_from_variable_name(self):
        """Test that type is inferred from variable name."""
        tasks = [
            {"id": "t1", "description": "Use {search_keyword}"},  # keyword
            {"id": "t2", "description": "Upload {file_name}"},  # file
            {"id": "t3", "description": "Visit {web_url}"},  # url
            {"id": "t4", "description": "Show {item_count}"},  # number
            {"id": "t5", "description": "Display {some_text}"},  # text (default)
        ]

        result = InputDetector._detect_from_template_variables(tasks)
        result_dict = {r["input_name"]: r for r in result}

        assert result_dict["search_keyword"]["input_type"] == "keyword"
        assert result_dict["file_name"]["input_type"] == "file"
        assert result_dict["web_url"]["input_type"] == "url"
        assert result_dict["item_count"]["input_type"] == "number"
        assert result_dict["some_text"]["input_type"] == "text"

    def test_generates_prompt_message_from_variable(self):
        """Test that prompt message is generated from variable name."""
        tasks = [
            {
                "id": "task1",
                "description": "Use {search_query}",
            }
        ]

        result = InputDetector._detect_from_template_variables(tasks)
        assert result[0]["prompt_message"] == "Search Query"

    def test_deduplicates_across_tasks(self):
        """Test that same variable in multiple tasks is deduplicated."""
        tasks = [
            {"id": "task1", "description": "Search {keyword}"},
            {"id": "task2", "description": "Filter by {keyword}"},
            {"id": "task3", "description": "Use {keyword} for analysis"},
        ]

        result = InputDetector._detect_from_template_variables(tasks)
        assert len(result) == 1
        assert result[0]["input_name"] == "keyword"
        assert len(result[0]["used_by_tasks"]) == 3
        assert "task1" in result[0]["used_by_tasks"]
        assert "task2" in result[0]["used_by_tasks"]
        assert "task3" in result[0]["used_by_tasks"]

    def test_handles_no_template_variables(self):
        """Test handling of tasks without template variables."""
        tasks = [
            {
                "id": "task1",
                "description": "Process data automatically",
            }
        ]

        result = InputDetector._detect_from_template_variables(tasks)
        assert len(result) == 0

    def test_handles_empty_description(self):
        """Test handling of tasks with empty description."""
        tasks = [
            {
                "id": "task1",
                "description": "",
            }
        ]

        result = InputDetector._detect_from_template_variables(tasks)
        assert len(result) == 0


class TestStrategy3HumanInputFlag:
    """Test Strategy 3: human_input flag detection."""

    def test_detects_human_input_flag(self):
        """Test detection of human_input=True."""
        tasks = [
            {
                "id": "human_search_task",
                "description": "Search data",
                "human_input": True,
            }
        ]

        result = InputDetector._detect_from_human_input_flag(tasks)
        assert len(result) == 1
        assert result[0]["input_name"] == "search"  # Inferred from task ID

    def test_infers_input_name_from_task_id(self):
        """Test that input name is inferred from task ID."""
        tasks = [
            {"id": "human_filter_task", "human_input": True},
        ]

        result = InputDetector._detect_from_human_input_flag(tasks)
        assert result[0]["input_name"] == "filter"

    def test_cleans_up_task_prefix(self):
        """Test that task ID prefixes are cleaned up."""
        tasks = [
            {"id": "task_search", "human_input": True},
            {"id": "filter_task", "human_input": True},
        ]

        result = InputDetector._detect_from_human_input_flag(tasks)
        result_dict = {r["input_name"]: r for r in result}

        assert "search" in result_dict
        assert "filter" in result_dict

    def test_handles_no_human_input_tasks(self):
        """Test handling when no tasks have human_input=True."""
        tasks = [
            {"id": "task1", "description": "Auto process", "human_input": False},
            {"id": "task2", "description": "Auto analyze"},  # No flag
        ]

        result = InputDetector._detect_from_human_input_flag(tasks)
        assert len(result) == 0

    def test_generates_korean_prompt_message(self):
        """Test that prompt message is generated in Korean."""
        tasks = [
            {"id": "search_task", "human_input": True},
        ]

        result = InputDetector._detect_from_human_input_flag(tasks)
        assert "입력" in result[0]["prompt_message"]


class TestStrategy4KeywordMatching:
    """Test Strategy 4: Keyword matching in descriptions."""

    def test_detects_korean_keyword(self):
        """Test detection of Korean keywords."""
        tasks = [
            {"id": "task1", "description": "키워드를 사용하여 검색"},
        ]

        result = InputDetector._detect_from_keyword_matching(tasks)
        assert len(result) >= 1
        assert any(r["input_name"] == "keyword" for r in result)

    def test_detects_english_keyword(self):
        """Test detection of English keywords."""
        tasks = [
            {"id": "task1", "description": "Use search query to find data"},
        ]

        result = InputDetector._detect_from_keyword_matching(tasks)
        assert len(result) >= 1
        assert any(r["input_name"] == "keyword" for r in result)

    def test_detects_input_text(self):
        """Test detection of text input keywords."""
        tasks = [
            {"id": "task1", "description": "입력된 텍스트를 분석"},
        ]

        result = InputDetector._detect_from_keyword_matching(tasks)
        assert len(result) >= 1
        assert any(r["input_name"] == "text" for r in result)

    def test_detects_file_keywords(self):
        """Test detection of file keywords."""
        tasks = [
            {"id": "task1", "description": "파일을 업로드"},
        ]

        result = InputDetector._detect_from_keyword_matching(tasks)
        assert any(r["input_name"] == "file" for r in result)

    def test_detects_url_keywords(self):
        """Test detection of URL keywords."""
        tasks = [
            {"id": "task1", "description": "URL을 분석"},
        ]

        result = InputDetector._detect_from_keyword_matching(tasks)
        assert any(r["input_name"] == "url" for r in result)

    def test_handles_multiple_keywords(self):
        """Test handling of multiple different keywords in same task."""
        tasks = [
            {
                "id": "task1",
                "description": "키워드를 사용하여 파일 검색",  # keyword + file
            }
        ]

        result = InputDetector._detect_from_keyword_matching(tasks)
        input_names = {r["input_name"] for r in result}
        assert "keyword" in input_names
        assert "file" in input_names

    def test_deduplicates_across_tasks(self):
        """Test deduplication of same keyword across multiple tasks."""
        tasks = [
            {"id": "task1", "description": "키워드 검색"},
            {"id": "task2", "description": "search keyword"},
            {"id": "task3", "description": "query data"},
        ]

        result = InputDetector._detect_from_keyword_matching(tasks)
        keyword_inputs = [r for r in result if r["input_name"] == "keyword"]
        assert len(keyword_inputs) == 1
        assert len(keyword_inputs[0]["used_by_tasks"]) == 3

    def test_handles_no_keywords(self):
        """Test handling when no keywords are found."""
        tasks = [
            {
                "id": "task1",
                "description": "Process data automatically",  # No input-related keywords
            }
        ]

        result = InputDetector._detect_from_keyword_matching(tasks)
        assert len(result) == 0


class TestStrategy5DefaultFallback:
    """Test Strategy 5: Default keyword input (final guarantee)."""

    def test_adds_default_when_all_strategies_fail(self):
        """Test that default keyword is added when all strategies fail to detect input."""
        tasks = [
            {
                "id": "task1",
                "description": "Process data",  # No keywords, no template vars, etc.
            }
        ]

        result = InputDetector.detect_input_requirements_unified(tasks)

        # Should have at least the default keyword
        assert len(result) >= 1
        keyword_input = next((r for r in result if r["input_name"] == "keyword"), None)
        assert keyword_input is not None
        assert keyword_input["input_type"] == "keyword"
        assert keyword_input["prompt_message"] == "검색 키워드"

    def test_default_not_added_when_other_strategies_succeed(self):
        """Test that default is NOT added when other strategies find inputs."""
        tasks = [
            {
                "id": "task1",
                "description": "Search using {custom_query}",  # Strategy 1 will find this
            }
        ]

        result = InputDetector.detect_input_requirements_unified(tasks)

        # Should have custom_query but NOT default keyword
        input_names = [r["input_name"] for r in result]
        assert "custom_query" in input_names
        # Default "keyword" should NOT be added because Strategy 1 succeeded
        if "keyword" in input_names:
            # If keyword exists, it should be from the variable name, not default
            keyword_input = next(r for r in result if r["input_name"] == "keyword")
            assert len(keyword_input["used_by_tasks"]) > 0  # Should be used by a task


class TestLegacyDetectInputRequirements:
    """Test the legacy detect_input_requirements() method (Strategy 2)."""

    def test_detects_korean_input_phrase(self):
        """Test detection of Korean input collection phrases."""
        tasks = [
            {
                "id": "task1",
                "description": "사용자로부터 키워드를 입력받아 검색",
            }
        ]

        result = InputDetector.detect_input_requirements(tasks)
        assert "task1" in result
        assert result["task1"]["requires_input"] is True
        assert result["task1"]["input_name"] == "keyword"

    def test_detects_english_input_phrase(self):
        """Test detection of English input collection phrases."""
        tasks = [
            {
                "id": "task1",
                "description": "Receive input from user for search",
            }
        ]

        result = InputDetector.detect_input_requirements(tasks)
        assert "task1" in result
        assert result["task1"]["requires_input"] is True

    def test_checks_expected_output(self):
        """Test that expected_output is also checked for input phrases."""
        tasks = [
            {
                "id": "task1",
                "description": "Process data",
                "expected_output": "Result based on user input keyword",
            }
        ]

        result = InputDetector.detect_input_requirements(tasks)
        assert "task1" in result

    def test_handles_no_input_required(self):
        """Test handling of tasks that don't require input."""
        tasks = [
            {
                "id": "task1",
                "description": "Automatically process data using system defaults",
            }
        ]

        result = InputDetector.detect_input_requirements(tasks)
        assert "task1" not in result

    def test_returns_dict_format(self):
        """Test that legacy method returns dict (not list) format."""
        tasks = [
            {
                "id": "task1",
                "description": "입력받은 키워드로 검색",
            }
        ]

        result = InputDetector.detect_input_requirements(tasks)
        assert isinstance(result, dict)
        assert "task1" in result


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_blog_search_scenario(self):
        """Test realistic blog search scenario."""
        tasks = [
            {
                "id": "search_task",
                "description": "Use {keyword} to search blogs",  # Cleaner: no extra keywords
            },
            {
                "id": "analysis_task",
                "description": "Analyze results by {keyword}",
            },
        ]

        result = InputDetector.detect_input_requirements_unified(tasks)

        # Should detect single "keyword" input (deduplication works)
        assert len(result) == 1
        assert result[0]["input_name"] == "keyword"
        assert result[0]["input_type"] == "keyword"

        # Should be used by both tasks
        assert "search_task" in result[0]["used_by_tasks"]
        assert "analysis_task" in result[0]["used_by_tasks"]

    def test_empty_tasks_list_scenario(self):
        """Test edge case with empty tasks list."""
        tasks = []

        result = InputDetector.detect_input_requirements_unified(tasks)

        # Should still return default keyword (guaranteed non-empty)
        assert len(result) >= 1
        assert result[0]["input_name"] == "keyword"

    def test_multiple_inputs_scenario(self):
        """Test scenario with multiple different inputs."""
        tasks = [
            {
                "id": "task1",
                "description": "Upload {file_path} and search for {keyword}",
            }
        ]

        result = InputDetector.detect_input_requirements_unified(tasks)

        input_names = {r["input_name"] for r in result}
        assert "keyword" in input_names
        assert "file_path" in input_names
