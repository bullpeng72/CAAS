"""
Code Generator Agent

Expert agent responsible for Phase 5 (Delivery):
- Generates production-ready code
- Creates tests, documentation, deployment files
- Ensures code quality and best practices
- Integrates error handling and logging
"""

from typing import Any, Dict, List, Optional

from caas_framework.agents.base import AgentPhase, BaseExpertAgent, ValidationIssue
from caas_framework.agents.code_gen_helpers import (
    CodeAutoFix,
    CodeValidation,
    StaticFileGenerators,
)
from caas_framework.agents.process_selector import ProcessSelector
from caas_framework.agents.registry import register_agent
from caas_framework.agents.utils import AgentErrorHandler, AgentOutputParser
from caas_framework.config.settings import LLMConstants
from caas_framework.exceptions import (
    AgentExecutionError,
    CodeGenerationError,
    TemplateRenderingError,
)
from caas_framework.models.specifications import (
    AgentSpecModel,
    ConcretizedRequirement,
    TaskSpecModel,
)
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils import PromptBuilder, ResponseParser
from caas_framework.utils.logger import get_logger

logger = get_logger()


@register_agent(phase=AgentPhase.DELIVERY)
class CodeGeneratorAgent(BaseExpertAgent):
    """
    Code Generator Agent

    Specializes in generating production-ready code from
    agent/task specifications and architecture design.
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        golden_data: Optional[ConcretizedRequirement] = None,
    ):
        super().__init__(llm_plugin, golden_data, AgentPhase.DELIVERY)
        self.process_selector = ProcessSelector()
        # ✅ P1-1: Initialize frontend config instance variables
        self._current_enable_frontend = False
        self._current_frontend_framework = "streamlit"

    @property
    def agent_name(self) -> str:
        return "CodeGenerator"

    @property
    def agent_role(self) -> str:
        return "Expert Code Generator"

    @property
    def agent_expertise(self) -> List[str]:
        return [
            "Python code generation",
            "CrewAI implementation",
            "Test-driven development",
            "Error handling patterns",
            "Logging best practices",
            "Documentation generation",
            "Deployment automation",
            "Code quality assurance",
        ]

    async def _do_work(
        self,
        requirement: Optional[str],
        context: Optional[Dict[str, Any]],
        previous_outputs: Optional[Dict[AgentPhase, Any]],
    ) -> Dict[str, Any]:
        """
        Generate production-ready code.

        Returns:
            Dict with:
            - files: Dict[str, str] - Generated code files
            - project_structure: Dict - Project structure
            - generation_metadata: Dict - Generation details
        """
        self._build_context_summary(context, previous_outputs)

        # Get design and architecture from previous phases
        design = previous_outputs.get(AgentPhase.DESIGN) if previous_outputs else None
        architecture = (
            previous_outputs.get(AgentPhase.ARCHITECTURE) if previous_outputs else None
        )
        analysis = (
            previous_outputs.get(AgentPhase.DISCOVERY) if previous_outputs else None
        )

        if not design:
            return {"error": "No design provided for code generation"}

        # Extract agents and tasks
        agents = design.get("agents", [])
        tasks = design.get("tasks", [])

        # If no agents/tasks, return empty dict (no code generated)
        if not agents or not tasks:
            return {}

        # ✅ FIX #1: Extract frontend configuration from context
        enable_frontend = context.get("enable_frontend") if context else None
        frontend_framework = context.get("frontend_framework") if context else None

        # ✅ P1-1: Store in instance variables for fallback access
        self._current_enable_frontend = enable_frontend if enable_frontend is not None else False
        self._current_frontend_framework = frontend_framework if frontend_framework else "streamlit"

        # Generate code using LLM
        generated_files = await self._generate_code_files(
            agents=agents,
            tasks=tasks,
            architecture=architecture,
            analysis=analysis,
            requirement=requirement,
            enable_frontend=enable_frontend,  # ✅ FIX #1: Pass frontend config
            frontend_framework=frontend_framework,  # ✅ FIX #1: Pass framework choice
        )

        # Evaluate code quality with LLM Judge (if enabled)
        quality_evaluation = await self._evaluate_code_quality(
            (
                generated_files.get("files")
                if isinstance(generated_files, dict) and "files" in generated_files
                else generated_files
            ),
            agents=agents,
            tasks=tasks,
        )

        # Extract files and metadata from generated_files
        if (
            isinstance(generated_files, dict)
            and "_boundaries_violations" in generated_files
        ):
            # generated_files already contains metadata
            result = generated_files.copy()
        else:
            # No metadata, wrap in result dict
            result = (
                generated_files.copy()
                if isinstance(generated_files, dict)
                else {"files": generated_files}
            )

        # Add quality evaluation metadata
        if quality_evaluation:
            result["_quality_evaluation"] = {
                "overall_score": quality_evaluation.overall_score,
                "passed": quality_evaluation.passed,
                "summary": quality_evaluation.summary,
                "issues": quality_evaluation.issues,
                "recommendations": quality_evaluation.recommendations,
            }

        # Return the generated files with all metadata
        return result

    async def _generate_code_files(
        self,
        agents: List[Any],
        tasks: List[Any],
        architecture: Optional[Dict[str, Any]],
        analysis: Optional[Dict[str, Any]],
        requirement: Optional[str],
        enable_frontend: Optional[bool] = None,  # ✅ FIX #1: Frontend override
        frontend_framework: Optional[str] = None,  # ✅ FIX #1: Framework choice
    ) -> Dict[str, str]:
        """Generate actual code files using LLM."""

        # Build comprehensive prompt
        prompt = self._build_code_generation_prompt(
            agents, tasks, architecture, analysis, requirement, enable_frontend, frontend_framework
        )

        # Call LLM with retry logic from base class
        response = await self._execute_with_retry(
            lambda: self.llm.ainvoke(
                messages=[{"role": "user", "content": prompt}],
                response_format=LLMConstants.RESPONSE_FORMAT_JSON,
                temperature=LLMConstants.TEMPERATURE_PRECISE,
                max_tokens=4000,
            ),
            operation="code generation",
        )

        # Debug logging
        raw_response = str(response)[:1000]
        logger.info(
            f"[CodeGenerator] Raw LLM response (first 1000 chars): {raw_response}"
        )

        # Parse response using helper
        code_structure = await AgentOutputParser.parse_llm_json(
            response,
            expected_fields=["files"],
            fallback_factory=lambda: self._create_fallback_code(
                agents,
                tasks,
                enable_frontend=self._current_enable_frontend,  # ✅ P1-1: Pass from instance
                frontend_framework=self._current_frontend_framework  # ✅ P1-1: Pass from instance
            ),
            agent_name=self.agent_name,
        )

        logger.info(
            f"[CodeGenerator] Parsed code_structure keys: {list(code_structure.keys()) if code_structure else 'None'}"
        )

        if code_structure and "files" in code_structure:
            files = code_structure["files"]
            logger.info(
                f"[CodeGenerator] Files count: {len(files)}, file sizes: {[(k, len(v)) for k, v in files.items()]}"
            )

        # If LLM didn't return files, use fallback
        if not code_structure or "files" not in code_structure:
            logger.warning("[CodeGenerator] No files in response, using fallback")
            code_structure = self._create_fallback_code(
                agents,
                tasks,
                enable_frontend=self._current_enable_frontend,  # ✅ P1-1: Pass from instance
                frontend_framework=self._current_frontend_framework  # ✅ P1-1: Pass from instance
            )
            logger.info(
                f"[CodeGenerator] Fallback generated {len(code_structure.get('files', {}))} files"
            )
            if code_structure and "files" in code_structure:
                files = code_structure["files"]
                logger.info(
                    f"[CodeGenerator] Fallback file sizes: {[(k, len(v)) for k, v in files.items()]}"
                )

        result_files = code_structure.get("files", {})
        logger.info(f"[CodeGenerator] Returning {len(result_files)} files")

        # CRITICAL: Validate generated code contains CrewAI imports
        if result_files:
            has_crewai = CodeValidation.validate_crewai_code(result_files)
            if not has_crewai:
                logger.error(
                    "[CodeGenerator] Generated code does NOT contain CrewAI imports!"
                )
                logger.warning(
                    "[CodeGenerator] LLM generated wrong format, forcing fallback"
                )
                # Force fallback with proper CrewAI code
                fallback = self._create_fallback_code(
                    agents,
                    tasks,
                    enable_frontend=self._current_enable_frontend,  # ✅ P1-1: Pass from instance
                    frontend_framework=self._current_frontend_framework  # ✅ P1-1: Pass from instance
                )
                result_files = fallback.get("files", {})
                logger.info(
                    f"[CodeGenerator] Forced fallback generated {len(result_files)} files"
                )

        # CRITICAL: Auto-fix common Agent bugs and ensure tools.py exists
        if result_files:
            result_files = self._autofix_generated_code(result_files, agents)
            logger.info("[CodeGenerator] Auto-fix validation complete")

        # ✅ v0.4.2 (P0-2): Quality validation for frontend code
        if result_files and self._current_enable_frontend:
            from caas_framework.validation.code_quality_validator import CodeQualityValidator

            validator = CodeQualityValidator()

            app_code = result_files.get("app.py", "")
            main_code = result_files.get("main.py", "")

            if app_code and main_code:
                logger.info("[CodeGenerator] Running frontend quality validation...")

                validation_result = validator.validate_frontend(
                    app_code=app_code,
                    main_code=main_code,
                    framework=self._current_frontend_framework or "streamlit"
                )

                # Log validation report
                report = validator.format_validation_report(validation_result)
                logger.info(report)

                # If validation failed, use fallback
                if validation_result.use_fallback:
                    logger.warning(
                        f"[CodeGenerator] Frontend quality validation FAILED "
                        f"(score={validation_result.score:.1f}/10.0, "
                        f"{len([i for i in validation_result.issues if i.severity == 'critical'])} critical issues)"
                    )
                    logger.warning("[CodeGenerator] Forcing fallback due to low quality")

                    # Force fallback
                    fallback = self._create_fallback_code(
                        agents,
                        tasks,
                        enable_frontend=self._current_enable_frontend,
                        frontend_framework=self._current_frontend_framework
                    )
                    result_files = fallback.get("files", {})
                    logger.info(
                        f"[CodeGenerator] Fallback generated {len(result_files)} files due to quality failure"
                    )
                else:
                    logger.info(
                        f"[CodeGenerator] Frontend quality validation PASSED "
                        f"(score={validation_result.score:.1f}/10.0)"
                    )

        # CRITICAL: Validate boundaries if specified
        boundaries_violations = []
        if self.golden_data and self.golden_data.boundaries:
            violations = CodeValidation.validate_boundaries(
                result_files, self.golden_data.boundaries
            )
            if violations:
                logger.error(
                    f"[CodeGenerator] BOUNDARY VIOLATIONS DETECTED: {len(violations)}"
                )
                for violation in violations:
                    logger.error(f"  - {violation}")
                boundaries_violations = violations

        # Return files with boundaries metadata
        result = result_files.copy()
        if boundaries_violations:
            result["_boundaries_violations"] = boundaries_violations

        return result


    def _autofix_generated_code(
        self, files: Dict[str, str], agents: List[Any]
    ) -> Dict[str, str]:
        """
        Auto-fix common bugs in LLM-generated code.

        Uses CodeAutoFix helper to eliminate duplication.

        Args:
            files: Dictionary of filename -> content
            agents: List of agent specifications

        Returns:
            Fixed files dictionary
        """
        import re

        from caas_framework.utils import ObjectAccessor

        fixed_files = files.copy()

        # Fix agents.py using helper
        if "agents.py" in fixed_files:
            fixed_files["agents.py"] = CodeAutoFix.fix_agent_code(fixed_files["agents.py"])

        # Ensure tools.py exists if agents have tools
        agents_data = ObjectAccessor.to_dict_list(agents)
        all_tools = set()
        for agent in agents_data:
            if agent.get("tools"):
                all_tools.update(agent["tools"])

        if all_tools and "tools.py" not in fixed_files:
            logger.warning(
                f"[AutoFix] tools.py missing but {len(all_tools)} tools needed - generating"
            )
            tools_py = self._generate_tools_file_fallback(all_tools)
            fixed_files["tools.py"] = tools_py

            # Add tools import to agents.py using helper
            if "agents.py" in fixed_files:
                fixed_files["agents.py"] = CodeAutoFix.ensure_tools_import(
                    fixed_files["agents.py"], all_tools
                )

        # Fix main.py for hierarchical process using helper
        if "main.py" in fixed_files:
            fixed_files["main.py"] = CodeAutoFix.add_manager_llm(
                fixed_files["main.py"], is_main_py=True
            )

        # Fix crew.py if it exists
        for crew_file in ["crew.py", "src/crew.py"]:
            if crew_file in fixed_files:
                fixed_files[crew_file] = CodeAutoFix.add_manager_llm(
                    fixed_files[crew_file], is_main_py=False
                )

        return fixed_files

    def _build_code_generation_prompt(
        self,
        agents: List[Any],
        tasks: List[Any],
        architecture: Optional[Dict[str, Any]],
        analysis: Optional[Dict[str, Any]],
        requirement: Optional[str],
        enable_frontend: Optional[bool] = None,  # ✅ FIX #1: Frontend override
        frontend_framework: Optional[str] = None,  # ✅ FIX #1: Framework choice
    ) -> str:
        """Build LLM prompt for code generation."""

        # Convert agents and tasks to dicts if they're Pydantic models
        from caas_framework.utils import ObjectAccessor

        agents_data = ObjectAccessor.to_dict_list(agents)
        tasks_data = ObjectAccessor.to_dict_list(tasks)

        # ✅ FIX #1: Build task description with frontend requirements
        # ✅ v0.5.0: 한국어 주석/docstring 강제 (P0 수정)
        task_description = """당신은 완전한 CrewAI 애플리케이션을 생성하는 전문 Python 개발자입니다.

