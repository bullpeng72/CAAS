"""
Input Detector

Automatically detects if user input is needed based on task descriptions.
"""

from typing import Any, Dict, List


class InputDetector:
    """
    Detects if tasks require user input and extracts input specifications.
    """

    # ✅ v0.4.2 (P1-1): Expanded input collection phrases
    # These are verb phrases that indicate INPUT COLLECTION, not just data usage
    INPUT_COLLECTION_PHRASES = [
        # Korean
        "입력받",  # receive input
        "입력하",  # input/enter
        "사용자로부터",  # from user
        "사용자 입력",  # user input
        "입력을 받",  # receive input
        "입력을",  # input (as object)
        # English - existing
        "from user",
        "from the user",
        "receive input",
        "collect input",
        "get input from",
        "user input",
        # ✅ NEW: English input collection patterns
        "allow users to input",
        "users to input",
        "input keyword",
        "input text",
        "enter keyword",
        "enter text",
        "provide keyword",
        "provide input",
        "submit keyword",
        "submit input",
        # ✅ NEW: Expected output patterns
        "inputted by",
        "provided by",
        "entered by",
        "submitted by",
    ]

    # ✅ v0.4.2 (P1-1): Expanded input types with plural forms
    INPUT_TYPES = {
        # Korean
        "키워드": "keyword",
        "텍스트": "text",
        "숫자": "number",
        "파일": "file",
        # English (singular)
        "keyword": "keyword",
        "text": "text",
        "number": "number",
        "file": "file",
        "url": "url",
        "URL": "url",
        # ✅ NEW: Plural forms
        "keywords": "keyword",  # plural → singular
        "texts": "text",
        "files": "file",
        "urls": "url",
        # ✅ NEW: Variations
        "search term": "keyword",
        "search query": "keyword",
        "query": "keyword",
    }

    @classmethod
    def detect_input_requirements(
        cls, tasks: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Detect which tasks require user input.

        ✅ v0.4.2 (P1-1): Enhanced to check both description AND expected_output

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
            expected_output = task.get("expected_output", "")  # ✅ NEW

            # ✅ v0.4.2: Check both description AND expected_output
            combined_text = f"{description} {expected_output}"

            # Check if task requires input
            requires_input = cls._check_requires_input(combined_text)

            if requires_input:
                # Extract input specification
                input_spec = cls._extract_input_spec(combined_text)
                input_requirements[task_id] = input_spec

        return input_requirements

    @classmethod
    def detect_input_requirements_unified(
        cls, tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        ✅ v0.5.0: Detect and deduplicate input requirements with 4-strategy fallback.

        GUARANTEED to return at least 1 input (never empty list).

        Strategy 1: Template variables ({keyword}) in task descriptions
        Strategy 2: INPUT_COLLECTION_PHRASES detection (existing)
        Strategy 3: human_input flag in tasks
        Strategy 4: Keyword matching in descriptions (입력, 검색, search, input)
        Strategy 5: Default 'keyword' input (final fallback - guaranteed)

        Returns a list of unique inputs (not per-task).
        Merges duplicate inputs that multiple tasks use.

        Args:
            tasks: List of task definitions

        Returns:
            List[input_spec]: [
                {
                    "input_type": "keyword",
                    "input_name": "keyword",
                    "prompt_message": "키워드를 입력하세요",
                    "used_by_tasks": ["task1_id", "task2_id"]
                }
            ]
        """
        # Strategy 1: Extract template variables from task descriptions
        template_inputs = cls._detect_from_template_variables(tasks)

        # Strategy 2: Use existing INPUT_COLLECTION_PHRASES detection
        per_task_requirements = cls.detect_input_requirements(tasks)

        # Strategy 3: Detect from human_input flag
        human_input_tasks = cls._detect_from_human_input_flag(tasks)

        # Strategy 4: Keyword matching in descriptions
        keyword_inputs = cls._detect_from_keyword_matching(tasks)

        # Merge all strategies (template variables take priority)
        unified_inputs = {}

        # Add template variables first (highest priority)
        for input_spec in template_inputs:
            input_name = input_spec["input_name"]
            unified_inputs[input_name] = input_spec

        # Add from INPUT_COLLECTION_PHRASES (v0.4.2 existing logic)
        for task_id, spec in per_task_requirements.items():
            input_name = spec["input_name"]

            if input_name not in unified_inputs:
                # First occurrence - create new entry
                unified_inputs[input_name] = {
                    "input_type": spec["input_type"],
                    "input_name": input_name,
                    "prompt_message": spec["prompt_message"],
                    "used_by_tasks": [task_id],
                }
            else:
                # Duplicate - add task to list
                if "used_by_tasks" not in unified_inputs[input_name]:
                    unified_inputs[input_name]["used_by_tasks"] = []
                unified_inputs[input_name]["used_by_tasks"].append(task_id)

        # Add from human_input flag
        for input_spec in human_input_tasks:
            input_name = input_spec["input_name"]
            if input_name not in unified_inputs:
                unified_inputs[input_name] = input_spec

        # Add from keyword matching
        for input_spec in keyword_inputs:
            input_name = input_spec["input_name"]
            if input_name not in unified_inputs:
                unified_inputs[input_name] = input_spec

        # Strategy 5: Final fallback - GUARANTEE at least 1 input
        if not unified_inputs:
            # ✅ v0.5.0: NEVER return empty - add default keyword input
            unified_inputs["keyword"] = {
                "input_type": "keyword",
                "input_name": "keyword",
                "prompt_message": "검색 키워드",
                "used_by_tasks": [],
            }

        # Convert to list and sort by input_name for consistency
        return sorted(unified_inputs.values(), key=lambda x: x["input_name"])

    @classmethod
    def _detect_from_template_variables(cls, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        ✅ v0.5.0 Strategy 1: Extract template variables from task descriptions.

        Finds patterns like {keyword}, {query}, {text} in task descriptions.

        Returns:
            List of input specifications
        """
        import re

        template_vars = {}

        for task in tasks:
            task_id = task.get("id", "unknown")
            description = task.get("description", "")

            # Find all {variable} patterns
            matches = re.findall(r"\{(\w+)\}", description)

            for var_name in matches:
                if var_name not in template_vars:
                    # Infer type from variable name
                    input_type = "text"
                    if "keyword" in var_name.lower() or "query" in var_name.lower():
                        input_type = "keyword"
                    elif "file" in var_name.lower():
                        input_type = "file"
                    elif "url" in var_name.lower():
                        input_type = "url"
                    elif "number" in var_name.lower() or "count" in var_name.lower():
                        input_type = "number"

                    template_vars[var_name] = {
                        "input_type": input_type,
                        "input_name": var_name,
                        "prompt_message": var_name.replace("_", " ").title(),
                        "used_by_tasks": [task_id],
                    }
                else:
                    template_vars[var_name]["used_by_tasks"].append(task_id)

        return list(template_vars.values())

    @classmethod
    def _detect_from_human_input_flag(cls, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        ✅ v0.5.0 Strategy 3: Detect tasks with human_input=True.

        Returns:
            List of input specifications
        """
        human_input_tasks = [task for task in tasks if task.get("human_input", False)]

        if not human_input_tasks:
            return []

        input_specs = []

        for task in human_input_tasks:
            task_id = task.get("id", "input")
            # Infer input name from task ID
            input_name = task_id.replace("_task", "").replace("task_", "")

            # Clean up input name
            if input_name.startswith("human_"):
                input_name = input_name[6:]

            input_specs.append({
                "input_type": "text",
                "input_name": input_name,
                "prompt_message": f"{input_name.replace('_', ' ').title()} 입력",
                "used_by_tasks": [task_id],
            })

        return input_specs

    @classmethod
    def _detect_from_keyword_matching(cls, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        ✅ v0.5.0 Strategy 4: Match keywords in task descriptions.

        Keywords: "키워드", "검색", "query", "search" (NOT generic "입력"/"input")

        ⚠️ IMPORTANT: This is a FALLBACK strategy. Only use when template variables
        are NOT found. Generic words like "입력" should NOT be used as they match
        too broadly (e.g., "입력받다", "입력된" are common Korean verbs).

        Returns:
            List of input specifications
        """
        keywords_map = {
            # ✅ Specific keywords only (no generic "입력"/"input")
            "keyword": ["키워드", "keyword", "검색어", "search keyword", "검색 키워드"],
            # ❌ REMOVED: "입력", "input" (too generic - matches "입력받다", "입력된", etc.)
            # "text": ["텍스트", "text"],  # REMOVED entirely - let template variables handle it
            "file": ["파일", "file"],
            "url": ["URL", "url", "링크", "link"],
        }

        detected_inputs = {}

        for task in tasks:
            task_id = task.get("id", "unknown")
            description = task.get("description", "").lower()

            for input_name, keywords in keywords_map.items():
                # ✅ Require EXACT word boundary match (not substring)
                import re
                pattern = r'\b(' + '|'.join(re.escape(kw.lower()) for kw in keywords) + r')\b'
                if re.search(pattern, description):
                    if input_name not in detected_inputs:
                        detected_inputs[input_name] = {
                            "input_type": input_name,
                            "input_name": input_name,
                            "prompt_message": input_name.replace("_", " ").title(),
                            "used_by_tasks": [task_id],
                        }
                    else:
                        detected_inputs[input_name]["used_by_tasks"].append(task_id)

        return list(detected_inputs.values())

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
        """
        Extract input specification from task description.

        ✅ v0.4.2 (P1-1): Enhanced to handle more patterns and plural forms
        """
        desc_lower = description.lower()

        # Determine input type (check all patterns)
        input_type = "text"  # default
        input_name = "user_input"  # default

        # ✅ v0.4.2: Check all input type patterns (including plurals)
        for type_pattern, type_english in cls.INPUT_TYPES.items():
            if type_pattern.lower() in desc_lower:
                input_type = type_english
                input_name = type_english
                break  # Use first match

        # ✅ v0.4.2: More comprehensive prompt message generation
        if "키워드" in description or "keyword" in desc_lower or "search" in desc_lower or "query" in desc_lower:
            prompt_message = "검색할 키워드를 입력하세요"
            input_name = "keyword"
            input_type = "keyword"
        elif "텍스트" in description or "text" in desc_lower:
            prompt_message = "텍스트를 입력하세요"
            input_name = "text"
            input_type = "text"
        elif "파일" in description or "file" in desc_lower:
            prompt_message = "파일 경로를 입력하세요"
            input_name = "file_path"
            input_type = "file"
        elif "url" in desc_lower:
            prompt_message = "URL을 입력하세요"
            input_name = "url"
            input_type = "url"
        elif "숫자" in description or "number" in desc_lower:
            prompt_message = "숫자를 입력하세요"
            input_name = "number"
            input_type = "number"
        else:
            prompt_message = "입력하세요"
            input_name = "user_input"
            input_type = "text"

        return {
            "requires_input": True,
            "input_type": input_type,
            "input_name": input_name,
            "prompt_message": prompt_message,
        }

    @classmethod
    def generate_input_collection_code(
        cls, input_requirements
    ) -> str:
        """
        Generate Python code to collect user inputs.

        ✅ v0.4.2: Supports both Dict (old) and List (new unified) formats

        Args:
            input_requirements: Dict from detect_input_requirements() OR
                               List from detect_input_requirements_unified()

        Returns:
            Python code string
        """
        if not input_requirements:
            return ""

        code_lines = ["# Collect user inputs", "user_inputs = {}", ""]

        # ✅ v0.4.2: Support both formats
        if isinstance(input_requirements, list):
            # New unified format (deduplicated)
            for spec in input_requirements:
                input_name = spec["input_name"]
                prompt_message = spec["prompt_message"]

                code_lines.append(f"{input_name} = input('{prompt_message}: ')")
                code_lines.append(f"user_inputs['{input_name}'] = {input_name}")
                code_lines.append("")
        else:
            # Old per-task format (may have duplicates)
            seen_inputs = set()
            for task_id, spec in input_requirements.items():
                input_name = spec["input_name"]
                prompt_message = spec["prompt_message"]

                # ✅ v0.4.2: Skip duplicates
                if input_name in seen_inputs:
                    continue
                seen_inputs.add(input_name)

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
