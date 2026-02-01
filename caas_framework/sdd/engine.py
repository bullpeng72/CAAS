"""
CAAS SDD Engine

Spec-Driven Development 엔진입니다.
YAML 스펙 파싱, 검증, 생성을 담당합니다.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator

import logging
from caas_framework.utils.security import (
    safe_yaml_load,
    validate_project_name,
    YAMLSecurityError,
)
from caas_framework.models import (
    LLMConfigSpec,
    AgentSpecModel,
    TaskSpecModel,
)

logger = logging.getLogger("caas_framework.sdd.engine")


# =============================================================================
# Spec Models
# NOTE: AgentSpecModel, TaskSpecModel은 app.models.schemas에서 import됨
# =============================================================================


class CrewConfigSpec(BaseModel):
    """Crew 설정 스펙"""
    process: str = "sequential"
    verbose: bool = True
    memory: bool = True
    max_rpm: Optional[int] = None
    share_crew: bool = False
    
    @field_validator("process")
    @classmethod
    def validate_process(cls, v: str) -> str:
        if v not in ["sequential", "hierarchical"]:
            raise ValueError(f"process는 sequential 또는 hierarchical이어야 합니다: {v}")
        return v


class ProjectSpec(BaseModel):
    """프로젝트 스펙"""
    name: str
    description: str
    domain: str
    core_entities: Optional[List[str]] = None  # Week 3: CRUD 코드 생성용

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """프로젝트 이름을 보안 검증"""
        return validate_project_name(v)


class CrewAISpec(BaseModel):
    """CrewAI 전체 스펙"""
    version: str = "1.0"
    project: ProjectSpec
    agents: List[AgentSpecModel]
    tasks: List[TaskSpecModel]
    crew: CrewConfigSpec


# =============================================================================
# Validation
# =============================================================================

class ValidationError(BaseModel):
    """검증 오류"""
    type: str
    location: str
    message: str
    severity: str = "error"  # error, warning


class ValidationResult(BaseModel):
    """검증 결과"""
    valid: bool
    errors: List[ValidationError] = []
    warnings: List[str] = []
    suggestions: List[str] = []


class SpecValidator:
    """스펙 검증기"""
    
    def validate(self, spec: CrewAISpec) -> ValidationResult:
        """
        CrewAI 스펙을 검증합니다.

        Args:
            spec: CrewAI 스펙

        Returns:
            ValidationResult: 검증 결과
        """
        errors = []
        warnings = []
        suggestions = []

        # Tool Registry에서 등록된 도구 가져오기
        from caas_framework.models.tool_registry import get_enabled_tools_dict, get_all_tools_dict
        from difflib import get_close_matches

        enabled_tools = set(get_enabled_tools_dict().keys())
        all_tools = set(get_all_tools_dict().keys())

        # 에이전트 ID 수집
        agent_ids = {agent.id for agent in spec.agents}
        task_ids = {task.id for task in spec.tasks}

        # 태스크의 에이전트 참조 검증
        for task in spec.tasks:
            if task.agent not in agent_ids:
                errors.append(ValidationError(
                    type="invalid_reference",
                    location=f"tasks.{task.id}.agent",
                    message=f"존재하지 않는 에이전트 참조: {task.agent}",
                ))

            # 컨텍스트 참조 검증
            for ctx in task.context:
                if ctx not in task_ids:
                    errors.append(ValidationError(
                        type="invalid_reference",
                        location=f"tasks.{task.id}.context",
                        message=f"존재하지 않는 태스크 참조: {ctx}",
                    ))

        # 순환 의존성 검사
        if self._has_circular_dependency(spec.tasks):
            errors.append(ValidationError(
                type="circular_dependency",
                location="tasks",
                message="태스크 간 순환 의존성이 발견되었습니다.",
            ))

        # 에이전트 도구 검증 및 경고
        for agent in spec.agents:
            # 도구 등록 여부 검증
            for tool in agent.tools:
                if tool not in enabled_tools:
                    if tool in all_tools:
                        # 비활성화된 도구
                        warnings.append(
                            f"에이전트 '{agent.id}'의 도구 '{tool}'가 "
                            f"비활성화되어 있습니다. Tool Manager에서 활성화하세요."
                        )
                    else:
                        # 등록되지 않은 도구 - 유사 도구 제안
                        similar = get_close_matches(tool, enabled_tools, n=3, cutoff=0.6)

                        if similar:
                            suggestions.append(
                                f"에이전트 '{agent.id}'의 도구 '{tool}'를 찾을 수 없습니다. "
                                f"유사한 도구: {', '.join(similar)}"
                            )

                        errors.append(ValidationError(
                            type="invalid_tool",
                            location=f"agents.{agent.id}.tools",
                            message=f"등록되지 않은 도구: {tool}",
                        ))

            # 도구 미할당 경고
            if not agent.tools:
                warnings.append(f"에이전트 '{agent.id}'에 도구가 할당되지 않았습니다.")

            # Backstory 권장사항
            if len(agent.backstory) < 50:
                suggestions.append(f"에이전트 '{agent.id}'의 backstory를 더 상세히 작성하세요.")

        # Hierarchical 모드 검증
        if spec.crew.process == "hierarchical":
            # Allow delegation 권장사항
            if all(not agent.allow_delegation for agent in spec.agents):
                suggestions.append(
                    "Hierarchical 모드에서는 일부 에이전트에 allow_delegation을 활성화하면 "
                    "Manager가 더 효과적으로 작업을 조율할 수 있습니다."
                )

            # 에이전트 수 권장사항
            if len(spec.agents) < 2:
                warnings.append(
                    "Hierarchical 모드는 여러 에이전트를 조율할 때 효과적입니다. "
                    "에이전트가 1개뿐이라면 Sequential 모드를 고려하세요."
                )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )
    
    def _has_circular_dependency(self, tasks: List[TaskSpecModel]) -> bool:
        """순환 의존성 검사"""
        task_map = {t.id: t.context for t in tasks}
        
        def has_cycle(task_id: str, visited: set, rec_stack: set) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            
            for dep in task_map.get(task_id, []):
                if dep not in visited:
                    if has_cycle(dep, visited, rec_stack):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(task_id)
            return False
        
        visited = set()
        for task_id in task_map:
            if task_id not in visited:
                if has_cycle(task_id, visited, set()):
                    return True
        
        return False


# =============================================================================
# Parser & Generator
# =============================================================================

class SpecParser:
    """스펙 파서"""

    def __init__(self):
        self.logger = logger

    def parse_yaml(self, yaml_content: str) -> CrewAISpec:
        """
        YAML 문자열을 파싱합니다.

        Args:
            yaml_content: YAML 문자열

        Returns:
            CrewAISpec: 파싱된 스펙

        Raises:
            ValueError: YAML이 유효하지 않은 경우
            YAMLSecurityError: YAML이 보안 정책을 위반하는 경우
        """
        try:
            # SECURITY: 제한이 있는 safe YAML 로더 사용
            data = safe_yaml_load(
                yaml_content,
                max_size=1_000_000,  # 1MB 제한
                max_depth=10,         # 10 레벨 최대
            )
            return CrewAISpec(**data)
        except YAMLSecurityError as e:
            self.logger.error(f"YAML 보안 검사 실패: {e}")
            raise ValueError(f"YAML이 보안 정책을 위반했습니다: {e}")
        except ValueError as e:
            # 이미 ValueError
            raise
        except Exception as e:
            self.logger.error(f"스펙 파싱 오류: {e}")
            raise ValueError(f"스펙 파싱 실패: {e}")
    
    def parse_file(self, file_path: Path) -> CrewAISpec:
        """
        YAML 파일을 파싱합니다.
        
        Args:
            file_path: YAML 파일 경로
        
        Returns:
            CrewAISpec: 파싱된 스펙
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return self.parse_yaml(f.read())


