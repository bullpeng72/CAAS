"""
CAAS Crew Assembler

CrewAI Crew를 조립하고 실행 코드를 생성합니다.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader

import logging
from pathlib import Path
PROJECT_ROOT = Path.cwd()
from caas_framework.sdd import CrewAISpec
from caas_framework.factory.agent_factory import AgentFactory
from caas_framework.factory.task_factory import TaskFactory, TaskDefinition
from caas_framework.models import DomainType
# Lazy imports to avoid circular dependency
# from caas_app.codegen.domain_strategy import DomainCodeStrategy
# from caas_app.codegen.crud_entity_extractor import CRUDEntityExtractor

logger = logging.getLogger("caas_framework.factory.crew")


class CrewDefinition(BaseModel):
    """Crew 정의 (코드 생성용)"""
    name: str
    description: str
    process: str = "sequential"
    verbose: bool = True
    memory: bool = True
    max_rpm: Optional[int] = None
    agent_ids: List[str] = []
    task_ids: List[str] = []


class CrewAssembler:
    """
    Crew 어셈블러
    
    에이전트와 태스크를 조합하여 CrewAI Crew를 생성합니다.
    """
    
    def __init__(self):
        self.logger = logger
        self.agent_factory = AgentFactory()
        self.task_factory = TaskFactory()

        # Lazy import to avoid circular dependency
        from caas_app.codegen.crud_entity_extractor import CRUDEntityExtractor
        self.crud_extractor = CRUDEntityExtractor()

        # Initialize Jinja2 template environment
        template_dir = PROJECT_ROOT / "data" / "templates"
        self.template_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def _parse_domain_type(self, domain_str: str) -> Optional[DomainType]:
        """
        도메인 문자열을 DomainType enum으로 변환합니다.

        Args:
            domain_str: 도메인 문자열 (예: "task management", "e-commerce")

        Returns:
            DomainType 또는 None (매핑 실패 시)
        """
        if not domain_str:
            return None

        # 정규화: 소문자 + 공백/하이픈을 언더스코어로
        normalized = domain_str.lower().replace(" ", "_").replace("-", "_")

        # DomainType enum 값과 매칭 시도
        try:
            return DomainType(normalized)
        except ValueError:
            # Enum 값이 아니면 None 반환
            self.logger.debug(f"도메인 타입 매핑 실패: '{domain_str}' -> '{normalized}'")
            return None
    
    def _infer_inputs_from_spec(self, spec: CrewAISpec) -> List[Dict[str, Any]]:
        """
        P0 FIX: Spec에서 입력 필드를 추론합니다.

        Args:
            spec: CrewAI 스펙

        Returns:
            List[Dict]: 입력 필드 정보 리스트
        """
        inputs = []

        # Check project description for input hints
        description = spec.project.description.lower()

        # Common input patterns
        input_patterns = {
            "person": ["person", "individual", "인물", "사람"],
            "topic": ["topic", "subject", "주제"],
            "text": ["text", "content", "내용", "텍스트"],
            "query": ["query", "search", "검색"],
            "keyword": ["keyword", "키워드", "키워드를", "키워드를 입력"],  # P0 FIX: Add keyword pattern
            "data": ["data", "데이터"],
            "file": ["file", "파일"],
        }

        detected_inputs = set()

        # Detect inputs from description
        for input_name, keywords in input_patterns.items():
            if any(keyword in description for keyword in keywords):
                detected_inputs.add(input_name)

        # Also check task descriptions
        for task in spec.tasks:
            task_desc = task.description.lower()
            for input_name, keywords in input_patterns.items():
                if any(keyword in task_desc for keyword in keywords):
                    detected_inputs.add(input_name)

        # Create input definitions
        for input_name in sorted(detected_inputs):
            # Customize prompt based on input type
            if input_name == "person":
                prompt = "Enter person name"
            elif input_name == "topic":
                prompt = "Enter topic"
            elif input_name == "text":
                prompt = "Enter text to analyze"
            elif input_name == "query":
                prompt = "Enter search query"
            elif input_name == "keyword":
                prompt = "키워드를 입력하세요"  # P0 FIX: Add keyword prompt
            elif input_name == "data":
                prompt = "Enter data"
            elif input_name == "file":
                prompt = "Enter file path"
            else:
                prompt = f"Enter {input_name}"

            inputs.append({
                "name": input_name,
                "prompt": prompt,
                "required": True,
                "min_length": 1
            })

        # If no inputs detected, add a generic user_input
        if not inputs:
            inputs.append({
                "name": "user_input",
                "prompt": "Enter your input",
                "required": False,
                "min_length": 0
            })

        self.logger.info(f"Inferred {len(inputs)} input field(s): {[i['name'] for i in inputs]}")

        return inputs

    def create_crew_definition(
        self,
        spec: CrewAISpec,
    ) -> CrewDefinition:
        """
        CrewAI 스펙에서 Crew 정의를 생성합니다.

        Args:
            spec: CrewAI 스펙

        Returns:
            CrewDefinition: Crew 정의
        """
        return CrewDefinition(
            name=spec.project.name,
            description=spec.project.description,
            process=spec.crew.process,
            verbose=spec.crew.verbose,
            memory=spec.crew.memory,
            max_rpm=spec.crew.max_rpm,
            agent_ids=[a.id for a in spec.agents],
            task_ids=[t.id for t in spec.tasks],
        )
    
    def create_crew_code(self, definition: CrewDefinition) -> str:
        """
        Crew 정의를 Python 코드로 변환합니다.
        
        Args:
            definition: Crew 정의
        
        Returns:
            str: Python 코드 문자열
        """
        agents_str = ", ".join(definition.agent_ids)
        tasks_str = ", ".join(definition.task_ids)
        
        max_rpm_str = ""
        if definition.max_rpm:
            max_rpm_str = f"\n    max_rpm={definition.max_rpm},"
        
        code = f'''
crew = Crew(
    agents=[{agents_str}],
    tasks=[{tasks_str}],
    process=Process.{definition.process.upper()},
    verbose={definition.verbose},
    memory={definition.memory},{max_rpm_str}
)
'''
        return code.strip()
    
    def create_crew_module_code(self, spec: CrewAISpec) -> str:
        """
        재사용 가능한 crew 모듈 코드를 생성합니다.
        Frontend, Backend, CLI에서 공통으로 사용할 수 있는 run_crew() 함수를 제공합니다.

        Args:
            spec: CrewAI 스펙

        Returns:
            str: crew.py 코드
        """
        code = f'''"""
{spec.project.name} - Crew Module

