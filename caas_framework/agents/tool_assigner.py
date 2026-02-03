"""
Minimal Tool Assignment for Agents

Analyzes task descriptions to determine the minimum set of tools each agent needs,
reducing overhead and improving performance.
"""

from typing import Dict, List, Set

from caas_framework.utils.logger import get_logger

logger = get_logger()


class MinimalToolAssigner:
    """Assigns only the minimum necessary tools to each agent based on their tasks."""

    # Tool keywords mapping
    TOOL_KEYWORDS = {
        "web_search": [
            "search",
            "find online",
            "look up",
            "google",
            "web",
            "검색",
            "찾아",
            "조사",
            "웹",
            "인터넷",
        ],
        "file_read": [
            "read file",
            "load file",
            "open file",
            "read from",
            "read the",
            "read config",
            "load data",
            "파일 읽",
            "파일 불러",
            "파일 열",
        ],
        "file_write": [
            "write file",
            "save file",
            "create file",
            "write to",
            "save to",
            "write the",
            "save results",
            "write results",
            "write code",
            "write documentation",
            "write doc",
            "create doc",
            "write a",
            "write blog",
            "write post",
            "write article",
            "파일 쓰",
            "파일 저장",
            "파일 생성",
            "저장",
        ],
        "http_client": [
            "api",
            "http",
            "rest",
            "request",
            "endpoint",
            "fetch",
            "get data",
            "post data",
            "call api",
            "API 호출",
            "HTTP 요청",
            "데이터 가져",
        ],
        "database": [
            "database",
            "db",
            "sql",
            "query",
            "table",
            "schema",
            "crud",
            "select",
            "insert",
            "update",
            "delete",
            "데이터베이스",
            "쿼리",
            "테이블",
            "스키마",
        ],
        "shell": [
            "command",
            "shell",
            "bash",
            "execute",
            "run command",
            "terminal",
            "cli",
            "명령",
            "실행",
            "터미널",
            "쉘",
        ],
        "code_analysis": [
            "analyze code",
            "parse",
            "ast",
            "lint",
            "check syntax",
            "review code",
            "inspect",
            "analyze the code",
            "check for issues",
            "check code",
            "review the code",
            "코드 분석",
            "파싱",
            "검토",
            "검사",
        ],
        "git": [
            "git",
            "commit",
            "push",
            "pull",
            "branch",
            "merge",
            "version control",
            "repository",
            "커밋",
            "푸시",
            "풀",
            "브랜치",
            "병합",
            "저장소",
        ],
        "package_manager": [
            "install",
            "pip",
            "npm",
            "yarn",
            "poetry",
            "package",
            "dependency",
            "requirements",
            "설치",
            "패키지",
            "의존성",
        ],
        "docker": [
            "docker",
            "container",
            "image",
            "dockerfile",
            "containerize",
            "deploy",
            "도커",
            "컨테이너",
            "이미지",
            "배포",
        ],
    }

    def __init__(self, available_tools: List[str] = None):
        """
        Initialize the MinimalToolAssigner.

        Args:
            available_tools: List of all available tool names. If None, uses all predefined tools.
        """
        self.available_tools = available_tools or list(self.TOOL_KEYWORDS.keys())

    def assign_tools(
        self,
        agent_id: str,
        agent_role: str,
        tasks: List[Dict[str, str]],
        agent_specs: List[Dict[str, str]] = None,
    ) -> List[str]:
        """
        Assign minimal set of tools to an agent based on their tasks.

        Args:
            agent_id: Unique identifier for the agent
            agent_role: Role/name of the agent
            tasks: List of task specifications with 'description', 'agent', etc.
            agent_specs: Optional list of agent specifications for additional context

        Returns:
            List of tool names that this agent needs
        """
        # Filter tasks for this specific agent
        agent_tasks = [
            task
            for task in tasks
            if task.get("agent") == agent_id or task.get("agent_id") == agent_id
        ]

        if not agent_tasks:
            # No tasks assigned to this agent, check role
            return self._infer_tools_from_role(agent_role)

        required_tools: Set[str] = set()

        # Analyze each task description
        for task in agent_tasks:
            description = task.get("description", "")
            tools = self._analyze_description(description)
            required_tools.update(tools)

        # Filter to only available tools
        result = [tool for tool in required_tools if tool in self.available_tools]

        # If no tools detected, provide minimal default based on role
        if not result:
            result = self._get_default_tools_for_role(agent_role)

        return result

    def _analyze_description(self, description: str) -> Set[str]:
        """
        Analyze a task description to determine required tools.

        Args:
            description: Task description text

        Returns:
            Set of tool names required for this task
        """
        tools = set()
        description_lower = description.lower()

        # Check for each tool's keywords
        for tool_name, keywords in self.TOOL_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in description_lower:
                    tools.add(tool_name)
                    break  # Found a match for this tool

        return tools

    def _infer_tools_from_role(self, role: str) -> List[str]:
        """
        Infer tools from agent role when no tasks are assigned.

        Args:
            role: Agent role/title

        Returns:
            List of tools inferred from the role
        """
        role_lower = role.lower()
        tools = set()

        # Role-based tool mapping
        role_mappings = {
            "research": ["web_search", "file_read", "http_client"],
            "analyst": ["file_read", "code_analysis", "database"],
            "developer": ["file_read", "file_write", "code_analysis", "git"],
            "writer": ["file_read", "file_write"],
            "tester": ["file_read", "shell", "code_analysis"],
            "test": ["file_read", "shell"],
            "qa": ["file_read", "shell", "code_analysis"],
            "deploy": ["shell", "docker", "git"],
            "database": ["database", "file_read"],
            "api": ["http_client", "file_read"],
            "devops": ["shell", "docker", "git", "package_manager"],
            "code review": ["file_read", "code_analysis"],
            "reviewer": ["file_read", "code_analysis"],
            "publish": ["http_client", "file_read"],
        }

        for role_keyword, role_tools in role_mappings.items():
            if role_keyword in role_lower:
                tools.update(role_tools)

        # If no tools found, return default
        if not tools:
            tools = set(["file_read", "file_write"])

        return list(tools)

    def _get_default_tools_for_role(self, role: str) -> List[str]:
        """
        Get default minimal tools when nothing else can be inferred.

        Args:
            role: Agent role

        Returns:
            Minimal default tool set
        """
        # Very basic default - file read/write for most roles
        return ["file_read", "file_write"]

    def assign_tools_for_all_agents(
        self, agents: List[Dict[str, str]], tasks: List[Dict[str, str]]
    ) -> Dict[str, List[str]]:
        """
        Assign tools to all agents based on their tasks.

        Args:
            agents: List of agent specifications
            tasks: List of task specifications

        Returns:
            Dictionary mapping agent_id to list of required tools
        """
        result = {}

        for agent in agents:
            agent_id = agent.get("id", agent.get("role"))
            agent_role = agent.get("role", "")

            tools = self.assign_tools(
                agent_id=agent_id,
                agent_role=agent_role,
                tasks=tasks,
                agent_specs=agents,
            )

            result[agent_id] = tools

        return result

    def get_tool_usage_report(
        self, agents: List[Dict[str, str]], tasks: List[Dict[str, str]]
    ) -> Dict[str, any]:
        """
        Generate a report on tool usage optimization.

        Args:
            agents: List of agent specifications
            tasks: List of task specifications

        Returns:
            Dictionary with tool usage statistics
        """
        # Get minimal tool assignments
        minimal_assignments = self.assign_tools_for_all_agents(agents, tasks)

        # Calculate statistics
        total_tools_minimal = sum(len(tools) for tools in minimal_assignments.values())
        avg_tools_per_agent = total_tools_minimal / len(agents) if agents else 0

        # Count tool frequency
        tool_frequency = {}
        for tools in minimal_assignments.values():
            for tool in tools:
                tool_frequency[tool] = tool_frequency.get(tool, 0) + 1

        # Most common tools
        most_common = sorted(tool_frequency.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        return {
            "total_agents": len(agents),
            "total_tools_assigned": total_tools_minimal,
            "avg_tools_per_agent": round(avg_tools_per_agent, 2),
            "tool_frequency": tool_frequency,
            "most_common_tools": most_common,
            "assignments": minimal_assignments,
        }


def optimize_agent_tools(
    agents: List[Dict[str, str]],
    tasks: List[Dict[str, str]],
    available_tools: List[str] = None,
    verbose: bool = False,
) -> List[Dict[str, str]]:
    """
    Convenience function to optimize tool assignments for all agents.

    Args:
        agents: List of agent specifications
        tasks: List of task specifications
        available_tools: Optional list of available tool names
        verbose: Whether to print optimization report

    Returns:
        Updated list of agent specifications with optimized tool assignments
    """
    assigner = MinimalToolAssigner(available_tools)

    # Get optimal tool assignments
    assignments = assigner.assign_tools_for_all_agents(agents, tasks)

    # Update agent specifications
    optimized_agents = []
    for agent in agents:
        agent_id = agent.get("id", agent.get("role"))
        updated_agent = agent.copy()
        updated_agent["tools"] = assignments.get(agent_id, [])
        optimized_agents.append(updated_agent)

    # Print report if verbose
    if verbose:
        report = assigner.get_tool_usage_report(agents, tasks)
        logger.info("\n" + "=" * 70)
        logger.info("Tool Assignment Optimization Report")
        logger.info("=" * 70)
        logger.info(f"Total Agents: {report['total_agents']}")
        logger.info(f"Total Tools Assigned: {report['total_tools_assigned']}")
        logger.info(f"Average Tools per Agent: {report['avg_tools_per_agent']}")
        logger.info("\nMost Common Tools:")
        for tool, count in report["most_common_tools"]:
            logger.info(f"  - {tool}: {count} agents")
        logger.info("=" * 70 + "\n")

    return optimized_agents
