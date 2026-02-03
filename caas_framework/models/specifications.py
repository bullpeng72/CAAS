"""
Specification Models

Models for agents, tasks, and requirements.
"""

import re
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# ==================== Agent Models ====================


class AgentSpecModel(BaseModel):
    """
    에이전트 스펙 모델

    CrewAI 에이전트 정의
    """

    id: str
    role: str
    goal: str
    backstory: str
    tools: List[str] = Field(default_factory=list)
    verbose: bool = True
    memory: bool = True
    allow_delegation: bool = False
    max_iter: int = 15

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """ID 검증 (snake_case, 최대 64자)"""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(f"ID는 snake_case여야 합니다: {v}")
        if len(v) > 64:
            raise ValueError(f"ID가 너무 깁니다 (최대 64자): {len(v)}")
        return v


# ==================== Task Models ====================


class TaskSpecModel(BaseModel):
    """
    태스크 스펙 모델

    CrewAI 태스크 정의
    """

    id: str
    description: str
    expected_output: str
    agent: str
    context: List[str] = Field(default_factory=list)
    async_execution: bool = False
    output_file: Optional[str] = None
    human_input: bool = False

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """ID 검증 (snake_case, 최대 64자)"""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(f"ID는 snake_case여야 합니다: {v}")
        if len(v) > 64:
            raise ValueError(f"ID가 너무 깁니다 (최대 64자): {len(v)}")
        return v


# ==================== Golden Data Models ====================


class SystemScope(BaseModel):
    """System scope specification"""

    project_name: str
    purpose: str
    target_users: List[str] = Field(default_factory=list)
    system_type: str = "web_app"
    scope_description: Optional[str] = None
    out_of_scope: List[str] = Field(default_factory=list)


class FeatureSpec(BaseModel):
    """Feature specification from requirements"""

    id: str
    name: str
    description: str
    priority: str = "medium"  # low, medium, high, critical
    acceptance_criteria: List[str] = Field(default_factory=list)
    functional_requirements: List[str] = Field(default_factory=list)
    user_stories: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def convert_strings_to_lists(cls, values: Any) -> Any:
        """Convert string fields to lists if needed"""
        if isinstance(values, dict):
            # Convert string to single-item list for list fields
            for field_name in [
                "acceptance_criteria",
                "functional_requirements",
                "user_stories",
            ]:
                if field_name in values and isinstance(values[field_name], str):
                    # If it's a non-empty string, wrap it in a list
                    if values[field_name].strip():
                        values[field_name] = [values[field_name]]
                    else:
                        values[field_name] = []
        return values


class AttributeSpec(BaseModel):
    """Data attribute specification"""

    name: str
    type: str
    required: bool = True


class RelationshipSpec(BaseModel):
    """Data relationship specification"""

    type: str  # one-to-one, one-to-many, many-to-one, many-to-many
    target: str  # Target entity name


class DataModel(BaseModel):
    """Data model specification"""

    entity_name: str
    description: Optional[str] = None
    attributes: List[AttributeSpec] = Field(default_factory=list)
    relationships: List[RelationshipSpec] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def convert_attributes_and_relationships(cls, values: Any) -> Any:
        """Convert attributes and relationships from various formats"""
        if isinstance(values, dict):
            # Convert string attributes to AttributeSpec objects
            if "attributes" in values and isinstance(values["attributes"], list):
                converted_attrs = []
                for attr in values["attributes"]:
                    if isinstance(attr, str):
                        # Old format: just a string
                        converted_attrs.append(
                            {"name": attr, "type": "string", "required": True}
                        )
                    elif isinstance(attr, dict):
                        # New format: already a dict, ensure 'required' is bool
                        attr_copy = attr.copy()
                        if "required" in attr_copy:
                            # Convert "true"/"false" strings to boolean
                            if isinstance(attr_copy["required"], str):
                                attr_copy["required"] = attr_copy[
                                    "required"
                                ].lower() in (
                                    "true",
                                    "1",
                                    "yes",
                                )
                        converted_attrs.append(attr_copy)
                    else:
                        converted_attrs.append(attr)
                values["attributes"] = converted_attrs

            # Convert string relationships to RelationshipSpec objects
            if "relationships" in values and isinstance(values["relationships"], list):
                converted_rels = []
                for rel in values["relationships"]:
                    if isinstance(rel, str):
                        # Old format: just a string
                        converted_rels.append({"type": "one-to-many", "target": rel})
                    else:
                        converted_rels.append(rel)
                values["relationships"] = converted_rels

        return values


class UIComponent(BaseModel):
    """UI component specification"""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )  # Auto-generate UUID if not provided
    component_type: str
    page_name: str
    description: Optional[str] = None  # Made optional
    purpose: Optional[str] = None
    data_source: Optional[str] = None  # Automatically converted from list in validator
    interactions: List[str] = Field(default_factory=list)
    related_features: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_fields(cls, values: Any) -> Any:
        """Handle legacy field names and ensure at least description or purpose exists"""
        if isinstance(values, dict):
            # Handle 'component_name' -> 'page_name' mapping
            if "component_name" in values and "page_name" not in values:
                values["page_name"] = values.pop("component_name")

            # Handle 'type' -> 'component_type' mapping
            if "type" in values and "component_type" not in values:
                values["component_type"] = values.pop("type")

            # Normalize data_source: convert list to comma-separated string
            if "data_source" in values and isinstance(values["data_source"], list):
                if values["data_source"]:  # Non-empty list
                    values["data_source"] = ", ".join(
                        str(item) for item in values["data_source"]
                    )
                else:  # Empty list
                    values["data_source"] = None

            # If neither description nor purpose exists, create a default description
            if not values.get("description") and not values.get("purpose"):
                values[
                    "description"
                ] = f"{values.get('component_type', 'UI component')} in {values.get('page_name', 'unknown page')}"

        return values


