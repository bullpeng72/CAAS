'''"""
Agent definitions for CrewAI system.
"""'''

from crewai import Agent
from tools import file_read, file_write


def create_agents():
    agents = {}
    agents["task_creator_agent"] = Agent(
        role="작업 생성 에이전트",
        goal="사용자가 새로운 작업을 생성할 수 있도록 지원합니다.",
        backstory="작업 관리 시스템에서 작업 생성에 대한 전문성을 가진 에이전트입니다.",
        verbose=True,
        allow_delegation=True,
        tools=[file_read, file_write],
    )
    agents["task_retriever_agent"] = Agent(
        role="작업 조회 에이전트",
        goal="사용자가 특정 작업의 세부 정보를 조회할 수 있도록 지원합니다.",
        backstory="작업 관리 시스템에서 작업 조회에 대한 전문성을 가진 에이전트입니다.",
        verbose=True,
        allow_delegation=True,
        tools=[file_read, file_write],
    )
    agents["task_updater_agent"] = Agent(
        role="작업 업데이트 에이전트",
        goal="사용자가 기존 작업의 세부 정보를 업데이트할 수 있도록 지원합니다.",
        backstory="작업 관리 시스템에서 작업 업데이트에 대한 전문성을 가진 에이전트입니다.",
        verbose=True,
        allow_delegation=True,
        tools=[file_read, file_write],
    )
    agents["task_deleter_agent"] = Agent(
        role="작업 삭제 에이전트",
        goal="사용자가 특정 작업을 삭제할 수 있도록 지원합니다.",
        backstory="작업 관리 시스템에서 작업 삭제에 대한 전문성을 가진 에이전트입니다.",
        verbose=True,
        allow_delegation=True,
        tools=[file_read, file_write],
    )
    agents["user_auth_agent"] = Agent(
        role="사용자 인증 에이전트",
        goal="사용자가 이메일과 비밀번호로 로그인할 수 있도록 지원합니다.",
        backstory="사용자 인증 시스템에서 로그인 처리에 대한 전문성을 가진 에이전트입니다.",
        verbose=True,
        allow_delegation=True,
        tools=[file_read, file_write],
    )
    return agents
