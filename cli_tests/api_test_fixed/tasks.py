'''"""
Task definitions for CrewAI system.
"""'''

from crewai import Task


def create_tasks(agents):
    tasks = []
    tasks.append(
        Task(
            description="사용자가 새로운 작업을 생성합니다. 제목, 설명 및 마감일을 포함합니다.",
            expected_output="생성된 작업의 고유 task_id와 생성 타임스탬프",
            agent=agents["task_creator_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="특정 작업의 고유 식별자를 사용하여 세부 정보를 조회합니다.",
            expected_output="조회된 작업의 세부 정보",
            agent=agents["task_retriever_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="기존 작업의 세부 정보를 업데이트합니다. 제목, 설명 및 마감일을 포함합니다.",
            expected_output="업데이트된 작업의 세부 정보",
            agent=agents["task_updater_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="특정 작업을 고유 식별자를 사용하여 삭제합니다.",
            expected_output="작업 삭제 성공 메시지",
            agent=agents["task_deleter_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="사용자가 이메일과 비밀번호로 로그인합니다.",
            expected_output="로그인 성공 또는 실패 메시지",
            agent=agents["user_auth_agent"],
            human_input=False,
        )
    )
    return tasks
