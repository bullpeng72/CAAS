"""
Code Generator Agent

Expert agent responsible for Phase 5 (Delivery):
- Generates production-ready code
- Creates tests, documentation, deployment files
- Ensures code quality and best practices
- Integrates error handling and logging
"""

from typing import Any, Dict, List, Optional

from caas_framework.utils.logger import get_logger

from caas_framework.agents.base import AgentPhase, BaseExpertAgent, ValidationIssue
from caas_framework.agents.process_selector import ProcessSelector
from caas_framework.agents.registry import register_agent
from caas_framework.config.settings import LLMConstants
from caas_framework.models.specifications import (
    AgentSpecModel,
    ConcretizedRequirement,
    TaskSpecModel,
)
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils import PromptBuilder, ResponseParser


@register_agent(phase=AgentPhase.DELIVERY)
class CodeGeneratorAgent(BaseExpertAgent):
    """
    Code Generator Agent

    Specializes in generating production-ready code from
    agent/task specifications and architecture design.
    """

    def __init__(self, llm_plugin: LLMPlugin, golden_data: Optional[ConcretizedRequirement] = None):
        super().__init__(llm_plugin, golden_data, AgentPhase.DELIVERY)
        self.process_selector = ProcessSelector()

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
        context_summary = self._build_context_summary(context, previous_outputs)

        # Get design and architecture from previous phases
        design = previous_outputs.get(AgentPhase.DESIGN) if previous_outputs else None
        architecture = previous_outputs.get(AgentPhase.ARCHITECTURE) if previous_outputs else None
        analysis = previous_outputs.get(AgentPhase.DISCOVERY) if previous_outputs else None

        if not design:
            return {"error": "No design provided for code generation"}

        # Extract agents and tasks
        agents = design.get("agents", [])
        tasks = design.get("tasks", [])

        # If no agents/tasks, return empty dict (no code generated)
        if not agents or not tasks:
            return {}

        # Generate code using LLM
        generated_files = await self._generate_code_files(
            agents=agents,
            tasks=tasks,
            architecture=architecture,
            analysis=analysis,
            requirement=requirement,
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
        if isinstance(generated_files, dict) and "_boundaries_violations" in generated_files:
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
    ) -> Dict[str, str]:
        """Generate actual code files using LLM."""

        # Build comprehensive prompt
        prompt = self._build_code_generation_prompt(
            agents, tasks, architecture, analysis, requirement
        )

        # Call LLM
        response = await self.llm.ainvoke(
            messages=[{"role": "user", "content": prompt}],
            response_format=LLMConstants.RESPONSE_FORMAT_JSON,
            temperature=LLMConstants.TEMPERATURE_PRECISE,
            max_tokens=4000,
        )

        # Debug logging
        import logging

        logger = get_logger()
        raw_response = str(response)[:1000]
        logger.info(f"[CodeGenerator] Raw LLM response (first 1000 chars): {raw_response}")

        # Parse response
        code_structure = ResponseParser.parse_structured_response(
            response,
            expected_fields=["files"],
            fallback_factory=lambda: self._create_fallback_code(agents, tasks),
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
            code_structure = self._create_fallback_code(agents, tasks)
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
            has_crewai = self._validate_crewai_code(result_files)
            if not has_crewai:
                logger.error("[CodeGenerator] Generated code does NOT contain CrewAI imports!")
                logger.warning("[CodeGenerator] LLM generated wrong format, forcing fallback")
                # Force fallback with proper CrewAI code
                fallback = self._create_fallback_code(agents, tasks)
                result_files = fallback.get("files", {})
                logger.info(f"[CodeGenerator] Forced fallback generated {len(result_files)} files")

        # CRITICAL: Auto-fix common Agent bugs and ensure tools.py exists
        if result_files:
            result_files = self._autofix_generated_code(result_files, agents)
            logger.info(f"[CodeGenerator] Auto-fix validation complete")

        # CRITICAL: Validate boundaries if specified
        boundaries_violations = []
        if self.golden_data and self.golden_data.boundaries:
            violations = self._validate_boundaries(result_files, self.golden_data.boundaries)
            if violations:
                logger.error(f"[CodeGenerator] BOUNDARY VIOLATIONS DETECTED: {len(violations)}")
                for violation in violations:
                    logger.error(f"  - {violation}")
                boundaries_violations = violations

        # Return files with boundaries metadata
        result = result_files.copy()
        if boundaries_violations:
            result["_boundaries_violations"] = boundaries_violations

        return result

    def _validate_boundaries(self, files: Dict[str, str], boundaries) -> List[str]:
        """
        Validate generated code against security boundaries.

        Args:
            files: Dictionary of filename -> code content
            boundaries: BoundariesSpec from golden_data

        Returns:
            List of violation messages (empty if no violations)
        """
        import logging

        logger = get_logger()

        violations = []

        # Never allowed patterns to check
        never_patterns = boundaries.never_allowed if boundaries.never_allowed else []
        ask_first_patterns = boundaries.ask_first if boundaries.ask_first else []

        for filename, content in files.items():
            if not filename.endswith(".py"):
                continue

            # Check for dangerous patterns in code
            content_lower = content.lower()

            for pattern in never_patterns:
                pattern_lower = pattern.lower()

                # Check for common dangerous patterns
                if "sudo" in pattern_lower and "sudo" in content_lower:
                    violations.append(f"NEVER_ALLOWED: {filename} contains 'sudo' command")

                if "system" in pattern_lower and "os.system" in content_lower:
                    violations.append(f"NEVER_ALLOWED: {filename} uses os.system()")

                if "security" in pattern_lower and "disable" in pattern_lower:
                    if "disable" in content_lower and "security" in content_lower:
                        violations.append(
                            f"NEVER_ALLOWED: {filename} may disable security features"
                        )

            for pattern in ask_first_patterns:
                pattern_lower = pattern.lower()

                # Check for operations that should ask first
                if "api" in pattern_lower and "requests" in content_lower:
                    logger.warning(f"ASK_FIRST: {filename} makes API calls (review recommended)")

                if "delete" in pattern_lower and (
                    "os.remove" in content_lower or "shutil.rmtree" in content_lower
                ):
                    logger.warning(f"ASK_FIRST: {filename} deletes files (review recommended)")

        return violations

    def _validate_crewai_code(self, files: Dict[str, str]) -> bool:
        """
        Validate that generated code uses CrewAI framework.

        Args:
            files: Dictionary of filename -> content

        Returns:
            True if code contains CrewAI imports, False otherwise
        """
        # Check main files for CrewAI imports
        main_file = files.get("main.py", "")
        agents_file = files.get("agents.py", "")
        tasks_file = files.get("tasks.py", "")

        # Look for CrewAI imports
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

    def _autofix_generated_code(self, files: Dict[str, str], agents: List[Any]) -> Dict[str, str]:
        """
        Auto-fix common bugs in LLM-generated code.

        Fixes:
        1. Remove 'id=' parameter from Agent() calls (causes ValidationError)
        2. Convert tools=['string'] to tools=[] (causes ValidationError)
        3. Generate tools.py if missing but agents have tools

        Args:
            files: Dictionary of filename -> content
            agents: List of agent specifications

        Returns:
            Fixed files dictionary
        """
        import logging
        import re

        from caas_framework.utils import ObjectAccessor

        logger = get_logger()
        fixed_files = files.copy()

        # Fix agents.py if it exists
        if "agents.py" in fixed_files:
            agents_code = fixed_files["agents.py"]
            original_code = agents_code

            # Fix #1: Remove id='...' parameter from Agent() calls
            # Pattern: id='anything', or id="anything",
            agents_code = re.sub(r"\bid\s*=\s*['\"][^'\"]*['\"],?\s*\n", "", agents_code)

            # Fix #2: Convert tools=['str1', 'str2'] to tools=[]
            # Pattern: tools=['...', '...'] or tools=["...", "..."]
            # This is tricky because we need to detect string lists vs variable lists
            def fix_tools_param(match):
                tools_value = match.group(1)
                # Check if it contains quoted strings
                if "'" in tools_value or '"' in tools_value:
                    # It's a string list - replace with empty list
                    logger.warning(f"[AutoFix] Converting invalid tools={tools_value} to tools=[]")
                    return "tools=[]"
                else:
                    # It's a variable list - keep it
                    return match.group(0)

            agents_code = re.sub(r"tools\s*=\s*\[([^\]]*)\]", fix_tools_param, agents_code)

            # Fix #3: Remove extra parameters not supported by CrewAI Agent
            # Common issues: memory=, max_iter=, etc.
            unsupported_params = ["memory", "max_iter", "max_execution_time"]
            for param in unsupported_params:
                agents_code = re.sub(rf"\b{param}\s*=\s*[^,\n]+,?\s*\n", "", agents_code)

            if agents_code != original_code:
                logger.info(
                    "[AutoFix] Fixed agents.py (removed id, invalid tools, unsupported params)"
                )
                fixed_files["agents.py"] = agents_code

        # Fix #4: Ensure tools.py exists if agents have tools
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

            # Also need to add tools import to agents.py if missing
            if "agents.py" in fixed_files:
                agents_code = fixed_files["agents.py"]
                if "from tools import" not in agents_code:
                    # Find the import section and add tools import
                    import_match = re.search(r"(from crewai import Agent.*?\n)", agents_code)
                    if import_match:
                        import_section = import_match.group(1)
                        tools_import = f"from tools import {', '.join(sorted(all_tools))}\n"
                        agents_code = agents_code.replace(
                            import_section, import_section + tools_import
                        )
                        fixed_files["agents.py"] = agents_code
                        logger.info(f"[AutoFix] Added tools import to agents.py")

        return fixed_files

    def _build_code_generation_prompt(
        self,
        agents: List[Any],
        tasks: List[Any],
        architecture: Optional[Dict[str, Any]],
        analysis: Optional[Dict[str, Any]],
        requirement: Optional[str],
    ) -> str:
        """Build LLM prompt for code generation."""

        # Convert agents and tasks to dicts if they're Pydantic models
        from caas_framework.utils import ObjectAccessor

        agents_data = ObjectAccessor.to_dict_list(agents)
        tasks_data = ObjectAccessor.to_dict_list(tasks)

        builder = PromptBuilder(
            "generate production-ready Python code for a CrewAI multi-agent system"
        ).add_task(
            """You are an expert Python developer generating a complete CrewAI application.

CRITICAL REQUIREMENT: You MUST generate code using the CrewAI framework.
- ALWAYS use 'from crewai import Crew, Agent, Task, Process'
- NEVER generate plain Python/FastAPI/Streamlit code without CrewAI
- The requirement description mentions what the system DOES, but you must implement it using CrewAI agents and tasks
- CrewAI agents orchestrate the work; they don't replace frameworks like FastAPI or Streamlit"""
        )

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

        # Define output format
        builder.add_output_format(
            {
                "files": {
                    "main.py": "# Main crew execution script",
                    "agents.py": "# Agent definitions",
                    "tasks.py": "# Task definitions",
                    "requirements.txt": "# Dependencies",
                    "README.md": "# Documentation",
                    ".env.example": "# Environment variables template",
                }
            },
            "Generate a complete CrewAI project with the following files:",
        )

        # Add guidelines
        builder.add_guidelines(
            [
                "MANDATORY: Use CrewAI framework - import Crew, Agent, Task from crewai",
                "MANDATORY: agents.py MUST define Agent objects using crewai.Agent",
                "MANDATORY: tasks.py MUST define Task objects using crewai.Task",
                "MANDATORY: main.py MUST create a Crew and call crew.kickoff()",
                "CRITICAL: Agent() constructor - DO NOT use 'id' parameter (it's auto-generated)",
                "CRITICAL: Agent() tools parameter - use empty list [] if no tools, NEVER use string list",
                "CRITICAL: If agents need tools, you MUST also generate tools.py with BaseTool classes",
                "Create a working CrewAI application with all agents and tasks from the design",
                "Include proper CrewAI imports: from crewai import Crew, Agent, Task, Process",
                "Add crewai to requirements.txt with other dependencies",
                "Add error handling and logging",
                "Follow Python best practices and PEP 8",
                "Include clear comments and docstrings",
                "Create a README with setup and usage instructions",
                "Use environment variables for sensitive data (OPENAI_API_KEY, etc.)",
                "Make the code modular and maintainable",
            ]
        )

        return builder.build()

    def _create_fallback_code(self, agents: List[Any], tasks: List[Any]) -> Dict[str, Any]:
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

        # Non-Python files remain as simple strings
        requirements_txt = self._generate_requirements_file()
        readme_md = self._generate_readme_file()
        env_example = self._generate_env_file()

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

        return {"files": files_dict}

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
                    agent=t.get("agent", agent_models[0].id if agent_models else "agent_0"),
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
            import logging

            logger = get_logger()
            logger.warning(f"Process selection failed: {e}, defaulting to sequential")
            return "sequential"

    def _generate_main_file(self, agents: List[Dict], tasks: List[Dict]) -> str:
        """Generate main.py file with automatic input collection."""
        project_name = self.golden_data.project_name if self.golden_data else "CrewAI Project"

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
        except Exception:
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
    print(f"Created {{len(agents)}} agents")

    # Create tasks
    tasks = create_tasks(agents)
    print(f"Created {{len(tasks)}} tasks")
{input_collection_code}
    # Create crew
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.{process_type},
        verbose=True
    )

    # Execute
    print("\\nStarting crew execution...")
    {kickoff_call}

    print("\\n" + "="*50)
    print("RESULT:")
    print("="*50)
    print(result)

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
        imports_section = f'''"""
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
                tasks = InputDetector.inject_input_placeholders(tasks, input_requirements)
        except Exception as e:
            # If detection fails, continue with original tasks
            pass

        tasks_code = []
        for task in tasks:
            task_id = task.get("id", "task")
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

    def _generate_requirements_file(self) -> str:
        """Generate requirements.txt file."""
        return """# CrewAI Dependencies
crewai>=0.65.0,<1.0.0
crewai-tools>=0.12.0
python-dotenv>=1.0.0
langchain>=0.2.0
"""

    def _generate_readme_file(self) -> str:
        """Generate README.md file."""
        project_name = self.golden_data.project_name if self.golden_data else "CrewAI Project"
        features = (
            self.golden_data.features if self.golden_data and self.golden_data.features else []
        )

        features_list = (
            "\\n".join([f"- {f.name}: {f.description}" for f in features[:5]])
            if features
            else "- Task execution"
        )

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

3. Run the application:
```bash
python main.py
```

## Project Structure

- `main.py` - Main execution script
- `agents.py` - Agent definitions
- `tasks.py` - Task definitions
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variables template

## Generated by CAAS Framework

This project was automatically generated using the CrewAI Agent Auto-generation System (CAAS).
"""

    def _generate_env_file(self) -> str:
        """Generate .env.example file."""
        return """# OpenAI API Key (required)
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Other LLM providers
# ANTHROPIC_API_KEY=your_anthropic_key
# GOOGLE_API_KEY=your_google_key

# Optional: Custom settings
# CREW_VERBOSE=True
"""

    def _generate_tools_file_fallback(self, tools: set) -> str:
        """
        Generate tools.py file with fallback stub implementations.

        This is now a thin wrapper around the centralized tool generation utility.

        Call Path (Expert Agent Mode - DEFAULT):
            BMADEngine.run() [use_expert_agents=True]
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

        project_name = self.golden_data.project_name if self.golden_data else "CrewAI Project"

        # Select optimal process type
        process_type = self._select_process(agents, tasks)

        # Detect if user input is needed
        needs_input = False
        input_collection_code = ""
        try:
            from caas_framework.analysis.input_detector import InputDetector

            input_requirements = InputDetector.detect_input_requirements(tasks)
            needs_input = len(input_requirements) > 0

            if needs_input:
                input_collection_code = InputDetector.generate_input_collection_code(
                    input_requirements
                )
        except Exception:
            pass

        # Create AST generator
        ast_gen = ASTCodeGenerator(use_black=True)

        # Generate main function with selected process type
        main_func_code = ast_gen.generate_main_function(
            process=process_type, has_user_inputs=needs_input
        )

        # Build module with imports
        module_body = []

        # Docstring
        docstring = (
            f'"""\n{project_name}\n\nMain execution script for CrewAI multi-agent system.\n"""'
        )
        module_body.append(ast.Expr(value=ast.Constant(value=docstring)))

        # Imports
        imports = [
            ast.ImportFrom(
                module="crewai",
                names=[ast.alias(name="Crew", asname=None), ast.alias(name="Process", asname=None)],
                level=0,
            ),
            ast.ImportFrom(
                module="agents", names=[ast.alias(name="create_agents", asname=None)], level=0
            ),
            ast.ImportFrom(
                module="tasks", names=[ast.alias(name="create_tasks", asname=None)], level=0
            ),
            ast.ImportFrom(
                module="dotenv", names=[ast.alias(name="load_dotenv", asname=None)], level=0
            ),
        ]
        module_body.extend(imports)

        # load_dotenv() call
        load_dotenv_call = ast.Expr(
            value=ast.Call(func=ast.Name(id="load_dotenv", ctx=ast.Load()), args=[], keywords=[])
        )
        module_body.append(load_dotenv_call)

        # Parse main function and add it
        main_func_ast = ast.parse(main_func_code).body[0]

        # If needs input, inject input collection code into main function body
        if needs_input and input_collection_code:
            # Parse input collection code
            input_collection_ast = ast.parse(input_collection_code).body

            # Insert after tasks creation (index 2 in main function body)
            main_func_ast.body = (
                main_func_ast.body[:2] + input_collection_ast + main_func_ast.body[2:]
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
                    value=ast.Call(func=ast.Name(id="main", ctx=ast.Load()), args=[], keywords=[])
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
            ast.ImportFrom(module="crewai", names=[ast.alias(name="Agent", asname=None)], level=0)
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
                    names=[ast.alias(name=tool, asname=None) for tool in sorted(all_tools)],
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
                tasks = InputDetector.inject_input_placeholders(tasks, input_requirements)
        except Exception:
            pass

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
            ast.ImportFrom(module="crewai", names=[ast.alias(name="Task", asname=None)], level=0)
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
                context["agents"] = ObjectAccessor.to_dict_list(agents)[:3]  # First 3 for brevity
            if tasks:
                context["tasks_count"] = len(tasks)
                context["tasks"] = ObjectAccessor.to_dict_list(tasks)[:3]  # First 3 for brevity

            # Filter to Python files only
            python_files = {
                filename: content
                for filename, content in code_files.items()
                if filename.endswith(".py")
            }

            if not python_files:
                return None

            # Evaluate
            import logging

            logger = get_logger()
            logger.info(f"[CodeGenerator] Evaluating code quality with LLM Judge...")

            evaluation = await judge.evaluate_code_quality(python_files, context)

            logger.info(
                f"[CodeGenerator] Quality evaluation complete: "
                f"score={evaluation.overall_score:.2f}/10, "
                f"passed={'YES' if evaluation.passed else 'NO'}"
            )

            return evaluation

        except ImportError:
            # LLM Judge not available
            import logging

            logger = get_logger()
            logger.warning("[CodeGenerator] LLM Judge not available - skipping quality evaluation")
            return None

        except Exception as e:
            # Evaluation failed, log but don't fail code generation
            import logging

            logger = get_logger()
            logger.error(f"[CodeGenerator] Quality evaluation failed: {e}")
            return None

    async def _refine_implementation(
        self,
        output: Dict[str, Any],
        issues: List[ValidationIssue],
        context: Optional[Dict[str, Any]],
        iteration: int,
    ) -> Dict[str, Any]:
        """
        Refine generated code based on validation feedback.

        Uses LLM to fix specific issues in the generated code.
        """
        if not issues:
            return output

        # Group issues by severity
        critical_issues = [i for i in issues if i.severity == "critical"]
        high_issues = [i for i in issues if i.severity == "high"]

        # Focus on critical and high issues
        focus_issues = critical_issues + high_issues

        if not focus_issues:
            return output

        # Build refinement prompt
        issues_summary = "\n".join(
            [
                f"- [{issue.severity.upper()}] {issue.issue_type}: {issue.message}"
                for issue in focus_issues[:10]  # Limit to 10 most important issues
            ]
        )

        prompt = (
            PromptBuilder("refine code generation based on validation feedback")
            .add_task("You are refining code to fix validation issues.")
            .add_input(current_iteration=f"{iteration}/3", issues_found=issues_summary)
            .add_output_format(
                {
                    "fixes_applied": ["list of fixes"],
                    "suggested_changes": {"file_path": "changes description"},
                    "remaining_issues": ["issues that cannot be automatically fixed"],
                },
                "Provide a JSON object with:",
            )
            .add_guidelines(
                [
                    "Review each issue carefully",
                    "Propose concrete fixes",
                    "Ensure fixes don't break existing functionality",
                    "Provide specific code changes or suggestions",
                ]
            )
            .build()
        )

        # Get LLM response
        from caas_framework.plugins.llm.base import LLMMessage

        response = await self.llm.ainvoke(
            messages=[LLMMessage(role="user", content=prompt)],
            temperature=LLMConstants.TEMPERATURE_PRECISE,
            max_tokens=1500,
        )

        # Parse response
        try:
            import json

            refinement_plan = ResponseParser.parse_structured_response(
                response, expected_fields=["improvements", "changes"], fallback_factory=lambda: {}
            )

            # Add refinement info to output
            output["refinement"] = refinement_plan
            output["iteration"] = iteration
            output["issues_addressed"] = len(focus_issues)

        except json.JSONDecodeError:
            # If parsing fails, just add raw response
            output["refinement"] = {"raw_response": response.content, "iteration": iteration}

        return output
