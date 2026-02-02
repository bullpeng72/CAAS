'''"""
Task definitions for CrewAI system.
"""'''

from crewai import Task


def create_tasks(agents):
    tasks = []
    tasks.append(
        Task(
            description="사용자의 인증을 수행한다.",
            expected_output="인증 성공 또는 실패 메시지",
            agent=agents["user_authentication_agent"],
            human_input=True,
        )
    )
    tasks.append(
        Task(
            description="Using the keyword '{keyword}', 이를 저장한다.",
            expected_output="입력된 키워드가 저장되었다는 메시지",
            agent=agents["keyword_input_agent"],
            human_input=True,
        )
    )
    tasks.append(
        Task(
            description="입력된 키워드의 유효성을 검증한다.",
            expected_output="유효성 검증 결과 및 오류 메시지",
            agent=agents["keyword_validation_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="유효성 검증 중 발생한 오류를 처리한다.",
            expected_output="오류 처리 결과 메시지",
            agent=agents["keyword_error_handling_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="유효한 키워드에 대해 관련 데이터를 수집한다.",
            expected_output="수집된 데이터 목록",
            agent=agents["data_collection_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="수집된 데이터를 바탕으로 동향 리포트를 생성한다.",
            expected_output="생성된 리포트 파일",
            agent=agents["report_generation_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="사용자에게 키워드 제안을 제공한다.",
            expected_output="제안된 키워드 목록",
            agent=agents["keyword_suggestion_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="입력된 키워드의 이력을 관리하고 저장한다.",
            expected_output="키워드 이력 저장 완료 메시지",
            agent=agents["keyword_history_tracking_agent"],
            human_input=False,
        )
    )
    tasks.append(
        Task(
            description="데이터의 보안을 유지하고 접근을 관리한다.",
            expected_output="보안 상태 보고서",
            agent=agents["data_security_agent"],
            human_input=False,
        )
    )
    return tasks
