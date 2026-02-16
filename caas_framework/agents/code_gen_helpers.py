"""
Code Generation Helpers

Extracted from CodeGeneratorAgent to eliminate duplication.
Provides reusable code generation utilities.
"""

import re
from typing import Any, Dict, List, Set

from caas_framework.models.specifications import ConcretizedRequirement
from caas_framework.utils.logger import get_logger

logger = get_logger()


class CodeValidation:
    """Code validation helpers."""

    @staticmethod
    def validate_crewai_code(files: Dict[str, str]) -> bool:
        """
        Validate that generated code uses CrewAI framework.

        Args:
            files: Dictionary of filename -> content

        Returns:
            True if code contains CrewAI imports, False otherwise
        """
        main_file = files.get("main.py", "")
        agents_file = files.get("agents.py", "")
        tasks_file = files.get("tasks.py", "")

        crewai_indicators = [
            "from crewai import",
            "import crewai",
            "from crewai.agent import",
            "from crewai.task import",
            "from crewai.crew import",
        ]

        combined_content = main_file + agents_file + tasks_file

        for indicator in crewai_indicators:
            if indicator in combined_content:
                return True

        return False

    @staticmethod
    def validate_boundaries(
        files: Dict[str, str], boundaries
    ) -> List[str]:
        """
        Validate generated code against security boundaries.

        Args:
            files: Dictionary of filename -> code content
            boundaries: BoundariesSpec from golden_data

        Returns:
            List of violation messages (empty if no violations)
        """
        violations = []

        never_patterns = boundaries.never_allowed if boundaries.never_allowed else []
        ask_first_patterns = boundaries.ask_first if boundaries.ask_first else []

        for filename, content in files.items():
            if not filename.endswith(".py"):
                continue

            content_lower = content.lower()

            for pattern in never_patterns:
                pattern_lower = pattern.lower()

                if "sudo" in pattern_lower and "sudo" in content_lower:
                    violations.append(
                        f"NEVER_ALLOWED: {filename} contains 'sudo' command"
                    )

                if "system" in pattern_lower and "os.system" in content_lower:
                    violations.append(f"NEVER_ALLOWED: {filename} uses os.system()")

                if "security" in pattern_lower and "disable" in pattern_lower:
                    if "disable" in content_lower and "security" in content_lower:
                        violations.append(
                            f"NEVER_ALLOWED: {filename} may disable security features"
                        )

            for pattern in ask_first_patterns:
                pattern_lower = pattern.lower()

                if "api" in pattern_lower and "requests" in content_lower:
                    logger.warning(
                        f"ASK_FIRST: {filename} makes API calls (review recommended)"
                    )

                if "delete" in pattern_lower and (
                    "os.remove" in content_lower or "shutil.rmtree" in content_lower
                ):
                    logger.warning(
                        f"ASK_FIRST: {filename} deletes files (review recommended)"
                    )

        return violations


class CodeAutoFix:
    """Automatic code fixing helpers."""

    @staticmethod
    def fix_agent_code(agents_code: str) -> str:
        """
        Auto-fix common bugs in agents.py.

        Fixes:
        1. Remove 'id=' parameter from Agent() calls
        2. Convert tools=['string'] to tools=[]
        3. Remove unsupported parameters

        Args:
            agents_code: Original agents.py content

        Returns:
            Fixed agents.py content
        """
        original_code = agents_code

        # Fix #1: Remove id='...' parameter
        agents_code = re.sub(
            r"\bid\s*=\s*['\"][^'\"]*['\"],?\s*\n", "", agents_code
        )

        # Fix #2: Convert tools=['str1', 'str2'] to tools=[]
        def fix_tools_param(match):
            tools_value = match.group(1)
            if "'" in tools_value or '"' in tools_value:
                logger.warning(
                    f"[AutoFix] Converting invalid tools={tools_value} to tools=[]"
                )
                return "tools=[]"
            else:
                return match.group(0)

        agents_code = re.sub(
            r"tools\s*=\s*\[([^\]]*)\]", fix_tools_param, agents_code
        )

        # Fix #3: Remove unsupported parameters
        unsupported_params = ["memory", "max_iter", "max_execution_time"]
        for param in unsupported_params:
            agents_code = re.sub(
                rf"\b{param}\s*=\s*[^,\n]+,?\s*\n", "", agents_code
            )

        if agents_code != original_code:
            logger.info(
                "[AutoFix] Fixed agents.py (removed id, invalid tools, unsupported params)"
            )

        return agents_code

    @staticmethod
    def add_manager_llm(code: str, is_main_py: bool = True) -> str:
        """
        Add manager_llm for hierarchical process.

        Args:
            code: Original code content
            is_main_py: True if main.py, False if crew.py

        Returns:
            Fixed code with manager_llm
        """
        if "Process.hierarchical" not in code or "manager_llm" in code:
            return code

        original_code = code

        # Add langchain_openai import
        if "from langchain_openai import ChatOpenAI" not in code:
            import_match = re.search(r"(from crewai import .*?\n)", code)
            if import_match:
                import_line = import_match.group(1)
                code = code.replace(
                    import_line,
                    import_line + "from langchain_openai import ChatOpenAI\n",
                )

        # Add manager_llm initialization
        if is_main_py:
            crew_match = re.search(
                r"(\s+)(crew\s*=\s*Crew\()", code, re.MULTILINE
            )
            if crew_match:
                indent = crew_match.group(1)
                crew_start = crew_match.group(2)
                manager_llm_code = f"""{indent}# Manager LLM for hierarchical process
{indent}manager_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

{indent}"""
                code = code.replace(indent + crew_start, manager_llm_code + crew_start)
        else:
            crew_match = re.search(r"(^|\n)(crew\s*=\s*Crew\()", code, re.MULTILINE)
            if crew_match:
                manager_llm_code = """# Manager LLM for hierarchical process
manager_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

"""
                code = code.replace(
                    crew_match.group(2), manager_llm_code + crew_match.group(2)
                )

        # Add manager_llm parameter
        code = re.sub(
            r"(process=Process\.hierarchical),(\s*)",
            r"\1,\2manager_llm=manager_llm,\2",
            code,
        )

        if code != original_code:
            logger.info(
                f"[AutoFix] Added manager_llm for hierarchical process"
            )

        return code

    @staticmethod
    def ensure_tools_import(agents_code: str, all_tools: Set[str]) -> str:
        """
        Ensure tools import exists in agents.py.

        Args:
            agents_code: Original agents.py content
            all_tools: Set of tool names

        Returns:
            agents.py with tools import
        """
        if not all_tools or "from tools import" in agents_code:
            return agents_code

        import_match = re.search(r"(from crewai import Agent.*?\n)", agents_code)
        if import_match:
            import_section = import_match.group(1)
            tools_import = f"from tools import {', '.join(sorted(all_tools))}\n"
            agents_code = agents_code.replace(
                import_section, import_section + tools_import
            )
            logger.info("[AutoFix] Added tools import to agents.py")

        return agents_code


