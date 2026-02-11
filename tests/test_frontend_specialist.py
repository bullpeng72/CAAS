"""
Test suite for Frontend Specialist Agent (v0.5.0)

Tests the FrontendSpecialistAgent implementation.
Target coverage: 90%+
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from caas_framework.agents.frontend_specialist import (
    FrontendSpecialistAgent,
    UIRequirement,
    UILayout,
    UISection,
    UIWidget,
    ValidationRule,
    FrontendGenerationResult,
    UIValidationResult,
)
from caas_framework.models.specifications import (
    AgentSpecModel,
    TaskSpecModel,
    ConcretizedRequirement,
)


class TestFrontendSpecialistAgent:
    """Test FrontendSpecialistAgent initialization and basic properties."""

    def test_initialization(self):
        """Test agent initialization with default parameters."""
        llm = MagicMock()
        golden_data = MagicMock(spec=ConcretizedRequirement)

        agent = FrontendSpecialistAgent(
            llm_plugin=llm, golden_data=golden_data, framework="streamlit"
        )

        assert agent.agent_name == "frontend_specialist"
        assert agent.agent_role == "Frontend UI Specialist"
        assert agent.framework == "streamlit"
        assert agent.enable_testing is False
        assert len(agent.agent_expertise) == 5

    def test_initialization_with_custom_framework(self):
        """Test agent initialization with custom framework."""
        llm = MagicMock()
        agent = FrontendSpecialistAgent(
            llm_plugin=llm, framework="gradio", enable_testing=True
        )

        assert agent.framework == "gradio"
        assert agent.enable_testing is True


class TestAnalyzeUIRequirements:
    """Test _analyze_ui_requirements method."""

    def test_analyzes_template_variables(self):
        """Test UI requirements extraction from template variables."""
        llm = MagicMock()
        agent = FrontendSpecialistAgent(llm_plugin=llm)

        tasks = [
            TaskSpecModel(
                id="task1",
                description="Search for {keyword}",
                agent="agent1",
                expected_output="Results",
            )
        ]

        requirements = agent._analyze_ui_requirements(tasks)

        assert len(requirements) >= 1
        assert any(req.input_name == "keyword" for req in requirements)

    def test_guarantees_at_least_one_requirement(self):
        """Test that at least 1 requirement is always returned."""
        llm = MagicMock()
        agent = FrontendSpecialistAgent(llm_plugin=llm)

        # Empty tasks
        requirements = agent._analyze_ui_requirements([])

        assert len(requirements) >= 1
        assert requirements[0].input_name == "keyword"
        assert requirements[0].widget_type == "text_input"

    def test_infers_correct_widget_types(self):
        """Test widget type inference from input types."""
        llm = MagicMock()
        agent = FrontendSpecialistAgent(llm_plugin=llm)

        # Test different widget types
        assert agent._infer_widget_type("keyword") == "text_input"
        assert agent._infer_widget_type("text") == "text_area"
        assert agent._infer_widget_type("number") == "number_input"
        assert agent._infer_widget_type("file") == "file_uploader"
        assert agent._infer_widget_type("url") == "text_input"

    def test_infers_validation_rules(self):
        """Test validation rule inference."""
        llm = MagicMock()
        agent = FrontendSpecialistAgent(llm_plugin=llm)

        rules = agent._infer_validation_rules("keyword", "keyword")

        assert len(rules) >= 1
        assert any(rule.type == "not_empty" for rule in rules)

    def test_infers_url_validation(self):
        """Test URL-specific validation rules."""
        llm = MagicMock()
        agent = FrontendSpecialistAgent(llm_plugin=llm)

        rules = agent._infer_validation_rules("url", "url")

        assert any(rule.type == "regex" for rule in rules)
        assert any("https?" in rule.expression for rule in rules if rule.expression)


class TestDesignUILayout:
    """Test _design_ui_layout method."""

    @pytest.mark.asyncio
    async def test_design_layout_with_llm(self):
        """Test UI layout design using LLM."""
        llm = AsyncMock()
        llm.ainvoke.return_value = """{
            "sections": [{
                "title": "Input Section",
                "widgets": [{
                    "input_name": "keyword",
                    "widget_type": "text_input",
                    "label": "키워드:",
                    "placeholder": "검색어 입력",
                    "required": true,
                    "col_span": 12
                }]
            }],
            "action_button": {
                "label": "검색",
                "icon": "🔍",
                "position": "center"
            }
        }"""

        golden_data = MagicMock(spec=ConcretizedRequirement)
        golden_data.project_name = "Search System"
        golden_data.description = "Search for information"

        agent = FrontendSpecialistAgent(llm_plugin=llm, golden_data=golden_data)

        ui_requirements = [
            UIRequirement(
                input_name="keyword",
                widget_type="text_input",
                prompt_message="키워드",
                validation_rules=[],
                required=True,
            )
        ]

        layout = await agent._design_ui_layout(ui_requirements, golden_data)

        assert len(layout.sections) == 1
        assert layout.sections[0].title == "Input Section"
        assert len(layout.sections[0].widgets) == 1
        assert layout.action_button["label"] == "검색"

    @pytest.mark.asyncio
    async def test_design_layout_fallback_on_error(self):
        """Test fallback to default layout when LLM fails."""
        llm = AsyncMock()
        llm.ainvoke.side_effect = Exception("LLM error")

        golden_data = MagicMock(spec=ConcretizedRequirement)
        agent = FrontendSpecialistAgent(llm_plugin=llm, golden_data=golden_data)

        ui_requirements = [
            UIRequirement(
                input_name="keyword",
                widget_type="text_input",
                prompt_message="키워드",
                validation_rules=[],
                required=True,
            )
        ]

        layout = await agent._design_ui_layout(ui_requirements, golden_data)

        # Should use fallback layout
        assert len(layout.sections) == 1
        assert layout.sections[0].title == "Input Parameters"
        assert len(layout.sections[0].widgets) == 1


class TestGenerateStreamlitCode:
    """Test _generate_streamlit_code method."""

    def test_generates_valid_streamlit_code(self):
        """Test Streamlit code generation."""
        llm = MagicMock()
        golden_data = MagicMock(spec=ConcretizedRequirement)
        golden_data.project_name = "Test App"
        golden_data.description = "Test Description"

        agent = FrontendSpecialistAgent(llm_plugin=llm, golden_data=golden_data)

        layout = UILayout(
            sections=[
                UISection(
                    title="Input",
                    widgets=[
                        UIWidget(
                            input_name="keyword",
                            widget_type="text_input",
                            label="키워드:",
                            placeholder="검색어",
                            required=True,
                        )
                    ],
                )
            ],
            action_button={"label": "Run", "icon": "▶️"},
        )

        code = agent._generate_streamlit_code(layout, [], [], {})

        assert "import streamlit as st" in code
        assert "from main import main" in code
        assert "st.text_input" in code
        assert "keyword" in code
        assert "main(inputs=" in code

    def test_generates_widget_code(self):
        """Test individual widget code generation."""
        llm = MagicMock()
        agent = FrontendSpecialistAgent(llm_plugin=llm)

        widget = UIWidget(
            input_name="keyword",
            widget_type="text_input",
            label="키워드:",
            placeholder="검색어",
            help_text="도움말",
        )

        code = agent._generate_widget_code(widget)

        assert "st.text_input" in code
        assert "keyword" in code
        assert "키워드:" in code
        assert "검색어" in code


class TestValidateUICompleteness:
    """Test _validate_ui_completeness method."""

    def test_validates_widget_existence(self):
        """Test validation checks for widget existence."""
        llm = MagicMock()
        agent = FrontendSpecialistAgent(llm_plugin=llm)

        app_code = """
