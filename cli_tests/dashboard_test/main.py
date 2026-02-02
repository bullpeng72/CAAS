'''"""
작업 관리 대시보드

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
    crew = Crew(
        agents=list(agents.values()), tasks=tasks, process=Process.hierarchical, verbose=True
    )
    result = crew.kickoff()
    return result


if __name__ == "__main__":
    main()
