"""
Code Generation Engine

Main engine for production-ready code generation.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from caas_framework.models.specifications import (
    ConcretizedRequirement,
    AgentSpecModel,
    TaskSpecModel,
)
from caas_framework.codegen.domain_strategy import DomainStrategy, CodeGenStrategy
from caas_framework.codegen.injectors import ErrorHandlingInjector, LoggingInjector
from caas_framework.codegen.test_generator import TestGenerator
from caas_framework.codegen.deployment_generator import (
    DeploymentGenerator,
    DeploymentConfig,
)
from caas_framework.codegen.llm_code_generator import LLMCodeGenerator
from caas_framework.codegen.frontend_generator import (
    FrontendGenerator,
    FrontendConfig,
    FrontendFramework,
)
from caas_framework.codegen.port_manager import PortManager
from caas_framework.plugins.llm.base import LLMPlugin


@dataclass
class GeneratedFile:
    """Generated file specification"""
    path: str
    content: str
    file_type: str  # "python", "yaml", "dockerfile", "markdown"


@dataclass
class CodeGenerationResult:
    """Code generation result"""
    project_name: str
    files: Dict[str, str] = field(default_factory=dict)  # path -> content
    generated_files: List[GeneratedFile] = field(default_factory=list)
    success: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class CodeGenerationEngine:
    """
    Code Generation Engine

    Generates production-ready CrewAI projects with:
    - Domain-specific code templates
    - Error handling injection
    - Logging injection
    - Test generation
    - Deployment configurations
    """

    def __init__(
        self,
        llm_plugin: Optional[LLMPlugin] = None,
        enable_error_handling: bool = True,
        enable_logging: bool = True,
        enable_tests: bool = True,
        enable_deployment: bool = True,
        enable_llm_generation: bool = True,
        enable_frontend: bool = False,
        frontend_framework: FrontendFramework = FrontendFramework.STREAMLIT,
        tdd_mode: bool = False
    ):
        """
        Initialize code generation engine.

        Args:
            llm_plugin: LLM plugin for intelligent code generation
            enable_error_handling: Enable error handling injection
            enable_logging: Enable logging injection
            enable_tests: Enable test generation
            enable_deployment: Enable deployment files generation
            enable_llm_generation: Enable LLM-based code generation
            enable_frontend: Enable frontend generation
            frontend_framework: Frontend framework to use (streamlit or react)
            tdd_mode: Enable Test-First Code Generation (TDD approach)
        """
        self.llm_plugin = llm_plugin
        self.enable_error_handling = enable_error_handling
        self.enable_logging = enable_logging
        self.enable_tests = enable_tests
        self.enable_deployment = enable_deployment
        self.enable_llm_generation = enable_llm_generation
        self.enable_frontend = enable_frontend
        self.frontend_framework = frontend_framework
        self.tdd_mode = tdd_mode

        # Initialize generators
        self.error_injector = ErrorHandlingInjector() if enable_error_handling else None
        self.logging_injector = LoggingInjector() if enable_logging else None
        self.test_generator = TestGenerator() if enable_tests else None
        self.deployment_generator = DeploymentGenerator() if enable_deployment else None
        self.llm_generator = LLMCodeGenerator(llm_plugin) if (enable_llm_generation and llm_plugin) else None

        # Initialize TDD generator if TDD mode is enabled
        if tdd_mode:
            from caas_framework.codegen.test_generator import TestFirstCodeGenerator
            self.tdd_generator = TestFirstCodeGenerator(llm_client=llm_plugin)
        else:
            self.tdd_generator = None

        # Initialize port manager and frontend generator
        self.port_manager = PortManager() if enable_frontend else None
        self.frontend_generator = FrontendGenerator(self.port_manager) if enable_frontend else None

    async def generate(
        self,
        golden_data: ConcretizedRequirement,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
        deployment_target: str = "docker",
        tdd_mode: bool = False
    ) -> CodeGenerationResult:
        """
        Generate complete project code.

        Args:
            golden_data: Golden Data
            agents: Agent specifications
            tasks: Task specifications
            deployment_target: Deployment target
            tdd_mode: Enable Test-First Code Generation (TDD approach)

        Returns:
            CodeGenerationResult: Generation result
        """
        result = CodeGenerationResult(
            project_name=golden_data.project_name or "my_crew_project"
        )

        try:
            # 1. Determine domain strategy
            strategy_config = DomainStrategy.get_strategy_config(golden_data.domain)

            # 2. Generate core files
            core_files = await self._generate_core_files(
                golden_data,
                agents,
                tasks,
                strategy_config.strategy
            )
            result.files.update(core_files)

            # Check if tools.py was generated using fallback
            if "src/tools.py" in core_files:
                tools_content = core_files["src/tools.py"]
                if "fallback" in tools_content.lower() or "stub" in tools_content.lower():
                    result.warnings.append(
                        "⚠️  tools.py was generated using fallback mechanism. "
                        "LLM generation may have failed. Review and implement actual tool logic."
                    )

            # 2.5. Run TDD cycle if TDD mode is enabled
            if tdd_mode or self.tdd_mode:
                if self.tdd_generator and golden_data.features:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info("🔴 Starting TDD (Test-First) Code Generation...")

                    # Run TDD cycle for each feature
                    for feature in golden_data.features[:3]:  # Limit to first 3 features for now
                        feature_spec = {
                            "name": feature.name.replace(" ", "_").lower(),
                            "description": feature.description,
                            "acceptance_criteria": feature.acceptance_criteria if hasattr(feature, "acceptance_criteria") else [],
                            "components": ["agent", "task"],
                            "domain": golden_data.domain
                        }

                        logger.info(f"  Running TDD cycle for feature: {feature.name}")

                        # Execute TDD cycle (RED-GREEN-REFACTOR)
                        tdd_result = self.tdd_generator.tdd_cycle(
                            feature_spec=feature_spec,
                            output_dir=f"./tdd_{result.project_name}"
                        )

                        # Integrate TDD-generated files into result
                        if tdd_result.get("all_tests_passed"):
                            logger.info(f"  ✅ TDD cycle completed successfully for {feature.name}")
                            logger.info(f"     Coverage: {tdd_result.get('final_coverage', 0) * 100:.1f}%")
                            logger.info(f"     Iterations: {tdd_result.get('iterations', 0)}")

                            # Add TDD test file to result
                            test_file_path = tdd_result.get("test_file", "")
                            if test_file_path:
                                with open(test_file_path, "r") as f:
                                    result.files[f"tests/tdd_{feature_spec['name']}.py"] = f.read()

                            # Add TDD implementation file to result
                            impl_file_path = tdd_result.get("implementation_file", "")
                            if impl_file_path:
                                with open(impl_file_path, "r") as f:
                                    result.files[f"src/tdd_{feature_spec['name']}.py"] = f.read()
                        else:
                            logger.warning(f"  ⚠️  TDD cycle incomplete for {feature.name}")
                            result.warnings.append(
                                f"TDD cycle for {feature.name} did not complete successfully. "
                                f"Failed tests: {tdd_result.get('test_results', {}).get('failed', 0)}"
                            )

                    logger.info("🔵 TDD Code Generation completed!")
                else:
                    result.warnings.append(
                        "⚠️  TDD mode enabled but no features found in golden_data. "
                        "TDD requires feature specifications with acceptance criteria."
                    )

            # 3. Inject error handling
            if self.enable_error_handling and self.error_injector:
                self._inject_error_handling(result.files)

            # 4. Inject logging
            if self.enable_logging and self.logging_injector:
                self._inject_logging(result.files)

            # 5. Generate tests
            if self.enable_tests and self.test_generator:
                test_files = self.test_generator.generate_all_tests(
                    agents=agents,
                    tasks=tasks,
                    api_endpoints=[] if not strategy_config.requires_crud else [
                        {"path": "/", "method": "GET"},
                        {"path": "/health", "method": "GET"}
                    ]
                )
                result.files.update(test_files)

            # 6. Allocate frontend port if needed
            frontend_port = None
            if self.enable_frontend and self.frontend_generator:
                frontend_port = self.port_manager.allocate_port(
                    service_name="frontend",
                    project_name=result.project_name
                )

            # 7. Generate deployment files
            if self.enable_deployment and self.deployment_generator:
                deployment_config = DeploymentConfig(
                    target=deployment_target,
                    project_name=result.project_name,
                    has_database=strategy_config.requires_database,
                    has_api=strategy_config.requires_crud,
                    has_ui=True,
                    ui_port=frontend_port if frontend_port else 8600
                )
                deployment_files = self.deployment_generator.generate_all(deployment_config)
                result.files.update(deployment_files)

            # 8. Generate frontend
            if self.enable_frontend and self.frontend_generator and frontend_port:
                frontend_config = FrontendConfig(
                    framework=self.frontend_framework,
                    project_name=result.project_name,
                    port=frontend_port,
                    backend_url="http://localhost:8000"
                )
                frontend_files = self.frontend_generator.generate(frontend_config)
                # Prefix all frontend files with "frontend/" directory
                prefixed_frontend_files = {
                    f"frontend/{path}": content
                    for path, content in frontend_files.items()
                }
                result.files.update(prefixed_frontend_files)

            # 9. Generate additional files
            additional_files = self._generate_additional_files(
                golden_data,
                strategy_config
            )
            result.files.update(additional_files)

            # Convert to GeneratedFile objects
            result.generated_files = [
                GeneratedFile(
                    path=path,
                    content=content,
                    file_type=self._get_file_type(path)
                )
                for path, content in result.files.items()
            ]

            result.success = True

        except Exception as e:
            result.success = False
            result.errors.append(str(e))

        return result

    async def _generate_core_files(
        self,
        golden_data: ConcretizedRequirement,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
        strategy: CodeGenStrategy
    ) -> Dict[str, str]:
        """Generate core project files with LLM-powered code generation"""
        files = {}

        # 1. Generate custom tools (if LLM generator is available)
        generated_tool_classes = []
        if self.llm_generator and agents:
            tools_code = await self.llm_generator.generate_custom_tools(agents, golden_data)
            if tools_code:
                files["src/tools.py"] = tools_code
                # Extract tool class names from generated code
                generated_tool_classes = self._extract_tool_classes(tools_code)

                # Check if fallback was used
                if "fallback" in tools_code.lower() or "stub" in tools_code.lower():
                    # Note: We'll add the warning when we have access to result
                    # This will be done later in the generate() method
                    pass
            else:
                # This should not happen with the new implementation, but keep for safety
                pass

        # 2. Generate CRUD API (for CRUD_BASED and HYBRID strategies)
        if strategy in [CodeGenStrategy.CRUD_BASED, CodeGenStrategy.HYBRID]:
            if self.llm_generator:
                crud_files = await self.llm_generator.generate_crud_api(
                    golden_data, agents, tasks
                )
                files.update(crud_files)

        # 3. agents.py (pass generated tool classes for proper mapping)
        files["src/agents.py"] = self._generate_agents_file(agents, generated_tool_classes)

        # 4. tasks.py
        files["src/tasks.py"] = self._generate_tasks_file(tasks)

        # 5. crew.py
        files["src/crew.py"] = self._generate_crew_file(
            golden_data.project_name or "my_crew",
            agents,
            tasks,
            golden_data
        )

        # 6. main.py
        files["main.py"] = self._generate_main_file(
            golden_data.project_name or "my_crew",
            strategy
        )

        # 7. requirements.txt (pass generated files for dependency detection)
        files["requirements.txt"] = self._generate_requirements(strategy, files)

        # 8. README.md
        files["README.md"] = self._generate_readme(golden_data, strategy)

        # 9. __init__.py files
        files["src/__init__.py"] = ""
        files["__init__.py"] = ""

        return files

    def _extract_tool_classes(self, tools_code: str) -> List[str]:
        """
        Extract tool class names from generated tools.py code.

        Args:
            tools_code: Generated tools.py content

        Returns:
            List of tool class names
        """
        import re

        # Find all class definitions that inherit from BaseTool
        pattern = r'class\s+([A-Z][a-zA-Z0-9]*)\s*\(.*BaseTool.*\):'
        matches = re.findall(pattern, tools_code)

        return matches

    def _generate_agents_file(
        self,
        agents: List[AgentSpecModel],
        generated_tool_classes: Optional[List[str]] = None
    ) -> str:
        """
        Generate agents.py with tool imports.

        Args:
            agents: Agent specifications
            generated_tool_classes: List of actual tool class names generated by LLM

        Returns:
            agents.py content
        """
        # Check if any agent uses tools
        has_tools = any(agent.tools for agent in agents)
        generated_tool_classes = generated_tool_classes or []

        code = '''"""