재사용 가능한 CrewAI 실행 모듈입니다.
Frontend, Backend, CLI에서 공통으로 사용할 수 있습니다.

Generated by CAAS - CrewAI Agent Auto-generation System
Domain: {spec.project.domain}
"""

import os
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from crewai import Crew, Process
from agents import AGENTS
from tasks import TASKS


def create_crew() -> Crew:
    """Create and configure the crew."""
    crew_config = {{
        "agents": AGENTS,
        "tasks": TASKS,
        "process": Process.{spec.crew.process},
        "verbose": {spec.crew.verbose},
        "memory": {spec.crew.memory},
    }}

    # Add manager LLM for hierarchical process
    if Process.{spec.crew.process} == Process.hierarchical:
        from langchain_openai import ChatOpenAI
        crew_config["manager_llm"] = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"),
            temperature=0.3
        )

    return Crew(**crew_config)


def run_crew(inputs: Optional[Dict[str, Any]] = None) -> Any:
    """
    Crew를 실행하고 결과를 반환합니다.

    Args:
        inputs: Crew에 전달할 입력 데이터 (dict)
                예: {{"text": "분석할 텍스트", "topic": "주제"}}

    Returns:
        Crew 실행 결과
    """
    if inputs is None:
        inputs = {{}}

    # Create crew
    crew = create_crew()

    # Run the crew
    result = crew.kickoff(inputs=inputs)

    return result
'''
        return code

    def create_main_code(self, spec: CrewAISpec) -> str:
        """
        메인 실행 파일 코드를 생성합니다 (간단한 버전).

        Args:
            spec: CrewAI 스펙

        Returns:
            str: main.py 코드
        """
        code = f'''#!/usr/bin/env python3
"""
{spec.project.name}

{spec.project.description}

