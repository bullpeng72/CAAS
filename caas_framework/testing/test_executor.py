"""
Test Executor

테스트 실행 및 결과 분석
"""

import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field


class TestCaseResult(BaseModel):
    """단일 테스트 케이스 결과"""

    test_name: str
    status: str  # "passed", "failed", "skipped", "error"
    duration: float = 0.0  # seconds
    error_message: Optional[str] = None
    traceback: Optional[str] = None


class TestResult(BaseModel):
    """전체 테스트 결과"""

    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float  # total seconds
    coverage_percentage: Optional[float] = None
    test_cases: List[TestCaseResult] = Field(default_factory=list)
    success: bool = False


class TestExecutor:
    """테스트 실행기"""

    def __init__(self, working_directory: Optional[Path] = None):
        """
        Args:
            working_directory: 테스트 실행 디렉토리
        """
        self.working_directory = working_directory or Path.cwd()

    def execute_pytest(
        self,
        test_file_path: str,
        test_code: str,
        coverage: bool = True,
        verbose: bool = True,
    ) -> TestResult:
        """
        Pytest 실행

        Args:
            test_file_path: 테스트 파일 경로
            test_code: 테스트 코드
            coverage: 커버리지 측정 여부
            verbose: 상세 출력 여부

        Returns:
            TestResult
        """

        # 임시 디렉토리에 테스트 파일 작성
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_file = tmpdir_path / test_file_path
            test_file.parent.mkdir(parents=True, exist_ok=True)

            # 테스트 파일 작성
            test_file.write_text(test_code, encoding="utf-8")

            # pytest 명령어 구성
            cmd = ["pytest", str(test_file)]

            if verbose:
                cmd.append("-v")

            if coverage:
                cmd.extend(["--cov", "--cov-report=term-missing"])

            # pytest 실행
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(tmpdir_path),
                    timeout=60,
                )

                # 결과 파싱
                return self._parse_pytest_output(
                    result.stdout, result.stderr, result.returncode
                )

            except subprocess.TimeoutExpired:
                return TestResult(
                    total_tests=0,
                    passed=0,
                    failed=1,
                    skipped=0,
                    errors=1,
                    duration=60.0,
                    success=False,
                    test_cases=[
                        TestCaseResult(
                            test_name="timeout",
                            status="error",
                            duration=60.0,
                            error_message="Test execution timed out",
                        )
                    ],
                )

            except Exception as e:
                return TestResult(
                    total_tests=0,
                    passed=0,
                    failed=1,
                    skipped=0,
                    errors=1,
                    duration=0.0,
                    success=False,
                    test_cases=[
                        TestCaseResult(
                            test_name="execution_error",
                            status="error",
                            duration=0.0,
                            error_message=str(e),
                        )
                    ],
                )

    def _parse_pytest_output(
        self, stdout: str, stderr: str, returncode: int
    ) -> TestResult:
        """Pytest 출력 파싱"""

        # 기본값
        total_tests = 0
        passed = 0
        failed = 0
        skipped = 0
        errors = 0
        duration = 0.0
        coverage = None

        # stdout에서 정보 추출
        lines = stdout.split("\n")

        for line in lines:
            # 테스트 결과 요약 파싱
            if "passed" in line or "failed" in line:
                # 예: "5 passed, 2 failed in 3.45s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed":
                        passed = int(parts[i - 1]) if i > 0 else 0
                    elif part == "failed":
                        failed = int(parts[i - 1]) if i > 0 else 0
                    elif part == "skipped":
                        skipped = int(parts[i - 1]) if i > 0 else 0
                    elif part == "error" or part == "errors":
                        errors = int(parts[i - 1]) if i > 0 else 0
                    elif part.endswith("s") and "in" in parts:
                        # Duration: "in 3.45s"
                        try:
                            duration = float(part.replace("s", ""))
                        except ValueError:
                            pass

            # 커버리지 파싱
            if "TOTAL" in line and "%" in line:
                # 예: "TOTAL      100      20    80%"
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        try:
                            coverage = float(part.replace("%", ""))
                        except ValueError:
                            pass

        total_tests = passed + failed + skipped + errors

        return TestResult(
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=duration,
            coverage_percentage=coverage,
            success=(returncode == 0),
        )

    def dry_run(self, test_code: str) -> bool:
        """
        Dry run - 테스트 코드 구문 검증만 수행

        Args:
            test_code: 테스트 코드

        Returns:
            bool: 구문이 유효하면 True
        """
        try:
            compile(test_code, "<string>", "exec")
            return True
        except SyntaxError:
            return False


def execute_tests(
    test_file_path: str,
    test_code: str,
    coverage: bool = True,
    working_directory: Optional[Path] = None,
) -> TestResult:
    """
    Helper function - 테스트 실행

    Args:
        test_file_path: 테스트 파일 경로
        test_code: 테스트 코드
        coverage: 커버리지 측정
        working_directory: 작업 디렉토리

    Returns:
        TestResult
    """
    executor = TestExecutor(working_directory=working_directory)
    return executor.execute_pytest(test_file_path, test_code, coverage=coverage)