Agents Module

Defines all agents for the crew.
"""

from crewai import Agent
from typing import List
'''

        # Import tools if any agent uses them
        if has_tools:
            code += "from src.tools import *\n"

        code += "\n\n"

        for agent in agents:
            # If agent has tools, use generated tool classes
            if agent.tools and generated_tool_classes:
                # Use actual generated tool classes instead of generic names
                # Create tool instances: [ToolName()] instead of [ToolName]
                tools_list = ", ".join([f"{tool}()" for tool in generated_tool_classes])
                tools_str = f"[{tools_list}]"
            elif agent.tools:
                # Fallback: if no generated classes, don't use tools
                # Abstract tool names (like "키보드", "마우스") are not valid Tool classes
                # Better to have no tools than invalid code
                tools_str = "[]"
                # Note: Tool generation failed, agent will work without tools
            else:
                tools_str = "[]"

            code += f'''
{agent.id} = Agent(
    role="{agent.role}",
    goal="{agent.goal}",
    backstory="""{agent.backstory}""",
    tools={tools_str},
    verbose={agent.verbose},
    allow_delegation={agent.allow_delegation},
    max_iter={agent.max_iter}
)

'''

        return code

    def _generate_tasks_file(self, tasks: List[TaskSpecModel]) -> str:
        """Generate tasks.py"""
        code = '''"""
