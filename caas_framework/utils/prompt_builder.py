"""
Prompt Builder Utility

Unified utilities for building structured prompts for LLM interactions.
Consolidates duplicate prompt building patterns across agents.
"""

import json
from typing import Any, Dict, List, Optional


class PromptBuilder:
    """
    Utility for building structured prompts with consistent formatting.

    Consolidates 5+ duplicate prompt building methods across:
    - agents/system_architect.py: _build_architecture_prompt()
    - agents/requirement_analyst.py: _build_analysis_prompt()
    - agents/agent_designer.py: _build_design_prompt()
    - agents/qa_specialist.py: _build_qa_prompt()
    - agents/code_generator.py: _build_generation_prompt()

    Example:
        >>> prompt = (
        ...     PromptBuilder("design the system architecture")
        ...     .add_task()
        ...     .add_input(requirement="Build a todo app", domain="Web")
        ...     .add_golden_data(golden_data)
        ...     .add_constraints(["Use Python", "RESTful API"])
        ...     .add_output_format({"components": [], "dependencies": []})
        ...     .build()
        ... )
    """

    def __init__(self, task_description: str):
        """
        Initialize prompt builder with task description.

        Args:
            task_description: Description of what the LLM should do
        """
        self.sections: List[str] = []
        self.task_description = task_description

    def add_task(self, additional_context: Optional[str] = None) -> "PromptBuilder":
        """
        Add task description section.

        Args:
            additional_context: Optional additional context for the task

        Returns:
            Self for method chaining
        """
        self.sections.extend(["# Task", f"Your task is to {self.task_description}.", ""])

        if additional_context:
            self.sections.extend([additional_context, ""])

        return self

    def add_input(self, **inputs: Any) -> "PromptBuilder":
        """
        Add input section with key-value pairs.

        Args:
            **inputs: Input values as keyword arguments

        Returns:
            Self for method chaining

        Example:
            >>> builder.add_input(
            ...     requirement="Build a todo app",
            ...     domain="Web Application",
            ...     features=["CRUD", "Authentication"]
            ... )
        """
        if not inputs:
            return self

        self.sections.append("# Input")

        for key, value in inputs.items():
            # Format key as readable label
            label = key.replace("_", " ").title()

            # Format value based on type
            if isinstance(value, (list, dict)):
                value_str = json.dumps(value, indent=2, ensure_ascii=False)
                self.sections.append(f"{label}:")
                self.sections.append(value_str)
            else:
                self.sections.append(f"{label}: {value}")

        self.sections.append("")
        return self

    def add_golden_data(
        self, golden_data: Optional[Any] = None, fields: Optional[List[str]] = None
    ) -> "PromptBuilder":
        """
        Add golden data reference section.

        Args:
            golden_data: Golden data object (ConcretizedRequirement or dict)
            fields: Specific fields to extract from golden_data

        Returns:
            Self for method chaining
        """
        if not golden_data:
            return self

        self.sections.append("# Golden Data Reference")

        if isinstance(golden_data, dict):
            # Dict format
            if fields:
                filtered = {k: v for k, v in golden_data.items() if k in fields}
                self.sections.append(json.dumps(filtered, indent=2, ensure_ascii=False))
            else:
                self.sections.append(json.dumps(golden_data, indent=2, ensure_ascii=False))
        else:
            # Object with attributes
            if fields:
                data_dict = {}
                for field in fields:
                    value = getattr(golden_data, field, None)
                    # Convert Pydantic models to dict
                    if value is None:
                        data_dict[field] = None
                    elif hasattr(value, "model_dump"):
                        data_dict[field] = value.model_dump()
                    elif isinstance(value, list) and value and hasattr(value[0], "model_dump"):
                        data_dict[field] = [item.model_dump() for item in value]
                    else:
                        data_dict[field] = value
                self.sections.append(json.dumps(data_dict, indent=2, ensure_ascii=False))
            else:
                # Extract common fields
                data_dict = {}
                if hasattr(golden_data, "domain"):
                    data_dict["domain"] = golden_data.domain
                if hasattr(golden_data, "features") and golden_data.features:
                    data_dict["features"] = (
                        [f.name for f in golden_data.features]
                        if hasattr(golden_data.features[0], "name")
                        else golden_data.features
                    )
                if hasattr(golden_data, "data_models") and golden_data.data_models:
                    data_dict["data_models"] = (
                        [dm.entity_name for dm in golden_data.data_models]
                        if hasattr(golden_data.data_models[0], "entity_name")
                        else golden_data.data_models
                    )
                if hasattr(golden_data, "ui_components") and golden_data.ui_components:
                    data_dict["ui_components"] = (
                        [ui.page_name for ui in golden_data.ui_components]
                        if hasattr(golden_data.ui_components[0], "page_name")
                        else golden_data.ui_components
                    )
                if hasattr(golden_data, "deployment_target"):
                    data_dict["deployment_target"] = golden_data.deployment_target

                self.sections.append(json.dumps(data_dict, indent=2, ensure_ascii=False))

        self.sections.append("")
        return self

    def add_constraints(self, constraints: Optional[List[str]] = None) -> "PromptBuilder":
        """
        Add constraints section.

        Args:
            constraints: List of constraint strings

        Returns:
            Self for method chaining
        """
        if not constraints:
            return self

        self.sections.extend(
            ["# Constraints", *[f"- {constraint}" for constraint in constraints], ""]
        )
        return self

    def add_context(
        self, title: str, content: Any, format_as_json: bool = False
    ) -> "PromptBuilder":
        """
        Add custom context section.

        Args:
            title: Section title
            content: Content to add
            format_as_json: Whether to format content as JSON

        Returns:
            Self for method chaining
        """
        self.sections.append(f"# {title}")

        if format_as_json:
            if isinstance(content, str):
                self.sections.append(content)
            else:
                self.sections.append(json.dumps(content, indent=2, ensure_ascii=False))
        else:
            self.sections.append(str(content))

        self.sections.append("")
        return self

    def add_previous_outputs(
        self, previous_outputs: Optional[Dict[str, Any]] = None, phases: Optional[List[str]] = None
    ) -> "PromptBuilder":
        """
        Add previous agent outputs section.

        Args:
            previous_outputs: Dict of phase -> output
            phases: Specific phases to include

        Returns:
            Self for method chaining
        """
        if not previous_outputs:
            return self

        self.sections.append("# Previous Agent Outputs")

        outputs_to_show = previous_outputs
        if phases:
            outputs_to_show = {k: v for k, v in previous_outputs.items() if k in phases}

        for phase, output in outputs_to_show.items():
            phase_name = phase.replace("_", " ").title()
            self.sections.append(f"\n## {phase_name}")

            if isinstance(output, dict):
                # Show summary of dict output
                if "summary" in output:
                    self.sections.append(output["summary"])
                else:
                    # Show key fields
                    for key in list(output.keys())[:5]:  # Limit to 5 keys
                        value = output[key]
                        if isinstance(value, list):
                            self.sections.append(f"{key}: {len(value)} items")
                        elif isinstance(value, dict):
                            self.sections.append(f"{key}: {len(value)} fields")
                        else:
                            self.sections.append(f"{key}: {value}")
            else:
                self.sections.append(str(output))

        self.sections.append("")
        return self

    def add_output_format(
        self, template: Dict[str, Any], description: Optional[str] = None
    ) -> "PromptBuilder":
        """
        Add JSON output format section.

        Args:
            template: Template dict showing expected structure
            description: Optional description of the output format

        Returns:
            Self for method chaining
        """
        self.sections.append("# Output Format")

        if description:
            self.sections.append(description)
        else:
            self.sections.append("Return JSON with the following structure:")

        self.sections.extend(
            ["```json", json.dumps(template, indent=2, ensure_ascii=False), "```", ""]
        )
        return self

    def add_examples(
        self, examples: List[Dict[str, Any]], show_input: bool = True, show_output: bool = True
    ) -> "PromptBuilder":
        """
        Add examples section.

        Args:
            examples: List of example dicts with 'input' and 'output' keys
            show_input: Whether to show input in examples
            show_output: Whether to show output in examples

        Returns:
            Self for method chaining
        """
        if not examples:
            return self

        self.sections.append("# Examples")

        for i, example in enumerate(examples, 1):
            self.sections.append(f"\n## Example {i}")

            if show_input and "input" in example:
                self.sections.append("\nInput:")
                self.sections.append(f"```\n{example['input']}\n```")

            if show_output and "output" in example:
                self.sections.append("\nOutput:")
                self.sections.append(
                    f"```json\n{json.dumps(example['output'], indent=2, ensure_ascii=False)}\n```"
                )

        self.sections.append("")
        return self

    def add_guidelines(self, guidelines: List[str]) -> "PromptBuilder":
        """
        Add guidelines/best practices section.

        Args:
            guidelines: List of guideline strings

        Returns:
            Self for method chaining
        """
        if not guidelines:
            return self

        self.sections.extend(["# Guidelines", *[f"- {guideline}" for guideline in guidelines], ""])
        return self

    def add_refinement_intro(
        self, agent_role: str, output_type: str, iteration: Optional[int] = None
    ) -> "PromptBuilder":
        """
        Add refinement introduction section.

        Args:
            agent_role: Agent role (e.g., "Requirements Analyst", "System Architect")
            output_type: Type of output (e.g., "analysis", "architecture", "design")
            iteration: Optional iteration number

        Returns:
            Self for method chaining

        Example:
            >>> builder.add_refinement_intro(
            ...     agent_role="Requirements Analyst",
            ...     output_type="analysis",
            ...     iteration=2
            ... )
        """
        intro = f"You are an expert {agent_role} reviewing your previous {output_type}."

        if iteration:
            intro += f" This is iteration {iteration} of refinement."

        self.sections.extend([intro, ""])
        return self

    def add_current_output(
        self, output: Any, output_label: str = "Current Output"
    ) -> "PromptBuilder":
        """
        Add current output section for refinement.

        Args:
            output: Current output (dict or object)
            output_label: Label for the section

        Returns:
            Self for method chaining
        """
        self.sections.append(f"## {output_label}")

        if isinstance(output, dict):
            self.sections.append(json.dumps(output, indent=2, ensure_ascii=False))
        elif hasattr(output, "model_dump"):
            # Pydantic model
            self.sections.append(json.dumps(output.model_dump(), indent=2, ensure_ascii=False))
        elif hasattr(output, "dict"):
            # Legacy Pydantic
            self.sections.append(json.dumps(output.dict(), indent=2, ensure_ascii=False))
        else:
            self.sections.append(str(output))

        self.sections.append("")
        return self

    def add_validation_issues(
        self, issues_summary: str, issues_label: str = "Issues Identified"
    ) -> "PromptBuilder":
        """
        Add validation issues section for refinement.

        Args:
            issues_summary: Pre-formatted issues summary string
            issues_label: Label for the section

        Returns:
            Self for method chaining
        """
        self.sections.extend([f"## {issues_label}", issues_summary, ""])
        return self

    def add_refinement_task(
        self, output_type: str, guidelines: Optional[List[str]] = None
    ) -> "PromptBuilder":
        """
        Add refinement task section with guidelines.

        Args:
            output_type: Type of output being refined
            guidelines: Optional list of specific guidelines for refinement

        Returns:
            Self for method chaining
        """
        self.sections.extend(
            [
                "## Task",
                f"Refine the {output_type} to address all issues. Return the complete refined {output_type} in JSON format.",
                "",
            ]
        )

        if guidelines:
            self.sections.extend(
                [
                    "Important:",
                    *[f"- {guideline}" for guideline in guidelines],
                    "",
                    f"Return the complete refined {output_type}.",
                ]
            )

        return self

    @classmethod
    def build_refinement_prompt(
        cls,
        agent_role: str,
        output_type: str,
        current_output: Any,
        issues_summary: str,
        golden_data: Optional[Any] = None,
        golden_data_context: Optional[str] = None,
        guidelines: Optional[List[str]] = None,
        iteration: Optional[int] = None,
    ) -> str:
        """
        Convenience method to build a complete refinement prompt.

        Consolidates the refinement prompt pattern used across agents.

        Args:
            agent_role: Agent role (e.g., "Requirements Analyst")
            output_type: Type of output (e.g., "analysis", "architecture")
            current_output: Current output to be refined
            issues_summary: Formatted issues summary
            golden_data: Optional Golden Data object
            golden_data_context: Optional context string for Golden Data section
            guidelines: Optional refinement guidelines
            iteration: Optional iteration number

        Returns:
            Complete refinement prompt string

        Example:
            >>> prompt = PromptBuilder.build_refinement_prompt(
            ...     agent_role="Requirements Analyst",
            ...     output_type="analysis",
            ...     current_output=output_dict,
            ...     issues_summary=issues_str,
            ...     golden_data=golden_data,
            ...     golden_data_context="Features to align with",
            ...     guidelines=[
            ...         "Address each issue specifically",
            ...         "Maintain consistency with Golden Data"
            ...     ]
            ... )
        """
        builder = cls(f"refine {output_type} based on validation feedback")

        # Add introduction
        builder.add_refinement_intro(agent_role, output_type, iteration)

        # Add current output
        builder.add_current_output(current_output, f"Current {output_type.title()}")

        # Add validation issues
        builder.add_validation_issues(issues_summary)

        # Add golden data context if provided
        if golden_data:
            context_title = golden_data_context or "Golden Data Reference"
            builder.add_context(context_title, golden_data, format_as_json=True)

        # Add refinement task with guidelines
        builder.add_refinement_task(output_type, guidelines)

        return builder.build()

    def build(self) -> str:
        """
        Build final prompt string.

        Returns:
            Complete prompt as string
        """
        return "\n".join(self.sections).strip()

    def __str__(self) -> str:
        """String representation (same as build)"""
        return self.build()
