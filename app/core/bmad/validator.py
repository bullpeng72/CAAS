"""
CAAS BMAD Code Validator

코드 품질 검증을 수행합니다.
구문, 스타일, 보안, 메트릭을 검증합니다.
"""

import ast
import re
from typing import Any, Dict, List, Optional
from pathlib import Path

from app.utils.logger import get_logger, LoggerMixin

logger = get_logger("bmad.validator")


class ValidationResult:
    """코드 검증 결과"""

    def __init__(self):
        self.valid = True
        self.syntax_errors: List[Dict[str, Any]] = []
        self.style_warnings: List[Dict[str, Any]] = []
        self.security_issues: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {}
        self.total_files = 0
        self.validated_files = 0

    def add_syntax_error(self, file: str, line: int, message: str):
        """구문 오류 추가"""
        self.valid = False
        self.syntax_errors.append({
            "file": file,
            "line": line,
            "message": message,
            "severity": "error",
        })

    def add_style_warning(self, file: str, line: int, message: str):
        """스타일 경고 추가"""
        self.style_warnings.append({
            "file": file,
            "line": line,
            "message": message,
            "severity": "warning",
        })

    def add_security_issue(self, file: str, line: int, message: str, severity: str = "high"):
        """보안 이슈 추가"""
        self.security_issues.append({
            "file": file,
            "line": line,
            "message": message,
            "severity": severity,
        })
        if severity in ["critical", "high"]:
            self.valid = False

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "valid": self.valid,
            "total_files": self.total_files,
            "validated_files": self.validated_files,
            "syntax_errors": self.syntax_errors,
            "style_warnings": self.style_warnings,
            "security_issues": self.security_issues,
            "metrics": self.metrics,
        }


