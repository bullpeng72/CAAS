"""
Input Detector

Automatically detects if user input is needed based on task descriptions.
"""

from typing import Any, Dict, List


class InputDetector:
    """
    Detects if tasks require user input and extracts input specifications.
    """

    # Phrases that indicate user input collection is needed
    # These are verb phrases that indicate INPUT COLLECTION, not just data usage
    INPUT_COLLECTION_PHRASES = [
        "입력받",  # receive input
        "입력하",  # input/enter
        "사용자로부터",  # from user
        "사용자 입력",  # user input
        "입력을 받",  # receive input
        "입력을",  # input (as object)
        "from user",
        "from the user",
        "receive input",
        "collect input",
        "get input from",
        "user input",
    ]

    # Common input types
    INPUT_TYPES = {
        "키워드": "keyword",
        "keyword": "keyword",
        "텍스트": "text",
        "text": "text",
        "숫자": "number",
        "number": "number",
        "파일": "file",
        "file": "file",
        "URL": "url",
        "url": "url",
    }

    @classmethod
    def detect_input_requirements(cls, tasks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Detect which tasks require user input.

        Args:
            tasks: List of task definitions

        Returns:
            Dict[task_id, input_spec]: {
                "task_id": {
                    "requires_input": True,
                    "input_type": "keyword",
                    "input_name": "keyword",
                    "prompt_message": "키워드를 입력하세요"
                }
            }
        """
        input_requirements = {}

        for task in tasks:
            task_id = task.get("id", "unknown")
            description = task.get("description", "")

            # Check if task requires input
            requires_input = cls._check_requires_input(description)

            if requires_input:
                # Extract input specification
                input_spec = cls._extract_input_spec(description)
                input_requirements[task_id] = input_spec

        return input_requirements

    @classmethod
    def _check_requires_input(cls, description: str) -> bool:
        """
        Check if task description indicates input collection is needed.

        Only matches phrases that indicate INPUT COLLECTION, not just data usage.
        E.g., "입력받고" (receive input) matches, but "키워드를 사용" (use keyword) doesn't.
        """
        # Check if any input collection phrase is present
        return any(phrase in description for phrase in cls.INPUT_COLLECTION_PHRASES)

    @classmethod
    def _extract_input_spec(cls, description: str) -> Dict[str, Any]:
        """Extract input specification from task description."""
        desc_lower = description.lower()

        # Determine input type
        input_type = "text"  # default
        input_name = "user_input"  # default

        for type_korean, type_english in cls.INPUT_TYPES.items():
            if type_korean in desc_lower:
                input_type = type_english
                input_name = type_english
                break

        # Generate prompt message
        if "키워드" in description or "keyword" in desc_lower:
            prompt_message = "검색할 키워드를 입력하세요"
            input_name = "keyword"
        elif "텍스트" in description or "text" in desc_lower:
            prompt_message = "텍스트를 입력하세요"
            input_name = "text"
        elif "파일" in description or "file" in desc_lower:
            prompt_message = "파일 경로를 입력하세요"
            input_name = "file_path"
        elif "url" in desc_lower:
            prompt_message = "URL을 입력하세요"
            input_name = "url"
        else:
            prompt_message = "입력하세요"
            input_name = "user_input"

        return {
            "requires_input": True,
            "input_type": input_type,
            "input_name": input_name,
            "prompt_message": prompt_message,
        }

    @classmethod
    def generate_input_collection_code(cls, input_requirements: Dict[str, Dict[str, Any]]) -> str:
        """
        Generate Python code to collect user inputs.

        Args:
            input_requirements: Dict from detect_input_requirements()

        Returns:
            Python code string
        """
        if not input_requirements:
            return ""

        code_lines = ["# Collect user inputs", "user_inputs = {}", ""]

        for task_id, spec in input_requirements.items():
            input_name = spec["input_name"]
            prompt_message = spec["prompt_message"]

            code_lines.append(f"# Input for task: {task_id}")
            code_lines.append(f"{input_name} = input('{prompt_message}: ')")
            code_lines.append(f"user_inputs['{input_name}'] = {input_name}")
            code_lines.append("")

        return "\n".join(code_lines)

    @classmethod
    def should_use_kickoff_inputs(cls, tasks: List[Dict[str, Any]]) -> bool:
        """
        Determine if crew.kickoff(inputs=...) should be used.

        Args:
            tasks: List of task definitions

        Returns:
            True if kickoff(inputs=...) is recommended
        """
        input_requirements = cls.detect_input_requirements(tasks)
        return len(input_requirements) > 0

    @classmethod
    def inject_input_placeholders(
        cls, tasks: List[Dict[str, Any]], input_requirements: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Inject input placeholders into task descriptions and remove input collection phrases.

        This ensures that tasks can use the inputs passed to crew.kickoff(inputs=...).

        Args:
            tasks: List of task definitions
            input_requirements: Dict from detect_input_requirements()

        Returns:
            Updated tasks with placeholders in descriptions

        Example:
            Before: "사용자로부터 키워드를 입력받고 유효성을 검증합니다"
            After: "Using the keyword '{keyword}', validate its validity. (Input: {keyword})"
        """
        if not input_requirements:
            return tasks

        # Phrases to remove/replace from task descriptions
        INPUT_COLLECTION_PHRASES_TO_REMOVE = [
            "사용자로부터 키워드를 입력받고 ",
            "사용자로부터 키워드를 입력받아 ",
            "키워드를 입력받고 ",
            "키워드를 입력받아 ",
            "사용자 입력을 받고 ",
            "사용자 입력을 받아 ",
            "입력받고 ",
            "입력받아 ",
            "사용자로부터 ",
            "receive keyword from user and ",
            "get keyword from user and ",
            "collect user input and ",
            "receive user input and ",
        ]

        # Update task descriptions
        for task in tasks:
            task_id = task.get("id", "")
            description = task.get("description", "")

            # Check if this task should use any inputs
            if task_id in input_requirements:
                spec = input_requirements[task_id]
                input_name = spec["input_name"]

                # Remove input collection phrases
                cleaned_desc = description
                for phrase in INPUT_COLLECTION_PHRASES_TO_REMOVE:
                    cleaned_desc = cleaned_desc.replace(phrase, "")

                # Clean up spacing
                import re

                cleaned_desc = re.sub(r"\s+", " ", cleaned_desc).strip()

                # Capitalize first letter if needed
                if cleaned_desc and not cleaned_desc[0].isupper():
                    cleaned_desc = cleaned_desc[0].upper() + cleaned_desc[1:]

                # Add explicit instruction to use the input with placeholder
                if "keyword" in input_name.lower() or "키워드" in description:
                    # For keyword inputs
                    prefix = f"Using the keyword '{{{input_name}}}', "
                elif "text" in input_name.lower() or "텍스트" in description:
                    # For text inputs
                    prefix = f"Using the text '{{{input_name}}}', "
                elif "file" in input_name.lower() or "파일" in description:
                    # For file inputs
                    prefix = f"Using the file '{{{input_name}}}', "
                else:
                    # Generic input
                    prefix = f"Using the input '{{{input_name}}}', "

                # Combine prefix with cleaned description
                task["description"] = prefix + cleaned_desc

                # Save original for reference
                task["_original_description"] = description

        return tasks