class NonFunctionalRequirements(BaseModel):
    """
    Non-functional requirements (legacy compatibility)

    NOTE: ConcretizedRequirement now uses Dict[str, Any] for NFRs,
    but this class is kept for backward compatibility.
    """

    security: Optional[str] = None
    scalability: Optional[str] = None
    performance: Optional[str] = None
    reliability: Optional[str] = None
    usability: Optional[str] = None
    maintainability: Optional[str] = None


class BoundariesSpec(BaseModel):
    """
    Security Boundaries Specification (Spec-Driven Development Core Area #6)

    Defines what the generated code can/cannot do for security.
    Based on Addy Osmani's 3-tier boundary system.
    """

    always_allowed: List[str] = Field(
        default_factory=list,
        description="Operations that are always permitted without user approval",
    )
    ask_first: List[str] = Field(
        default_factory=list,
        description="Operations that require user approval before execution",
    )
    never_allowed: List[str] = Field(
        default_factory=list, description="Operations that are strictly forbidden"
    )


class CommandsSpec(BaseModel):
    """
    Commands Specification (Spec-Driven Development Core Area #1)

    Defines standard commands for project lifecycle.
    """

    install: str = Field(default="pip install -r requirements.txt")
    test: str = Field(default="pytest tests/")
    run: str = Field(default="python main.py")
    lint: Optional[str] = Field(default="pylint src/")
    format: Optional[str] = Field(default="black src/")
    build: Optional[str] = None
    deploy: Optional[str] = None


class CodeStyleSpec(BaseModel):
    """
    Code Style Specification (Spec-Driven Development Core Area #4)

    Defines coding standards and style guidelines.
    """

    formatter: str = Field(default="black")
    line_length: int = Field(default=88)
    use_type_hints: bool = Field(default=True)
    docstring_style: str = Field(default="google")  # google, numpy, sphinx
    import_order: str = Field(default="isort")


class GitWorkflowSpec(BaseModel):
    """
    Git Workflow Specification (Spec-Driven Development Core Area #5)

    Defines Git branching and commit conventions.
    """

    branch_naming: str = Field(default="feature/{issue-number}-{description}")
    commit_message_format: str = Field(default="<type>(<scope>): <subject>")
    requires_pr: bool = Field(default=True)
    main_branch: str = Field(default="main")


class ConcretizedRequirement(BaseModel):
    """
    Golden Data - Concretized Requirements

    Phase 0에서 생성되는 구체화된 요구사항
    모든 후속 Phase의 검증 기준이 됨

    Enhanced with 6 Core Spec-Driven Development Areas:
    1. Commands - Project lifecycle commands
    2. Testing - Test framework and structure (existing)
    3. Project Structure - Directory layout (existing)
    4. Code Style - Coding standards
    5. Git Workflow - Version control conventions
    6. Boundaries - Security boundaries (MOST CRITICAL)
    """

    # System scope (contains project_name, description, etc.)
    system_scope: SystemScope

    # Core specifications
    features: List[FeatureSpec] = Field(default_factory=list)
    data_models: List[DataModel] = Field(default_factory=list)
    ui_components: List[UIComponent] = Field(default_factory=list)

    # Non-functional requirements (can be dict or object)
    non_functional_requirements: Dict[str, Any] = Field(default_factory=dict)

    # Additional metadata
    constraints: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    domain: str = "general"

    # Workflow configuration
    workflow_type: str = "sequential"  # sequential, hierarchical, parallel
    deployment_target: str = "docker"  # docker, kubernetes, etc.

    # ========== Spec-Driven Development (6 Core Areas) ==========
    # CRITICAL: Boundaries for security
    boundaries: Optional[BoundariesSpec] = None

    # Commands for project lifecycle
    commands: Optional[CommandsSpec] = None

    # Code style guidelines
    code_style: Optional[CodeStyleSpec] = None

    # Git workflow conventions
    git_workflow: Optional[GitWorkflowSpec] = None

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_format(cls, values: Any) -> Any:
        """
        Migrate legacy format to new format.

        Old format had project_name, description at root level.
        New format has them in system_scope.
        Also converts NonFunctionalRequirements object to dict if needed.
        """
        if isinstance(values, dict):
            # If system_scope doesn't exist but project_name/description do, create system_scope
            if "system_scope" not in values:
                if "project_name" in values or "description" in values:
                    values["system_scope"] = {
                        "project_name": values.pop("project_name", "Untitled Project"),
                        "purpose": values.pop("description", ""),
                        "target_users": [],
                        "system_type": "web_app",
                    }

            # Convert NonFunctionalRequirements object to dict if needed
            if "non_functional_requirements" in values:
                nfr = values["non_functional_requirements"]
                # If it's a NonFunctionalRequirements object, convert to dict
                if not isinstance(nfr, dict) and hasattr(nfr, "model_dump"):
                    values["non_functional_requirements"] = nfr.model_dump(
                        exclude_none=True
                    )
                elif not isinstance(nfr, dict) and hasattr(nfr, "__dict__"):
                    # Fallback for non-Pydantic objects
                    values["non_functional_requirements"] = {
                        k: v
                        for k, v in nfr.__dict__.items()
                        if not k.startswith("_") and v is not None
                    }
        return values

    # Legacy compatibility: provide these as properties
    @property
    def project_name(self) -> str:
        """Get project name from system_scope"""
        return self.system_scope.project_name

    @property
    def description(self) -> str:
        """Get description from system_scope"""
        return self.system_scope.purpose or self.system_scope.scope_description or ""
