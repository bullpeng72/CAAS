"""
Golden Data Validator

ConcretizedRequirement (Golden Data)를 기준으로 각 Phase 출력을 검증합니다.
"""

from datetime import datetime
from typing import Dict, List, Any
from app.models.schemas import (
    ConcretizedRequirement,
    RequirementAnalysis,
    ArchitectureDesign,
    AgentSpecModel,
    TaskSpecModel,
    GoldenValidationReport,
    MissingItem,
    ExtraItem,
    ComplianceStatus,
)
from caas_framework.utils.logger import get_logger

logger = get_logger("validation.golden")


class GoldenDataValidator:
    """
    Golden Data Validator

    각 Phase 출력을 ConcretizedRequirement (Golden Data)와 비교하여 검증합니다.

    Validation Types:
    - Coverage: Golden Data의 모든 항목이 Output에 포함되었는가?
    - Hallucination: Output에 Golden Data에 없는 항목이 있는가?
    - Alignment: Output이 Golden Data의 내용과 일치하는가?
    """

    def __init__(self, golden_data: ConcretizedRequirement):
        """
        Args:
            golden_data: 검증 기준이 되는 Golden Data
        """
        self.golden_data = golden_data
        logger.info(f"🎯 Golden Data Validator initialized with {len(golden_data.features)} features")

    def validate_discovery(
        self,
        requirement_analysis: RequirementAnalysis
    ) -> GoldenValidationReport:
        """
        Discovery Phase 검증

        RequirementAnalysis가 Golden Data의 features를 모두 포함하는지 검증

        Args:
            requirement_analysis: Discovery Phase 출력

        Returns:
            GoldenValidationReport: 검증 결과
        """
        logger.info("🔍 Validating Discovery Phase against Golden Data...")

        missing_items = []
        extra_items = []
        mismatched_items = []

        # 1. Feature Coverage 검증
        golden_feature_names = {f.name.lower() for f in self.golden_data.features}
        golden_features_dict = {f.name.lower(): f for f in self.golden_data.features}

        # RequirementAnalysis의 tasks를 features로 간주
        output_task_names = {t.name.lower() for t in requirement_analysis.tasks}
        output_tasks_dict = {t.name.lower(): t for t in requirement_analysis.tasks}

        # Missing Features
        for feature_name in golden_feature_names:
            if feature_name not in output_task_names:
                feature = golden_features_dict[feature_name]
                missing_items.append(MissingItem(
                    item_type="feature",
                    item_id=feature.id,
                    item_name=feature.name,
                    description=f"Feature '{feature.name}' from Golden Data is missing in Discovery output",
                    severity="high" if feature.priority in ["high", "critical"] else "medium"
                ))

        # Extra Items (Hallucination)
        for task_name in output_task_names:
            if task_name not in golden_feature_names:
                task = output_tasks_dict[task_name]
                extra_items.append(ExtraItem(
                    item_type="feature",
                    item_id="",
                    item_name=task.name,
                    description=f"Task '{task.name}' in Discovery output not found in Golden Data (possible hallucination)",
                    severity="low"
                ))

        # 2. Data Model Coverage (if applicable)
        if self.golden_data.data_models:
            golden_entities = {dm.entity_name.lower() for dm in self.golden_data.data_models}
            output_entities = set()

            # RequirementAnalysis의 database_tables를 entities로 간주
            if requirement_analysis.database_tables:
                output_entities = {table.lower() for table in requirement_analysis.database_tables}

            for entity_name in golden_entities:
                if entity_name not in output_entities:
                    missing_items.append(MissingItem(
                        item_type="data_model",
                        item_id=entity_name,
                        item_name=entity_name,
                        description=f"Data model '{entity_name}' from Golden Data is missing",
                        severity="medium"
                    ))

        # 3. Calculate Coverage Score
        total_golden_items = len(self.golden_data.features) + len(self.golden_data.data_models)
        missing_count = len(missing_items)

        if total_golden_items > 0:
            coverage_score = max(0.0, 1.0 - (missing_count / total_golden_items))
        else:
            coverage_score = 1.0

        # 4. Determine Compliance Status
        if coverage_score >= 0.9 and len(extra_items) == 0:
            compliance_status = ComplianceStatus.COMPLIANT
            needs_fixing = False
        elif coverage_score >= 0.7:
            compliance_status = ComplianceStatus.PARTIAL
            needs_fixing = True
        else:
            compliance_status = ComplianceStatus.NON_COMPLIANT
            needs_fixing = True

        # 5. Generate Recommendations
        recommendations = []
        if missing_items:
            recommendations.append(f"Add {len(missing_items)} missing items to match Golden Data")
        if extra_items:
            recommendations.append(f"Review {len(extra_items)} extra items - remove if not needed")

        logger.info(
            f"✅ Discovery validation complete - "
            f"Coverage: {coverage_score:.2f}, "
            f"Missing: {len(missing_items)}, "
            f"Extra: {len(extra_items)}"
        )

        return GoldenValidationReport(
            phase_name="discovery",
            coverage_score=coverage_score,
            missing_items=missing_items,
            extra_items=extra_items,
            mismatched_items=mismatched_items,
            compliance_status=compliance_status,
            needs_fixing=needs_fixing,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )

    def validate_architecture(
        self,
        architecture_design: ArchitectureDesign
    ) -> GoldenValidationReport:
        """
        Architecture Phase 검증

        ArchitectureDesign이 Golden Data의 requirements를 반영하는지 검증

        Args:
            architecture_design: Architecture Phase 출력

        Returns:
            GoldenValidationReport: 검증 결과
        """
        logger.info("🔍 Validating Architecture Phase against Golden Data...")

        missing_items = []
        extra_items = []
        mismatched_items = []

        # 1. Component Coverage 검증
        # Golden Data의 각 Feature가 Architecture의 Component로 매핑되어야 함
        golden_features = {f.name.lower(): f for f in self.golden_data.features}
        architecture_components = {c.name.lower(): c for c in architecture_design.components}

        # High/Critical priority features는 반드시 Component로 존재해야 함
        for feature_name, feature in golden_features.items():
            if feature.priority in ["high", "critical"]:
                # Component 이름에 feature 이름이 포함되어 있는지 확인 (유연한 매칭)
                found = any(feature_name in comp_name for comp_name in architecture_components.keys())

                if not found:
                    missing_items.append(MissingItem(
                        item_type="component",
                        item_id=feature.id,
                        item_name=feature.name,
                        description=f"High-priority feature '{feature.name}' not reflected in architecture components",
                        severity="high"
                    ))

        # 2. Data Flow Coverage
        # Golden Data의 Data Models가 Architecture의 data flows에 반영되어야 함
        if self.golden_data.data_models:
            golden_entities = {dm.entity_name.lower() for dm in self.golden_data.data_models}
            data_flow_entities = set()

            for flow in architecture_design.data_flows:
                # data_type에서 entity 이름 추출
                data_flow_entities.add(flow.data_type.lower())

            for entity_name in golden_entities:
                if entity_name not in data_flow_entities:
                    missing_items.append(MissingItem(
                        item_type="data_flow",
                        item_id=entity_name,
                        item_name=entity_name,
                        description=f"Data model '{entity_name}' not reflected in architecture data flows",
                        severity="medium"
                    ))

        # 3. NFR Alignment
        golden_nfr = self.golden_data.non_functional_requirements

        if golden_nfr.security and not architecture_design.security_strategy:
            missing_items.append(MissingItem(
                item_type="nfr",
                item_id="security",
                item_name="Security Strategy",
                description="Golden Data specifies security requirements but architecture has no security strategy",
                severity="high"
            ))

        if golden_nfr.scalability and not architecture_design.scalability_strategy:
            missing_items.append(MissingItem(
                item_type="nfr",
                item_id="scalability",
                item_name="Scalability Strategy",
                description="Golden Data specifies scalability requirements but architecture has no scalability strategy",
                severity="medium"
            ))

        # 4. Calculate Coverage Score
        total_checks = len(golden_features) + len(self.golden_data.data_models) + 2  # +2 for NFRs
        missing_count = len(missing_items)

        if total_checks > 0:
            coverage_score = max(0.0, 1.0 - (missing_count / total_checks))
        else:
            coverage_score = 1.0

        # 5. Determine Compliance Status
        if coverage_score >= 0.85:
            compliance_status = ComplianceStatus.COMPLIANT
            needs_fixing = False
        elif coverage_score >= 0.65:
            compliance_status = ComplianceStatus.PARTIAL
            needs_fixing = True
        else:
            compliance_status = ComplianceStatus.NON_COMPLIANT
            needs_fixing = True

        # 6. Generate Recommendations
        recommendations = []
        if missing_items:
            recommendations.append(f"Add {len(missing_items)} missing architectural elements")
            recommendations.append("Ensure all high-priority features are reflected in components")

        logger.info(
            f"✅ Architecture validation complete - "
            f"Coverage: {coverage_score:.2f}, "
            f"Missing: {len(missing_items)}"
        )

        return GoldenValidationReport(
            phase_name="architecture",
            coverage_score=coverage_score,
            missing_items=missing_items,
            extra_items=extra_items,
            mismatched_items=mismatched_items,
            compliance_status=compliance_status,
            needs_fixing=needs_fixing,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )

    def validate_design(
        self,
        agent_specs: List[AgentSpecModel],
        task_specs: List[TaskSpecModel]
    ) -> GoldenValidationReport:
        """
        Design Phase 검증

        AgentSpecs와 TaskSpecs가 Golden Data의 features를 모두 커버하는지 검증

        Args:
            agent_specs: Agent 설계 결과
            task_specs: Task 설계 결과

        Returns:
            GoldenValidationReport: 검증 결과
        """
        logger.info("🔍 Validating Design Phase against Golden Data...")

        missing_items = []
        extra_items = []
        mismatched_items = []

        # 1. Feature Coverage by Tasks
        golden_features = {f.name.lower(): f for f in self.golden_data.features}
        output_tasks = {t.id.lower(): t for t in task_specs}

        # 각 Golden Feature에 대응하는 Task가 있는지 확인
        for feature_name, feature in golden_features.items():
            # Task description에 feature 이름이 포함되어 있는지 확인
            found = any(
                feature_name in task.description.lower() or
                feature_name in task.id.lower()
                for task in task_specs
            )

            if not found:
                missing_items.append(MissingItem(
                    item_type="task",
                    item_id=feature.id,
                    item_name=feature.name,
                    description=f"No task found for feature '{feature.name}'",
                    severity="high" if feature.priority in ["high", "critical"] else "medium"
                ))

        # 2. UI Component Coverage
        if self.golden_data.ui_components:
            golden_ui_pages = {ui.page_name.lower() for ui in self.golden_data.ui_components}

            # Task descriptions에서 UI 관련 키워드 확인
            ui_related_tasks = [
                task for task in task_specs
                if any(keyword in task.description.lower() for keyword in ["ui", "interface", "page", "form", "display"])
            ]

            if len(self.golden_data.ui_components) > 0 and len(ui_related_tasks) == 0:
                missing_items.append(MissingItem(
                    item_type="ui_task",
                    item_id="ui_components",
                    item_name="UI Implementation Tasks",
                    description=f"Golden Data has {len(self.golden_data.ui_components)} UI components but no UI-related tasks found",
                    severity="high"
                ))

        # 3. Calculate Coverage Score
        total_golden_items = len(self.golden_data.features)
        missing_count = len([item for item in missing_items if item.item_type in ["task", "ui_task"]])

        if total_golden_items > 0:
            coverage_score = max(0.0, 1.0 - (missing_count / total_golden_items))
        else:
            coverage_score = 1.0

        # 4. Determine Compliance Status
        if coverage_score >= 0.9:
            compliance_status = ComplianceStatus.COMPLIANT
            needs_fixing = False
        elif coverage_score >= 0.7:
            compliance_status = ComplianceStatus.PARTIAL
            needs_fixing = True
        else:
            compliance_status = ComplianceStatus.NON_COMPLIANT
            needs_fixing = True

        # 5. Generate Recommendations
        recommendations = []
        if missing_items:
            recommendations.append(f"Add {len(missing_items)} missing tasks to cover all features")
            recommendations.append("Ensure all Golden Data features have corresponding tasks")

        logger.info(
            f"✅ Design validation complete - "
            f"Coverage: {coverage_score:.2f}, "
            f"Missing: {len(missing_items)}"
        )

        return GoldenValidationReport(
            phase_name="design",
            coverage_score=coverage_score,
            missing_items=missing_items,
            extra_items=extra_items,
            mismatched_items=mismatched_items,
            compliance_status=compliance_status,
            needs_fixing=needs_fixing,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )

    def validate_code(
        self,
        generated_spec: Dict[str, Any]
    ) -> GoldenValidationReport:
        """
        Development Phase 검증

        생성된 YAML Spec이 Golden Data의 모든 요구사항을 반영하는지 검증

        Args:
            generated_spec: 생성된 YAML 스펙 (파싱된 딕셔너리)

        Returns:
            GoldenValidationReport: 검증 결과
        """
        logger.info("🔍 Validating Development Phase (Code) against Golden Data...")

        missing_items = []
        extra_items = []
        mismatched_items = []

        # 1. Agent Coverage
        spec_agents = generated_spec.get("agents", [])
        spec_agent_roles = {agent.get("role", "").lower() for agent in spec_agents}

        # 2. Task Coverage
        spec_tasks = generated_spec.get("tasks", [])
        spec_task_descriptions = [task.get("description", "").lower() for task in spec_tasks]

        golden_features = {f.name.lower(): f for f in self.golden_data.features}

        # 각 Golden Feature가 Task description에 언급되는지 확인
        for feature_name, feature in golden_features.items():
            found = any(feature_name in desc for desc in spec_task_descriptions)

            if not found:
                missing_items.append(MissingItem(
                    item_type="task_implementation",
                    item_id=feature.id,
                    item_name=feature.name,
                    description=f"Feature '{feature.name}' not implemented in generated code",
                    severity="critical" if feature.priority in ["high", "critical"] else "high"
                ))

        # 3. Calculate Coverage Score
        total_golden_items = len(self.golden_data.features)
        missing_count = len(missing_items)

        if total_golden_items > 0:
            coverage_score = max(0.0, 1.0 - (missing_count / total_golden_items))
        else:
            coverage_score = 1.0

        # 4. Determine Compliance Status
        if coverage_score >= 0.95:
            compliance_status = ComplianceStatus.COMPLIANT
            needs_fixing = False
        elif coverage_score >= 0.75:
            compliance_status = ComplianceStatus.PARTIAL
            needs_fixing = True
        else:
            compliance_status = ComplianceStatus.NON_COMPLIANT
            needs_fixing = True

        # 5. Generate Recommendations
        recommendations = []
        if missing_items:
            recommendations.append(f"Implement {len(missing_items)} missing features in code")
            recommendations.append("Regenerate code to include all Golden Data features")

        logger.info(
            f"✅ Code validation complete - "
            f"Coverage: {coverage_score:.2f}, "
            f"Missing: {len(missing_items)}"
        )

        return GoldenValidationReport(
            phase_name="development",
            coverage_score=coverage_score,
            missing_items=missing_items,
            extra_items=extra_items,
            mismatched_items=mismatched_items,
            compliance_status=compliance_status,
            needs_fixing=needs_fixing,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )

    def generate_summary_report(
        self,
        validation_reports: List[GoldenValidationReport]
    ) -> str:
        """
        검증 결과 요약 리포트 생성

        Args:
            validation_reports: 각 Phase의 검증 결과

        Returns:
            str: 포맷된 요약 리포트
        """
        report = "# Golden Data Validation Summary\n\n"

        for validation in validation_reports:
            report += f"## {validation.phase_name.upper()} Phase\n"
            report += f"**Coverage Score**: {validation.coverage_score:.2%}\n"
            report += f"**Compliance Status**: {validation.compliance_status.value}\n"
            report += f"**Needs Fixing**: {'Yes' if validation.needs_fixing else 'No'}\n\n"

            if validation.missing_items:
                report += f"**Missing Items ({len(validation.missing_items)})**:\n"
                for item in validation.missing_items:
                    report += f"- [{item.severity.upper()}] {item.description}\n"
                report += "\n"

            if validation.extra_items:
                report += f"**Extra Items ({len(validation.extra_items)})**:\n"
                for item in validation.extra_items:
                    report += f"- {item.description}\n"
                report += "\n"

            if validation.recommendations:
                report += "**Recommendations**:\n"
                for rec in validation.recommendations:
                    report += f"- {rec}\n"
                report += "\n"

            report += "---\n\n"

        return report
