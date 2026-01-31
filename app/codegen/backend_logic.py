"""
Backend Logic Generator

Domain-specific backend API 로직을 생성합니다.
run_crew() 호출 대신 execution agents를 직접 실행하는 코드를 생성합니다.
"""

from typing import Optional, Dict, Any
from app.models.domain_types import DomainType, ExecutionPattern
from app.utils.logger import get_logger

logger = get_logger("codegen.backend_logic")


class BackendLogicGenerator:
    """Backend domain-specific 로직 생성기"""

    def __init__(self):
        self.logger = logger

    def generate_agent_execution_code(
        self,
        domain_type: Optional[DomainType],
        execution_pattern: Optional[ExecutionPattern] = None
    ) -> str:
        """
        에이전트 실행 코드 생성

        Args:
            domain_type: Domain type
            execution_pattern: 실행 패턴

        Returns:
            실행 코드 (Python string)
        """
        if not domain_type:
            return self._generate_generic_execution()

        # Domain-specific execution code 생성
        if domain_type == DomainType.TASK_MANAGEMENT:
            return self._generate_task_management_execution()
        elif domain_type == DomainType.DATA_ANALYSIS:
            return self._generate_data_analysis_execution()
        elif domain_type == DomainType.CONVERSATIONAL_AI:
            return self._generate_conversational_execution()
        elif domain_type == DomainType.REPORT_GENERATION:
            return self._generate_report_execution()
        else:
            return self._generate_generic_execution()

    def _generate_generic_execution(self) -> str:
        """Generic agent execution (fallback)"""
        return '''# Generic agent execution
from crew import run_crew

result = run_crew(request.input_data)
return {"success": True, "result": result}'''

    def _generate_task_management_execution(self) -> str:
        """Task management domain execution code"""
        return '''# Task Management execution with domain-specific agents
import sys
import os

# agents 디렉토리를 Python 경로에 추가
agents_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agents")
if agents_path not in sys.path:
    sys.path.insert(0, agents_path)

# Import execution agents
from agents import task_manager, reminder_agent
from tasks import execute_task_management_operations
from crewai import Crew, Process

# Create crew with execution agents
crew = Crew(
    agents=[task_manager, reminder_agent],
    tasks=[execute_task_management_operations],
    process=Process.sequential,
    verbose=True
)

# Execute crew with input
result = crew.kickoff(inputs=request.input_data)

# Return result
return {"success": True, "result": str(result)}'''

    def _generate_data_analysis_execution(self) -> str:
        """Data analysis domain execution code"""
        return '''# Data Analysis execution with domain-specific agents
import sys
import os

# agents 디렉토리를 Python 경로에 추가
agents_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agents")
if agents_path not in sys.path:
    sys.path.insert(0, agents_path)

# Import execution agents
from agents import data_analyst, visualization_expert
from tasks import TASKS
from crewai import Crew, Process

# Create crew with execution agents
crew = Crew(
    agents=[data_analyst, visualization_expert],
    tasks=TASKS,
    process=Process.sequential,
    verbose=True
)

# Execute crew with input
result = crew.kickoff(inputs=request.input_data)

# Return result
return {"success": True, "result": str(result)}'''

    def _generate_conversational_execution(self) -> str:
        """Conversational AI domain execution code"""
        return '''# Conversational AI execution with domain-specific agents
import sys
import os

# agents 디렉토리를 Python 경로에 추가
agents_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agents")
if agents_path not in sys.path:
    sys.path.insert(0, agents_path)

# Import execution agents
from agents import conversation_assistant, context_manager
from tasks import TASKS
from crewai import Crew, Process

# Create crew with execution agents
crew = Crew(
    agents=[conversation_assistant, context_manager],
    tasks=TASKS,
    process=Process.sequential,
    verbose=True
)

# Execute crew with input
result = crew.kickoff(inputs=request.input_data)

# Return result as conversational response
return {"success": True, "result": str(result)}'''

    def _generate_report_execution(self) -> str:
        """Report generation domain execution code"""
        return '''# Report Generation execution with domain-specific agents
import sys
import os

# agents 디렉토리를 Python 경로에 추가
agents_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agents")
if agents_path not in sys.path:
    sys.path.insert(0, agents_path)

# Import execution agents
from agents import report_generator, data_collector
from tasks import TASKS
from crewai import Crew, Process

# Create crew with execution agents
crew = Crew(
    agents=[report_generator, data_collector],
    tasks=TASKS,
    process=Process.sequential,
    verbose=True
)

# Execute crew with input
result = crew.kickoff(inputs=request.input_data)

# Return result
return {"success": True, "result": str(result)}'''

    def generate_endpoint_code(
        self,
        endpoint_path: str,
        endpoint_method: str,
        endpoint_description: str,
        domain_type: Optional[DomainType] = None,
        execution_pattern: Optional[ExecutionPattern] = None
    ) -> str:
        """
        API 엔드포인트 코드 생성

        Args:
            endpoint_path: API 경로 (예: "/api/run")
            endpoint_method: HTTP 메서드 (예: "post")
            endpoint_description: 엔드포인트 설명
            domain_type: Domain type
            execution_pattern: 실행 패턴

        Returns:
            완전한 엔드포인트 함수 코드
        """
        func_name = endpoint_path.replace('/', '_').strip('_').replace('-', '_')
        execution_code = self.generate_agent_execution_code(domain_type, execution_pattern)

        return f'''
@router.{endpoint_method.lower()}("{endpoint_path}")
async def {func_name}(request: AgentRequest):
    """
    {endpoint_description}
    """
    try:
{self._indent_code(execution_code, 8)}
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"에이전트 모듈을 찾을 수 없습니다: {{str(e)}}. agents/ 디렉토리를 확인하세요."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"에이전트 실행 중 오류 발생: {{str(e)}}"
        )
'''

    def _indent_code(self, code: str, spaces: int) -> str:
        """코드 들여쓰기"""
        indent = ' ' * spaces
        lines = code.strip().split('\n')
        return '\n'.join(indent + line if line.strip() else '' for line in lines)