Generated by CAAS - CrewAI Agent Auto-generation System
Domain: {spec.project.domain}
"""

from crew import run_crew


def main():
    """Main entry point."""
    print("=" * 60)
    print("  {spec.project.name}")
    print("  {spec.project.description}")
    print("=" * 60)
    print()

    # Get user input if needed
    inputs = {{}}
    # Add any required inputs here
    # Example: inputs["topic"] = input("Enter topic: ")

    # Run the crew
    print("Starting crew execution...")
    print("-" * 40)

    result = run_crew(inputs=inputs)

    print("-" * 40)
    print("Execution completed!")
    print()
    print("Result:")
    print(result)

    return result


if __name__ == "__main__":
    main()
'''
        return code

    def _create_main_with_error_handling(self, spec: CrewAISpec) -> str:
        """
        에러 핸들링이 포함된 메인 실행 파일 생성 (템플릿 기반).

        Args:
            spec: CrewAI 스펙

        Returns:
            str: main.py 코드
        """
        # Load template
        template = self.template_env.get_template("main_with_error_handling.py.j2")

        # P0 FIX: Infer inputs from spec
        inputs = self._infer_inputs_from_spec(spec)

        # Prepare context
        context = {
            "project": {
                "name": spec.project.name,
                "description": spec.project.description,
                "domain": spec.project.domain
            },
            "crew": {
                "process": spec.crew.process.upper() if hasattr(spec.crew.process, 'upper') else spec.crew.process,
                "verbose": spec.crew.verbose,
                "memory": spec.crew.memory,
                "max_rpm": spec.crew.max_rpm
            },
            "inputs": inputs,  # P0 FIX: Add inferred inputs
            "generated_at": datetime.now().isoformat()
        }

        return template.render(**context)

    def _create_streamlit_main(self, spec: CrewAISpec) -> str:
        """
        Streamlit UI 메인 파일 생성 (템플릿 기반).

        Args:
            spec: CrewAI 스펙

        Returns:
            str: app.py 코드
        """
        # Load template
        template = self.template_env.get_template("streamlit_main.py.j2")

        # P1 FIX: Infer inputs from spec (same as main.py)
        inferred_inputs = self._infer_inputs_from_spec(spec)

        # Convert to UI-friendly format with labels and help text
        ui_inputs = []
        for inp in inferred_inputs:
            input_name = inp["name"]

            # Create user-friendly label
            label = input_name.replace("_", " ").title()

            # Add context-aware help text
            help_text_map = {
                "person": "Enter the name of the person to search for",
                "topic": "Enter the topic you want to explore",
                "text": "Enter the text to analyze",
                "query": "Enter your search query",
                "data": "Enter the data to process",
                "file": "Enter the file path"
            }
            help_text = help_text_map.get(input_name, f"Enter {label.lower()}")

            ui_inputs.append({
                "name": input_name,
                "label": label,
                "help": help_text,
                "required": inp.get("required", True),
                "default": ""
            })

        # Prepare context
        context = {
            "project": {
                "name": spec.project.name,
                "description": spec.project.description,
                "domain": spec.project.domain
            },
            "agents": [
                {"role": agent.role, "id": agent.id}
                for agent in spec.agents
            ],
            "tasks": [
                {"id": task.id, "description": task.description}
                for task in spec.tasks
            ],
            "inputs": ui_inputs,  # P1 FIX: Use inferred inputs
            "generated_at": datetime.now().isoformat()
        }

        return template.render(**context)

    def assemble_full_project(
        self,
        spec: CrewAISpec,
        include_tests: bool = False,
        use_error_handling: bool = True,
        project_template: str = "agent_only"
    ) -> Dict[str, str]:
        """
        전체 프로젝트 코드를 생성합니다.

        Args:
            spec: CrewAI 스펙
            include_tests: 테스트 파일 포함 여부
            use_error_handling: 에러 핸들링 템플릿 사용 여부 (기본: True)
            project_template: 프로젝트 템플릿 타입 (agent_only, agent_with_streamlit, full_stack, chatbot)

        Returns:
            Dict[str, str]: 파일명 -> 코드 매핑
        """
        self.logger.info(f"프로젝트 코드 생성: {spec.project.name} (템플릿: {project_template})")

        # Lazy import to avoid circular dependency
        from caas_app.codegen.domain_strategy import DomainCodeStrategy

        # 도메인 타입 파싱 및 전략 결정
        domain_type = self._parse_domain_type(spec.project.domain)
        strategy_config = None
        if domain_type:
            strategy_config = DomainCodeStrategy.get_strategy_config(domain_type)
            self.logger.info(
                f"도메인 전략 적용: {domain_type.value} → "
                f"Strategy={strategy_config.strategy.value}, "
                f"Agents 필요={strategy_config.requires_agents}, "
                f"CRUD 필요={strategy_config.requires_crud}"
            )
        else:
            self.logger.warning(
                f"도메인 타입 인식 실패: '{spec.project.domain}'. "
                f"기본 agent_only 전략 사용."
            )

        # 프로젝트 정보 준비
        project_info = {
            "name": spec.project.name,
            "description": spec.project.description,
            "domain": spec.project.domain
        }

        # 에이전트/태스크 정의 생성
        agent_definitions = [
            self.agent_factory.create_definition(agent)
            for agent in spec.agents
        ]

        task_definitions = [
            self.task_factory.create_definition(task)
            for task in spec.tasks
        ]

        # Agent context for tasks (for import statements)
        agent_contexts = [{"id": agent.id} for agent in spec.agents]

        # 기본 파일 생성 (공통)
        files = {
            "requirements.txt": self._create_requirements(
                include_tests=include_tests,
                template=project_template,
                strategy_config=strategy_config
            ),
            ".env.example": self._create_env_example(),
            "README.md": self._create_readme(spec, template=project_template, strategy_config=strategy_config),
        }

        # 전략에 따라 Agent/Task 파일 생성
        if strategy_config is None or strategy_config.requires_agents:
            # Agent 필요: agents.py, tasks.py, crew.py 생성
            self.logger.info("Agent 기반 코드 생성")
            files["agents.py"] = self.agent_factory.create_all_agents_code(
                agent_definitions,
                project_info=project_info,
                use_error_handling=use_error_handling
            )
            files["tasks.py"] = self.task_factory.create_all_tasks_code(
                task_definitions,
                project_info=project_info,
                agent_definitions=agent_contexts,
                use_error_handling=use_error_handling
            )
            files["crew.py"] = self.create_crew_module_code(spec)
        else:
            # Agent 불필요 (CRUD 중심 도메인)
            self.logger.info(
                f"CRUD 중심 도메인 - Agent 파일 생성 스킵 "
                f"(agent_purpose: {strategy_config.agent_purpose})"
            )

        # CRUD/Backend 생성 (전략에 따라)
        if strategy_config and strategy_config.requires_crud:
            self.logger.info("CRUD/Backend 코드 생성 시작")

            # 엔티티 추출 (spec.project.core_entities 또는 task description에서)
            entities = self._extract_entities_from_spec(spec, task_definitions)

            if entities:
                # Backend 파일 생성
                files["backend/__init__.py"] = self._create_backend_init(spec)
                files["backend/database.py"] = self._create_database_connection(spec)
                files["backend/models.py"] = self._create_database_models(spec, entities)
                files["backend/schemas.py"] = self._create_pydantic_schemas(spec, entities)
                files["backend/crud.py"] = self._create_crud_operations(spec, entities)
                files["backend/main.py"] = self._create_fastapi_backend(spec, entities)

                self.logger.info(f"CRUD 코드 생성 완료: {len(entities)}개 엔티티")
            else:
                self.logger.warning("엔티티를 추출할 수 없어 CRUD 코드 생성을 스킵합니다")

        # 템플릿 타입별 추가 파일
        if project_template == "agent_only":
            # CLI 전용 프로젝트
            files["main.py"] = self._create_main_with_error_handling(spec) if use_error_handling else self.create_main_code(spec)

        elif project_template == "agent_with_streamlit":
            # Streamlit UI + Agents
            files["frontend/app.py"] = self._create_streamlit_main(spec)
            self.logger.info("Streamlit UI 파일 추가됨")

        elif project_template in ["full_stack", "chatbot"]:
            # 향후 확장을 위한 플레이스홀더
            files["main.py"] = self._create_main_with_error_handling(spec) if use_error_handling else self.create_main_code(spec)
            self.logger.warning(f"{project_template} 템플릿은 아직 완전히 구현되지 않았습니다. 기본 구조만 생성됩니다.")

        else:
            # 기본값: agent_only
            files["main.py"] = self._create_main_with_error_handling(spec) if use_error_handling else self.create_main_code(spec)

        # 테스트 파일 추가
        if include_tests:
            files["tests/test_crew.py"] = self._create_test_file(spec)
            files["tests/__init__.py"] = ""

        self.logger.info(f"생성 완료: {len(files)}개 파일")
        return files
    
    def _create_requirements(
        self,
        include_tests: bool = False,
        template: str = "agent_only",
        strategy_config=None
    ) -> str:
        """requirements.txt 생성"""
        # 기본 의존성
        base_requirements = """# Python Project Requirements
