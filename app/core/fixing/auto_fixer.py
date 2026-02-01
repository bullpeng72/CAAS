"""
Auto-Fixer

Golden Data 검증 결과를 기반으로 자동으로 Phase Output을 수정합니다.
"""

from typing import Any, Dict, List, Union
from pydantic import BaseModel
from app.models.schemas import (
    ConcretizedRequirement,
    GoldenValidationReport,
    RequirementAnalysis,
    ArchitectureDesign,
    AgentSpecModel,
    TaskSpecModel,
    TaskRequirement,
)
from caas_framework.utils.logger import get_logger

logger = get_logger("fixing.auto_fixer")


def _to_dict(item: Union[Dict, BaseModel]) -> Dict:
    """Pydantic 모델을 딕셔너리로 변환"""
    if isinstance(item, BaseModel):
        return item.model_dump()
    return item


def _to_model(item: Union[Dict, BaseModel], model_class) -> BaseModel:
    """딕셔너리를 Pydantic 모델로 변환"""
    if isinstance(item, BaseModel):
        return item
    return model_class(**item)


class FixResult:
    """자동 수정 결과"""

    def __init__(
        self,
        success: bool,
        fixed_output: Any,
        fixes_applied: List[str],
        errors: List[str] = None
    ):
        self.success = success
        self.fixed_output = fixed_output
        self.fixes_applied = fixes_applied
        self.errors = errors or []


