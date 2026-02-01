"""
Test Runner Utility

pytest를 프로그래매틱하게 실행하고 결과를 파싱합니다.
"""

import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """개별 테스트 케이스"""
    name: str
    status: str  # passed, failed, skipped, error
    duration: float
    file: str
    line: int
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None


@dataclass
class TestSuite:
    """테스트 스위트"""
    name: str
    tests: List[TestCase] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0


@dataclass
class CoverageReport:
    """커버리지 리포트"""
    total_statements: int
    covered_statements: int
    coverage_percent: float
    missing_lines: Dict[str, List[int]] = field(default_factory=dict)

    @property
    def coverage_display(self) -> str:
        """커버리지를 %로 표시"""
        return f"{self.coverage_percent:.1f}%"


@dataclass
class TestResult:
    """전체 테스트 결과"""
    suites: List[TestSuite]
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    coverage: Optional[CoverageReport] = None
    timestamp: datetime = field(default_factory=datetime.now)
    exit_code: int = 0
    error_message: Optional[str] = None  # 실행 오류 메시지
    stdout: Optional[str] = None  # pytest stdout
    stderr: Optional[str] = None  # pytest stderr

    @property
    def success_rate(self) -> float:
        """성공률 계산"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100

    @property
    def is_success(self) -> bool:
        """모든 테스트가 통과했는지"""
        return self.failed == 0 and self.errors == 0


class TestRunner:
    """pytest 프로그래매틱 실행 및 결과 파싱"""

    def __init__(self, project_root: Optional[Path] = None):
        """
        Args:
            project_root: 프로젝트 루트 디렉토리 (기본값: 현재 디렉토리의 상위)
        """
        if project_root is None:
            # app/utils/test_runner.py -> caas/
            project_root = Path(__file__).parent.parent.parent

        self.project_root = project_root
        self.tests_dir = project_root / "tests"

    def run_tests(
        self,
        test_path: Optional[str] = None,
        test_type: str = "all",
        verbose: bool = True,
        coverage: bool = True,
        markers: Optional[List[str]] = None,
    ) -> TestResult:
        """
        테스트 실행

        Args:
            test_path: 특정 테스트 경로 (없으면 전체)
            test_type: 테스트 타입 (all, unit, integration, e2e, security)
            verbose: 상세 출력
            coverage: 커버리지 측정
            markers: pytest 마커 필터

        Returns:
            TestResult: 테스트 결과
        """
        logger.info(f"테스트 실행 시작: type={test_type}, coverage={coverage}")

        # 테스트 타입별 타임아웃 설정
        timeout_map = {
            "e2e": 2400,     # E2E: 40분 (LLM 호출 포함, 54개 테스트)
            "all": 3000,     # 전체: 50분 (E2E 포함)
            "unit": 300,     # 유닛: 5분
            "security": 180, # 보안: 3분
            "integration": 240, # 통합: 4분
        }
        timeout = timeout_map.get(test_type, 300)

        # pytest 명령 찾기
        pytest_path = shutil.which("pytest")
        if not pytest_path:
            error_msg = "pytest가 설치되어 있지 않습니다. 'pip install pytest pytest-json-report pytest-cov'를 실행하세요."
            logger.error(error_msg)
            return TestResult(
                suites=[],
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=0.0,
                exit_code=-1,
                error_message=error_msg,
            )

        logger.info(f"pytest 경로: {pytest_path}")

        # pytest 명령 구성
        cmd = [pytest_path]

        # 테스트 경로 설정
        if test_path:
            cmd.append(test_path)
        else:
            # 테스트 타입별 경로 설정
            if test_type == "unit":
                cmd.extend([
                    str(self.tests_dir / "test_bmad"),
                    str(self.tests_dir / "test_sdd"),
                    str(self.tests_dir / "test_codegen/test_generator.py"),  # 순환 import 문제로 validator_integration 제외
                    str(self.tests_dir / "test_knowledge"),
                ])
            elif test_type == "security":
                cmd.append(str(self.tests_dir / "test_security"))
            elif test_type == "e2e":
                # E2E: tests/e2e/ 디렉토리 + 루트의 test_e2e_*.py 파일들
                cmd.extend([
                    str(self.tests_dir / "e2e"),
                    str(self.tests_dir / "test_e2e_chatbot.py"),
                    str(self.tests_dir / "test_e2e_todo_app.py"),
                ])
            elif test_type == "integration":
                cmd.extend([
                    str(self.tests_dir / "test_codegen/test_validator_integration.py"),
                    str(self.tests_dir / "test_workflow_manager.py"),
                ])
            else:  # all
                cmd.append(str(self.tests_dir))

        # 옵션 추가
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")

        # JSON 리포트 생성
        json_report_path = self.project_root / "test_report.json"
        cmd.extend(["--json-report", f"--json-report-file={json_report_path}"])

        # 커버리지 측정
        if coverage:
            cmd.extend([
                "--cov=app",
                "--cov-report=json",
                f"--cov-report=html:{self.project_root / 'htmlcov'}",
            ])

        # 마커 필터
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])

        # 색상 출력 비활성화 (파싱 용이성)
        cmd.append("--color=no")

        # 경고 요약 비활성화
        cmd.append("--disable-warnings")

        logger.info(f"실행 명령: {' '.join(cmd)}")

        try:
            # pytest 실행
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=timeout,  # E2E: 10분, 기타: 5분
            )

            logger.info(f"pytest 종료 코드: {result.returncode}")

            # stdout/stderr 로깅 (처음 500자만)
            if result.stdout:
                logger.info(f"pytest stdout (처음 500자): {result.stdout[:500]}")
            if result.stderr:
                logger.warning(f"pytest stderr: {result.stderr}")

            # JSON 리포트 파싱
            test_result = self._parse_json_report(json_report_path, result.returncode)

            # stdout/stderr 저장
            test_result.stdout = result.stdout
            test_result.stderr = result.stderr

            # 커버리지 파싱
            if coverage:
                coverage_report = self._parse_coverage_report()
                test_result.coverage = coverage_report

            return test_result

        except subprocess.TimeoutExpired as e:
            timeout_minutes = timeout // 60
            error_msg = f"테스트 실행이 {timeout_minutes}분 타임아웃을 초과했습니다."
            logger.error(error_msg)
            return TestResult(
                suites=[],
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=0.0,
                exit_code=-1,
                error_message=error_msg,
                stdout=str(e.stdout) if e.stdout else None,
                stderr=str(e.stderr) if e.stderr else None,
            )
        except Exception as e:
            error_msg = f"테스트 실행 중 예외 발생: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return TestResult(
                suites=[],
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=0.0,
                exit_code=-1,
                error_message=error_msg,
            )

    def _parse_json_report(self, report_path: Path, exit_code: int) -> TestResult:
        """
        pytest JSON 리포트 파싱

        Args:
            report_path: JSON 리포트 파일 경로
            exit_code: pytest 종료 코드

        Returns:
            TestResult: 파싱된 테스트 결과
        """
        if not report_path.exists():
            logger.warning(f"JSON 리포트 파일이 없습니다: {report_path}")
            return TestResult(
                suites=[],
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                duration=0.0,
                exit_code=exit_code,
            )

        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 통계 추출
            summary = data.get("summary", {})
            total = summary.get("total", 0)
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)
            skipped = summary.get("skipped", 0)
            errors = summary.get("error", 0)
            duration = data.get("duration", 0.0)

            # 테스트 케이스 파싱
            suites = self._parse_test_suites(data.get("tests", []))

            return TestResult(
                suites=suites,
                total_tests=total,
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=errors,
                duration=duration,
                exit_code=exit_code,
            )

        except Exception as e:
            logger.error(f"JSON 리포트 파싱 오류: {e}")
            return TestResult(
                suites=[],
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=0.0,
                exit_code=exit_code,
            )

    def _parse_test_suites(self, tests: List[Dict]) -> List[TestSuite]:
        """
        테스트 케이스를 스위트별로 그룹화

        Args:
            tests: pytest JSON 리포트의 tests 배열

        Returns:
            List[TestSuite]: 테스트 스위트 목록
        """
        suites_dict: Dict[str, TestSuite] = {}

        for test in tests:
            # 테스트 파일명을 스위트 이름으로 사용
            nodeid = test.get("nodeid", "")
            file_path = nodeid.split("::")[0] if "::" in nodeid else nodeid

            # 테스트 케이스 생성
            test_case = TestCase(
                name=test.get("nodeid", "unknown"),
                status=test.get("outcome", "unknown"),
                duration=test.get("call", {}).get("duration", 0.0),
                file=file_path,
                line=test.get("lineno", 0),
                error_message=self._extract_error_message(test),
                error_traceback=self._extract_traceback(test),
            )

            # 스위트에 추가
            if file_path not in suites_dict:
                suites_dict[file_path] = TestSuite(name=file_path)

            suite = suites_dict[file_path]
            suite.tests.append(test_case)
            suite.duration += test_case.duration

            # 통계 업데이트
            if test_case.status == "passed":
                suite.passed += 1
            elif test_case.status == "failed":
                suite.failed += 1
            elif test_case.status == "skipped":
                suite.skipped += 1
            else:
                suite.errors += 1

        return list(suites_dict.values())

    def _extract_error_message(self, test: Dict) -> Optional[str]:
        """테스트 케이스에서 에러 메시지 추출"""
        call = test.get("call", {})
        if "longrepr" in call:
            longrepr = call["longrepr"]
            if isinstance(longrepr, str):
                # 첫 줄만 추출
                return longrepr.split("\n")[0]
        return None

    def _extract_traceback(self, test: Dict) -> Optional[str]:
        """테스트 케이스에서 전체 traceback 추출"""
        call = test.get("call", {})
        if "longrepr" in call:
            longrepr = call["longrepr"]
            if isinstance(longrepr, str):
                return longrepr
        return None

    def _parse_coverage_report(self) -> Optional[CoverageReport]:
        """
        커버리지 JSON 리포트 파싱

        Returns:
            Optional[CoverageReport]: 커버리지 리포트 또는 None
        """
        coverage_json = self.project_root / ".coverage.json"

        if not coverage_json.exists():
            # coverage.json 대신 .coverage 파일 확인
            coverage_file = self.project_root / ".coverage"
            if not coverage_file.exists():
                logger.warning("커버리지 파일이 없습니다")
                return None

            # coverage.py를 사용하여 JSON으로 변환 시도
            try:
                subprocess.run(
                    ["coverage", "json", "-o", str(coverage_json)],
                    cwd=str(self.project_root),
                    capture_output=True,
                    timeout=30,
                )
            except Exception as e:
                logger.warning(f"커버리지 JSON 생성 실패: {e}")
                return None

        try:
            with open(coverage_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            totals = data.get("totals", {})

            return CoverageReport(
                total_statements=totals.get("num_statements", 0),
                covered_statements=totals.get("covered_lines", 0),
                coverage_percent=totals.get("percent_covered", 0.0),
                missing_lines={},  # 상세 정보는 생략
            )

        except Exception as e:
            logger.error(f"커버리지 리포트 파싱 오류: {e}")
            return None

    def get_test_categories(self) -> List[Dict[str, Any]]:
        """
        사용 가능한 테스트 카테고리 목록 반환

        Returns:
            List[Dict]: 카테고리 정보 목록
        """
        return [
            {
                "id": "all",
                "name": "전체 테스트",
                "description": "모든 테스트 실행 (317개, 20-40분 소요, 타임아웃: 50분)",
                "icon": "🧪",
            },
            {
                "id": "unit",
                "name": "유닛 테스트",
                "description": "BMAD, SDD, Codegen, Knowledge 모듈 테스트 (83개, 타임아웃: 5분)",
                "icon": "⚙️",
            },
            {
                "id": "security",
                "name": "보안 테스트",
                "description": "Path Traversal, YAML Bomb, Secrets, Cypher Injection (109개, 타임아웃: 3분)",
                "icon": "🔒",
            },
            {
                "id": "integration",
                "name": "통합 테스트",
                "description": "Validator Integration, Workflow Manager (18개, 타임아웃: 4분)",
                "icon": "🔗",
            },
            {
                "id": "e2e",
                "name": "E2E 테스트",
                "description": "전체 파이프라인 테스트 (56개, 10-30분 소요, 타임아웃: 40분)",
                "icon": "🚀",
            },
        ]


def get_test_runner() -> TestRunner:
    """TestRunner 인스턴스 반환 (싱글톤)"""
    if not hasattr(get_test_runner, "_instance"):
        get_test_runner._instance = TestRunner()
    return get_test_runner._instance