python-dotenv>=1.0.0
"""

        # Agent 기반: CrewAI 의존성
        if strategy_config is None or strategy_config.requires_agents:
            base_requirements += """
# CrewAI Project Requirements
crewai>=0.65.0
crewai-tools>=0.12.0
langchain>=0.2.0
langchain-openai>=0.1.0
openai>=1.30.0
"""

        # CRUD 기반: FastAPI 의존성
        if strategy_config and strategy_config.requires_crud:
            base_requirements += """
# FastAPI Backend Requirements
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
"""

        # Database 필요: SQLAlchemy 의존성
        if strategy_config and strategy_config.requires_database:
            base_requirements += """
# Database Requirements
sqlalchemy>=2.0.0
alembic>=1.12.0
"""

        # 템플릿별 추가 의존성
        if template == "agent_with_streamlit":
            base_requirements += """
# Streamlit UI Dependencies
streamlit>=1.28.0
"""

        # 테스트 의존성
        if include_tests:
            base_requirements += """
# Testing Dependencies
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-mock>=3.11.0
"""
        return base_requirements
    
    def _create_env_example(self) -> str:
        """
        .env.example 파일 생성 (명확한 설명 포함)
        """
        return """# =============================================================================
# Environment Variables for CrewAI Project
# =============================================================================
#
# IMPORTANT: Copy this file to .env and fill in your actual values
#   cp .env.example .env
#
# =============================================================================

