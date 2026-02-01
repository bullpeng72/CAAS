"""
Refactored execute_development() - Phase 1 리팩토링

기존 391줄 단일 함수를 다음과 같이 분해:
- execute_development(): 30줄 (orchestration)
- _apply_spec_reflection(): 40줄
- _validate_traceability(): 50줄
- _apply_code_reflection(): 40줄
- _run_quality_pipeline(): 60줄
- _validate_golden_data(): 50줄
- _validate_boundaries(): 40줄
- _create_development_history(): 80줄
- _check_plan_mode_gate(): 20줄
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime


class BMADEngineRefactored:
    """리팩토링된 BMADEngine - execute_development() 분해 버전"""

    def execute_development(
        self,
        context,
        enable_reflection: bool = True,
        enable_traceability: bool = True,
        quality_threshold: float = 0.7,
        max_reflection_iterations: int = 3
    ):
        """
        Development 단계 실행 - 코드 생성 (Refactored: 30 lines)

        기존 391줄을 orchestration 로직만 남김
        """
        self.logger.info("=== BMAD Development 단계 시작 ===")
        context.current_phase = "DEVELOPMENT"

        if not context.agent_specs or not context.task_specs:
            raise ValueError("Design 단계가 먼저 실행되어야 합니다.")

        try:
            # 1. Pattern Matching
            matched_patterns = self._match_patterns(context)

            # 2. Spec Generation + Reflection
            spec_yaml, spec_reflection = self._generate_and_reflect_spec(
                context, matched_patterns, enable_reflection,
                quality_threshold, max_reflection_iterations
            )
            context.spec_yaml = spec_yaml

            # 3. Traceability Validation
            traceability_report = self._validate_traceability_if_enabled(
                context, enable_traceability
            )

            # 4. Code Generation + Reflection
            generated_code, code_reflection = self._generate_and_reflect_code(
                context, spec_yaml, matched_patterns, enable_reflection,
                quality_threshold, max_reflection_iterations
            )
            context.generated_code = generated_code

            # 5. Code Validation
            validation_result = self._validate_generated_code(generated_code)

            # 6. Quality Pipeline
            quality_report = self._run_quality_pipeline_if_available(generated_code)

            # 7. Golden Data Validation
            self._validate_golden_data_if_enabled(context, generated_code)

            # 8. Boundaries Validation
            boundaries_violations = self._validate_boundaries_if_enabled(
                context, generated_code
            )

            # 9. History Recording
            self._record_development_history(
                context, matched_patterns, generated_code, validation_result,
                enable_reflection, spec_reflection, code_reflection,
                enable_traceability, traceability_report,
                boundaries_violations, quality_report
            )

            self.logger.info("=== BMAD Development 단계 완료 ===")

            # 10. Plan Mode Gate
            self._check_plan_mode_gate_if_enabled(generated_code)

            return context

        except Exception as e:
            self._record_development_failure(context, e)
            raise

    def _generate_and_reflect_spec(
        self,
        context,
        matched_patterns,
        enable_reflection: bool,
        quality_threshold: float,
        max_reflection_iterations: int
    ) -> Tuple[str, Optional[Any]]:
        """
        Spec 생성 및 Reflection 적용 (40 lines)

        Returns:
            (spec_yaml, spec_reflection)
        """
        self.logger.info("스펙 생성 시작...")
        spec_yaml = self._generate_spec(context, matched_patterns)

        spec_reflection = None
        if enable_reflection:
            spec_yaml, spec_reflection = self._apply_spec_reflection(
                spec_yaml, context.requirement, quality_threshold,
                max_reflection_iterations, context, matched_patterns
            )

        self.logger.info("스펙 생성 완료")
        return spec_yaml, spec_reflection

    def _apply_spec_reflection(
        self,
        spec_yaml: str,
        requirement: str,
        quality_threshold: float,
        max_iterations: int,
        context,
        matched_patterns
    ) -> Tuple[str, Any]:
        """
        Spec에 대한 Reflection 적용 (40 lines)

        Returns:
            (improved_spec_yaml, spec_reflection)
        """
        from app.core.bmad.reflection import ReflectionEngine

        reflection_engine = ReflectionEngine(quality_threshold=quality_threshold)
        spec_reflection = reflection_engine.reflect_on_spec(
            spec_yaml, requirement, use_llm=False
        )

        iteration_count = 0
        while (spec_reflection.requires_iteration and
               iteration_count < max_iterations):
            self.logger.info(
                f"스펙 개선 필요 (점수: {spec_reflection.overall_score:.2f}), "
                f"반복 {iteration_count+1}/{max_iterations}"
            )
            self.logger.debug(f"개선 계획:\n{spec_reflection.iteration_plan}")

            # 스펙 재생성
            spec_yaml = self._generate_spec(context, matched_patterns)

            # 재평가
            spec_reflection = reflection_engine.reflect_on_spec(
                spec_yaml, requirement, use_llm=False
            )
            iteration_count += 1

        self.logger.info(
            f"스펙 반성 완료: 점수={spec_reflection.overall_score:.2f}"
        )
        return spec_yaml, spec_reflection

    def _validate_traceability_if_enabled(
        self, context, enable_traceability: bool
    ) -> Optional[Any]:
        """
        추적성 검증 (enable 시에만 실행) (50 lines)

        Returns:
            traceability_report or None
        """
        if not enable_traceability:
            return None

        from app.core.validation.traceability import TraceabilityValidator

        self.logger.info("추적성 검증 시작...")
        validator = TraceabilityValidator(min_match_confidence=0.6)

        # RequirementAnalysis 준비
        from app.models.schemas import RequirementAnalysis
        requirement_analysis = RequirementAnalysis(**context.analysis)

        generated_spec = {
            "agents": context.agent_specs,
            "tasks": context.task_specs,
        }

        traceability_report = validator.validate_coverage(
            requirement_analysis, generated_spec
        )

        self.logger.info(
            f"추적성 검증 완료: valid={traceability_report.valid}, "
            f"coverage={traceability_report.coverage_score:.2%}"
        )

        # 심각한 이슈 경고
        self._warn_critical_traceability_issues(traceability_report)

        return traceability_report

    def _warn_critical_traceability_issues(self, report) -> None:
        """추적성 검증 결과의 Critical 이슈 경고 (20 lines)"""
        critical_issues = [
            issue for issue in report.issues
            if issue.get("severity") in ["critical", "high"]
        ]

        if critical_issues:
            self.logger.warning(
                f"⚠️ {len(critical_issues)}개의 심각한 추적성 이슈 발견"
            )
            for issue in critical_issues[:3]:
                self.logger.warning(f"  - {issue.get('message')}")

        # 누락된 요소 경고
        if report.missing_agents:
            self.logger.warning(
                f"⚠️ 누락된 Agent: {', '.join(report.missing_agents)}"
            )
        if report.missing_tasks:
            self.logger.warning(
                f"⚠️ 누락된 Task: {', '.join(report.missing_tasks[:5])}"
            )

    def _generate_and_reflect_code(
        self,
        context,
        spec_yaml: str,
        matched_patterns,
        enable_reflection: bool,
        quality_threshold: float,
        max_reflection_iterations: int
    ) -> Tuple[List[Dict], Optional[Any]]:
        """
        코드 생성 및 Reflection 적용 (40 lines)

        Returns:
            (generated_code, code_reflection)
        """
        self.logger.info("코드 생성 시작...")
        generated_code = self._generate_code_with_patterns(
            context, spec_yaml, matched_patterns
        )

        code_reflection = None
        if enable_reflection:
            generated_code, code_reflection = self._apply_code_reflection(
                generated_code, spec_yaml, quality_threshold,
                max_reflection_iterations, context, matched_patterns
            )

        self.logger.info(f"코드 생성 완료: {len(generated_code)}개 파일")
        return generated_code, code_reflection

    def _apply_code_reflection(
        self,
        generated_code: List[Dict],
        spec_yaml: str,
        quality_threshold: float,
        max_iterations: int,
        context,
        spec_yaml_str: str,
        matched_patterns
    ) -> Tuple[List[Dict], Any]:
        """
        Code에 대한 Reflection 적용 (40 lines)

        Returns:
            (improved_code, code_reflection)
        """
        from app.core.bmad.reflection import ReflectionEngine

        reflection_engine = ReflectionEngine(quality_threshold=quality_threshold)
        code_reflection = reflection_engine.reflect_on_code(
            generated_code, spec_yaml
        )

        iteration_count = 0
        while (code_reflection.requires_iteration and
               iteration_count < max_iterations):
            self.logger.info(
                f"코드 개선 필요 (점수: {code_reflection.overall_score:.2f}), "
                f"반복 {iteration_count+1}/{max_iterations}"
            )
            self.logger.debug(f"개선 계획:\n{code_reflection.iteration_plan}")

            # 코드 재생성
            generated_code = self._generate_code_with_patterns(
                context, spec_yaml_str, matched_patterns
            )

            # 재평가
            code_reflection = reflection_engine.reflect_on_code(
                generated_code, spec_yaml
            )
            iteration_count += 1

        self.logger.info(
            f"코드 반성 완료: 점수={code_reflection.overall_score:.2f}"
        )
        return generated_code, code_reflection

    def _run_quality_pipeline_if_available(
        self, generated_code: List[Dict]
    ) -> Optional[Any]:
        """
        Code Quality Pipeline 실행 (60 lines)

        Returns:
            quality_report or None
        """
        try:
            from caas_framework.quality.pipeline import CodeQualityPipeline

            self.logger.info("🔍 Code Quality Pipeline 실행 중...")

            # 코드 파일 준비
            code_files = {
                file["path"]: file.get("content", "")
                for file in generated_code
            }

            # Quality pipeline 실행
            quality_pipeline = CodeQualityPipeline(
                enable_syntax=True,
                enable_imports=True,
                enable_style=True
            )

            quality_report = quality_pipeline.verify(code_files)

            self.logger.info(
                f"Quality Report - Passed: {quality_report.overall_passed}, "
                f"Errors: {quality_report.total_errors}, "
                f"Warnings: {quality_report.total_warnings}"
            )

            if not quality_report.overall_passed:
                self._log_quality_issues(quality_report)
            else:
                self.logger.info("✅ All quality checks passed")

            return quality_report

        except Exception as e:
            self.logger.error(f"Quality Pipeline 실행 중 오류: {e}")
            return None

    def _log_quality_issues(self, quality_report) -> None:
        """Quality check 이슈 로깅 (20 lines)"""
        self.logger.warning(
            f"⚠️ {quality_report.total_errors} error(s) and "
            f"{quality_report.total_warnings} warning(s) detected"
        )

        for check in quality_report.checks:
            if check.errors:
                self.logger.warning(f"  [{check.name}] Errors:")
                for error in check.errors[:3]:
                    self.logger.warning(f"    - {error}")
                if len(check.errors) > 3:
                    self.logger.warning(
                        f"    ... and {len(check.errors) - 3} more"
                    )

            if check.warnings:
                self.logger.warning(f"  [{check.name}] Warnings:")
                for warning in check.warnings[:2]:
                    self.logger.warning(f"    - {warning}")
                if len(check.warnings) > 2:
                    self.logger.warning(
                        f"    ... and {len(check.warnings) - 2} more"
                    )

    def _validate_golden_data_if_enabled(
        self, context, generated_code: List[Dict]
    ) -> None:
        """
        Golden Data 검증 및 자동 수정 (50 lines)
        """
        if not (self.golden_validator and context.concretized_requirement and
                context.golden_data_validation_enabled):
            return

        try:
            self.logger.info("🎯 Golden Data 검증 시작 (Development Phase)")

            # 생성된 스펙 구조화
            generated_spec = {
                "agents": context.agent_specs,
                "tasks": context.task_specs,
                "code_files": [file["path"] for file in generated_code],
                "spec_yaml": context.spec_yaml,
            }

            # Development Phase 검증
            validation_report = self.golden_validator.validate_code(
                generated_spec
            )

            self.logger.info(
                f"검증 결과 - 커버리지: {validation_report.coverage_score:.1%}, "
                f"누락: {len(validation_report.missing_items)}개, "
                f"추가: {len(validation_report.extra_items)}개"
            )

            # 자동 수정 실행
            if validation_report.needs_fixing and self.auto_fixer:
                self._apply_auto_fix(context, generated_spec, validation_report)

            # 검증 리포트 저장
            context.golden_validation_reports.append(
                validation_report.model_dump()
            )

        except Exception as e:
            self.logger.error(f"Golden Data 검증 중 오류: {e}")

    def _apply_auto_fix(
        self, context, generated_spec: Dict, validation_report
    ) -> None:
        """자동 수정 적용 (15 lines)"""
        self.logger.info("🔧 자동 수정 실행 중...")
        fix_result = self.auto_fixer.fix_code(generated_spec, validation_report)

        if fix_result.success:
            self.logger.info(
                f"✅ 자동 수정 완료: {len(fix_result.fixes_applied)}개 항목 수정"
            )
            # 수정된 결과로 context 업데이트
            if "agents" in fix_result.fixed_output:
                context.agent_specs = fix_result.fixed_output["agents"]
            if "tasks" in fix_result.fixed_output:
                context.task_specs = fix_result.fixed_output["tasks"]
        else:
            self.logger.warning("⚠️ 자동 수정 실패")

    def _validate_boundaries_if_enabled(
        self, context, generated_code: List[Dict]
    ) -> List[str]:
        """
        Security Boundaries 검증 (40 lines)

        Returns:
            boundaries_violations list
        """
        boundaries_violations = []

        if not context.concretized_requirement:
            return boundaries_violations

        from app.models.schemas import ConcretizedRequirement
        concretized = ConcretizedRequirement(**context.concretized_requirement)

        if not concretized.boundaries:
            return boundaries_violations

        self.logger.info("🔒 Security Boundaries 검증 시작...")

        # 코드 파일 준비
        code_files = {
            file["path"]: file.get("content", "")
            for file in generated_code
        }

        # Boundary 검증
        boundaries = concretized.boundaries
        for filename, content in code_files.items():
            if not filename.endswith('.py'):
                continue

            content_lower = content.lower()

            # never_allowed 패턴 체크
            for pattern in (boundaries.never_allowed or []):
                if pattern.lower() in content_lower:
                    violation = (
                        f"NEVER_ALLOWED: {filename} contains '{pattern}'"
                    )
                    boundaries_violations.append(violation)
                    self.logger.warning(f"⚠️ {violation}")

        if boundaries_violations:
            self.logger.warning(
                f"🚨 {len(boundaries_violations)} boundary violation(s) detected!"
            )
        else:
            self.logger.info("✅ No boundary violations detected")

        return boundaries_violations

    def _record_development_history(
        self,
        context,
        matched_patterns,
        generated_code: List[Dict],
        validation_result,
        enable_reflection: bool,
        spec_reflection,
        code_reflection,
        enable_traceability: bool,
        traceability_report,
        boundaries_violations: List[str],
        quality_report
    ) -> None:
        """
        Development 히스토리 기록 (80 lines)
        """
        history_entry = {
            "phase": "DEVELOPMENT",
            "status": "COMPLETED",
            "timestamp": datetime.now().isoformat(),
            "summary": (
                f"Generated {len(generated_code)} files "
                f"with {len(matched_patterns)} patterns"
            ),
            "patterns_used": [p.pattern_name for p in matched_patterns],
            "validation": validation_result,
        }

        # Reflection 정보
        if enable_reflection and spec_reflection and code_reflection:
            history_entry["reflection"] = {
                "spec_score": spec_reflection.overall_score,
                "code_score": code_reflection.overall_score,
                "spec_iterations": spec_reflection.iteration_count,
                "code_iterations": code_reflection.iteration_count,
            }

        # Traceability 정보
        if enable_traceability and traceability_report:
            history_entry["traceability"] = {
                "valid": traceability_report.valid,
                "coverage_score": traceability_report.coverage_score,
                "total_issues": len(traceability_report.issues),
                "critical_issues": len([
                    i for i in traceability_report.issues
                    if i.get("severity") in ["critical", "high"]
                ]),
                "missing_agents": len(traceability_report.missing_agents),
                "missing_tasks": len(traceability_report.missing_tasks),
                "missing_tools": len(traceability_report.missing_tools),
            }

        # Boundaries 정보
        if boundaries_violations:
            history_entry["boundaries"] = {
                "violations_count": len(boundaries_violations),
                "violations": boundaries_violations
            }

        # Quality 정보
        if quality_report:
            syntax_check = next(
                (c for c in quality_report.checks if c.name == "Syntax Check"),
                None
            )
            import_check = next(
                (c for c in quality_report.checks if c.name == "Import Check"),
                None
            )
            style_check = next(
                (c for c in quality_report.checks if c.name == "Code Style Check"),
                None
            )

            history_entry["quality"] = {
                "passed": quality_report.overall_passed,
                "total_errors": quality_report.total_errors,
                "total_warnings": quality_report.total_warnings,
                "syntax_errors": len(syntax_check.errors) if syntax_check else 0,
                "import_errors": len(import_check.errors) if import_check else 0,
                "style_warnings": len(style_check.warnings) if style_check else 0,
            }

        context.phase_history.append(history_entry)

    def _check_plan_mode_gate_if_enabled(
        self, generated_code: List[Dict]
    ) -> None:
        """
        Plan Mode Gate 3: Code Review (20 lines)
        """
        if not self.plan_mode_api:
            return

        self.logger.info("\n" + "="*70)
        self.logger.info("💻 Gate 3: Code Review")
        self.logger.info("="*70)

        # 코드 파일 준비
        code_files = {
            file["path"]: file.get("content", "")
            for file in generated_code
        }

        decision = self.plan_mode_api.request_code_review(code_files)

        if decision == "reject":
            self.logger.warning("❌ User rejected generated code")
            from app.exceptions import UserAbortedError
            raise UserAbortedError("User rejected code at Gate 3")
        else:
            self.logger.info("✅ User approved generated code")

    def _record_development_failure(self, context, error: Exception) -> None:
        """Development 실패 기록 (10 lines)"""
        self.logger.error(f"Development 실패: {error}")
        context.phase_history.append({
            "phase": "DEVELOPMENT",
            "status": "FAILED",
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
        })