Tasks Module

Defines all tasks for the crew.
"""

from crewai import Task
from src.agents import *


'''

        for task in tasks:
            # Generate context as list of task variable references, not strings
            if task.context:
                # task.context is already a list of task IDs like ['task_1']
                # We need to reference them as variables: [task_1] not ['task_1']
                context_str = f"[{', '.join(task.context)}]"
            else:
                context_str = "[]"

            code += f'''
{task.id} = Task(
    description="""{task.description}""",
    expected_output="""{task.expected_output}""",
    agent={task.agent},
    context={context_str},
    async_execution={task.async_execution},
    human_input={task.human_input}
)

'''

        return code

    def _generate_crew_file(
        self,
        project_name: str,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
        golden_data: ConcretizedRequirement
    ) -> str:
        """Generate crew.py with dynamic process type based on workflow_type"""
        agent_ids = ", ".join([a.id for a in agents])
        task_ids = ", ".join([t.id for t in tasks])

        # Determine process type from golden_data
        workflow_type = getattr(golden_data, 'workflow_type', 'sequential')
        if workflow_type == 'hierarchical':
            process_type = 'Process.hierarchical'
        else:
            process_type = 'Process.sequential'

        # Base imports
        imports = f'''"""
Crew Definition

Main crew configuration.
"""

from crewai import Crew, Process'''

        # Add ChatOpenAI import for hierarchical mode
        if workflow_type == 'hierarchical':
            imports += '\nfrom langchain_openai import ChatOpenAI'

        imports += f'''
from src.agents import {agent_ids}
from src.tasks import {task_ids}
'''

        # Generate manager LLM configuration for hierarchical mode
        manager_llm_config = ""
        if workflow_type == 'hierarchical':
            manager_llm_config = '''
# Manager LLM for hierarchical process
manager_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1
)
'''

        # Generate crew configuration
        crew_config = f'''
# Create crew
crew = Crew(
    agents=[{agent_ids}],
    tasks=[{task_ids}],
    process={process_type},'''

        if workflow_type == 'hierarchical':
            crew_config += '''
    manager_llm=manager_llm,'''

        crew_config += '''
    verbose=True,
    memory=True
)
'''

        # Generate kickoff functions
        kickoff_functions = '''

def kickoff():
    """Execute the crew"""
    return crew.kickoff()


async def kickoff_async():
    """Execute the crew asynchronously"""
    return await crew.kickoff_async()
'''

        code = imports + manager_llm_config + crew_config + kickoff_functions

        return code

    def _generate_main_file(self, project_name: str, strategy: CodeGenStrategy) -> str:
        """Generate main.py based on strategy"""

        # For CRUD_BASED and HYBRID, generate main.py that starts both API and crew
        if strategy in [CodeGenStrategy.CRUD_BASED, CodeGenStrategy.HYBRID]:
            code = f'''"""
{project_name.replace("_", " ").title()}

