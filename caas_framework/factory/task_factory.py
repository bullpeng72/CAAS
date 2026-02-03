"""
CAAS Task Factory

CrewAI 태스크를 생성하고 관리합니다.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel

from caas_framework.utils.logger import get_logger

from caas_framework.factory.base_factory import BaseFactory
from caas_framework.sdd import TaskSpecModel

logger = get_logger(name="caas_framework.factory.task")


class TaskDefinition(BaseModel):
    """태스크 정의 (코드 생성용)"""

    id: str
    description: str
    expected_output: str
    agent_id: str
    context_tasks: List[str] = []
    async_execution: bool = False
    output_file: Optional[str] = None
    human_input: bool = False


class TaskFactory(BaseFactory[TaskSpecModel, TaskDefinition]):
    """
    태스크 팩토리

    TaskSpec을 기반으로 CrewAI Task 객체 또는 코드를 생성합니다.
    """

    def create_definition(self, spec: TaskSpecModel) -> TaskDefinition:
        """
        TaskSpec에서 TaskDefinition을 생성합니다.

        Args:
            spec: 태스크 스펙

        Returns:
            TaskDefinition: 태스크 정의
        """
        return TaskDefinition(
            id=spec.id,
            description=spec.description,
            expected_output=spec.expected_output,
            agent_id=spec.agent,
            context_tasks=spec.context,
            async_execution=spec.async_execution,
            output_file=spec.output_file,
            human_input=spec.human_input,
        )

    def create_code(self, definition: TaskDefinition, **kwargs) -> str:
        """
        태스크 정의를 Python 코드로 변환합니다.

        Args:
            definition: 태스크 정의
            **kwargs: 추가 파라미터 (미사용, 인터페이스 호환성)

        Returns:
            str: Python 코드 문자열
        """
        # 컨텍스트 태스크
        context_str = ""
        if definition.context_tasks:
            context_list = ", ".join(definition.context_tasks)
            context_str = f"\n    context=[{context_list}],"

        # 출력 파일
        output_file_str = ""
        if definition.output_file:
            output_file_str = f'\n    output_file="{definition.output_file}",'

        code = f'''
{definition.id} = Task(
    description="""{definition.description}""",
    expected_output="""{definition.expected_output}""",
    agent={definition.agent_id},{context_str}
    async_execution={definition.async_execution},{output_file_str}
    human_input={definition.human_input},
)
'''
        return code.strip()

    def create_task_code(self, definition: TaskDefinition) -> str:
        """
        [DEPRECATED] 하위 호환성을 위한 래퍼. create_code()를 사용하세요.
        """
        return self.create_code(definition)

    def create_all_tasks_code(
        self,
        definitions: List[TaskDefinition],
        project_info: Optional[Dict[str, str]] = None,
        agent_definitions: Optional[List[Dict[str, str]]] = None,
        use_error_handling: bool = True,
    ) -> str:
        """
        모든 태스크의 코드를 생성합니다.

        Args:
            definitions: 태스크 정의 목록
            project_info: 프로젝트 정보 (name, description, domain)
            agent_definitions: 에이전트 정의 목록 (id 포함)
            use_error_handling: 에러 핸들링 템플릿 사용 여부

        Returns:
            str: 전체 태스크 코드
        """
        # Use template-based generation
        if use_error_handling:
            return self._generate_from_template(definitions, project_info, agent_definitions)
        else:
            # Fallback to old string-based generation
            return self._generate_simple(definitions)

    def _generate_from_template(
        self,
        definitions: List[TaskDefinition],
        project_info: Optional[Dict[str, str]] = None,
        agent_definitions: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """템플릿 기반 코드 생성 (에러 핸들링 포함)"""
        # Load template
        template = self.template_env.get_template("tasks_with_error_handling.py.j2")

        # Prepare context
        project = project_info or {
            "name": "Generated Tasks",
            "description": "AI Task System",
            "domain": "general",
        }

        # Convert definitions to template format
        tasks_context = []
        for defn in definitions:
            task_data = {
                "id": defn.id,
                "description": defn.description,
                "expected_output": defn.expected_output,
                "agent": defn.agent_id,
                "context": defn.context_tasks,
                "async_execution": defn.async_execution,
                "output_file": defn.output_file,
                "human_input": defn.human_input,
            }
            tasks_context.append(task_data)

        # Prepare agents list for import
        agents = agent_definitions or []
        if not agents and definitions:
            # Extract agent IDs from task definitions
            agent_ids = set(defn.agent_id for defn in definitions)
            agents = [{"id": aid} for aid in agent_ids]

        context = {
            "project": project,
            "tasks": tasks_context,
            "agents": agents,
            "generated_at": datetime.now().isoformat(),
        }

        return template.render(**context)

    def _generate_simple(self, definitions: List[TaskDefinition]) -> str:
        """간단한 문자열 기반 코드 생성 (하위 호환성)"""
        # 사용된 에이전트 ID 수집
        used_agent_ids = set()
        for defn in definitions:
            used_agent_ids.add(defn.agent_id)

        # Import 에이전트 목록 생성
        agent_imports = ", ".join(sorted(used_agent_ids))

        imports = f'''"""
Task Definitions

Generated by CAAS - CrewAI Agent Auto-generation System
"""

from crewai import Task

# Import agents
from agents import {agent_imports}


'''

        # 태스크 코드 생성
        tasks_code = []
        for defn in definitions:
            tasks_code.append(self.create_task_code(defn))

        # __all__ 변수 생성 (명시적 export)
        all_exports = ['"TASKS"']
        for defn in definitions:
            all_exports.append(f'"{defn.id}"')
        all_list = f"__all__ = [{', '.join(all_exports)}]\n\n"

        # 태스크 목록 생성
        task_list = "TASKS = [\n"
        for defn in definitions:
            task_list += f"    {defn.id},\n"
        task_list += "]\n"

        return imports + "\n\n".join(tasks_code) + "\n\n" + all_list + task_list