class StaticFileGenerators:
    """Generators for static files (requirements.txt, README.md, .env)."""

    @staticmethod
    def generate_requirements(
        enable_frontend: bool = False,  # ✅ P0-2: Frontend support
        frontend_framework: str = "streamlit",  # ✅ P0-2: Framework choice
    ) -> str:
        """Generate requirements.txt with optional frontend dependencies."""
        base_requirements = """# CrewAI Dependencies
crewai>=0.65.0,<1.0.0
crewai-tools>=0.12.0
python-dotenv>=1.0.0
langchain>=0.2.0
"""

        # ✅ P0-2: Add frontend dependencies
        if enable_frontend:
            if frontend_framework == "streamlit":
                base_requirements += """
# Streamlit UI
streamlit>=1.28.0
"""
            elif frontend_framework == "react":
                base_requirements += """
# React frontend (requires Node.js separately)
# npm install react react-dom
"""

        return base_requirements

    @staticmethod
    def generate_readme(
        project_name: str = "CrewAI Project",
        features: List[Any] = None,
        enable_frontend: bool = False,  # ✅ P0-2: Frontend support
        frontend_framework: str = "streamlit",  # ✅ P0-2: Framework choice
    ) -> str:
        """Generate README.md with optional frontend instructions."""
        features = features or []
        features_list = (
            "\n".join([f"- {f.name}: {f.description}" for f in features[:5]])
            if features
            else "- Task execution"
        )

        # ✅ P0-2: Add frontend-specific run instructions
        if enable_frontend:
            if frontend_framework == "streamlit":
                run_instructions = """3. Run the application:

**Option 1: Streamlit UI (Recommended)**
```bash
streamlit run app.py
```
Then open http://localhost:8501 in your browser.

**Option 2: Command Line**
```bash
python main.py
```"""
                project_structure = """- `app.py` - Streamlit user interface (recommended)
- `main.py` - Main execution script (CLI)
- `agents.py` - Agent definitions
- `tasks.py` - Task definitions
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variables template"""
            else:
                run_instructions = """3. Run the application:
```bash
python main.py
```"""
                project_structure = """- `main.py` - Main execution script
- `agents.py` - Agent definitions
- `tasks.py` - Task definitions
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variables template"""
        else:
            run_instructions = """3. Run the application:
```bash
python main.py
```"""
            project_structure = """- `main.py` - Main execution script
- `agents.py` - Agent definitions
- `tasks.py` - Task definitions
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variables template"""

        return f"""# {project_name}

Auto-generated CrewAI multi-agent system.

## Features

{features_list}

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

{run_instructions}

## Project Structure

{project_structure}

## Generated by CAAS Framework

This project was automatically generated using the CrewAI Agent Auto-generation System (CAAS).
"""

    @staticmethod
    def generate_env_example() -> str:
        """Generate .env.example."""
        return """# OpenAI API Key (required)
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Other LLM providers
# ANTHROPIC_API_KEY=your_anthropic_key
# GOOGLE_API_KEY=your_google_key

# Optional: Custom settings
# CREW_VERBOSE=True
"""


class ProcessSelector:
    """Helper to select optimal CrewAI process type."""

    @staticmethod
    def select_from_golden_data(golden_data: ConcretizedRequirement) -> str:
        """
        Select process type from Golden Data.

        Args:
            golden_data: Golden Data with workflow hints

        Returns:
            Process type ("sequential" or "hierarchical")
        """
        if golden_data and golden_data.workflow_type:
            workflow = golden_data.workflow_type.lower()
            if "hierarchical" in workflow or "manager" in workflow:
                return "hierarchical"

        return "sequential"
