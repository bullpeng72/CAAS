"""
Frontend Specialist Agent (v0.5.0)

Dedicated agent for frontend UI generation with comprehensive validation.

Responsibilities:
- Analyze input requirements from tasks
- Design UI layout and widget placement
- Generate framework-specific code (Streamlit, Gradio, etc.)
- Validate UI completeness (all inputs have widgets)
- Test UI interaction flow

Phase: DELIVERY (parallel with CodeGenerator)
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from caas_framework.agents.base import AgentPhase, AgentWorkResult, BaseExpertAgent
from caas_framework.analysis.input_detector import InputDetector
from caas_framework.models.specifications import (
    AgentSpecModel,
    ConcretizedRequirement,
    TaskSpecModel,
)
from caas_framework.models.validation import ValidationIssue, ValidationSeverity
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils.logger import get_logger

logger = get_logger("agents.frontend_specialist")


@dataclass
class UIRequirement:
    """UI input requirement specification."""

    input_name: str
    widget_type: str  # "text_input", "number_input", "file_uploader", etc.
    prompt_message: str
    validation_rules: List["ValidationRule"] = field(default_factory=list)
    required: bool = True
    default_value: Optional[Any] = None
    help_text: Optional[str] = None
    placeholder: Optional[str] = None


@dataclass
class ValidationRule:
    """Validation rule for UI input."""

    type: str  # "not_empty", "regex", "range", "custom"
    expression: Optional[str] = None  # For regex or custom validation
    error_message: Optional[str] = None


@dataclass
class UILayout:
    """UI layout specification."""

    sections: List["UISection"] = field(default_factory=list)
    action_button: Optional[Dict[str, Any]] = None


@dataclass
class UISection:
    """UI section with widgets."""

    title: str
    widgets: List["UIWidget"] = field(default_factory=list)
    description: Optional[str] = None


@dataclass
class UIWidget:
    """UI widget specification."""

    input_name: str
    widget_type: str
    label: str
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    col_span: int = 12  # 1-12 for responsive layout
    required: bool = True
    default_value: Optional[Any] = None


@dataclass
class FrontendGenerationResult:
    """Result of frontend generation."""

    app_code: str
    ui_requirements: List[UIRequirement]
    ui_layout: UILayout
    validation_result: "UIValidationResult"
    framework: str = "streamlit"


@dataclass
class UIValidationResult:
    """Result of UI validation."""

    passed: bool
    issues: List[ValidationIssue]
    score: float = 10.0  # 0-10


class FrontendSpecialistAgent(BaseExpertAgent):
    """
    Frontend Specialist Agent

    Dedicated agent for frontend UI generation with comprehensive validation.
    Ensures all user inputs have corresponding UI widgets and proper validation.
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        golden_data: Optional[ConcretizedRequirement] = None,
        framework: str = "streamlit",
        enable_testing: bool = False,
    ):
        """
        Initialize Frontend Specialist Agent.

        Args:
            llm_plugin: LLM plugin for generation
            golden_data: Golden Data reference
            framework: UI framework (streamlit, gradio)
            enable_testing: Enable UI interaction testing
        """
        super().__init__(
            llm_plugin=llm_plugin,
            golden_data=golden_data,
            phase=AgentPhase.DELIVERY,
        )
        self.framework = framework
        self.enable_testing = enable_testing

    @property
    def agent_name(self) -> str:
        return "frontend_specialist"

    @property
    def agent_role(self) -> str:
        return "Frontend UI Specialist"

    @property
    def agent_expertise(self) -> List[str]:
        return [
            "UI/UX design",
            "Streamlit development",
            "Input validation",
            "Widget mapping",
            "User interaction flow",
        ]

    async def _do_work(
        self,
        requirement: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        previous_outputs: Optional[Dict[Any, Any]] = None,
    ) -> Any:
        """
        Internal work method (BaseExpertAgent interface).

        Delegates to work() method for actual implementation.
        """
        # Extract necessary data from context
        agents = context.get("agents", []) if context else []
        tasks = context.get("tasks", []) if context else []
        backend_files = context.get("backend_files", {}) if context else {}

        return await self.work(agents=agents, tasks=tasks, backend_files=backend_files)

    async def _refine_implementation(
        self,
        output: Any,
        feedback: List[ValidationIssue],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Refine implementation based on feedback.

        For Frontend Specialist, this would re-generate UI with feedback.
        """
        # Not implemented yet - return original output
        return output

    async def work(
        self,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
        backend_files: Dict[str, str],
        **kwargs,
    ) -> FrontendGenerationResult:
        """
        Generate frontend UI code with comprehensive validation.

        Workflow:
        1. Analyze input requirements from tasks
        2. Design UI layout
        3. Generate framework code
        4. Validate completeness
        5. Auto-fix issues if needed

        Args:
            agents: List of agent specifications
            tasks: List of task specifications
            backend_files: Backend code files (main.py, agents.py, etc.)

        Returns:
            FrontendGenerationResult with generated UI code
        """
        logger.info(f"🎨 Frontend Specialist Agent starting UI generation ({self.framework})")

        # Step 1: Analyze input requirements using 5-strategy fallback
        logger.info("📋 Analyzing UI requirements...")
        ui_requirements = self._analyze_ui_requirements(tasks)
        logger.info(f"✅ Found {len(ui_requirements)} input requirements")

        # Step 2: Design UI layout
        logger.info("🎨 Designing UI layout...")
        ui_layout = await self._design_ui_layout(ui_requirements, self.golden_data)
        logger.info(f"✅ Layout designed with {len(ui_layout.sections)} sections")

        # Step 3: Generate framework code
        logger.info(f"💻 Generating {self.framework} code...")
        app_code = self._generate_framework_code(ui_layout, agents, tasks, backend_files)
        logger.info(f"✅ Generated {len(app_code)} characters of code")

        # Step 4: Validate completeness
        logger.info("🔍 Validating UI completeness...")
        validation_result = self._validate_ui_completeness(app_code, ui_requirements)

        if not validation_result.passed:
            logger.warning(
                f"⚠️ UI validation found {len(validation_result.issues)} issues - attempting auto-fix"
            )
            # Auto-fix
            app_code = self._auto_fix_ui_issues(app_code, validation_result.issues)

            # Re-validate
            validation_result = self._validate_ui_completeness(app_code, ui_requirements)

            if not validation_result.passed:
                logger.error(
                    f"❌ UI validation still failed after auto-fix: {len(validation_result.issues)} issues"
                )
            else:
                logger.info("✅ Auto-fix successful - UI validation passed")
        else:
            logger.info("✅ UI validation passed on first attempt")

        return FrontendGenerationResult(
            app_code=app_code,
            ui_requirements=ui_requirements,
            ui_layout=ui_layout,
            validation_result=validation_result,
            framework=self.framework,
        )

    def _analyze_ui_requirements(
        self, tasks: List[TaskSpecModel]
    ) -> List[UIRequirement]:
        """
        Extract UI requirements from tasks using 5-strategy approach.

        Uses InputDetector.detect_input_requirements_unified() which guarantees
        at least 1 input (never returns empty list).

        Strategy 1: Template variables ({keyword})
        Strategy 2: INPUT_COLLECTION_PHRASES detection
        Strategy 3: human_input flag
        Strategy 4: Keyword matching (입력, 검색, search, input)
        Strategy 5: Default 'keyword' input (fallback)

        Args:
            tasks: List of task specifications

        Returns:
            List of UIRequirement objects (guaranteed non-empty)
        """
        # Convert TaskSpecModel to dict for InputDetector
        tasks_dict = [
            {
                "id": task.id,
                "description": task.description,
                "expected_output": task.expected_output,
                "human_input": getattr(task, "human_input", False),
            }
            for task in tasks
        ]

        # Use enhanced InputDetector with 5-strategy fallback
        input_specs = InputDetector.detect_input_requirements_unified(tasks_dict)

        # Convert to UIRequirement objects
        ui_requirements = []

        for input_spec in input_specs:
            input_name = input_spec["input_name"]
            input_type = input_spec.get("input_type", "text")
            prompt_message = input_spec.get("prompt_message", input_name)

            # Infer widget type from input type
            widget_type = self._infer_widget_type(input_type)

            # Infer validation rules
            validation_rules = self._infer_validation_rules(input_name, input_type)

            # Create placeholder
            placeholder = self._generate_placeholder(input_name, input_type)

            ui_requirements.append(
                UIRequirement(
                    input_name=input_name,
                    widget_type=widget_type,
                    prompt_message=prompt_message,
                    validation_rules=validation_rules,
                    required=True,
                    placeholder=placeholder,
                )
            )

        # Guarantee at least 1 requirement (defensive check, should already be guaranteed)
        if not ui_requirements:
            logger.warning(
                "⚠️ No UI requirements detected - adding default 'keyword' input"
            )
            ui_requirements.append(
                UIRequirement(
                    input_name="keyword",
                    widget_type="text_input",
                    prompt_message="검색 키워드",
                    validation_rules=[ValidationRule(type="not_empty")],
                    required=True,
                    placeholder="예: AI 기술 동향",
                )
            )

        return ui_requirements

    def _infer_widget_type(self, input_type: str) -> str:
        """
        Infer Streamlit widget type from input type.

        Args:
            input_type: Input type (keyword, text, number, file, url)

        Returns:
            Streamlit widget type
        """
        widget_map = {
            "keyword": "text_input",
            "text": "text_area",
            "number": "number_input",
            "file": "file_uploader",
            "url": "text_input",
            "email": "text_input",
            "date": "date_input",
            "time": "time_input",
            "boolean": "checkbox",
            "select": "selectbox",
            "multiselect": "multiselect",
        }

        return widget_map.get(input_type, "text_input")

    def _infer_validation_rules(
        self, input_name: str, input_type: str
    ) -> List[ValidationRule]:
        """
        Infer validation rules based on input name and type.

        Args:
            input_name: Input variable name
            input_type: Input type

        Returns:
            List of validation rules
        """
        rules = []

        # Always require non-empty
        rules.append(
            ValidationRule(
                type="not_empty",
                error_message=f"{input_name} is required",
            )
        )

        # Type-specific rules
        if input_type == "url":
            rules.append(
                ValidationRule(
                    type="regex",
                    expression=r"^https?://",
                    error_message="Must be a valid URL",
                )
            )
        elif input_type == "email":
            rules.append(
                ValidationRule(
                    type="regex",
                    expression=r"^[^@]+@[^@]+\.[^@]+$",
                    error_message="Must be a valid email",
                )
            )
        elif input_type == "number":
            rules.append(
                ValidationRule(
                    type="range",
                    expression="min:0",
                    error_message="Must be a positive number",
                )
            )

        return rules

    def _generate_placeholder(self, input_name: str, input_type: str) -> str:
        """Generate helpful placeholder text."""
        placeholders = {
            "keyword": "예: AI 기술 동향",
            "url": "https://example.com",
            "email": "user@example.com",
            "text": "텍스트를 입력하세요...",
            "number": "0",
        }

        return placeholders.get(input_type, f"Enter {input_name}")

    async def _design_ui_layout(
        self,
        ui_requirements: List[UIRequirement],
        golden_data: Optional[ConcretizedRequirement],
    ) -> UILayout:
        """
        Design UI layout using LLM.

        Creates a user-friendly layout with sections, widgets, and action button.

        Args:
            ui_requirements: List of UI requirements
            golden_data: Golden Data reference

        Returns:
            UILayout specification
        """
        # Build prompt for LLM
        project_name = golden_data.project_name if golden_data else "Multi-Agent System"
        description = golden_data.description if golden_data else "AI-powered system"

        requirements_text = "\n".join(
            [
                f"- {req.input_name} ({req.widget_type}): {req.prompt_message}"
                for req in ui_requirements
            ]
        )

        prompt = f"""Design a user-friendly UI layout for a {self.framework} application.

Project: {project_name}
Description: {description}

Input Requirements:
{requirements_text}

Design a layout that:
1. Groups related inputs together
2. Uses appropriate widget types
3. Has clear labels and placeholders
4. Includes validation feedback
5. Has a prominent action button

Return JSON with this structure:
{{
    "sections": [
        {{
            "title": "Input Section",
            "description": "Enter your parameters",
            "widgets": [
                {{
                    "input_name": "keyword",
                    "widget_type": "text_input",
                    "label": "검색 키워드:",
                    "placeholder": "예: AI 기술 동향",
                    "help_text": "Enter keywords to search",
                    "col_span": 12,
                    "required": true
                }}
            ]
        }}
    ],
    "action_button": {{
        "label": "Run Analysis",
        "icon": "▶️",
        "position": "center"
    }}
}}

Return ONLY valid JSON, no explanations."""

        try:
            response = await self.llm.ainvoke(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )

            # Parse JSON response
            layout_dict = json.loads(response)

            # Convert to UILayout
            sections = []
            for section_data in layout_dict.get("sections", []):
                widgets = []
                for widget_data in section_data.get("widgets", []):
                    widgets.append(UIWidget(**widget_data))

                sections.append(
                    UISection(
                        title=section_data["title"],
                        description=section_data.get("description"),
                        widgets=widgets,
                    )
                )

            action_button = layout_dict.get("action_button", {
                "label": "Run",
                "icon": "▶️",
                "position": "center"
            })

            return UILayout(sections=sections, action_button=action_button)

        except Exception as e:
            logger.warning(f"⚠️ LLM layout design failed: {e} - using default layout")
            # Fallback: Create simple single-section layout
            widgets = [
                UIWidget(
                    input_name=req.input_name,
                    widget_type=req.widget_type,
                    label=f"{req.prompt_message}:",
                    placeholder=req.placeholder,
                    required=req.required,
                )
                for req in ui_requirements
            ]

            return UILayout(
                sections=[UISection(title="Input Parameters", widgets=widgets)],
                action_button={"label": "Run", "icon": "▶️", "position": "center"},
            )

    def _generate_framework_code(
        self,
        ui_layout: UILayout,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
        backend_files: Dict[str, str],
    ) -> str:
        """
        Generate framework-specific code.

        Args:
            ui_layout: UI layout specification
            agents: Agent specifications
            tasks: Task specifications
            backend_files: Backend code files

        Returns:
            Generated app code
        """
        if self.framework == "streamlit":
            return self._generate_streamlit_code(ui_layout, agents, tasks, backend_files)
        else:
            raise ValueError(f"Unsupported framework: {self.framework}")

    def _generate_streamlit_code(
        self,
        ui_layout: UILayout,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
        backend_files: Dict[str, str],
    ) -> str:
        """
        Generate Streamlit app.py code.

        Args:
            ui_layout: UI layout specification
            agents: Agent specifications
            tasks: Task specifications
            backend_files: Backend code files

        Returns:
            Streamlit app code
        """
        project_name = self.golden_data.project_name if self.golden_data else "Multi-Agent System"
        description = self.golden_data.description if self.golden_data else "AI-powered system"

        # Build widget code
        widget_codes = []
        input_dict_items = []
        validation_checks = []

        for section in ui_layout.sections:
            for widget in section.widgets:
                # Generate widget code
                widget_code = self._generate_widget_code(widget)
                widget_codes.append(widget_code)

                # Add to input dict
                input_dict_items.append(f'"{widget.input_name}": {widget.input_name}')

                # Add validation
                if widget.required:
                    validation_checks.append(f"not {widget.input_name}")

        # Join components
        widgets_section = "\n".join(widget_codes)
        input_dict = "{" + ", ".join(input_dict_items) + "}"
        validation_condition = " or ".join(validation_checks) if validation_checks else "False"

        action_button = ui_layout.action_button or {"label": "Run", "icon": "▶️"}

        # Generate full code
        code = f'''"""
{project_name} - Streamlit UI

{description}

Auto-generated by CAAS v0.5.0 Frontend Specialist Agent
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from main import main

# Page configuration
st.set_page_config(
    page_title="{project_name}",
    page_icon="🤖",
    layout="wide"
)

# Title and description
st.title("🤖 {project_name}")
st.markdown("""
{description}
""")
st.markdown("---")

# Sidebar with info
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown(f"""
    This is an AI-powered multi-agent system built with CrewAI.

    **System Info:**
    - Agents: {len(agents)}
    - Tasks: {len(tasks)}
    - Framework: CrewAI

    **Generated by:**
    - CAAS v0.5.0
    - Frontend Specialist Agent
    """)

    st.markdown("---")
    st.caption("Powered by CAAS Framework")

# Main content
st.subheader("📝 Input Parameters")

# Input widgets
{widgets_section}

st.markdown("---")

# Action button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run_button = st.button(
        "{action_button.get('icon', '▶️')} {action_button.get('label', 'Run')}",
        type="primary",
        use_container_width=True
    )

