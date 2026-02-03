"""
Task Validator

Validates task definitions and detects common mistakes.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TaskValidationIssue:
    """Task validation issue"""

    task_id: str
    severity: str  # "error", "warning", "info"
    issue_type: str
    message: str
    suggestion: Optional[str] = None


class TaskValidator:
    """
    Validates task definitions and detects common anti-patterns.
    """

    @staticmethod
    def validate_human_input_usage(
        tasks: List[Dict[str, Any]],
    ) -> List[TaskValidationIssue]:
        """
        Validate human_input usage.

        Common mistake: Using human_input=True for "input collection" tasks.
        Correct usage: human_input is for feedback AFTER task completion.

        Args:
            tasks: List of task definitions

        Returns:
            List of validation issues
        """
        issues = []

        input_keywords = [
            "입력",
            "input",
            "받",
            "receive",
            "collect",
            "get from user",
            "사용자로부터",
            "from user",
            "키워드를 입력",
            "텍스트 입력",
        ]

        for task in tasks:
            task_id = task.get("id", "unknown")
            description = task.get("description", "").lower()
            human_input = task.get("human_input", False)

            # Check if task description mentions "input" but uses human_input
            has_input_keyword = any(
                keyword in description for keyword in input_keywords
            )

            if has_input_keyword and human_input:
                issues.append(
                    TaskValidationIssue(
                        task_id=task_id,
                        severity="error",
                        issue_type="human_input_misuse",
                        message=f"Task '{task_id}' description mentions user input collection, "
                        f"but human_input=True is for feedback, not input collection.",
                        suggestion="Use crew.kickoff(inputs={...}) to pass user input, or remove "
                        "the 'input collection' part from task description.",
                    )
                )

        return issues

    @staticmethod
    def validate_task_agent_tool_alignment(
        tasks: List[Dict[str, Any]], agents: List[Dict[str, Any]]
    ) -> List[TaskValidationIssue]:
        """
        Validate that agents have tools needed for their tasks.

        Args:
            tasks: List of task definitions
            agents: List of agent definitions

        Returns:
            List of validation issues
        """
        issues = []

        # Build agent tools map
        agent_tools = {}
        for agent in agents:
            agent_id = agent.get("id")
            tools = agent.get("tools", [])
            agent_tools[agent_id] = tools

        # Check each task
        for task in tasks:
            task_id = task.get("id", "unknown")
            description = task.get("description", "").lower()
            agent_id = task.get("agent")

            if not agent_id:
                continue

            tools = agent_tools.get(agent_id, [])

            # Check for search tasks without search tools
            search_keywords = [
                "검색",
                "search",
                "찾",
                "find",
                "조회",
                "lookup",
                "웹",
                "web",
                "인터넷",
                "internet",
            ]
            needs_search = any(keyword in description for keyword in search_keywords)

            if needs_search and not any(
                "search" in str(tool).lower() for tool in tools
            ):
                issues.append(
                    TaskValidationIssue(
                        task_id=task_id,
                        severity="warning",
                        issue_type="missing_search_tool",
                        message=f"Task '{task_id}' requires search but agent '{agent_id}' has no search tools.",
                        suggestion="Add 'web_search' or 'scrape_website' to agent tools.",
                    )
                )

            # Check for file tasks without file tools
            file_keywords = [
                "파일",
                "file",
                "저장",
                "save",
                "쓰",
                "write",
                "기록",
                "record",
            ]
            needs_file = any(keyword in description for keyword in file_keywords)

            if needs_file and not any("file" in str(tool).lower() for tool in tools):
                issues.append(
                    TaskValidationIssue(
                        task_id=task_id,
                        severity="warning",
                        issue_type="missing_file_tool",
                        message=f"Task '{task_id}' requires file operations but agent '{agent_id}' has no file tools.",
                        suggestion="Add 'file_write' or 'code_interpreter' to agent tools.",
                    )
                )

        return issues

    @staticmethod
    def suggest_task_decomposition(
        task: Dict[str, Any],
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Suggest task decomposition if task is too complex.

        Args:
            task: Task definition

        Returns:
            List of suggested sub-tasks, or None if no decomposition needed
        """
        description = task.get("description", "")

        # Check for multiple verbs (multiple actions)
        action_keywords = [
            "그리고",
            "and",
            "한 후",
            "after",
            "다음",
            "then",
            "또한",
            "also",
        ]

        has_multiple_actions = any(
            keyword in description for keyword in action_keywords
        )

        if has_multiple_actions:
            # Suggest decomposition
            return None  # TODO: Implement smart decomposition

        return None

    @classmethod
    def validate_all(
        cls, tasks: List[Dict[str, Any]], agents: List[Dict[str, Any]]
    ) -> List[TaskValidationIssue]:
        """
        Run all validations.

        Args:
            tasks: List of task definitions
            agents: List of agent definitions

        Returns:
            List of all validation issues
        """
        issues = []

        issues.extend(cls.validate_human_input_usage(tasks))
        issues.extend(cls.validate_task_agent_tool_alignment(tasks, agents))

        return issues
