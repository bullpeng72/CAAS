'''"""
Task definitions for CrewAI system.
"""'''

from crewai import Task


def create_tasks(agents):
    tasks = []
    tasks.append(
        Task(
            description="사용자가 이메일과 비밀번호를 사용하여 로그인할 수 있도록 처리한다.",
            expected_output="사용자가 성공적으로 로그인하거나 오류 메시지를 받는다.",
            agent=agents["auth_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="새 사용자가 이메일과 비밀번호를 사용하여 계정을 생성할 수 있도록 처리한다.",
            expected_output="사용자가 성공적으로 등록되거나 오류 메시지를 받는다.",
            agent=agents["auth_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="사용자가 로그아웃할 수 있도록 처리한다.",
            expected_output="사용자가 성공적으로 로그아웃되거나 오류 메시지를 받는다.",
            agent=agents["auth_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="로그인 시 2단계 인증을 처리하여 추가 보안을 제공한다.",
            expected_output="사용자가 2단계 인증을 성공적으로 완료하거나 오류 메시지를 받는다.",
            agent=agents["auth_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="사용자가 새로운 작업을 생성할 수 있도록 처리한다.",
            expected_output="사용자가 성공적으로 작업을 생성하거나 오류 메시지를 받는다.",
            agent=agents["task_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="사용자가 기존 작업을 조회할 수 있도록 처리한다.",
            expected_output="사용자가 성공적으로 작업을 조회하거나 오류 메시지를 받는다.",
            agent=agents["task_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="사용자가 기존 작업을 수정할 수 있도록 처리한다.",
            expected_output="사용자가 성공적으로 작업을 수정하거나 오류 메시지를 받는다.",
            agent=agents["task_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="사용자가 기존 작업을 삭제할 수 있도록 처리한다.",
            expected_output="사용자가 성공적으로 작업을 삭제하거나 오류 메시지를 받는다.",
            agent=agents["task_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="작업 업데이트에 대한 알림을 사용자에게 제공한다.",
            expected_output="사용자가 작업 업데이트 알림을 받는다.",
            agent=agents["task_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="작업의 실시간 상태 업데이트를 제공한다.",
            expected_output="사용자가 실시간 작업 상태 업데이트를 받는다.",
            agent=agents["task_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="사용자가 실시간으로 작업을 공동으로 수행할 수 있도록 지원한다.",
            expected_output="사용자가 실시간으로 작업을 공동으로 수행할 수 있다.",
            agent=agents["task_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="사용자가 비밀번호를 재설정할 수 있도록 처리한다.",
            expected_output="사용자가 비밀번호를 성공적으로 재설정하거나 오류 메시지를 받는다.",
            agent=agents["auth_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="사용자의 세션을 관리한다.",
            expected_output="사용자가 세션을 성공적으로 관리하거나 오류 메시지를 받는다.",
            agent=agents["auth_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="사용자가 자신의 작업 목록을 조회할 수 있도록 처리한다.",
            expected_output="사용자가 작업 목록을 성공적으로 조회하거나 오류 메시지를 받는다.",
            agent=agents["task_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="사용자의 활동 피드를 제공한다.",
            expected_output="사용자가 활동 피드를 성공적으로 조회하거나 오류 메시지를 받는다.",
            agent=agents["task_service_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="실시간 업데이트에 대한 오류 처리를 수행한다.",
            expected_output="사용자가 오류 처리를 성공적으로 수행하거나 오류 메시지를 받는다.",
            agent=agents["task_service_agent"],
            human_input=False,
        )
    )
    return tasks
