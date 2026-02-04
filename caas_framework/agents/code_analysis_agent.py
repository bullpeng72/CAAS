"""
Code Analysis Agent

Expert agent responsible for code quality assurance:
- Analyzes implementation completeness against Golden Data
- Detects and fixes runtime errors automatically
- Verifies business rules and acceptance criteria
- Provides traceability analysis
"""

import ast
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from caas_framework.agents.base import AgentPhase, BaseExpertAgent
from caas_framework.agents.executors import RefinementExecutor
from caas_framework.agents.registry import register_agent
from caas_framework.models.validation import ValidationIssue
from caas_framework.models.code_analysis import (
    BusinessRuleViolation,
    CodeAnalysisReport,
    CodeFix,
    ErrorCategory,
    ErrorSeverity,
    ImplementationAnalysisResult,
    ImplementationGap,
    RuntimeErrorFix,
    RuntimeErrorInfo,
    TraceabilityResult,
)
from caas_framework.models.specifications import ConcretizedRequirement
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils import ResponseParser

logger = logging.getLogger(__name__)


@register_agent(phase=AgentPhase.CODE_ANALYSIS)
class CodeAnalysisAgent(BaseExpertAgent):
    """
    Code Analysis Agent (6th Expert Agent)

    Specializes in:
    - Implementation completeness analysis
    - Runtime error detection and fixing
    - Business logic verification
    - Traceability analysis between Golden Data and implementation
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        golden_data: Optional[ConcretizedRequirement] = None,
    ):
        super().__init__(llm_plugin, golden_data, AgentPhase.CODE_ANALYSIS)

    @property
    def agent_name(self) -> str:
        return "CodeAnalyst"

    @property
    def agent_role(self) -> str:
        return "Expert Code Analysis and Quality Assurance Specialist"

    @property
    def agent_expertise(self) -> List[str]:
        return [
            "Implementation completeness analysis",
            "Runtime error detection and fixing",
            "Business logic verification",
            "Traceability analysis",
            "Code quality assurance",
            "Requirement coverage validation",
            "Automatic bug fixing",
        ]

    async def _do_work(
        self,
        requirement: Optional[str],
        context: Optional[Dict[str, Any]],
        previous_outputs: Optional[Dict[AgentPhase, Any]],
    ) -> Dict[str, Any]:
        """
        Execute code analysis work.

        Returns:
            Dict with analysis results
        """
        # This is the main entry point when called via agent collaboration
        # The specific analysis methods below are called directly for CLI commands
        return {
            "agent": self.agent_name,
            "capabilities": self.agent_expertise,
            "status": "ready",
        }

    async def analyze_implementation(
        self,
        project_path: Path,
        golden_data: Optional[ConcretizedRequirement] = None,
    ) -> ImplementationAnalysisResult:
        """
        Analyze implementation completeness against Golden Data.

        Args:
            project_path: Path to generated project
            golden_data: Golden Data to validate against

        Returns:
            ImplementationAnalysisResult with completeness analysis
        """
        logger.info(f"Analyzing implementation completeness for {project_path}")

        golden_data = golden_data or self.golden_data
        if not golden_data:
            raise ValueError("Golden Data is required for implementation analysis")

        # Extract features from Golden Data
        features = golden_data.features

        # Scan project files
        project_files = self._scan_project_files(project_path)

        # Analyze each feature
        traceability_results = []
        for feature in features:
            result = await self._analyze_feature_traceability(
                feature, project_files, project_path
            )
            traceability_results.append(result)

        # Calculate statistics
        implemented = sum(1 for r in traceability_results if r.is_implemented)
        partial = sum(
            1
            for r in traceability_results
            if not r.is_implemented and r.coverage_percentage > 0
        )
        missing = sum(
            1 for r in traceability_results if r.coverage_percentage == 0
        )

        overall_coverage = (
            sum(r.coverage_percentage for r in traceability_results)
            / len(traceability_results)
            if traceability_results
            else 0.0
        )

        # Detect business rule violations
        violations = await self._detect_business_rule_violations(
            features, project_files, project_path
        )

        # Collect all implementation gaps
        all_gaps = []
        for result in traceability_results:
            all_gaps.extend(result.gaps)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            traceability_results, violations, all_gaps
        )

        return ImplementationAnalysisResult(
            project_name=golden_data.system_scope.project_name,
            total_features=len(features),
            implemented_features=implemented,
            partial_features=partial,
            missing_features=missing,
            overall_coverage=overall_coverage,
            traceability_results=traceability_results,
            business_rule_violations=violations,
            implementation_gaps=all_gaps,
            recommendations=recommendations,
        )

    async def analyze_runtime_error(
        self,
        error_log: str,
        project_path: Path,
    ) -> RuntimeErrorFix:
        """
        Analyze runtime error and generate automatic fix.

        Args:
            error_log: Error log or traceback
            project_path: Path to project

        Returns:
            RuntimeErrorFix with fix suggestions
        """
        logger.info("Analyzing runtime error")

        # Parse error information
        error_info = self._parse_error_log(error_log)

        # Read affected file
        affected_file = project_path / error_info.file_path
        if not affected_file.exists():
            logger.warning(f"Affected file not found: {affected_file}")
            error_info.context_lines = []
        else:
            error_info.context_lines = self._extract_context_lines(
                affected_file, error_info.line_number
            )

        # Analyze root cause using LLM
        root_cause = await self._analyze_error_root_cause(error_info, project_path)

        # Generate fix using LLM
        fixes = await self._generate_error_fixes(error_info, root_cause, project_path)

        # Determine fix strategy
        fix_strategy = self._determine_fix_strategy(error_info, fixes)

        # Generate test command
        test_command = self._generate_test_command(project_path)

        return RuntimeErrorFix(
            error_info=error_info,
            fixes=fixes,
            root_cause=root_cause,
            fix_strategy=fix_strategy,
            test_command=test_command,
            additional_notes=[
                "Review the fix before applying",
                "Run tests after applying the fix",
                "Check if similar errors exist in other files",
            ],
        )

    async def verify_business_rules(
        self,
        project_path: Path,
        golden_data: Optional[ConcretizedRequirement] = None,
    ) -> List[BusinessRuleViolation]:
        """
        Verify business rules and acceptance criteria.

        Args:
            project_path: Path to generated project
            golden_data: Golden Data with business rules

        Returns:
            List of BusinessRuleViolation
        """
        logger.info("Verifying business rules")

        golden_data = golden_data or self.golden_data
        if not golden_data:
            raise ValueError("Golden Data is required for business rule verification")

        project_files = self._scan_project_files(project_path)
        features = golden_data.features

        violations = await self._detect_business_rule_violations(
            features, project_files, project_path
        )

        return violations

    async def _refine_implementation(
        self,
        output: Dict[str, Any],
        issues: List[ValidationIssue],
        context: Optional[Dict[str, Any]],
        iteration: int,
    ) -> Dict[str, Any]:
        """
        Refine code analysis based on validation feedback.

        Uses RefinementExecutor for standardized refinement workflow.
        """
        executor = RefinementExecutor.create_for_agent(
            agent=self,
            agent_role="Expert Code Analysis and Quality Assurance Specialist",
            output_type="code analysis report",
        )

        return await executor.refine_output(
            output=output,
            issues=issues,
            iteration=iteration,
            guidelines=[
                "Address each identified issue with specific fixes",
                "Maintain traceability to Golden Data requirements",
                "Ensure all business rules are verified",
                "Provide actionable recommendations for gaps",
            ],
        )

    # ==================== Helper Methods ====================

    def _scan_project_files(self, project_path: Path) -> Dict[str, str]:
        """Scan project files and return file contents."""
        files = {}
        for ext in ["*.py", "*.md", "*.json", "*.yaml", "*.yml"]:
            for file_path in project_path.rglob(ext):
                if ".venv" in str(file_path) or "__pycache__" in str(file_path):
                    continue
                try:
                    files[str(file_path.relative_to(project_path))] = file_path.read_text()
                except Exception as e:
                    logger.warning(f"Could not read {file_path}: {e}")
        return files

    async def _analyze_feature_traceability(
        self, feature, project_files: Dict[str, str], project_path: Path
    ) -> TraceabilityResult:
        """Analyze traceability for a single feature."""
        # Search for feature implementation in files
        implementation_files = []
        missing_requirements = []

        # Build search keywords from feature
        keywords = self._extract_keywords(feature.name, feature.description)

        # Search in project files
        for file_path, content in project_files.items():
            if self._matches_feature(content, keywords):
                implementation_files.append(file_path)

        # Check acceptance criteria coverage
        for criterion in feature.acceptance_criteria:
            if not self._is_criterion_implemented(criterion, project_files):
                missing_requirements.append(criterion)

        # Calculate coverage
        total_criteria = len(feature.acceptance_criteria)
        implemented_criteria = total_criteria - len(missing_requirements)
        coverage = (
            (implemented_criteria / total_criteria * 100) if total_criteria > 0 else 0.0
        )

        # Detect gaps
        gaps = []
        if missing_requirements:
            gaps.append(
                ImplementationGap(
                    feature_id=feature.id,
                    feature_name=feature.name,
                    expected=f"{len(feature.acceptance_criteria)} acceptance criteria",
                    actual=f"{implemented_criteria} implemented",
                    gap_type="partial",
                    impact=f"{len(missing_requirements)} criteria not implemented",
                    priority=feature.priority,
                )
            )

        return TraceabilityResult(
            feature_id=feature.id,
            feature_name=feature.name,
            is_implemented=coverage >= 80.0,  # 80% threshold
            implementation_files=implementation_files,
            coverage_percentage=coverage,
            missing_requirements=missing_requirements,
            gaps=gaps,
        )

    async def _detect_business_rule_violations(
        self, features, project_files: Dict[str, str], project_path: Path
    ) -> List[BusinessRuleViolation]:
        """Detect business rule violations using LLM."""
        violations = []

        # Use LLM to analyze business rules
        for feature in features:
            prompt = self._build_business_rule_prompt(feature, project_files)

            try:
                response = await self.llm.generate(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=2000,
                )

                # Parse violations from response
                feature_violations = self._parse_violations(response, feature)
                violations.extend(feature_violations)

            except Exception as e:
                logger.error(f"Error analyzing business rules for {feature.name}: {e}")

        return violations

    def _parse_error_log(self, error_log: str) -> RuntimeErrorInfo:
        """Parse error log and extract error information."""
        # Extract error type
        error_type_match = re.search(r"(\w+Error):", error_log)
        error_type = error_type_match.group(1) if error_type_match else "UnknownError"

        # Extract error message
        error_msg_match = re.search(r"\w+Error: (.+)", error_log)
        error_message = error_msg_match.group(1) if error_msg_match else error_log

        # Extract file path and line number
        file_match = re.search(r'File "([^"]+)", line (\d+)', error_log)
        file_path = file_match.group(1) if file_match else "unknown"
        line_number = int(file_match.group(2)) if file_match else None

        # Categorize error
        category = self._categorize_error(error_type)

        # Determine severity
        severity = self._determine_severity(category, error_type)

        return RuntimeErrorInfo(
            error_type=error_type,
            error_message=error_message,
            file_path=file_path,
            line_number=line_number,
            traceback=error_log,
            category=category,
            severity=severity,
        )

    def _categorize_error(self, error_type: str) -> ErrorCategory:
        """Categorize error by type."""
        error_map = {
            "SyntaxError": ErrorCategory.SYNTAX,
            "ImportError": ErrorCategory.IMPORT,
            "ModuleNotFoundError": ErrorCategory.IMPORT,
            "TypeError": ErrorCategory.TYPE,
            "NameError": ErrorCategory.NAME,
            "AttributeError": ErrorCategory.ATTRIBUTE,
            "KeyError": ErrorCategory.KEY,
            "IndexError": ErrorCategory.INDEX,
            "ValueError": ErrorCategory.VALUE,
        }
        return error_map.get(error_type, ErrorCategory.RUNTIME)

    def _determine_severity(
        self, category: ErrorCategory, error_type: str
    ) -> ErrorSeverity:
        """Determine error severity."""
        critical_errors = {ErrorCategory.SYNTAX, ErrorCategory.IMPORT}
        if category in critical_errors:
            return ErrorSeverity.CRITICAL
        return ErrorSeverity.HIGH

    def _extract_context_lines(
        self, file_path: Path, line_number: Optional[int], context_size: int = 5
    ) -> List[str]:
        """Extract context lines around error location."""
        if not line_number:
            return []

        try:
            lines = file_path.read_text().splitlines()
            start = max(0, line_number - context_size - 1)
            end = min(len(lines), line_number + context_size)
            return lines[start:end]
        except Exception as e:
            logger.warning(f"Could not extract context lines: {e}")
            return []

    async def _analyze_error_root_cause(
        self, error_info: RuntimeErrorInfo, project_path: Path
    ) -> str:
        """Analyze error root cause using LLM."""
        prompt = self._build_error_analysis_prompt(error_info)

        try:
            response = await self.llm.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1000,
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Error analyzing root cause: {e}")
            return f"Could not analyze root cause: {str(e)}"

    async def _generate_error_fixes(
        self, error_info: RuntimeErrorInfo, root_cause: str, project_path: Path
    ) -> List[CodeFix]:
        """Generate code fixes using LLM."""
        prompt = self._build_fix_generation_prompt(error_info, root_cause)

        try:
            response = await self.llm.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=2000,
            )

            # Parse fixes from response
            fixes = self._parse_fixes(response, error_info)
            return fixes

        except Exception as e:
            logger.error(f"Error generating fixes: {e}")
            return []

    def _extract_keywords(self, *texts: str) -> List[str]:
        """Extract keywords from texts."""
        keywords = set()
        for text in texts:
            # Simple keyword extraction: words longer than 3 chars
            words = re.findall(r"\b\w{4,}\b", text.lower())
            keywords.update(words)
        return list(keywords)

    def _matches_feature(self, content: str, keywords: List[str]) -> bool:
        """Check if content matches feature keywords."""
        content_lower = content.lower()
        matches = sum(1 for kw in keywords if kw in content_lower)
        return matches >= len(keywords) * 0.3  # 30% threshold

    def _is_criterion_implemented(
        self, criterion: str, project_files: Dict[str, str]
    ) -> bool:
        """Check if acceptance criterion is implemented."""
        keywords = self._extract_keywords(criterion)
        for content in project_files.values():
            if self._matches_feature(content, keywords):
                return True
        return False

    def _generate_recommendations(
        self, traceability_results, violations, gaps
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Low coverage features
        low_coverage = [r for r in traceability_results if r.coverage_percentage < 50]
        if low_coverage:
            recommendations.append(
                f"Improve implementation for {len(low_coverage)} features with <50% coverage"
            )

        # Critical violations
        critical_violations = [v for v in violations if v.severity == ErrorSeverity.CRITICAL]
        if critical_violations:
            recommendations.append(
                f"Fix {len(critical_violations)} critical business rule violations immediately"
            )

        # High-priority gaps
        high_priority_gaps = [g for g in gaps if g.priority in ["high", "critical"]]
        if high_priority_gaps:
            recommendations.append(
                f"Address {len(high_priority_gaps)} high-priority implementation gaps"
            )

        return recommendations

    def _build_business_rule_prompt(self, feature, project_files) -> str:
        """Build prompt for business rule analysis."""
        prompt_parts = [
            "# Task",
            "Analyze if the feature's business rules and acceptance criteria are correctly implemented.",
            "",
            "# Feature",
            f"ID: {feature.id}",
            f"Name: {feature.name}",
            "",
            "# Acceptance Criteria",
            "\n".join(f"- {c}" for c in feature.acceptance_criteria),
            "",
            "# Implementation Files (sample)",
        ]

        # Add sample of implementation files
        for k, v in list(project_files.items())[:3]:
            prompt_parts.append(f"**{k}**:")
            prompt_parts.append(f"```\n{v[:300]}...\n```")

        prompt_parts.extend([
            "",
            "# Output",
            "List any violations as JSON array with fields: rule_id, violation_type, description, severity",
            "If no violations, return empty array: []",
        ])

        return "\n".join(prompt_parts)

    def _build_error_analysis_prompt(self, error_info: RuntimeErrorInfo) -> str:
        """Build prompt for error root cause analysis."""
        prompt_parts = [
            "# Task",
            "Analyze the root cause of this runtime error.",
            "",
            "# Error Details",
            f"Type: {error_info.error_type}",
            f"Message: {error_info.error_message}",
            f"File: {error_info.file_path}:{error_info.line_number}",
            "",
        ]

        if error_info.context_lines:
            prompt_parts.extend([
                "# Code Context",
                "```python",
                "\n".join(error_info.context_lines),
                "```",
                "",
            ])

        prompt_parts.extend([
            "# Output",
            "Explain the root cause in 2-3 sentences, focusing on why it happened.",
        ])

        return "\n".join(prompt_parts)

    def _build_fix_generation_prompt(
        self, error_info: RuntimeErrorInfo, root_cause: str
    ) -> str:
        """Build prompt for fix generation."""
        prompt_parts = [
            "# Task",
            "Generate a code fix for this error.",
            "",
            "# Error",
            f"{error_info.error_type}: {error_info.error_message}",
            "",
            "# Root Cause",
            root_cause,
            "",
        ]

        if error_info.context_lines:
            prompt_parts.extend([
                "# Original Code",
                "```python",
                "\n".join(error_info.context_lines),
                "```",
                "",
            ])

        prompt_parts.extend([
            "# Output",
            "Provide fixed code and explanation as JSON:",
            '{"fixed_code": "corrected code here", "explanation": "what was fixed"}',
        ])

        return "\n".join(prompt_parts)

    def _parse_violations(self, response: str, feature) -> List[BusinessRuleViolation]:
        """Parse business rule violations from LLM response."""
        try:
            # Try to extract JSON array
            violations_data = ResponseParser.extract_json(response)
            if not isinstance(violations_data, list):
                violations_data = [violations_data]

            violations = []
            for v_data in violations_data:
                violations.append(
                    BusinessRuleViolation(
                        rule_id=v_data.get("rule_id", f"{feature.id}_violation"),
                        feature_id=feature.id,
                        feature_name=feature.name,
                        violation_type=v_data.get("violation_type", "unknown"),
                        description=v_data.get("description", ""),
                        severity=ErrorSeverity(
                            v_data.get("severity", "medium").lower()
                        ),
                    )
                )
            return violations

        except Exception as e:
            logger.warning(f"Could not parse violations: {e}")
            return []

    def _parse_fixes(
        self, response: str, error_info: RuntimeErrorInfo
    ) -> List[CodeFix]:
        """Parse code fixes from LLM response."""
        try:
            fix_data = ResponseParser.extract_json(response)

            return [
                CodeFix(
                    file_path=error_info.file_path,
                    original_code="\n".join(error_info.context_lines),
                    fixed_code=fix_data.get("fixed_code", ""),
                    explanation=fix_data.get("explanation", ""),
                    line_start=error_info.line_number,
                    confidence=0.8,
                )
            ]

        except Exception as e:
            logger.warning(f"Could not parse fixes: {e}")
            return []

    def _determine_fix_strategy(
        self, error_info: RuntimeErrorInfo, fixes: List[CodeFix]
    ) -> str:
        """Determine fix strategy."""
        if error_info.category == ErrorCategory.IMPORT:
            return "Install missing dependency or fix import path"
        elif error_info.category == ErrorCategory.SYNTAX:
            return "Fix syntax error in code"
        elif error_info.category == ErrorCategory.TYPE:
            return "Add type conversion or fix type mismatch"
        else:
            return "Apply suggested code fix"

    def _generate_test_command(self, project_path: Path) -> str:
        """Generate test command for verification."""
        if (project_path / "pytest.ini").exists() or (project_path / "tests").exists():
            return "pytest tests/ -v"
        elif (project_path / "main.py").exists():
            return "python main.py"
        else:
            return "python -m unittest discover"