**중요: 모든 주석(comments)과 docstring을 한국어로 작성하세요.**
- 함수/클래스의 docstring은 한국어로
- 코드 내 주석(# ...)은 한국어로
- 변수명, 함수명은 영어 snake_case 유지

핵심 요구사항: CrewAI 프레임워크를 반드시 사용해야 합니다.
- 항상 'from crewai import Crew, Agent, Task, Process' 사용
- CrewAI 없이 단순 Python/FastAPI/Streamlit 코드 생성 금지
- 요구사항 설명은 시스템이 무엇을 하는지이지만, CrewAI 에이전트와 태스크로 구현해야 함
- CrewAI 에이전트가 작업을 조율하며, FastAPI나 Streamlit을 대체하는 것이 아님"""

        # ✅ v0.4.2 (P0-1): Enhanced frontend prompt with examples and checklist
        if enable_frontend:
            framework_name = frontend_framework or "streamlit"

            # Streamlit-specific enhanced prompt
            if framework_name == "streamlit":
                task_description += """

═══════════════════════════════════════════════════════════════════
📱 STREAMLIT UI 생성 MANDATORY REQUIREMENTS (v0.4.2)
═══════════════════════════════════════════════════════════════════

🎯 CRITICAL SUCCESS CRITERIA:

1️⃣ INPUT WIDGETS 생성 (MANDATORY):
   ✅ tasks.py를 분석하여 필요한 입력 자동 감지
   ✅ 각 입력마다 st.text_input() 또는 적절한 위젯 생성
   ✅ 예시: keyword = st.text_input("검색 키워드:", key="keyword")
   ❌ 절대 빈 Input 섹션 생성 금지!

2️⃣ INPUT VALIDATION (MANDATORY):
   ✅ if not keyword: st.error("⚠️ 키워드를 입력하세요!")
   ✅ 모든 필수 입력 검증
   ❌ 빈 리스트 검증 금지: if any(not val for val in [])  # WRONG!

3️⃣ MAIN 함수 호출 (CRITICAL):
   ✅ inputs dict 준비: user_inputs = {"keyword": keyword}
   ✅ result = main(inputs=user_inputs)  # CORRECT
   ❌ result = main()  # WRONG - inputs 파라미터 없이 호출 금지!

4️⃣ ERROR HANDLING (MANDATORY):
   ✅ try-except로 crew.kickoff() 감싸기
   ✅ st.error(f"❌ 오류: {e}") 표시

5️⃣ RESULT DISPLAY (MANDATORY):
   ✅ st.markdown(result.raw) if hasattr(result, 'raw')
   ✅ 결과를 보기 좋게 포맷팅

═══════════════════════════════════════════════════════════════════
📝 COMPLETE EXAMPLE CODE (Follow this pattern exactly):
═══════════════════════════════════════════════════════════════════

```python
\"\"\"
AI 보고서 생성 시스템 - Streamlit UI
\"\"\"
import streamlit as st
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))
from main import main

# Page config
st.set_page_config(page_title="AI 시스템", page_icon="🤖", layout="wide")

st.title("🤖 AI 보고서 생성 시스템")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown(\"\"\"
    CrewAI 기반 멀티 에이전트 시스템

    **Powered by:**
    - CrewAI Framework
    - CAAS Generator
    \"\"\")

# Input section
st.subheader("📝 입력")

# ✅ CRITICAL: Create input widgets (detect from tasks)
keyword = st.text_input("검색 키워드:", key="keyword",
                        placeholder="예: AI 기술 동향")

st.markdown("---")

# Run button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run_button = st.button("▶️ 실행", type="primary", use_container_width=True)

# Execution
if run_button:
    # ✅ CRITICAL: Validate inputs
    if not keyword:
        st.error("⚠️ 키워드를 입력하세요!")
    else:
        with st.spinner("🔄 AI 에이전트가 작업 중입니다..."):
            try:
                # ✅ CRITICAL: Call main with inputs dict
                user_inputs = {"keyword": keyword}
                result = main(inputs=user_inputs)

                # Success
                st.success("✅ 보고서 생성 완료!")

                st.markdown("---")
                st.subheader("📊 결과")

                # ✅ CRITICAL: Format result properly
                if result:
                    if isinstance(result, str):
                        st.markdown(result)
                    elif hasattr(result, 'raw'):
                        st.markdown(result.raw)
                    else:
                        st.text(str(result))
                else:
                    st.info("결과가 생성되지 않았습니다")

            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")
                with st.expander("🔍 상세 오류"):
                    st.code(str(e))

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>"
            "<small>Powered by CAAS Framework</small></div>",
            unsafe_allow_html=True)
```

═══════════════════════════════════════════════════════════════════
🚨 COMMON MISTAKES TO AVOID:
═══════════════════════════════════════════════════════════════════

❌ WRONG: Empty input section
   # Input section


❌ WRONG: result = main() without inputs

❌ WRONG: if any(not val for val in []): # Empty list validation

✅ CORRECT: Follow the example above exactly!

═══════════════════════════════════════════════════════════════════

ALSO UPDATE main.py TO ACCEPT inputs PARAMETER:

```python
def main(inputs=None):
    \"\"\"
    Main execution function.

    Args:
        inputs: Optional dict of user inputs. If None, prompts for CLI input.
    \"\"\"
    agents = create_agents()
    tasks = create_tasks(agents)

    # ✅ CRITICAL: Handle both CLI and Frontend modes
    if inputs is None:
        # CLI mode - prompt for input
        user_inputs = {}
        keyword = input("검색할 키워드를 입력하세요: ")
        user_inputs["keyword"] = keyword
    else:
        # Frontend mode - use provided inputs
        user_inputs = inputs

    crew = Crew(agents=list(agents.values()), tasks=tasks,
                process=Process.sequential, verbose=True)
    result = crew.kickoff(inputs=user_inputs)  # ✅ Pass inputs!
    return result
```

═══════════════════════════════════════════════════════════════════
"""
            else:
                # Generic frontend prompt (React, Vue, etc.)
                task_description += f"""

FRONTEND UI REQUIREMENT:
- MANDATORY: Generate a {framework_name} user interface
- Create app.py with {framework_name} UI code that calls the CrewAI crew
- Add {framework_name} to requirements.txt
- Update main.py to support both CLI and {framework_name} modes
- The {framework_name} app should provide an interactive interface for users
"""

        builder = PromptBuilder(
            "generate production-ready Python code for a CrewAI multi-agent system"
        ).add_task(task_description)

        # Add input data
        input_data = {
            "requirement": requirement or "Task management system",
            "agents_count": len(agents_data),
            "tasks_count": len(tasks_data),
        }

        if self.golden_data:
            input_data["project_name"] = self.golden_data.project_name
            input_data["features"] = (
                len(self.golden_data.features) if self.golden_data.features else 0
            )

        builder.add_input(**input_data)

        # Add agents and tasks
        builder.add_context("Agents Design", agents_data, format_as_json=True)
        builder.add_context("Tasks Design", tasks_data, format_as_json=True)

        # Add architecture if available
        if architecture:
            tech_stack = architecture.get("technology_stack", {})
            builder.add_context("Technology Stack", tech_stack, format_as_json=True)

        # ✅ FIX #1: Define output format with optional frontend file
        output_files = {
            "main.py": "# Main crew execution script",
            "agents.py": "# Agent definitions",
            "tasks.py": "# Task definitions",
            "requirements.txt": "# Dependencies",
            "README.md": "# Documentation",
            ".env.example": "# Environment variables template",
        }

        # ✅ FIX #1: Add frontend file if enabled
        if enable_frontend:
            framework_name = frontend_framework or "streamlit"
            output_files["app.py"] = f"# {framework_name.capitalize()} UI application"

        builder.add_output_format(
            {"files": output_files},
            "Generate a complete CrewAI project with the following files:",
        )

        # ✅ v0.4.2 (P0-1): Enhanced guidelines with frontend checklist
        # ✅ v0.5.0: 한국어 주석/docstring 강제 (P0 수정)
        guidelines = [
            "**중요: 모든 주석(comments)과 docstring을 한국어로 작성하세요**",
            "변수명, 함수명, 클래스명은 영어 snake_case/PascalCase 유지",
            "MANDATORY: CrewAI 프레임워크 사용 - from crewai import Crew, Agent, Task",
            "MANDATORY: agents.py는 crewai.Agent를 사용하여 Agent 객체 정의",
            "MANDATORY: tasks.py는 crewai.Task를 사용하여 Task 객체 정의",
            "MANDATORY: main.py는 Crew를 생성하고 crew.kickoff() 호출",
            "CRITICAL: Agent() 생성자 - 'id' 파라미터 사용 금지 (자동 생성됨)",
            "CRITICAL: Agent() tools 파라미터 - 도구 없으면 빈 리스트 [] 사용, 문자열 리스트 절대 금지",
            "CRITICAL: 에이전트가 도구 필요 시, tools.py도 BaseTool 클래스로 생성 필수",
            "설계된 모든 에이전트와 태스크가 포함된 작동하는 CrewAI 애플리케이션 생성",
            "적절한 CrewAI import 포함: from crewai import Crew, Agent, Task, Process",
            "requirements.txt에 crewai와 기타 의존성 추가",
            "에러 핸들링과 로깅 추가",
            "Python 모범 사례와 PEP 8 준수",
            "명확한 주석과 docstring 포함 (한국어로)",
            "설정 및 사용법이 포함된 README 생성",
            "민감한 데이터는 환경변수 사용 (OPENAI_API_KEY 등)",
            "모듈화되고 유지보수 가능한 코드 작성",
        ]

        # ✅ v0.4.2 (P0-1): Add frontend-specific guidelines
        if enable_frontend:
            frontend_guidelines = [
                "🎯 FRONTEND CHECKLIST:",
                "✅ app.py: Create actual input widgets (st.text_input, etc.) - NOT empty lines!",
                "✅ app.py: Validate all inputs before calling main()",
                "✅ app.py: Call main(inputs=user_inputs) with inputs dict - NOT main() alone!",
                "✅ app.py: Wrap crew execution in try-except with st.error() for errors",
                "✅ app.py: Display results with proper formatting (st.markdown, st.text)",
                "✅ main.py: Define main(inputs=None) with optional inputs parameter",
                "✅ main.py: if inputs is None: collect CLI inputs, else: use frontend inputs",
                "✅ main.py: crew.kickoff(inputs=user_inputs) - pass inputs to kickoff!",
                "❌ NEVER generate empty input sections in app.py",
                "❌ NEVER call main() without inputs parameter in app.py",
                "❌ NEVER validate empty lists: if any(not val for val in [])",
            ]
            guidelines.extend(frontend_guidelines)

        builder.add_guidelines(guidelines)

        return builder.build()

    def _create_fallback_code(
        self,
        agents: List[Any],
        tasks: List[Any],
        enable_frontend: bool = False,  # ✅ P0-1: Frontend support
        frontend_framework: str = "streamlit",  # ✅ P0-1: Framework choice
    ) -> Dict[str, Any]:
        """Create basic code structure when LLM fails using AST-based generation."""

        # Convert to dicts if needed
        from caas_framework.utils import ObjectAccessor

        agents_data = ObjectAccessor.to_dict_list(agents)
        tasks_data = ObjectAccessor.to_dict_list(tasks)

        # Extract all unique tools from agents for tools.py generation
        all_tools = set()
        for agent in agents_data:
            if agent.get("tools"):
                all_tools.update(agent["tools"])

        # Generate tools.py if tools are present
        tools_py = None
        if all_tools:
            tools_py = self._generate_tools_file_fallback(all_tools)

        # Use AST-based code generation for Python files
        main_py = self._generate_main_file_ast(agents_data, tasks_data)
        agents_py = self._generate_agents_file_ast(agents_data)
        tasks_py = self._generate_tasks_file_ast(tasks_data)

        # Non-Python files using StaticFileGenerators
        requirements_txt = StaticFileGenerators.generate_requirements(
            enable_frontend=enable_frontend,  # ✅ P0-1: Pass frontend flag
            frontend_framework=frontend_framework  # ✅ P0-1: Pass framework
        )
        readme_md = StaticFileGenerators.generate_readme(
            project_name=self.golden_data.project_name if self.golden_data else "CrewAI Project",
            features=self.golden_data.features if self.golden_data else [],
            enable_frontend=enable_frontend,  # ✅ P0-1: Pass frontend flag
            frontend_framework=frontend_framework  # ✅ P0-1: Pass framework
        )
        env_example = StaticFileGenerators.generate_env_example()

        # Build files dict
        files_dict = {
            "main.py": main_py,
            "agents.py": agents_py,
            "tasks.py": tasks_py,
            "requirements.txt": requirements_txt,
            "README.md": readme_md,
            ".env.example": env_example,
        }

        # Add tools.py if generated
        if tools_py:
            files_dict["tools.py"] = tools_py

        # ✅ P0-1: Generate frontend UI file if enabled
        if enable_frontend:
            logger.info(f"[Fallback] Generating {frontend_framework} UI file")
            app_py = self._generate_streamlit_app(agents_data, tasks_data, frontend_framework)
            files_dict["app.py"] = app_py

        return {"files": files_dict}

    def _generate_streamlit_app(
        self,
        agents: List[Dict],
        tasks: List[Dict],
        framework: str = "streamlit"
    ) -> str:
        """
        ✅ P0-3: Generate Streamlit app.py file.

        Creates a user-friendly Streamlit interface that:
        - Detects required inputs from tasks
        - Generates appropriate input widgets
        - Calls the main() function with user inputs
        - Displays results in a formatted way
        """
        project_name = self.golden_data.project_name if self.golden_data else "CrewAI App"

        # ✅ v0.4.2: Detect input requirements (deduplicated)
        input_requirements = []
        try:
            from caas_framework.analysis.input_detector import InputDetector
            # Use new unified method to avoid duplicates
            input_requirements = InputDetector.detect_input_requirements_unified(tasks)
        except Exception as e:
            logger.warning(f"[Streamlit] Input detection failed: {e}, using default 'keyword'")
            # Fallback to default keyword input
            input_requirements = [{
                "input_name": "keyword",
                "input_type": "keyword",
                "prompt_message": "검색 키워드"
            }]

        # Build input widgets for each requirement
        input_widgets = []
        input_dict_items = []
        for req_spec in input_requirements:
            input_name = req_spec["input_name"]
            prompt_message = req_spec.get("prompt_message", input_name)

            # Convert to user-friendly display name
            display_name = prompt_message if prompt_message else input_name.replace("_", " ").title()

            input_widgets.append(
                f'{input_name} = st.text_input("{display_name}:", key="{input_name}", placeholder="예: AI 기술 동향")'
            )
            input_dict_items.append(f'"{input_name}": {input_name}')

        # Join all widgets
        widgets_code = "\n".join(input_widgets)
        input_dict_code = "{" + ", ".join(input_dict_items) + "}"

        # ✅ v0.4.2: Build validation list (variable names)
        validation_vars = [req_spec["input_name"] for req_spec in input_requirements]
        validation_list = ", ".join(validation_vars)

        # Detect if main() needs inputs parameter
        needs_inputs = len(input_requirements) > 0

        if needs_inputs:
            main_call = f"""# Prepare inputs
                user_inputs = {input_dict_code}

                # Call main with inputs
                result = main(inputs=user_inputs)"""
        else:
            main_call = "result = main()"

        return f'''"""
{project_name} - Streamlit UI

Auto-generated Streamlit interface for CrewAI multi-agent system.
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path to import main
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
st.markdown("---")

# Sidebar with info
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown("""
    This is an AI-powered multi-agent system built with CrewAI.

    **Powered by:**
    - CrewAI Framework
    - CAAS Generator
    """)

    st.markdown("---")
    st.caption("Generated by CAAS Framework")

# Main content
st.subheader("📝 Input")
st.markdown("Please provide the required information below:")

# Input section
{widgets_code}

st.markdown("---")

# Run button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run_button = st.button("▶️ Run", type="primary", use_container_width=True)

# Execution section
if run_button:
    # Validate inputs
    if any(not val for val in [{validation_list}]):
        st.error("⚠️ Please fill in all required fields!")
    else:
        with st.spinner("🔄 Processing... This may take a moment."):
            try:
                # Execute the crew
                {main_call}

                # Display success
                st.success("✅ Completed successfully!")

                # Display results
                st.markdown("---")
                st.subheader("📊 Results")

                # Format output
                if result:
                    # If result is a string, display as markdown
                    if isinstance(result, str):
                        st.markdown(result)
                    # If result has .raw attribute (CrewOutput)
                    elif hasattr(result, 'raw'):
                        st.markdown(result.raw)
                    # Otherwise, display as text
                    else:
                        st.text(str(result))
                else:
                    st.info("No output generated")

            except Exception as e:
                st.error(f"❌ Error occurred: {{str(e)}}")

                # Show detailed error in expander
                with st.expander("🔍 Error Details"):
                    st.code(str(e))

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 20px;'>
        <small>Powered by CAAS Framework | CrewAI Multi-Agent System</small>
    </div>
    """,
    unsafe_allow_html=True
)
'''

    def _select_process(self, agents: List[Dict], tasks: List[Dict]) -> str:
        """
        Select optimal CrewAI Process type.

        Args:
            agents: List of agent dictionaries
            tasks: List of task dictionaries

        Returns:
            Process type as string ("sequential" or "hierarchical")
        """
        try:
            # Convert to Pydantic models for analysis
            agent_models = [
                AgentSpecModel(
                    id=a.get("id", f"agent_{i}"),
                    role=a.get("role", "Agent"),
                    goal=a.get("goal", ""),
                    backstory=a.get("backstory", ""),
                    tools=a.get("tools", []),
                )
                for i, a in enumerate(agents)
            ]

            task_models = [
                TaskSpecModel(
                    id=t.get("id", f"task_{i}"),
                    description=t.get("description", ""),
                    expected_output=t.get("expected_output", ""),
                    agent=t.get(
                        "agent", agent_models[0].id if agent_models else "agent_0"
                    ),
                    context=t.get("context", []),
                )
                for i, t in enumerate(tasks)
            ]

            # Use ProcessSelector to determine optimal process
            selected_process = self.process_selector.select_process(
                tasks=task_models, agents=agent_models, verbose=True
            )

            return selected_process.value

        except Exception as e:
            logger = get_logger()
            logger.warning(f"Process selection failed: {e}, defaulting to sequential")
            raise AgentExecutionError(
                "Failed to select process type for agents",
                details={"error": str(e), "agent_count": len(agents), "task_count": len(tasks)}
            ) from e

    def _generate_main_file(self, agents: List[Dict], tasks: List[Dict]) -> str:
        """Generate main.py file with automatic input collection."""
        project_name = (
            self.golden_data.project_name if self.golden_data else "CrewAI Project"
        )

        # Select optimal process type
        process_type = self._select_process(agents, tasks)

        # Detect if user input is needed
        try:
            from caas_framework.analysis.input_detector import InputDetector

            input_requirements = InputDetector.detect_input_requirements(tasks)
            needs_input = len(input_requirements) > 0

            if needs_input:
                # Generate input collection code
                input_collection_code = InputDetector.generate_input_collection_code(
                    input_requirements
                )
                # Add proper indentation (4 spaces for being inside main() function)
                input_collection_code = "\n".join(
                    "    " + line if line.strip() else ""
                    for line in input_collection_code.split("\n")
                )
            else:
                input_collection_code = ""
        except Exception as e:
            logger = get_logger()
            logger.warning(f"Input detection failed: {e}, disabling input collection")
            needs_input = False
            input_collection_code = ""

        # Build kickoff call
        if needs_input:
            kickoff_call = "result = crew.kickoff(inputs=user_inputs)"
        else:
            kickoff_call = "result = crew.kickoff()"

        return f'''"""
{project_name}

Main execution script for CrewAI multi-agent system.
"""

from crewai import Crew, Process
from agents import create_agents
from tasks import create_tasks
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def main():
    """Execute the crew workflow."""

    # Create agents
    agents = create_agents()
    logger.info(f"Created {{len(agents)}} agents")
    # Create tasks
    tasks = create_tasks(agents)
    logger.info(f"Created {{len(tasks)}} tasks")
{input_collection_code}
    # Create crew
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.{process_type},
        verbose=True
    )

    # Execute
    logger.info("\\nStarting crew execution...")
    {kickoff_call}

    logger.info("\\n" + "="*50)
    logger.info("RESULT:")
    logger.info("="*50)
    logger.info(result)
    return result


if __name__ == "__main__":
    main()
'''

    def _generate_agents_file(self, agents: List[Dict]) -> str:
        """Generate agents.py file with automatic tool assignment."""

        # Import tool recommendation functions
        try:
            import os
            import sys

            # Add app directory to path if not already there
            app_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "app"
            )
            if app_path not in sys.path:
                sys.path.insert(0, app_path)

            from caas_framework.codegen.tool_generator import (
                generate_tool_imports,
                generate_tools_list,
                get_recommended_tools_for_task,
                get_valid_tools,
            )

            tool_functions_available = True
        except ImportError:
            tool_functions_available = False

        # Collect all tools needed for all agents
        all_agent_tools = {}
        for agent in agents:
            agent_id = agent.get("id", "agent")
            role = agent.get("role", "Agent")
            goal = agent.get("goal", "Execute tasks")

            # First check if agent already has tools (from PostGenerationFixer or AgentDesigner)
            existing_tools = agent.get("tools", [])

            if existing_tools:
                # Use existing tools
                all_agent_tools[agent_id] = existing_tools
            elif tool_functions_available:
                # Recommend tools if none exist
                recommended_tools = get_recommended_tools_for_task(
                    task_description=goal, agent_role=role
                )
                # Validate tools
                recommended_tools = get_valid_tools(recommended_tools)
                all_agent_tools[agent_id] = recommended_tools
            else:
                all_agent_tools[agent_id] = []

        # Generate tool imports and initialization if any tools are needed
        all_tools = []
        for tools in all_agent_tools.values():
            all_tools.extend(tools)
        all_tools = list(set(all_tools))  # Remove duplicates

        tool_imports = ""
        tool_init_code = ""

        if all_tools and tool_functions_available:
            import_lines, init_lines = generate_tool_imports(all_tools, use_mcp=False)
            tool_imports = "\n".join(import_lines)
            tool_init_code = "\n".join(init_lines)

        # Generate agent creation code
        agents_code = []
        for agent in agents:
            agent_id = agent.get("id", "agent")
            role = agent.get("role", "Agent")
            goal = agent.get("goal", "Execute tasks")
            backstory = agent.get("backstory", "Expert agent")

            # Get tools for this agent
            agent_tools = all_agent_tools.get(agent_id, [])

            # Generate tools list
            tools_param = ""
            if agent_tools and tool_functions_available:
                tools_list = generate_tools_list(agent_tools, use_mcp=False)
                tools_param = f",\n        tools={tools_list}"

            agents_code.append(
                f"""
    agents["{agent_id}"] = Agent(
        role="{role}",
        goal="{goal}",
        backstory="{backstory}",
        verbose=True,
        allow_delegation={'True' if agent.get('allow_delegation', False) else 'False'}{tools_param}
    )"""
            )

        # Build the complete file
        imports_section = '''"""
Agent definitions for CrewAI system.
"""

from crewai import Agent
'''

        if tool_imports:
            imports_section += tool_imports + "\n"

        init_section = ""
        if tool_init_code:
            init_section = f"\n\n{tool_init_code}\n"

        return f'''{imports_section}

def create_agents():
    """Create and return all agents."""{init_section}
    agents = {{}}
{''.join(agents_code)}

    return agents
'''

    def _generate_tasks_file(self, tasks: List[Dict], agents: List[Dict]) -> str:
        """Generate tasks.py file with input placeholders."""

        # Detect if input is needed and inject placeholders
        try:
            from caas_framework.analysis.input_detector import InputDetector

            input_requirements = InputDetector.detect_input_requirements(tasks)
            if input_requirements:
                # Inject placeholders into task descriptions
                tasks = InputDetector.inject_input_placeholders(
                    tasks, input_requirements
                )
        except Exception as e:
            # If detection fails, continue with original tasks
            logger = get_logger()
            logger.warning(f"Input placeholder injection failed: {e}, using original tasks")

        tasks_code = []
        for task in tasks:
            task.get("id", "task")
            description = task.get("description", "Execute task")
            expected_output = task.get("expected_output", "Task completed")
            agent_id = task.get("agent", agents[0].get("id") if agents else "agent")
            human_input = task.get("human_input", False)

            tasks_code.append(
                f"""
    tasks.append(Task(
        description="{description}",
        expected_output="{expected_output}",
        agent=agents["{agent_id}"],
        human_input={human_input}
    ))"""
            )

        return f'''"""
Task definitions for CrewAI system.
"""

from crewai import Task


def create_tasks(agents):
    """Create and return all tasks."""
    tasks = []
{''.join(tasks_code)}

    return tasks
'''


    def _generate_tools_file_fallback(self, tools: set) -> str:
        """
        Generate tools.py file with fallback stub implementations.

        This is now a thin wrapper around the centralized tool generation utility.

        Call Path (Expert Agent Mode - DEFAULT):
            SixPhaseEngine.run() [use_expert_agents=True]
              → ExpertAgentCollaboration.collaborate()
              → CodeGeneratorAgent._do_work() (Phase 5: Delivery)
              → CodeGeneratorAgent._generate_tools_file_fallback() ← YOU ARE HERE
              → tool_utils.generate_fallback_tools_code()

        Args:
            tools: Set of tool names (e.g., {'file_read', 'file_write', 'web_search'})

        Returns:
            Python code for tools.py with CrewAI tool implementations

        Configuration:
            - Fallback warning: Disabled (Expert Agents don't show LLM failure message)
            - Helper functions: Enabled (includes get_all_tools() and tool instances)
            - Return type: str (tools return strings from _run method)

        See Also:
            caas_framework.codegen.tool_utils.generate_fallback_tools_code
            LLMCodeGenerator._generate_fallback_tools (alternative Legacy LLM path)
        """
        from caas_framework.codegen.tool_utils import generate_fallback_tools_code

        return generate_fallback_tools_code(
            tools=tools,  # Will be sanitized internally
            include_header=True,
            fallback_warning=False,  # No warning for Expert Agent path
            include_helper_functions=True,  # Include get_all_tools() and instances
            return_type="str",  # Return string from _run method
        )

    def _generate_main_file_ast(self, agents: List[Dict], tasks: List[Dict]) -> str:
        """Generate main.py file using AST-based code generation."""
        import ast

        from caas_framework.codegen.ast_code_generator import ASTCodeGenerator

        project_name = (
            self.golden_data.project_name if self.golden_data else "CrewAI Project"
        )

        # Select optimal process type
        process_type = self._select_process(agents, tasks)

        # ✅ v0.4.2: Detect if user input is needed (deduplicated)
        needs_input = False
        input_collection_code = ""
        try:
            from caas_framework.analysis.input_detector import InputDetector

            # Use unified method to avoid duplicates
            input_requirements = InputDetector.detect_input_requirements_unified(tasks)
            needs_input = len(input_requirements) > 0

            if needs_input:
                input_collection_code = InputDetector.generate_input_collection_code(
                    input_requirements
                )
        except Exception as e:
            logger = get_logger()
            logger.warning(f"Input placeholder injection failed for AST generation: {e}")

        # Create AST generator
        ast_gen = ASTCodeGenerator(use_black=True)

        # Generate main function with selected process type
        main_func_code = ast_gen.generate_main_function(
            process=process_type, has_user_inputs=needs_input
        )

        # Build module with imports
        module_body = []

        # Docstring
        docstring = f'"""\n{project_name}\n\nMain execution script for CrewAI multi-agent system.\n"""'
        module_body.append(ast.Expr(value=ast.Constant(value=docstring)))

        # Imports
        imports = [
            ast.ImportFrom(
                module="crewai",
                names=[
                    ast.alias(name="Crew", asname=None),
                    ast.alias(name="Process", asname=None),
                ],
                level=0,
            ),
            ast.ImportFrom(
                module="agents",
                names=[ast.alias(name="create_agents", asname=None)],
                level=0,
            ),
            ast.ImportFrom(
                module="tasks",
                names=[ast.alias(name="create_tasks", asname=None)],
                level=0,
            ),
            ast.ImportFrom(
                module="dotenv",
                names=[ast.alias(name="load_dotenv", asname=None)],
                level=0,
            ),
        ]
        module_body.extend(imports)

        # load_dotenv() call
        load_dotenv_call = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="load_dotenv", ctx=ast.Load()), args=[], keywords=[]
            )
        )
        module_body.append(load_dotenv_call)

        # Parse main function and add it
        main_func_ast = ast.parse(main_func_code).body[0]

        # ✅ v0.4.1: Inject input collection with frontend compatibility
        if needs_input and input_collection_code:
            # Parse input collection code (CLI mode)
            input_collection_ast = ast.parse(input_collection_code).body

            # Create if/else block:
            # if inputs is None:
            #     # CLI mode - use input()
            #     user_inputs = {}
            #     keyword = input("...")
            #     user_inputs["keyword"] = keyword
            # else:
            #     # Frontend mode - use provided inputs
            #     user_inputs = inputs

            # Build the if statement
            if_inputs_none = ast.If(
                test=ast.Compare(
                    left=ast.Name(id="inputs", ctx=ast.Load()),
                    ops=[ast.Is()],
                    comparators=[ast.Constant(value=None)],
                ),
                body=input_collection_ast,  # CLI input collection code
                orelse=[
                    # else: user_inputs = inputs
                    ast.Assign(
                        targets=[ast.Name(id="user_inputs", ctx=ast.Store())],
                        value=ast.Name(id="inputs", ctx=ast.Load()),
                    )
                ],
            )

            # Insert after tasks creation (index 2 in main function body)
            main_func_ast.body = (
                main_func_ast.body[:2] + [if_inputs_none] + main_func_ast.body[2:]
            )

        module_body.append(main_func_ast)

        # if __name__ == "__main__": main()
        main_guard = ast.If(
            test=ast.Compare(
                left=ast.Name(id="__name__", ctx=ast.Load()),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value="__main__")],
            ),
            body=[
                ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id="main", ctx=ast.Load()), args=[], keywords=[]
                    )
                )
            ],
            orelse=[],
        )
        module_body.append(main_guard)

        # Create module
        module = ast.Module(body=module_body, type_ignores=[])
        ast.fix_missing_locations(module)

        # Convert to code
        code = ast.unparse(module)

        # Format with black
        code = ast_gen.format_with_black(code)

        return code

    def _generate_agents_file_ast(self, agents: List[Dict]) -> str:
        """Generate agents.py file using AST-based code generation."""
        from caas_framework.codegen.ast_code_generator import ASTCodeGenerator

        # Collect tools for each agent
        tools_map = {}
        for agent in agents:
            agent_id = agent.get("id", "agent")
            existing_tools = agent.get("tools", [])
            if existing_tools:
                tools_map[agent_id] = existing_tools

        # Create AST generator
        ast_gen = ASTCodeGenerator(use_black=True)

        # Generate create_agents function
        agents_func_code = ast_gen.generate_create_agents_function(agents, tools_map)

        # Build module with imports and docstring
        import ast

        module_body = []

        # Docstring
        docstring = '"""\nAgent definitions for CrewAI system.\n"""'
        module_body.append(ast.Expr(value=ast.Constant(value=docstring)))

        # Imports
        imports = [
            ast.ImportFrom(
                module="crewai", names=[ast.alias(name="Agent", asname=None)], level=0
            )
        ]

        # Add tools import if tools are used
        if tools_map:
            # Collect all unique tool names
            all_tools = set()
            for tool_list in tools_map.values():
                all_tools.update(tool_list)

            # Create import: from tools import tool1, tool2, ...
            # Note: Expert Agent path generates tools.py in root, so use 'tools' not 'src.tools'
            imports.append(
                ast.ImportFrom(
                    module="tools",
                    names=[
                        ast.alias(name=tool, asname=None) for tool in sorted(all_tools)
                    ],
                    level=0,
                )
            )

        module_body.extend(imports)

        # Parse and add create_agents function
        agents_func_ast = ast.parse(agents_func_code).body[0]
        module_body.append(agents_func_ast)

        # Create module
        module = ast.Module(body=module_body, type_ignores=[])
        ast.fix_missing_locations(module)

        # Convert to code
        code = ast.unparse(module)

        # Format with black
        code = ast_gen.format_with_black(code)

        return code

    def _generate_tasks_file_ast(self, tasks: List[Dict]) -> str:
        """Generate tasks.py file using AST-based code generation."""
        from caas_framework.codegen.ast_code_generator import ASTCodeGenerator

        # Detect and inject input placeholders if needed
        try:
            from caas_framework.analysis.input_detector import InputDetector

            input_requirements = InputDetector.detect_input_requirements(tasks)
            if input_requirements:
                tasks = InputDetector.inject_input_placeholders(
                    tasks, input_requirements
                )
        except Exception as e:
            logger = get_logger()
            logger.warning(f"Input placeholder injection failed for AST tasks generation: {e}")

        # Create AST generator
        ast_gen = ASTCodeGenerator(use_black=True)

        # Generate create_tasks function
        tasks_func_code = ast_gen.generate_create_tasks_function(tasks)

        # Build module with imports and docstring
        import ast

        module_body = []

        # Docstring
        docstring = '"""\nTask definitions for CrewAI system.\n"""'
        module_body.append(ast.Expr(value=ast.Constant(value=docstring)))

        # Imports
        imports = [
            ast.ImportFrom(
                module="crewai", names=[ast.alias(name="Task", asname=None)], level=0
            )
        ]
        module_body.extend(imports)

        # Parse and add create_tasks function
        tasks_func_ast = ast.parse(tasks_func_code).body[0]
        module_body.append(tasks_func_ast)

        # Create module
        module = ast.Module(body=module_body, type_ignores=[])
        ast.fix_missing_locations(module)

        # Convert to code
        code = ast.unparse(module)

        # Format with black
        code = ast_gen.format_with_black(code)

        return code

    async def _evaluate_code_quality(
        self,
        code_files: Dict[str, str],
        agents: Optional[List[Any]] = None,
        tasks: Optional[List[Any]] = None,
    ) -> Optional[Any]:
        """
        Evaluate generated code quality using LLM-as-a-Judge

        Args:
            code_files: Generated code files
            agents: Agent specs (for context)
            tasks: Task specs (for context)

        Returns:
            EvaluationResult or None if evaluation is disabled/fails
        """
        try:
            from caas_framework.quality.llm_judge import LLMJudge
            from caas_framework.utils import ObjectAccessor

            # Create LLM Judge
            judge = LLMJudge(llm_plugin=self.llm, passing_score=7.0)

            # Prepare context
            context = {}
            if agents:
                context["agents_count"] = len(agents)
                context["agents"] = ObjectAccessor.to_dict_list(agents)[
                    :3
                ]  # First 3 for brevity
            if tasks:
                context["tasks_count"] = len(tasks)
                context["tasks"] = ObjectAccessor.to_dict_list(tasks)[
                    :3
                ]  # First 3 for brevity

            # Filter to Python files only
            python_files = {
                filename: content
                for filename, content in code_files.items()
                if filename.endswith(".py")
            }

            if not python_files:
                return None

            # Evaluate
            logger = get_logger()
            logger.info("[CodeGenerator] Evaluating code quality with LLM Judge...")

            evaluation = await judge.evaluate_code_quality(python_files, context)

            logger.info(
                f"[CodeGenerator] Quality evaluation complete: "
                f"score={evaluation.overall_score:.2f}/10, "
                f"passed={'YES' if evaluation.passed else 'NO'}"
            )

            return evaluation

        except ImportError as e:
            # LLM Judge not available
            logger = get_logger()
            logger.warning(
                "[CodeGenerator] LLM Judge not available - skipping quality evaluation"
            )
            return None

        except Exception as e:
            # Evaluation failed, log but don't fail code generation
            logger = get_logger()
            logger.error(f"[CodeGenerator] Quality evaluation failed: {e}")
            raise CodeGenerationError(
                "Code quality evaluation failed",
                details={"error": str(e), "file_count": len(code_files)}
            ) from e

    async def _refine_implementation(
        self,
        output: Dict[str, Any],
        issues: List[ValidationIssue],
        context: Optional[Dict[str, Any]],
        iteration: int,
    ) -> Dict[str, Any]:
        """
        Refine generated code based on validation feedback.

        Uses RefinementExecutor for standardized refinement workflow.
        """
        from caas_framework.agents.executors import RefinementExecutor

        executor = RefinementExecutor.create_for_agent(
            agent=self,
            agent_role="Expert Code Generator",
            output_type="generated code files",
        )

        refined_output = await executor.refine_output(
            output=output,
            issues=issues,
            iteration=iteration,
            guidelines=[
                "Fix CrewAI framework compatibility issues",
                "Ensure all generated files are syntactically correct",
                "Maintain consistency with agent/task specifications",
                "Preserve working code while fixing issues",
                "Add missing imports and dependencies",
            ],
        )

        # Preserve metadata
        refined_output["iteration"] = iteration
        refined_output["issues_addressed"] = len(issues)

        return refined_output