Main entry point for the application.
Starts both the FastAPI server and CrewAI agents.
"""

import uvicorn
from src.api import app
from src.database import init_db


def main():
    """Main function"""
    print("=" * 70)
    print(f"{{'{project_name}'.replace('_', ' ').title()}} - Application")
    print("=" * 70)

    # Initialize database
    print("\\nInitializing database...\\n")
    init_db()

    # Start API server
    print("\\nStarting API server on http://localhost:8000\\n")
    print("API Documentation: http://localhost:8000/docs")
    print("=" * 70)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
'''
        else:
            # AGENT_BASED: Pure CrewAI execution
            code = f'''"""
{project_name.replace("_", " ").title()}

Main entry point for the CrewAI application.
"""

from src.crew import kickoff


def main():
    """Main function"""
    print("=" * 70)
    print(f"{{'{project_name}'.replace('_', ' ').title()}} - CrewAI Application")
    print("=" * 70)

    # Execute crew
    print("\\nStarting crew execution...\\n")
    result = kickoff()

    # Display results
    print("\\n" + "=" * 70)
    print("Execution Complete!")
    print("=" * 70)
    print(f"\\nResult:\\n{{result}}")


if __name__ == "__main__":
    main()
'''

        return code

    def _generate_requirements(
        self,
        strategy: CodeGenStrategy,
        generated_files: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate requirements.txt with auto-detected dependencies.

        Args:
            strategy: Code generation strategy
            generated_files: Already generated files to analyze for imports

        Returns:
            requirements.txt content
        """
        # Base requirements
        requirements = [
            "crewai>=0.1.0",
            "pydantic>=2.0.0",
            "python-dotenv>=1.0.0"
        ]

        # Strategy-specific requirements
        if strategy in [CodeGenStrategy.CRUD_BASED, CodeGenStrategy.HYBRID]:
            requirements.extend([
                "fastapi>=0.104.0",
                "uvicorn>=0.24.0",
                "sqlalchemy>=2.0.0",
                "alembic>=1.12.0"
            ])

        # Auto-detect dependencies from generated files
        if generated_files:
            detected = self._extract_dependencies_from_code(generated_files)
            requirements.extend(detected)

        # Remove duplicates and sort
        unique_requirements = sorted(set(requirements))
        return "\n".join(unique_requirements)

    def _extract_dependencies_from_code(self, files: Dict[str, str]) -> List[str]:
        """
        Extract package dependencies from generated Python code.

        Args:
            files: Dict of file paths to file contents

        Returns:
            List of package requirements
        """
        import re

        # Mapping of import names to pip packages
        IMPORT_TO_PACKAGE = {
            "requests": "requests>=2.31.0",
            "bs4": "beautifulsoup4>=4.12.0",
            "BeautifulSoup": "beautifulsoup4>=4.12.0",
            "psycopg2": "psycopg2-binary>=2.9.0",
            "pymongo": "pymongo>=4.5.0",
            "redis": "redis>=5.0.0",
            "celery": "celery>=5.3.0",
            "pandas": "pandas>=2.0.0",
            "numpy": "numpy>=1.24.0",
            "sqlalchemy": "sqlalchemy>=2.0.0",
            "fastapi": "fastapi>=0.104.0",
            "flask": "flask>=3.0.0",
            "django": "django>=4.2.0",
            "pytest": "pytest>=7.4.0",
            "aiohttp": "aiohttp>=3.9.0",
            "httpx": "httpx>=0.25.0",
            "openai": "openai>=1.0.0",
            "anthropic": "anthropic>=0.7.0",
            "langchain": "langchain>=0.1.0",
            "langchain_openai": "langchain-openai>=0.0.5",
            "streamlit": "streamlit>=1.28.0",
        }

        detected_packages = set()

        # Only analyze Python files
        python_files = {
            path: content
            for path, content in files.items()
            if path.endswith('.py')
        }

        for file_path, content in python_files.items():
            # Find all import statements
            # Matches: import foo, from foo import bar, from foo.bar import baz
            import_pattern = r'^\s*(?:from\s+([a-zA-Z0-9_]+)|import\s+([a-zA-Z0-9_]+))'

            for line in content.split('\n'):
                match = re.match(import_pattern, line)
                if match:
                    # Get the base module name (either from 'from X' or 'import X')
                    module = match.group(1) or match.group(2)

                    # Check if this module maps to a pip package
                    if module in IMPORT_TO_PACKAGE:
                        detected_packages.add(IMPORT_TO_PACKAGE[module])

        return list(detected_packages)

    def _generate_readme(
        self,
        golden_data: ConcretizedRequirement,
        strategy: CodeGenStrategy
    ) -> str:
        """Generate README.md"""
        readme = f'''# {golden_data.project_name or "CrewAI Project"}

{golden_data.description}

## Features

'''
        for feature in golden_data.features[:10]:  # First 10 features
            readme += f"- **{feature.name}**: {feature.description}\n"

        readme += f'''

## Domain

- **Type**: {golden_data.domain or "General"}
- **Strategy**: {strategy.value}

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:

```bash
python main.py
```

## Project Structure

```
.
├── src/
│   ├── agents.py       # Agent definitions
│   ├── tasks.py        # Task definitions
│   └── crew.py         # Crew configuration
├── tests/              # Test files
├── main.py             # Entry point
├── requirements.txt    # Dependencies
└── README.md           # This file
```

## Testing

Run tests:

```bash
pytest tests/
```

## Deployment

Build Docker image:

```bash
docker build -t {golden_data.project_name or "crewai-app"}:latest .
```

Run with docker-compose:

```bash
docker-compose up
```

## License

MIT
'''

        return readme

    def _inject_error_handling(self, files: Dict[str, str]) -> None:
        """Inject error handling into Python files"""
        if not self.error_injector:
            return

        for path, content in files.items():
            if path.endswith('.py') and not path.startswith('tests/'):
                try:
                    files[path] = self.error_injector.inject(content)
                except Exception:
                    # If injection fails, keep original
                    pass

    def _inject_logging(self, files: Dict[str, str]) -> None:
        """Inject logging into Python files"""
        if not self.logging_injector:
            return

        for path, content in files.items():
            if path.endswith('.py') and not path.startswith('tests/'):
                try:
                    files[path] = self.logging_injector.inject(
                        content,
                        logger_name=path.replace('/', '.').replace('.py', '')
                    )
                except Exception:
                    # If injection fails, keep original
                    pass

    def _generate_additional_files(
        self,
        golden_data: ConcretizedRequirement,
        strategy_config: Any
    ) -> Dict[str, str]:
        """Generate additional helper files"""
        files = {}

        # .gitignore
        files[".gitignore"] = '''
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env
.venv

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Logs
*.log

# Database
*.db
*.sqlite
'''

        # pyproject.toml
        files["pyproject.toml"] = f'''
[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
'''

        return files

    def _get_file_type(self, path: str) -> str:
        """Get file type from path"""
        if path.endswith('.py'):
            return "python"
        elif path.endswith(('.yaml', '.yml')):
            return "yaml"
        elif path.endswith('.md'):
            return "markdown"
        elif 'Dockerfile' in path:
            return "dockerfile"
        elif path.endswith('.txt'):
            return "text"
        else:
            return "other"