import streamlit as st
keyword = st.text_input("키워드:", key="keyword")
result = main(inputs=user_inputs)
"""

        requirements = [
            UIRequirement(
                input_name="keyword",
                widget_type="text_input",
                prompt_message="키워드",
                validation_rules=[],
            )
        ]

        result = agent._validate_ui_completeness(app_code, requirements)

        assert result.passed is True
        assert len(result.issues) == 0

    def test_detects_missing_widget(self):
        """Test detection of missing widgets."""
        llm = MagicMock()
        agent = FrontendSpecialistAgent(llm_plugin=llm)

        app_code = """
import streamlit as st
result = main(inputs=user_inputs)
"""

        requirements = [
            UIRequirement(
                input_name="keyword",
                widget_type="text_input",
                prompt_message="키워드",
                validation_rules=[],
            )
        ]

        result = agent._validate_ui_completeness(app_code, requirements)

        assert result.passed is False
        assert any(issue.issue_type == "missing_widget" for issue in result.issues)

    def test_detects_missing_inputs_param(self):
        """Test detection of missing inputs parameter in main() call."""
        llm = MagicMock()
        agent = FrontendSpecialistAgent(llm_plugin=llm)

        app_code = """
import streamlit as st
keyword = st.text_input("키워드:")
result = main()  # Missing inputs parameter
"""

        requirements = [
            UIRequirement(
                input_name="keyword",
                widget_type="text_input",
                prompt_message="키워드",
                validation_rules=[],
            )
        ]

        result = agent._validate_ui_completeness(app_code, requirements)

        assert any(
            issue.issue_type == "missing_inputs_param" for issue in result.issues
        )


class TestAutoFixUIIssues:
    """Test _auto_fix_ui_issues method."""

    def test_fixes_missing_widget(self):
        """Test auto-fix for missing widget."""
        llm = MagicMock()
        agent = FrontendSpecialistAgent(llm_plugin=llm)

        app_code = """# Input widgets
