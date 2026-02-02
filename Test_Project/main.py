'''"""
동향 리포트 시스템

Main execution script for CrewAI multi-agent system.
"""'''

from crewai import Crew, Process
from agents import create_agents
from tasks import create_tasks
from dotenv import load_dotenv

load_dotenv()


def main():
    agents = create_agents()
    tasks = create_tasks(agents)
    user_inputs = {}
    keyword = input("검색할 키워드를 입력하세요: ")
    user_inputs["keyword"] = keyword
    crew = Crew(agents=list(agents.values()), tasks=tasks, process=Process.sequential, verbose=True)
    result = crew.kickoff(inputs=user_inputs)
    return result


if __name__ == "__main__":
    main()