# -----------------------------------------------------------------------------
# LLM API Keys (REQUIRED)
# -----------------------------------------------------------------------------
# Get your OpenAI API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-openai-api-key-here

# Get your Anthropic API key from: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# OpenAI Model (supports structured outputs)
# Use gpt-4o or gpt-4o-mini for structured outputs support
OPENAI_MODEL_NAME=gpt-4o

# -----------------------------------------------------------------------------
# Tool API Keys (Optional - depending on which tools your agents use)
# -----------------------------------------------------------------------------
# Serper API for web search: https://serper.dev/
SERPER_API_KEY=your-serper-api-key-here

# GitHub API: https://github.com/settings/tokens
GITHUB_API_KEY=your-github-api-key-here

# YouTube API: https://console.cloud.google.com/
YOUTUBE_API_KEY=your-youtube-api-key-here

# -----------------------------------------------------------------------------
# CrewAI Configuration
# -----------------------------------------------------------------------------
# Disable telemetry to avoid signal handler errors
OTEL_SDK_DISABLED=true
CREWAI_TELEMETRY_OPT_OUT=true
"""
    
    def _create_readme(
        self,
        spec: CrewAISpec,
        template: str = "agent_only",
        strategy_config=None
    ) -> str:
        """
        README.md 생성 (템플릿 기반)

        P0 개선: 환경 변수 가이드와 트러블슈팅 포함
        """
        # 도구 사용 여부 확인
        all_tools = set()
        for agent in spec.agents:
            all_tools.update(agent.tools or [])

        has_web_search = "web_search" in all_tools or "serper" in all_tools
        has_github_search = "github_search" in all_tools or "github" in all_tools

        # Agent 정보 준비
        agents = [
            {
                "role": agent.role,
                "goal": agent.goal,
            }
            for agent in spec.agents
        ] if (strategy_config is None or strategy_config.requires_agents) else []

        # Task 정보 준비
        tasks = [
            {
                "name": task.id,
                "description": task.description,
            }
            for task in spec.tasks
        ] if (strategy_config is None or strategy_config.requires_agents) else []

        # 템플릿 렌더링
        try:
            readme_template = self.template_env.get_template("README.md.j2")

            context = {
                "project": {
                    "name": spec.project.name,
                    "description": spec.project.description,
                    "domain": spec.project.domain,
                },
                "agents": agents,
                "tasks": tasks,
                "has_web_search": has_web_search,
                "has_github_search": has_github_search,
                "generated_at": datetime.now().isoformat(),
            }

            return readme_template.render(**context)

        except Exception as e:
            # 템플릿 렌더링 실패 시 폴백 (기존 로직)
            self.logger.warning(f"README 템플릿 렌더링 실패, 기본 README 사용: {e}")
            return self._create_readme_fallback(spec, template, strategy_config)

    def _create_readme_fallback(
        self,
        spec: CrewAISpec,
        template: str = "agent_only",
        strategy_config=None
    ) -> str:
        """
        README.md 폴백 생성 (템플릿 실패 시)

        기존 문자열 기반 생성 로직
        """
        # Agent 정보 (Agent 기반인 경우만)
        agents_section = ""
        if strategy_config is None or strategy_config.requires_agents:
            agents_list = "\n".join([
                f"- **{a.role}**: {a.goal}"
                for a in spec.agents
            ])
            agents_section = f"""## Agents