result = main(inputs=user_inputs)
"""

        from caas_framework.models.validation import ValidationIssue, ValidationSeverity

        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                issue_type="missing_widget",
                message="Widget for 'keyword' not found",
                auto_fix_available=True,
            )
        ]

        fixed_code = agent._auto_fix_ui_issues(app_code, issues)

        assert "keyword = st.text_input" in fixed_code

    def test_fixes_missing_inputs_param(self):
        """Test auto-fix for missing inputs parameter."""
        llm = MagicMock()
        agent = FrontendSpecialistAgent(llm_plugin=llm)

        app_code = "result = main()"

        from caas_framework.models.validation import ValidationIssue, ValidationSeverity

        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                issue_type="missing_inputs_param",
                message="main() not called with inputs parameter",
                auto_fix_available=True,
            )
        ]

        fixed_code = agent._auto_fix_ui_issues(app_code, issues)

        assert "main(inputs=user_inputs)" in fixed_code


@pytest.mark.asyncio
class TestWorkMethod:
    """Test the main work() method."""

    async def test_work_generates_frontend(self):
        """Test complete frontend generation workflow."""
        llm = AsyncMock()
        llm.ainvoke.return_value = """{
            "sections": [{
                "title": "Input",
                "widgets": [{
                    "input_name": "keyword",
                    "widget_type": "text_input",
                    "label": "키워드:",
                    "required": true,
                    "col_span": 12
                }]
            }],
            "action_button": {"label": "Run", "icon": "▶️"}
        }"""

        golden_data = MagicMock(spec=ConcretizedRequirement)
        golden_data.project_name = "Test"
        golden_data.description = "Test"

        agent = FrontendSpecialistAgent(llm_plugin=llm, golden_data=golden_data)

        agents = []
        tasks = [
            TaskSpecModel(
                id="task1",
                description="Search {keyword}",
                agent="agent1",
                expected_output="Results",
            )
        ]
        backend_files = {"main.py": "def main(): pass"}

        result = await agent.work(
            agents=agents, tasks=tasks, backend_files=backend_files
        )

        assert isinstance(result, FrontendGenerationResult)
        assert len(result.app_code) > 0
        assert len(result.ui_requirements) >= 1
        assert result.framework == "streamlit"


class TestIntegrationScenarios:
    """Integration test scenarios."""

    @pytest.mark.asyncio
    async def test_complete_workflow_with_auto_fix(self):
        """Test complete workflow including auto-fix."""
        llm = AsyncMock()
        llm.ainvoke.return_value = """{
            "sections": [{"title": "Input", "widgets": []}],
            "action_button": {"label": "Run"}
        }"""

        golden_data = MagicMock(spec=ConcretizedRequirement)
        golden_data.project_name = "Test"
        golden_data.description = "Test"

        agent = FrontendSpecialistAgent(llm_plugin=llm, golden_data=golden_data)

        tasks = [
            TaskSpecModel(
                id="task1",
                description="Process {keyword}",
                agent="agent1",
                expected_output="Output",
            )
        ]

        result = await agent.work(agents=[], tasks=tasks, backend_files={})

        # Should auto-fix missing widgets
        assert "keyword" in result.app_code
        assert result.validation_result.passed or len(result.validation_result.issues) < 3
