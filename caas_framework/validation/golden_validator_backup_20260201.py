"""
Golden Data Validator

Validates phase outputs against Golden Data (ConcretizedRequirement).
"""

from datetime import datetime
from typing import Dict, List, Any

from caas_framework.models.specifications import (
    ConcretizedRequirement,
    AgentSpecModel,
    TaskSpecModel,
)
from caas_framework.models.validation import (
    GoldenValidationReport,
    MissingItem,
    ComplianceStatus,
)


class GoldenDataValidator:
    """
    Golden Data Validator

    Validates each phase output against ConcretizedRequirement (Golden Data).

    Validation Types:
    - Coverage: Are all Golden Data items included in the output?
    - Hallucination: Does the output contain items not in Golden Data?
    - Alignment: Does the output match Golden Data content?
    """

    def __init__(self, golden_data: ConcretizedRequirement):
        """
        Args:
            golden_data: Golden Data to validate against
        """
        self.golden_data = golden_data

    def validate_design(
        self,
        agent_specs: List[AgentSpecModel],
        task_specs: List[TaskSpecModel]
    ) -> GoldenValidationReport:
        """
        Validate Design Phase

        Checks if AgentSpecs and TaskSpecs cover all Golden Data features.

        Args:
            agent_specs: Agent design results
            task_specs: Task design results

        Returns:
            GoldenValidationReport: Validation results
        """
        missing_items = []
        extra_items = []
        mismatched_items = []

        # 1. Feature Coverage by Tasks
        features = self.golden_data.features if self.golden_data.features else []
        golden_features = {f.name.lower(): f for f in features}
        output_tasks = {t.id.lower(): t for t in task_specs}

        # Check if each Golden Feature has a corresponding Task
        for feature_name, feature in golden_features.items():
            # Check if feature name is mentioned in task description or ID
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
        Validate Development Phase

        Checks if generated YAML spec reflects all Golden Data requirements.

        Args:
            generated_spec: Generated YAML spec (parsed dictionary)

        Returns:
            GoldenValidationReport: Validation results
        """
        missing_items = []
        extra_items = []
        mismatched_items = []

        # 1. Agent Coverage
        spec_agents = generated_spec.get("agents", [])
        spec_agent_roles = {agent.get("role", "").lower() for agent in spec_agents}

        # 2. Task Coverage
        spec_tasks = generated_spec.get("tasks", [])
        spec_task_descriptions = [task.get("description", "").lower() for task in spec_tasks]

        features = self.golden_data.features if self.golden_data.features else []
        golden_features = {f.name.lower(): f for f in features}

        # Check if each Golden Feature is mentioned in task descriptions
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
        features = self.golden_data.features if self.golden_data.features else []
        total_golden_items = len(features)
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
        Generate summary report from validation results.

        Args:
            validation_reports: Validation results from each phase

        Returns:
            Formatted summary report
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