class CodeValidator(LoggerMixin):
    """
    코드 품질 검증기

    구문, 스타일, 보안, 메트릭을 검증합니다.
    """

    def __init__(self):
        # 보안 패턴
        self.security_patterns = {
            "hardcoded_password": re.compile(r'password\s*=\s*["\'].*["\']', re.IGNORECASE),
            "hardcoded_api_key": re.compile(r'api[_-]?key\s*=\s*["\'][^"\']{10,}["\']', re.IGNORECASE),
            "hardcoded_secret": re.compile(r'secret\s*=\s*["\'].*["\']', re.IGNORECASE),
            "sql_injection": re.compile(r'execute\s*\(\s*["\'].*%s.*["\']', re.IGNORECASE),
            "eval_usage": re.compile(r'\beval\s*\('),
            "exec_usage": re.compile(r'\bexec\s*\('),
        }

        # 위험한 함수 목록
        self.dangerous_functions = [
            "eval", "exec", "compile", "__import__",
            "os.system", "subprocess.call", "subprocess.Popen",
        ]

    def validate(self, code_files: Dict[str, str]) -> ValidationResult:
        """
        코드 파일 전체 검증

        Args:
            code_files: 파일명 -> 코드 매핑

        Returns:
            ValidationResult: 검증 결과
        """
        result = ValidationResult()
        result.total_files = len(code_files)

        for filename, code in code_files.items():
            # Python 파일만 검증
            if not filename.endswith(".py"):
                continue

            self.logger.info(f"검증 중: {filename}")

            # 1. 구문 검증
            self._validate_syntax(filename, code, result)

            # 2. 스타일 검증
            self._validate_style(filename, code, result)

            # 3. 보안 검증
            self._validate_security(filename, code, result)

            result.validated_files += 1

        # 4. 메트릭 계산
        result.metrics = self._calculate_metrics(code_files)

        # 결과 요약 로깅
        self._log_summary(result)

        return result

    def _validate_syntax(self, filename: str, code: str, result: ValidationResult):
        """
        AST 기반 구문 검증

        Args:
            filename: 파일명
            code: 코드
            result: 검증 결과
        """
        try:
            ast.parse(code)
            self.logger.debug(f"구문 검증 성공: {filename}")
        except SyntaxError as e:
            result.add_syntax_error(
                file=filename,
                line=e.lineno or 0,
                message=f"Syntax error: {e.msg}",
            )
            self.logger.error(f"구문 오류 ({filename}:{e.lineno}): {e.msg}")

    def _validate_style(self, filename: str, code: str, result: ValidationResult):
        """
        PEP 8 스타일 검증 (기본적인 규칙만)

        Args:
            filename: 파일명
            code: 코드
            result: 검증 결과
        """
        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            # 라인 길이 검사 (79자 권장)
            if len(line) > 120:
                result.add_style_warning(
                    file=filename,
                    line=line_num,
                    message=f"Line too long ({len(line)} > 120 characters)",
                )

            # 트레일링 공백
            if line.endswith(" ") or line.endswith("\t"):
                result.add_style_warning(
                    file=filename,
                    line=line_num,
                    message="Trailing whitespace",
                )

            # 탭 사용 (공백 4개 권장)
            if "\t" in line:
                result.add_style_warning(
                    file=filename,
                    line=line_num,
                    message="Use 4 spaces instead of tabs",
                )

    def _validate_security(self, filename: str, code: str, result: ValidationResult):
        """
        보안 검증

        Args:
            filename: 파일명
            code: 코드
            result: 검증 결과
        """
        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            # 하드코딩된 비밀 검사
            for pattern_name, pattern in self.security_patterns.items():
                if pattern.search(line):
                    severity = "critical" if "password" in pattern_name or "secret" in pattern_name else "high"
                    result.add_security_issue(
                        file=filename,
                        line=line_num,
                        message=f"Potential {pattern_name.replace('_', ' ')} found",
                        severity=severity,
                    )

        # AST 기반 위험 함수 검사
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = self._get_function_name(node.func)
                    if func_name in self.dangerous_functions:
                        result.add_security_issue(
                            file=filename,
                            line=node.lineno,
                            message=f"Dangerous function '{func_name}' used",
                            severity="high",
                        )
        except SyntaxError:
            # 구문 오류는 이미 _validate_syntax에서 처리됨
            pass

    def _calculate_metrics(self, code_files: Dict[str, str]) -> Dict[str, Any]:
        """
        코드 메트릭 계산

        Args:
            code_files: 파일명 -> 코드 매핑

        Returns:
            Dict: 메트릭
        """
        metrics = {
            "total_lines": 0,
            "code_lines": 0,
            "comment_lines": 0,
            "blank_lines": 0,
            "function_count": 0,
            "class_count": 0,
            "docstring_coverage": 0.0,
            "avg_complexity": 0.0,
        }

        total_functions = 0
        documented_functions = 0
        total_complexity = 0

        for filename, code in code_files.items():
            if not filename.endswith(".py"):
                continue

            lines = code.split("\n")
            metrics["total_lines"] += len(lines)

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    metrics["blank_lines"] += 1
                elif stripped.startswith("#"):
                    metrics["comment_lines"] += 1
                else:
                    metrics["code_lines"] += 1

            # AST 기반 메트릭
            try:
                tree = ast.parse(code)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        metrics["function_count"] += 1
                        total_functions += 1

                        # Docstring 존재 여부
                        if ast.get_docstring(node):
                            documented_functions += 1

                        # 복잡도 계산 (간단한 버전: if/for/while 개수)
                        complexity = self._calculate_complexity(node)
                        total_complexity += complexity

                    elif isinstance(node, ast.ClassDef):
                        metrics["class_count"] += 1

            except SyntaxError:
                pass

        # 문서화 커버리지
        if total_functions > 0:
            metrics["docstring_coverage"] = (documented_functions / total_functions) * 100

        # 평균 복잡도
        if total_functions > 0:
            metrics["avg_complexity"] = total_complexity / total_functions

        return metrics

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """
        함수의 순환 복잡도 계산 (간단한 버전)

        Args:
            node: 함수 AST 노드

        Returns:
            int: 복잡도
        """
        complexity = 1  # 기본 경로

        for child in ast.walk(node):
            # 분기문마다 +1
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            # 논리 연산자마다 +1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _get_function_name(self, node: ast.AST) -> str:
        """
        함수 호출 노드에서 함수 이름 추출

        Args:
            node: AST 노드

        Returns:
            str: 함수 이름
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # obj.method -> "obj.method"
            value_name = self._get_function_name(node.value)
            return f"{value_name}.{node.attr}" if value_name else node.attr
        else:
            return ""

    def _log_summary(self, result: ValidationResult):
        """
        검증 결과 요약 로깅

        Args:
            result: 검증 결과
        """
        self.logger.info("="*60)
        self.logger.info("코드 검증 완료")
        self.logger.info(f"검증 파일: {result.validated_files}/{result.total_files}")

        if result.syntax_errors:
            self.logger.error(f"구문 오류: {len(result.syntax_errors)}개")
        else:
            self.logger.info("구문 오류: 0개 ✅")

        if result.style_warnings:
            self.logger.warning(f"스타일 경고: {len(result.style_warnings)}개")

        if result.security_issues:
            critical = len([i for i in result.security_issues if i["severity"] == "critical"])
            high = len([i for i in result.security_issues if i["severity"] == "high"])
            self.logger.error(f"보안 이슈: {critical} critical, {high} high")
        else:
            self.logger.info("보안 이슈: 0개 ✅")

        # 메트릭
        m = result.metrics
        self.logger.info(f"코드 라인: {m.get('code_lines', 0)}")
        self.logger.info(f"함수 개수: {m.get('function_count', 0)}")
        self.logger.info(f"클래스 개수: {m.get('class_count', 0)}")
        self.logger.info(f"문서화 커버리지: {m.get('docstring_coverage', 0):.1f}%")
        self.logger.info(f"평균 복잡도: {m.get('avg_complexity', 0):.1f}")

        self.logger.info("="*60)
