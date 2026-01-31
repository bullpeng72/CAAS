"""
Task Description Fixer

Automatically fixes task descriptions to remove input collection parts.
"""

from typing import List, Dict, Any
import re


class TaskDescriptionFixer:
    """
    Fixes task descriptions that incorrectly include input collection.
    """

    # Phrases to remove from task descriptions
    INPUT_PHRASES = [
        "사용자로부터 키워드를 입력받고 ",
        "사용자로부터 키워드를 입력받아 ",
        "키워드를 입력받고 ",
        "키워드를 입력받아 ",
        "사용자 입력을 받고 ",
        "사용자 입력을 받아 ",
        "입력받고 ",
        "입력받아 ",
        "입력하고 ",
        "입력하여 ",
        "사용자로부터 ",
        "입력된 키워드를 ",
        "입력된 텍스트를 ",
        # English
        "receive keyword from user and ",
        "get keyword from user and ",
        "collect user input and ",
        "receive user input and ",
        "get input and ",
    ]

    @classmethod
    def fix_task_description(cls, description: str) -> str:
        """
        Fix a single task description by removing input collection phrases.

        Args:
            description: Original task description

        Returns:
            Fixed description
        """
        fixed_desc = description

        # Remove input collection phrases
        for phrase in cls.INPUT_PHRASES:
            if phrase in fixed_desc:
                fixed_desc = fixed_desc.replace(phrase, "")

        # Clean up spacing
        fixed_desc = re.sub(r'\s+', ' ', fixed_desc)
        fixed_desc = fixed_desc.strip()

        # Capitalize first letter
        if fixed_desc:
            fixed_desc = fixed_desc[0].upper() + fixed_desc[1:]

        return fixed_desc

    @classmethod
    def fix_all_tasks(cls, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fix descriptions for all tasks.

        Args:
            tasks: List of task definitions

        Returns:
            Fixed task definitions
        """
        for task in tasks:
            if "description" in task:
                original_desc = task["description"]
                fixed_desc = cls.fix_task_description(original_desc)

                if original_desc != fixed_desc:
                    task["description"] = fixed_desc
                    task["_original_description"] = original_desc  # Keep for reference

        return tasks

    @classmethod
    def generate_expected_output_map(cls, tasks: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Generate expected_output map for tasks that were fixed.

        Args:
            tasks: List of task definitions

        Returns:
            Dict[task_id, expected_output_adjustment]
        """
        adjustments = {}

        for task in tasks:
            if "_original_description" in task:
                task_id = task.get("id", "unknown")

                # If original description mentioned input, adjust expected output
                original = task.get("_original_description", "")

                if "입력" in original or "input" in original.lower():
                    # Expected output should not mention "입력됨" anymore
                    current_output = task.get("expected_output", "")

                    if "입력된" in current_output or "입력됨" in current_output:
                        # Adjust expected output
                        new_output = current_output.replace("입력된 키워드가 ", "키워드가 ")
                        new_output = new_output.replace("입력됨", "준비됨")
                        adjustments[task_id] = new_output

        return adjustments
