"""
CAAS Agent Factory

CrewAI 에이전트를 생성하고 관리합니다.
"""

from typing import Dict, List, Optional, Set
from datetime import datetime

from pydantic import BaseModel

import logging
from caas_framework.sdd import AgentSpecModel
from caas_framework.factory.base_factory import BaseFactory

logger = logging.getLogger("caas_framework.factory.agent")


class AgentDefinition(BaseModel):
    """에이전트 정의 (코드 생성용)"""
    id: str
    role: str
    goal: str
    backstory: str
    tools: List[str]
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.3
    verbose: bool = True
    memory: bool = True
    allow_delegation: bool = False
    max_iter: int = 15
    max_rpm: Optional[int] = None


class AgentFactory(BaseFactory[AgentSpecModel, AgentDefinition]):
    """
    에이전트 팩토리

    AgentSpec을 기반으로 CrewAI Agent 객체 또는 코드를 생성합니다.

    Note:
        DynamicToolRegistry를 사용하여 도구 매핑을 동적으로 관리합니다.
        하드코딩된 BUILTIN_TOOLS는 제거되었습니다.
    """

    def __init__(self):
        super().__init__()  # Initialize base factory

        # Use dynamic tool registry for all tool lookups
        from caas_framework.models.tool_registry import DynamicToolRegistry
        self.tool_registry = DynamicToolRegistry
    
    def create_definition(self, spec: AgentSpecModel) -> AgentDefinition:
        """
        AgentSpec에서 AgentDefinition을 생성합니다.
        
        Args:
            spec: 에이전트 스펙
        
        Returns:
            AgentDefinition: 에이전트 정의
        """
        llm_model = self.settings.llm.default_llm_model
        llm_temperature = 0.3

        if spec.llm:
            llm_model = spec.llm.model
            llm_temperature = spec.llm.temperature
        
        return AgentDefinition(
            id=spec.id,
            role=spec.role,
            goal=spec.goal,
            backstory=spec.backstory,
            tools=spec.tools,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            verbose=spec.verbose,
            memory=spec.memory,
            allow_delegation=spec.allow_delegation,
            max_iter=spec.max_iter,
            max_rpm=spec.max_rpm,
        )
    
    def _map_tool_to_class(self, tool_name: str) -> str:
        """
        도구 이름을 클래스 경로로 매핑 (동적 레지스트리 사용)

        Args:
            tool_name: 도구 이름

        Returns:
            str: 도구 클래스 이름
        """
        # 동적 레지스트리에서 조회
        tool_class = self.tool_registry.get_tool_class(tool_name)

        # 레지스트리에 없으면 tool_name을 그대로 사용 (커스텀 도구)
        if tool_class is None:
            tool_class = tool_name
            self.logger.debug(f"도구 '{tool_name}'을 레지스트리에서 찾지 못했습니다. 커스텀 도구로 처리: {tool_class}")

        return tool_class

    def create_code(self, definition: AgentDefinition, **kwargs) -> str:
        """
        에이전트 정의를 Python 코드로 변환합니다.

        Args:
            definition: 에이전트 정의
            **kwargs: 추가 파라미터 (미사용, 인터페이스 호환성)

        Returns:
            str: Python 코드 문자열
        """
        # 도구 매핑 (P1-4: 동적 레지스트리 사용)
        tools_code = []
        for tool in definition.tools:
            tool_class = self._map_tool_to_class(tool)
            tools_code.append(f"    {tool_class}()")

        tools_str = ",\n".join(tools_code) if tools_code else "    # No tools assigned"
        
        code = f'''
{definition.id} = Agent(
    role="{definition.role}",
    goal="""{definition.goal}""",
    backstory="""{definition.backstory}""",
    tools=[
{tools_str}
    ],
    llm=ChatOpenAI(
        model="{definition.llm_model}",
        temperature={definition.llm_temperature},
    ),
    verbose={definition.verbose},
    memory={definition.memory},
    allow_delegation={definition.allow_delegation},
    max_iter={definition.max_iter},
)
'''
        return code.strip()

    def create_agent_code(self, definition: AgentDefinition) -> str:
        """
        [DEPRECATED] 하위 호환성을 위한 래퍼. create_code()를 사용하세요.
        """
        return self.create_code(definition)

    def create_all_agents_code(
        self,
        definitions: List[AgentDefinition],
        project_info: Optional[Dict[str, str]] = None,
        use_error_handling: bool = True
    ) -> str:
        """
        모든 에이전트의 코드를 생성합니다.

        Args:
            definitions: 에이전트 정의 목록
            project_info: 프로젝트 정보 (name, description, domain)
            use_error_handling: 에러 핸들링 템플릿 사용 여부

        Returns:
            str: 전체 에이전트 코드
        """
        # Use template-based generation
        if use_error_handling:
            return self._generate_from_template(definitions, project_info)
        else:
            # Fallback to old string-based generation for simple cases
            return self._generate_simple(definitions)

    def _is_crewai_tool(self, tool_name: str) -> bool:
        """
        도구가 crewai_tools 패키지에서 import 가능한지 확인

        Args:
            tool_name: 도구 이름

        Returns:
            bool: CrewAI 기본 도구이면 True, 커스텀 도구이면 False
        """
        from caas_app.codegen.tool_generator import is_custom_tool

        # is_custom_tool의 반대값 반환
        return not is_custom_tool(tool_name)

    def _collect_tools(self, definitions: List[AgentDefinition]) -> Set[str]:
        """
        수집된 CrewAI 도구 클래스 이름 반환 (커스텀 도구 제외)

        Note:
            커스텀 도구(calculator 등)는 crewai_tools에서 import할 수 없으므로 제외됩니다.
            커스텀 도구는 @tool 데코레이터를 사용하여 별도로 정의됩니다.
        """
        used_tools = set()
        for defn in definitions:
            for tool in defn.tools:
                # 커스텀 도구는 스킵
                if not self._is_crewai_tool(tool):
                    self.logger.debug(f"커스텀 도구 '{tool}'은 import 목록에서 제외됨")
                    continue

                tool_class = self._map_tool_to_class(tool)
                used_tools.add(tool_class)
        return used_tools

    def _generate_from_template(
        self,
        definitions: List[AgentDefinition],
        project_info: Optional[Dict[str, str]] = None
    ) -> str:
        """템플릿 기반 코드 생성 (에러 핸들링 포함)"""
        # Load template
        template = self.template_env.get_template("agents_with_error_handling.py.j2")

        # Prepare context
        project = project_info or {
            "name": "Generated Agents",
            "description": "AI Agent System",
            "domain": "general"
        }

        # Convert definitions to template format
        agents_context = []
        for defn in definitions:
            agent_data = {
                "id": defn.id,
                "role": defn.role,
                "goal": defn.goal,
                "backstory": defn.backstory,
                "tools": defn.tools,
                "llm": {
                    "model": defn.llm_model,
                    "temperature": defn.llm_temperature,
                    "max_retries": 3,
                    "timeout": 60
                },
                "verbose": defn.verbose,
                "memory": defn.memory,
                "allow_delegation": defn.allow_delegation,
                "max_iter": defn.max_iter
            }
            agents_context.append(agent_data)

        # Collect tool class names
        tools = sorted(self._collect_tools(definitions))

        # P0 FIX: Build tool mapping dictionary for runtime lookup
        # Only include CrewAI tools, exclude custom tools (like calculator)
        tool_mapping = {}
        all_tool_names = set()
        for defn in definitions:
            all_tool_names.update(defn.tools)

        for tool_name in sorted(all_tool_names):
            # Skip custom tools - they're not imported from crewai_tools
            if not self._is_crewai_tool(tool_name):
                self.logger.debug(f"커스텀 도구 '{tool_name}'은 TOOL_MAP에서 제외됨")
                continue

            tool_class = self._map_tool_to_class(tool_name)
            tool_mapping[tool_name] = tool_class

        context = {
            "project": project,
            "agents": agents_context,
            "tools": tools,
            "tool_mapping": tool_mapping,  # P0 FIX: Add tool mapping
            "generated_at": datetime.now().isoformat()
        }

        return template.render(**context)

    def _generate_simple(self, definitions: List[AgentDefinition]) -> str:
        """간단한 문자열 기반 코드 생성 (하위 호환성)"""
        # 사용된 도구 수집
        used_tools = self._collect_tools(definitions)

        # 임포트 생성
        imports = '''"""
Agent Definitions

Generated by CAAS - CrewAI Agent Auto-generation System
"""

from crewai import Agent
from langchain_openai import ChatOpenAI
'''

        if used_tools:
            imports += f"from crewai_tools import {', '.join(sorted(used_tools))}\n"

        imports += "\n\n"

        # 에이전트 코드 생성
        agents_code = []
        for defn in definitions:
            agents_code.append(self.create_agent_code(defn))

        # __all__ 변수 생성 (명시적 export)
        all_exports = ['"AGENTS"']
        for defn in definitions:
            all_exports.append(f'"{defn.id}"')
        all_list = f"__all__ = [{', '.join(all_exports)}]\n\n"

        # 에이전트 목록 생성
        agent_list = "AGENTS = [\n"
        for defn in definitions:
            agent_list += f"    {defn.id},\n"
        agent_list += "]\n"

        return imports + "\n\n".join(agents_code) + "\n\n" + all_list + agent_list