class AutoFixer:
    """
    Auto-Fixer

    Golden Data를 기준으로 Phase Output의 문제를 자동으로 수정합니다.

    Fixing Strategies:
    1. LLM-based Fixing: LLM을 사용하여 누락된 항목 생성
    2. Template-based Fixing: 템플릿을 사용하여 표준 패턴 적용
    3. Rule-based Fixing: 명확한 규칙에 따라 직접 수정
    """

    def __init__(self, golden_data: ConcretizedRequirement, llm_client=None):
        """
        Args:
            golden_data: 수정 기준이 되는 Golden Data
            llm_client: LLM 클라이언트 (선택적)
        """
        self.golden_data = golden_data
        self.llm_client = llm_client
        logger.info("🔧 AutoFixer initialized")

    def fix_discovery(
        self,
        requirement_analysis: RequirementAnalysis,
        validation_report: GoldenValidationReport
    ) -> FixResult:
        """
        Discovery Phase 자동 수정

        Args:
            requirement_analysis: 원본 RequirementAnalysis
            validation_report: 검증 결과

        Returns:
            FixResult: 수정 결과
        """
        logger.info("🔧 Auto-fixing Discovery Phase...")

        if not validation_report.needs_fixing:
            logger.info("✅ No fixing needed")
            return FixResult(
                success=True,
                fixed_output=requirement_analysis,
                fixes_applied=[]
            )

        fixes_applied = []
        errors = []

        # 누락된 Features를 Tasks로 추가
        for missing_item in validation_report.missing_items:
            if missing_item.item_type == "feature":
                try:
                    # Golden Data에서 해당 Feature 찾기
                    golden_feature = next(
                        (f for f in self.golden_data.features if f.id == missing_item.item_id),
                        None
                    )

                    if golden_feature:
                        # TaskRequirement 생성
                        new_task = TaskRequirement(
                            name=golden_feature.name,
                            description=golden_feature.description,
                            assigned_agent="",  # 임시 값 (나중에 할당)
                            dependencies=[],
                            output_type="text"
                        )

                        requirement_analysis.tasks.append(new_task)
                        fixes_applied.append(f"Added missing task: {golden_feature.name}")
                        logger.info(f"✅ Added task: {golden_feature.name}")

                except Exception as e:
                    error_msg = f"Failed to add task {missing_item.item_name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            elif missing_item.item_type == "data_model":
                try:
                    # Database table 추가
                    if missing_item.item_id not in requirement_analysis.database_tables:
                        requirement_analysis.database_tables.append(missing_item.item_id)
                        requirement_analysis.requires_database = True
                        fixes_applied.append(f"Added missing data model: {missing_item.item_id}")
                        logger.info(f"✅ Added data model: {missing_item.item_id}")

                except Exception as e:
                    error_msg = f"Failed to add data model {missing_item.item_name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

        # Extra Items 제거 (Optional - 사용자 확인 필요할 수 있음)
        # 현재는 경고만 로깅
        for extra_item in validation_report.extra_items:
            logger.warning(f"⚠️ Extra item detected (not removed): {extra_item.item_name}")

        success = len(errors) == 0

        logger.info(
            f"{'✅' if success else '❌'} Discovery fixing complete - "
            f"Fixes: {len(fixes_applied)}, Errors: {len(errors)}"
        )

        return FixResult(
            success=success,
            fixed_output=requirement_analysis,
            fixes_applied=fixes_applied,
            errors=errors
        )

    def fix_architecture(
        self,
        architecture_design: ArchitectureDesign,
        validation_report: GoldenValidationReport
    ) -> FixResult:
        """
        Architecture Phase 자동 수정

        Args:
            architecture_design: 원본 ArchitectureDesign
            validation_report: 검증 결과

        Returns:
            FixResult: 수정 결과
        """
        logger.info("🔧 Auto-fixing Architecture Phase...")

        if not validation_report.needs_fixing:
            logger.info("✅ No fixing needed")
            return FixResult(
                success=True,
                fixed_output=architecture_design,
                fixes_applied=[]
            )

        fixes_applied = []
        errors = []

        # NFR 전략 추가
        for missing_item in validation_report.missing_items:
            if missing_item.item_type == "nfr":
                try:
                    # Handle both dict and object formats
                    nfr = self.golden_data.non_functional_requirements
                    if isinstance(nfr, dict):
                        golden_security = nfr.get('security')
                        golden_scalability = nfr.get('scalability')
                    else:
                        golden_security = getattr(nfr, 'security', None)
                        golden_scalability = getattr(nfr, 'scalability', None)

                    if missing_item.item_id == "security":
                        if golden_security and not architecture_design.security_strategy:
                            architecture_design.security_strategy = golden_security
                            fixes_applied.append("Added security strategy from Golden Data")
                            logger.info("✅ Added security strategy")

                    elif missing_item.item_id == "scalability":
                        if golden_scalability and not architecture_design.scalability_strategy:
                            architecture_design.scalability_strategy = golden_scalability
                            fixes_applied.append("Added scalability strategy from Golden Data")
                            logger.info("✅ Added scalability strategy")

                except Exception as e:
                    error_msg = f"Failed to add NFR {missing_item.item_name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

        # Component 추가 (Template-based)
        # 현재는 로깅만 (LLM 기반 구현 필요)
        for missing_item in validation_report.missing_items:
            if missing_item.item_type == "component":
                logger.warning(f"⚠️ Missing component detected (requires LLM to generate): {missing_item.item_name}")

        success = len(errors) == 0

        logger.info(
            f"{'✅' if success else '❌'} Architecture fixing complete - "
            f"Fixes: {len(fixes_applied)}, Errors: {len(errors)}"
        )

        return FixResult(
            success=success,
            fixed_output=architecture_design,
            fixes_applied=fixes_applied,
            errors=errors
        )

    def fix_design(
        self,
        agent_specs: List[Union[Dict, AgentSpecModel]],
        task_specs: List[Union[Dict, TaskSpecModel]],
        validation_report: GoldenValidationReport
    ) -> FixResult:
        """
        Design Phase 자동 수정

        Args:
            agent_specs: 원본 Agent Specs (dict 또는 AgentSpecModel)
            task_specs: 원본 Task Specs (dict 또는 TaskSpecModel)
            validation_report: 검증 결과

        Returns:
            FixResult: 수정 결과
        """
        logger.info("🔧 Auto-fixing Design Phase...")

        # dict로 변환 (내부 처리용)
        agents_dict = [_to_dict(a) for a in agent_specs]
        tasks_dict = [_to_dict(t) for t in task_specs]

        if not validation_report.needs_fixing:
            logger.info("✅ No fixing needed")
            return FixResult(
                success=True,
                fixed_output={"agents": agents_dict, "tasks": tasks_dict},
                fixes_applied=[]
            )

        fixes_applied = []
        errors = []

        # 누락된 Features에 대한 Tasks 추가
        for missing_item in validation_report.missing_items:
            if missing_item.item_type == "feature" or missing_item.item_type == "task":
                try:
                    # Golden Data에서 해당 Feature 찾기
                    golden_feature = next(
                        (f for f in self.golden_data.features if f.id == missing_item.item_id or f.name == missing_item.item_name),
                        None
                    )

                    if golden_feature:
                        # Task ID 생성 (중복 방지)
                        base_task_id = golden_feature.id.lower().replace("f", "task_")
                        task_id = base_task_id
                        counter = 1
                        while any(t.get("id") == task_id for t in tasks_dict):
                            task_id = f"{base_task_id}_{counter}"
                            counter += 1

                        # Agent 할당 (첫 번째 agent에 할당)
                        assigned_agent = agents_dict[0]["id"] if agents_dict else "agent_1"

                        # TaskSpecModel 생성
                        new_task = {
                            "id": task_id,
                            "description": golden_feature.description,
                            "expected_output": f"Completed {golden_feature.name}",
                            "agent": assigned_agent,
                            "context": [],
                            "async_execution": False,
                            "output_file": None,
                            "human_input": False
                        }

                        tasks_dict.append(new_task)
                        fixes_applied.append(f"✅ Added missing task: {golden_feature.name} (assigned to {assigned_agent})")
                        logger.info(f"✅ Added task spec: {golden_feature.name}")

                except Exception as e:
                    error_msg = f"Failed to add task spec {missing_item.item_name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

        # Agent 추가 (누락된 agent가 있을 경우)
        for missing_item in validation_report.missing_items:
            if missing_item.item_type == "agent":
                try:
                    # 간단한 agent 생성
                    agent_id = f"agent_{missing_item.item_id.lower()}"
                    counter = 1
                    while any(a.get("id") == agent_id for a in agents_dict):
                        agent_id = f"agent_{missing_item.item_id.lower()}_{counter}"
                        counter += 1

                    new_agent = {
                        "id": agent_id,
                        "role": missing_item.item_name,
                        "goal": f"Handle {missing_item.item_name} related tasks",
                        "backstory": f"Expert in {missing_item.item_name}",
                        "tools": [],
                        "verbose": True,
                        "memory": True,
                        "allow_delegation": False,
                        "max_iter": 15
                    }

                    agents_dict.append(new_agent)
                    fixes_applied.append(f"✅ Added missing agent: {missing_item.item_name}")
                    logger.info(f"✅ Added agent: {missing_item.item_name}")

                except Exception as e:
                    error_msg = f"Failed to add agent {missing_item.item_name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

        success = len(errors) == 0

        logger.info(
            f"{'✅' if success else '❌'} Design fixing complete - "
            f"Fixes: {len(fixes_applied)}, Errors: {len(errors)}"
        )

        return FixResult(
            success=success,
            fixed_output={"agents": agents_dict, "tasks": tasks_dict},
            fixes_applied=fixes_applied,
            errors=errors
        )

    def fix_code(
        self,
        generated_spec: Dict[str, Any],
        validation_report: GoldenValidationReport
    ) -> FixResult:
        """
        Development Phase 자동 수정

        Args:
            generated_spec: 원본 생성 스펙
            validation_report: 검증 결과

        Returns:
            FixResult: 수정 결과
        """
        logger.info("🔧 Auto-fixing Development Phase...")

        if not validation_report.needs_fixing:
            logger.info("✅ No fixing needed")
            return FixResult(
                success=True,
                fixed_output=generated_spec,
                fixes_applied=[]
            )

        fixes_applied = []
        errors = []

        # Code 레벨 수정은 복잡하므로 LLM 기반 수정 필요
        # 현재는 로깅만
        for missing_item in validation_report.missing_items:
            if missing_item.item_type == "task_implementation":
                logger.warning(
                    f"⚠️ Missing task implementation (requires code regeneration): {missing_item.item_name}"
                )

        # 간단한 메타데이터 수정은 가능
        # (실제 구현에서는 더 복잡한 로직 필요)

        success = True  # Code 레벨은 일단 성공으로 처리

        logger.info(
            f"✅ Code fixing logged - Regeneration may be required for {len(validation_report.missing_items)} items"
        )

        return FixResult(
            success=success,
            fixed_output=generated_spec,
            fixes_applied=fixes_applied,
            errors=errors
        )


class LLMBasedFixer:
    """
    LLM 기반 자동 수정 (Advanced)

    복잡한 수정이 필요한 경우 LLM을 사용하여 수정안을 생성합니다.
    """

    def __init__(self, llm_client):
        """
        Args:
            llm_client: LLM 클라이언트
        """
        self.llm_client = llm_client

    def generate_missing_component(
        self,
        golden_feature,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        누락된 컴포넌트를 LLM으로 생성

        Args:
            golden_feature: Golden Data의 Feature
            context: 현재 Architecture Design 컨텍스트

        Returns:
            생성된 Component 스펙
        """
        prompt = f"""
        Generate an architecture component for the following feature:

        Feature Name: {golden_feature.name}
        Description: {golden_feature.description}
        Priority: {golden_feature.priority}

        Context:
        {context}

        Generate a ComponentSpec in JSON format with:
        - id (snake_case)
        - name
        - type (agent/service/database/api/ui/utility)
        - description
        - responsibilities (list)
        - interfaces (list)
        - dependencies (list)
        """

        # LLM 호출 및 파싱 (실제 구현 필요)
        # response = self.llm_client.invoke(prompt)
        # return parse_component_spec(response)

        return {}