{agents_list}
"""

        # Task 정보 (Agent 기반인 경우만)
        tasks_section = ""
        if strategy_config is None or strategy_config.requires_agents:
            tasks_list = "\n".join([
                f"- **{t.id}**: {t.description[:80]}..."
                for t in spec.tasks
            ])
            tasks_section = f"""## Tasks

{tasks_list}
"""

        # 전략 정보 (있는 경우)
        strategy_section = ""
        if strategy_config:
            strategy_section = f"""## Architecture

**Code Generation Strategy**: {strategy_config.strategy.value}

{strategy_config.recommended_architecture}
"""

        return f"""# {spec.project.name}

{spec.project.description}

**Domain**: {spec.project.domain}

Generated by CAAS - CrewAI Agent Auto-generation System

{strategy_section}

{agents_section}

{tasks_section}

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\\Scripts\\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Usage

```bash
python main.py
```

## Configuration

Edit the `.env` file to configure:
- `OPENAI_API_KEY`: Your OpenAI API key
- Other API keys as needed for tools

## Workflow

Process Type: **{spec.crew.process}**

{self._describe_workflow(spec)}

---
*Generated by CAAS*
"""

    def _describe_workflow(self, spec: CrewAISpec) -> str:
        """워크플로우 설명 생성"""
        if spec.crew.process == "sequential":
            return "Tasks are executed sequentially, with each task's output feeding into the next."
        else:
            return "Tasks are managed hierarchically by a manager agent that coordinates execution."

    # ========================================================================
    # CRUD Code Generation Methods (Week 3)
    # ========================================================================

    def _extract_entities_from_spec(
        self,
        spec: CrewAISpec,
        task_definitions: List[TaskDefinition]
    ) -> List:
        """
        Spec에서 엔티티 추출

        Args:
            spec: CrewAI spec
            task_definitions: Task 정의 목록

        Returns:
            엔티티 정의 목록
        """
        from caas_app.codegen.crud_entity_extractor import EntityDefinition

        # 1. Core entities from spec
        core_entities = spec.project.core_entities or []

        if not core_entities:
            self.logger.warning("spec.project.core_entities가 없습니다. Task description에서 추론 시도")
            # Fallback: task description에서 추론
            # 간단한 추론: "Task" 같은 단어 찾기
            for task in task_definitions:
                desc_lower = task.description.lower()
                if "task" in desc_lower and "Task" not in core_entities:
                    core_entities.append("Task")
                if "user" in desc_lower and "User" not in core_entities:
                    core_entities.append("User")

        if not core_entities:
            self.logger.error("엔티티를 추출할 수 없습니다")
            return []

        # 2. 각 엔티티에 대해 필드 추출
        entities = []
        for entity_name in core_entities:
            entity = EntityDefinition(
                name=entity_name,
                table_name=self._to_table_name(entity_name),
                description=f"{entity_name} model",
                fields=[]
            )

            # 필드 추출 (task description에서)
            entity.fields = self._extract_fields_from_tasks(entity_name, task_definitions)

            # 기본 필드 추가
            entity.fields = self._add_default_fields(entity.fields)

            # Enum 필드 감지
            entity.has_enum_fields = any(f.type == "Enum" for f in entity.fields)

            # Filterable 필드
            entity.filterable_fields = [
                f for f in entity.fields
                if f.name in ["status", "priority", "type", "category", "role"]
            ]

            entities.append(entity)

        return entities

    def _extract_fields_from_tasks(
        self,
        entity_name: str,
        task_definitions: List[TaskDefinition]
    ) -> List:
        """Task description에서 필드 추출"""
        from caas_app.codegen.crud_entity_extractor import FieldDefinition
        import re

        fields = {}  # field_name -> FieldDefinition

        # Type keywords (from CRUDEntityExtractor)
        TYPE_KEYWORDS = {
            "title": ("String", False),
            "name": ("String", False),
            "description": ("Text", True),
            "content": ("Text", True),
            "priority": ("Integer", True),
            "due_date": ("DateTime", True),
            "deadline": ("DateTime", True),
            "status": ("Enum", False),
            "state": ("Enum", False),
            "type": ("Enum", False),
            "created_at": ("DateTime", False),
            "updated_at": ("DateTime", False),
        }

        for task in task_definitions:
            desc_lower = task.description.lower()

            # 패턴 1: "with fields (title, description, ...)"
            fields_pattern = r"fields?\s*\(([^)]+)\)"
            matches = re.findall(fields_pattern, desc_lower)
            for match in matches:
                field_names = [f.strip() for f in match.split(",")]
                for field_name in field_names:
                    # Remove leading conjunctions (and, or)
                    field_name = re.sub(r'^(and|or)\s+', '', field_name).strip()
                    if field_name and field_name not in fields:
                        field_type, nullable = TYPE_KEYWORDS.get(field_name, ("String", True))
                        fields[field_name] = FieldDefinition(
                            name=field_name,
                            type=field_type,
                            nullable=nullable,
                            optional=nullable,
                            python_type=self._get_python_type(field_type),
                            enum_values=self._get_enum_values(field_name) if field_type == "Enum" else None,
                            description=f"{field_name} field"
                        )

            # 패턴 2: "filtering by status, priority, ..."
            filter_pattern = r"filtering by ([^.]+)"
            matches = re.findall(filter_pattern, desc_lower)
            for match in matches:
                field_names = [f.strip() for f in match.split(",")]
                for field_name in field_names:
                    # Remove leading conjunctions (and, or)
                    field_name = re.sub(r'^(and|or)\s+', '', field_name).strip()
                    if field_name and field_name not in fields:
                        field_type, nullable = TYPE_KEYWORDS.get(field_name, ("String", True))
                        fields[field_name] = FieldDefinition(
                            name=field_name,
                            type=field_type,
                            nullable=nullable,
                            optional=nullable,
                            python_type=self._get_python_type(field_type),
                            enum_values=self._get_enum_values(field_name) if field_type == "Enum" else None,
                            description=f"{field_name} field"
                        )

            # 패턴 3: 키워드 직접 언급
            for keyword, (field_type, nullable) in TYPE_KEYWORDS.items():
                if re.search(rf"\b{keyword}\b", desc_lower) and keyword not in fields:
                    fields[keyword] = FieldDefinition(
                        name=keyword,
                        type=field_type,
                        nullable=nullable,
                        optional=nullable,
                        python_type=self._get_python_type(field_type),
                        enum_values=self._get_enum_values(keyword) if field_type == "Enum" else None,
                        description=f"{keyword} field"
                    )

        return list(fields.values())

    def _add_default_fields(self, fields: List) -> List:
        """기본 필드 추가 (id, created_at, updated_at)"""
        from caas_app.codegen.crud_entity_extractor import FieldDefinition

        field_names = {f.name for f in fields}

        # id 필드
        if "id" not in field_names:
            fields.insert(0, FieldDefinition(
                name="id",
                type="Integer",
                primary_key=True,
                auto_generated=True,
                index=True,
                python_type="int"
            ))

        # created_at 필드
        if "created_at" not in field_names:
            fields.append(FieldDefinition(
                name="created_at",
                type="DateTime",
                auto_generated=True,
                default="now",
                python_type="datetime"
            ))

        # updated_at 필드
        if "updated_at" not in field_names:
            fields.append(FieldDefinition(
                name="updated_at",
                type="DateTime",
                auto_generated=True,
                default="now",
                nullable=True,
                python_type="datetime"
            ))

        return fields

    def _to_table_name(self, entity_name: str) -> str:
        """엔티티 이름을 테이블 이름으로 변환"""
        import re
        # CamelCase → snake_case
        table_name = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()
        # 복수형
        if not table_name.endswith('s'):
            table_name += 's'
        return table_name

    def _get_python_type(self, field_type: str) -> str:
        """필드 타입을 Python 타입 힌트로 변환"""
        type_map = {
            "String": "str",
            "Text": "str",
            "Integer": "int",
            "Float": "float",
            "Boolean": "bool",
            "DateTime": "datetime",
            "Enum": "str",
        }
        return type_map.get(field_type, "str")

    def _get_enum_values(self, field_name: str) -> Optional[List[str]]:
        """필드 이름에서 enum 값 추론"""
        enum_map = {
            "status": ["pending", "in_progress", "completed", "cancelled"],
            "state": ["active", "inactive", "archived"],
            "type": ["task", "event", "note"],
            "role": ["admin", "user", "guest"],
            "priority": ["low", "medium", "high"],
        }
        return enum_map.get(field_name)

    def _create_fastapi_backend(self, spec: CrewAISpec, entities: List) -> str:
        """FastAPI main.py 생성"""
        template = self.template_env.get_template("backend/main.py.j2")

        project_info = {
            "name": spec.project.name,
            "description": spec.project.description,
            "domain": spec.project.domain
        }

        return template.render(
            project=project_info,
            entities=entities,
            generated_at=datetime.now().isoformat()
        )

    def _create_database_models(self, spec: CrewAISpec, entities: List) -> str:
        """SQLAlchemy models.py 생성"""
        template = self.template_env.get_template("backend/models.py.j2")

        project_info = {
            "name": spec.project.name,
            "description": spec.project.description,
            "domain": spec.project.domain
        }

        return template.render(
            project=project_info,
            entities=entities,
            generated_at=datetime.now().isoformat()
        )

    def _create_crud_operations(self, spec: CrewAISpec, entities: List) -> str:
        """CRUD crud.py 생성"""
        template = self.template_env.get_template("backend/crud.py.j2")

        project_info = {
            "name": spec.project.name,
            "description": spec.project.description,
            "domain": spec.project.domain
        }

        return template.render(
            project=project_info,
            entities=entities,
            generated_at=datetime.now().isoformat()
        )

    def _create_pydantic_schemas(self, spec: CrewAISpec, entities: List) -> str:
        """Pydantic schemas.py 생성"""
        template = self.template_env.get_template("backend/schemas.py.j2")

        project_info = {
            "name": spec.project.name,
            "description": spec.project.description,
            "domain": spec.project.domain
        }

        # Check if any entity has enum fields
        has_enum_fields = any(entity.has_enum_fields for entity in entities)

        return template.render(
            project=project_info,
            entities=entities,
            has_enum_fields=has_enum_fields,
            generated_at=datetime.now().isoformat()
        )

    def _create_database_connection(self, spec: CrewAISpec) -> str:
        """Database database.py 생성"""
        template = self.template_env.get_template("backend/database.py.j2")

        project_info = {
            "name": spec.project.name,
            "description": spec.project.description,
            "domain": spec.project.domain
        }

        return template.render(
            project=project_info,
            database_url="sqlite:///./app.db",
            database_echo=False,
            generated_at=datetime.now().isoformat()
        )

    def _create_backend_init(self, spec: CrewAISpec) -> str:
        """Backend __init__.py 생성"""
        template = self.template_env.get_template("backend/__init__.py.j2")

        project_info = {
            "name": spec.project.name,
            "description": spec.project.description,
            "domain": spec.project.domain
        }

        return template.render(
            project=project_info,
            generated_at=datetime.now().isoformat()
        )

    def _create_test_file(self, spec: CrewAISpec) -> str:
        """기본 테스트 파일 생성"""
        return f'''"""
{spec.project.name} - Tests

Basic test suite for the crew.

Generated by CAAS - CrewAI Agent Auto-generation System
"""

import pytest
from crew import run_crew, create_crew


class TestCrew:
    """Basic crew tests"""

    def test_create_crew(self):
        """Test crew creation"""
        crew = create_crew()
        assert crew is not None
        assert len(crew.agents) == {len(spec.agents)}
        assert len(crew.tasks) == {len(spec.tasks)}

    def test_run_crew_with_empty_inputs(self):
        """Test crew execution with empty inputs"""
        result = run_crew(inputs={{}})
        assert result is not None

    def test_run_crew_with_sample_inputs(self):
        """Test crew execution with sample inputs"""
        # Modify this test with appropriate inputs for your crew
        inputs = {{"text": "Sample input text"}}
        result = run_crew(inputs=inputs)
        assert result is not None


class TestAgents:
    """Test individual agents"""

    def test_agents_exist(self):
        """Test that all agents are created"""
        from agents import AGENTS
        assert len(AGENTS) == {len(spec.agents)}


class TestTasks:
    """Test individual tasks"""

    def test_tasks_exist(self):
        """Test that all tasks are created"""
        from tasks import TASKS
        assert len(TASKS) == {len(spec.tasks)}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''