class SpecGenerator:
    """스펙 생성기"""

    def __init__(self):
        self.logger = logger

    def generate_yaml(self, spec: CrewAISpec) -> str:
        """
        CrewAI 스펙을 YAML 문자열로 변환합니다.
        
        Args:
            spec: CrewAI 스펙
        
        Returns:
            str: YAML 문자열
        """
        # Pydantic 모델을 딕셔너리로 변환
        data = spec.model_dump(exclude_none=True)
        
        # YAML 헤더 추가
        header = f"""# CrewAI Specification
# Generated by CAAS - SDD Methodology
# Project: {spec.project.name}
# Domain: {spec.project.domain}
# Version: {spec.version}
#
# This specification follows the Spec-Driven Development methodology.
# Modify with care and validate before code generation.

"""
        yaml_content = yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            indent=2,
        )
        
        return header + yaml_content
    
    def save_yaml(self, spec: CrewAISpec, file_path: Path) -> None:
        """
        스펙을 YAML 파일로 저장합니다.
        
        Args:
            spec: CrewAI 스펙
            file_path: 저장 경로
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.generate_yaml(spec))
        self.logger.info(f"스펙 저장 완료: {file_path}")


# =============================================================================
# SDD Engine
# =============================================================================

class SDDEngine:
    """
    SDD (Spec-Driven Development) 엔진
    
    스펙 기반 개발 워크플로우:
    1. 스펙 파싱 (YAML → 모델)
    2. 스펙 검증
    3. 스펙 생성/수정
    4. 코드 생성으로 전달
    """
    
    def __init__(self):
        self.logger = logger
        self.parser = SpecParser()
        self.generator = SpecGenerator()
        self.validator = SpecValidator()
    
    def parse(self, yaml_content: str) -> CrewAISpec:
        """YAML을 파싱합니다."""
        return self.parser.parse_yaml(yaml_content)
    
    def validate(self, spec: CrewAISpec) -> ValidationResult:
        """스펙을 검증합니다."""
        return self.validator.validate(spec)
    
    def generate(self, spec: CrewAISpec) -> str:
        """스펙을 YAML로 생성합니다."""
        return self.generator.generate_yaml(spec)
    
    def create_spec_from_analysis(
        self,
        project_name: str,
        domain: str,
        description: str,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        workflow_type: str = "sequential",
        core_entities: Optional[List[str]] = None,  # Week 3: CRUD 생성용
    ) -> CrewAISpec:
        """
        분석 결과로부터 스펙을 생성합니다.

        Args:
            project_name: 프로젝트 이름
            domain: 도메인
            description: 설명
            agents: 에이전트 목록
            tasks: 태스크 목록
            workflow_type: 워크플로우 유형
            core_entities: 핵심 엔티티 목록 (CRUD 코드 생성용)

        Returns:
            CrewAISpec: 생성된 스펙
        """
        # 프로젝트 스펙
        project = ProjectSpec(
            name=project_name,
            description=description,
            domain=domain,
            core_entities=core_entities,  # Week 3: 추가
        )
        
        # 에이전트 스펙 변환
        agent_specs = []
        for agent in agents:
            llm_config = None
            if "llm_config" in agent and agent["llm_config"]:
                llm_config = LLMConfigSpec(**agent["llm_config"])
            
            agent_spec = AgentSpecModel(
                id=agent["id"],
                role=agent["role"],
                goal=agent["goal"],
                backstory=agent["backstory"],
                tools=agent.get("tools", []),
                llm=llm_config,
                verbose=agent.get("verbose", True),
                memory=agent.get("memory", True),
                allow_delegation=agent.get("allow_delegation", False),
            )
            agent_specs.append(agent_spec)
        
        # 태스크 스펙 변환
        task_specs = []
        for task in tasks:
            task_spec = TaskSpecModel(
                id=task["id"],
                description=task["description"],
                expected_output=task["expected_output"],
                agent=task["agent"],
                context=task.get("context", []),
                async_execution=task.get("async_execution", False),
            )
            task_specs.append(task_spec)
        
        # Crew 설정
        crew_config = CrewConfigSpec(
            process=workflow_type,
            verbose=True,
            memory=True,
        )
        
        return CrewAISpec(
            version="1.0",
            project=project,
            agents=agent_specs,
            tasks=task_specs,
            crew=crew_config,
        )