# Execution section
if run_button:
    # Validate inputs
    if {validation_condition}:
        st.error("⚠️ Please fill in all required fields!")
    else:
        with st.spinner("🔄 Processing... This may take a moment."):
            try:
                # Prepare inputs
                user_inputs = {input_dict}

                # Execute the crew
                result = main(inputs=user_inputs)

                # Display success
                st.success("✅ Completed successfully!")

                # Display results
                st.markdown("---")
                st.subheader("📊 Results")

                # Format output
                if result:
                    if isinstance(result, str):
                        st.markdown(result)
                    elif hasattr(result, 'raw'):
                        st.markdown(result.raw)
                    else:
                        st.text(str(result))
                else:
                    st.info("No output generated")

            except Exception as e:
                st.error(f"❌ Error occurred: {{str(e)}}")

                with st.expander("🔍 Error Details"):
                    st.code(str(e))

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 20px;'>
        <small>Generated by CAAS v0.5.0 Frontend Specialist Agent | CrewAI Multi-Agent System</small>
    </div>
    """,
    unsafe_allow_html=True
)
'''

        return code

    def _generate_widget_code(self, widget: UIWidget) -> str:
        """
        Generate code for a single widget.

        Args:
            widget: Widget specification

        Returns:
            Python code string
        """
        label = widget.label
        key = widget.input_name
        placeholder = widget.placeholder or ""
        help_text = widget.help_text or ""

        if widget.widget_type == "text_input":
            return f'{key} = st.text_input("{label}", key="{key}", placeholder="{placeholder}", help="{help_text}")'
        elif widget.widget_type == "text_area":
            return f'{key} = st.text_area("{label}", key="{key}", placeholder="{placeholder}", help="{help_text}")'
        elif widget.widget_type == "number_input":
            return f'{key} = st.number_input("{label}", key="{key}", min_value=0, help="{help_text}")'
        elif widget.widget_type == "file_uploader":
            return f'{key} = st.file_uploader("{label}", key="{key}", help="{help_text}")'
        elif widget.widget_type == "checkbox":
            return f'{key} = st.checkbox("{label}", key="{key}", help="{help_text}")'
        elif widget.widget_type == "selectbox":
            return f'{key} = st.selectbox("{label}", options=[], key="{key}", help="{help_text}")'
        else:
            # Default to text_input
            return f'{key} = st.text_input("{label}", key="{key}", placeholder="{placeholder}")'

    def _validate_ui_completeness(
        self,
        app_code: str,
        ui_requirements: List[UIRequirement],
    ) -> UIValidationResult:
        """
        Validate that generated UI satisfies all requirements.

        Checks:
        1. All inputs have corresponding widgets
        2. main() is called with inputs parameter
        3. Validation logic is correct
        4. Error handling exists

        Args:
            app_code: Generated app code
            ui_requirements: UI requirements

        Returns:
            UIValidationResult
        """
        issues = []

        # Check 1: Widget existence
        for requirement in ui_requirements:
            widget_pattern = rf"st\.{requirement.widget_type}\([^)]*[\'\"]?{requirement.input_name}[\'\"]?"

            if not re.search(widget_pattern, app_code):
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        issue_type="missing_widget",
                        message=f"Widget for '{requirement.input_name}' not found",
                        suggested_fix=f"Add: {requirement.input_name} = st.{requirement.widget_type}(...)",
                        auto_fix_available=True,
                    )
                )

        # Check 2: main() call
        if "main(inputs=" not in app_code and "main(inputs =" not in app_code:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    issue_type="missing_inputs_param",
                    message="main() not called with inputs parameter",
                    suggested_fix="Change 'result = main()' to 'result = main(inputs=user_inputs)'",
                    auto_fix_available=True,
                )
            )

        # Check 3: Validation logic
        for requirement in ui_requirements:
            if requirement.required:
                validation_pattern = rf"(if|elif)\s+not\s+{requirement.input_name}"

                if not re.search(validation_pattern, app_code):
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            issue_type="missing_validation",
                            message=f"No validation for required input '{requirement.input_name}'",
                            suggested_fix=f"Add: if not {requirement.input_name}: st.error('Required!')",
                            auto_fix_available=True,
                        )
                    )

        # Check 4: Error handling
        if "try:" not in app_code or "except Exception" not in app_code:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    issue_type="missing_error_handling",
                    message="No error handling for main() execution",
                    suggested_fix="Wrap main() call in try-except block",
                    auto_fix_available=False,
                )
            )

        passed = len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0

        return UIValidationResult(
            passed=passed,
            issues=issues,
            score=10.0 - len(issues) * 1.5,
        )

    def _auto_fix_ui_issues(
        self,
        app_code: str,
        issues: List[ValidationIssue],
    ) -> str:
        """
        Auto-fix UI issues by patching code.

        Uses regex-based pattern replacement for simple fixes.

        Args:
            app_code: Original app code
            issues: Validation issues

        Returns:
            Fixed app code
        """
        fixed_code = app_code

        for issue in issues:
            if issue.issue_type == "missing_widget" and issue.auto_fix_available:
                # Extract input name from message
                match = re.search(r"'([^']+)'", issue.message)
                if match:
                    input_name = match.group(1)

                    # Generate widget code
                    widget_code = f'{input_name} = st.text_input("{input_name}:", key="{input_name}")'

                    # Insert after "# Input widgets" comment
                    pattern = r"(# Input widgets\s*\n)"
                    replacement = rf"\1{widget_code}\n"
                    fixed_code = re.sub(pattern, replacement, fixed_code, count=1)

            elif issue.issue_type == "missing_inputs_param" and issue.auto_fix_available:
                # Replace main() with main(inputs=user_inputs)
                pattern = r"result\s*=\s*main\s*\(\s*\)"
                replacement = "result = main(inputs=user_inputs)"
                fixed_code = re.sub(pattern, replacement, fixed_code)

        return fixed_code
