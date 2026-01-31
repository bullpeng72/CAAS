"""
Integration Test Runner

통합 테스트를 자동으로 실행하고 결과를 수집하는 시스템
"""

import subprocess
import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from app.utils.logger import get_logger

logger = get_logger("integration_runner")


class TestStatus(str, Enum):
    """테스트 실행 상태"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestResult(BaseModel):
    """개별 테스트 결과"""
    test_name: str
    status: TestStatus
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    output: Optional[str] = None


class TestRunReport(BaseModel):
    """테스트 실행 리포트"""
    run_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    test_results: List[TestResult] = Field(default=[])
    coverage_percent: Optional[float] = None


class IntegrationTestRunner:
    """
    통합 테스트 러너

    pytest를 활용하여 통합 테스트를 자동으로 실행하고 결과를 수집합니다.
    """

    def __init__(
        self,
        test_dir: str = "tests",
        coverage_enabled: bool = True,
        parallel: bool = False,
        num_workers: int = 4,
    ):
        """
        Args:
            test_dir: 테스트 디렉토리 경로
            coverage_enabled: 코드 커버리지 측정 활성화
            parallel: 병렬 실행 활성화
            num_workers: 병렬 실행 worker 수
        """
        self.test_dir = test_dir
        self.coverage_enabled = coverage_enabled
        self.parallel = parallel
        self.num_workers = num_workers
        self.logger = logger

    def run_tests(
        self,
        test_pattern: Optional[str] = None,
        markers: Optional[List[str]] = None,
        verbose: bool = True,
    ) -> TestRunReport:
        """
        테스트를 실행합니다.

        Args:
            test_pattern: 테스트 파일/함수 패턴 (예: "test_api.py::test_get_endpoint")
            markers: pytest marker 필터 (예: ["integration", "slow"])
            verbose: 상세 출력 활성화

        Returns:
            TestRunReport: 테스트 실행 리포트
        """
        run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        start_time = datetime.utcnow()

        self.logger.info(f"Starting test run: {run_id}")

        # pytest 명령어 구성
        cmd = self._build_pytest_command(test_pattern, markers, verbose)

        self.logger.info(f"Command: {' '.join(cmd)}")

        # 테스트 실행
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
            )

            # 결과 파싱
            report = self._parse_pytest_output(
                run_id=run_id,
                start_time=start_time,
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
            )

            self.logger.info(
                f"Test run completed: {report.passed}/{report.total_tests} passed"
            )

            return report

        except Exception as e:
            self.logger.error(f"Test execution failed: {e}")
            return TestRunReport(
                run_id=run_id,
                start_time=start_time,
                end_time=datetime.utcnow(),
                errors=1,
            )

    def _build_pytest_command(
        self,
        test_pattern: Optional[str],
        markers: Optional[List[str]],
        verbose: bool,
    ) -> List[str]:
        """pytest 명령어를 구성합니다"""
        cmd = ["pytest"]

        # 테스트 경로/패턴
        if test_pattern:
            cmd.append(test_pattern)
        else:
            cmd.append(self.test_dir)

        # Marker 필터
        if markers:
            marker_expr = " and ".join(markers)
            cmd.extend(["-m", marker_expr])

        # Verbose
        if verbose:
            cmd.append("-v")

        # JSON 리포트 생성
        report_file = "test_report.json"
        cmd.extend(["--json-report", f"--json-report-file={report_file}"])

        # 커버리지
        if self.coverage_enabled:
            cmd.extend([
                "--cov=app",
                "--cov-report=term",
                "--cov-report=html",
            ])

        # 병렬 실행
        if self.parallel:
            cmd.extend(["-n", str(self.num_workers)])

        # 출력 형식
        cmd.append("--tb=short")  # Traceback 짧게

        return cmd

    def _parse_pytest_output(
        self,
        run_id: str,
        start_time: datetime,
        stdout: str,
        stderr: str,
        returncode: int,
    ) -> TestRunReport:
        """pytest 출력을 파싱합니다"""
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        # JSON 리포트 파일 읽기
        report_file = "test_report.json"
        test_results = []
        total_tests = 0
        passed = 0
        failed = 0
        skipped = 0
        errors = 0

        if os.path.exists(report_file):
            try:
                with open(report_file, "r") as f:
                    json_data = json.load(f)

                # 통계 추출
                summary = json_data.get("summary", {})
                total_tests = summary.get("total", 0)
                passed = summary.get("passed", 0)
                failed = summary.get("failed", 0)
                skipped = summary.get("skipped", 0)

                # 개별 테스트 결과
                for test in json_data.get("tests", []):
                    outcome = test.get("outcome", "unknown")
                    status = self._map_outcome_to_status(outcome)

                    test_results.append(TestResult(
                        test_name=test.get("nodeid", "unknown"),
                        status=status,
                        duration_seconds=test.get("duration", 0.0),
                        error_message=test.get("call", {}).get("longrepr"),
                    ))

            except Exception as e:
                self.logger.warning(f"Failed to parse JSON report: {e}")

        # stdout에서 커버리지 파싱
        coverage_percent = self._extract_coverage(stdout)

        return TestRunReport(
            run_id=run_id,
            start_time=start_time,
            end_time=end_time,
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration_seconds=duration,
            test_results=test_results,
            coverage_percent=coverage_percent,
        )

    def _map_outcome_to_status(self, outcome: str) -> TestStatus:
        """pytest outcome을 TestStatus로 매핑"""
        mapping = {
            "passed": TestStatus.PASSED,
            "failed": TestStatus.FAILED,
            "skipped": TestStatus.SKIPPED,
            "error": TestStatus.ERROR,
        }
        return mapping.get(outcome, TestStatus.ERROR)

    def _extract_coverage(self, stdout: str) -> Optional[float]:
        """stdout에서 커버리지 비율을 추출합니다"""
        try:
            # "TOTAL  ... 87%" 형태에서 숫자 추출
            for line in stdout.split("\n"):
                if "TOTAL" in line and "%" in line:
                    # 마지막 % 앞 숫자 추출
                    parts = line.split()
                    for part in reversed(parts):
                        if "%" in part:
                            return float(part.replace("%", ""))
        except Exception as e:
            self.logger.warning(f"Failed to extract coverage: {e}")

        return None

    def setup_test_environment(
        self,
        env_vars: Optional[Dict[str, str]] = None,
        fixtures_dir: Optional[str] = None,
    ):
        """
        테스트 환경을 설정합니다.

        Args:
            env_vars: 환경 변수 설정
            fixtures_dir: 테스트 fixture 디렉토리
        """
        self.logger.info("Setting up test environment")

        # 환경 변수 설정
        if env_vars:
            for key, value in env_vars.items():
                os.environ[key] = value
                self.logger.debug(f"Set env var: {key}")

        # Fixture 디렉토리 생성
        if fixtures_dir:
            os.makedirs(fixtures_dir, exist_ok=True)
            self.logger.info(f"Created fixtures directory: {fixtures_dir}")

    def generate_test_report_html(self, report: TestRunReport, output_file: str):
        """
        HTML 형식의 테스트 리포트를 생성합니다.

        Args:
            report: 테스트 실행 리포트
            output_file: 출력 파일 경로
        """
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Report - {report.run_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .skipped {{ color: orange; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>Integration Test Report</h1>

    <div class="summary">
        <h2>Summary</h2>
        <div class="metric"><strong>Run ID:</strong> {report.run_id}</div>
        <div class="metric"><strong>Duration:</strong> {report.duration_seconds:.2f}s</div>
        <div class="metric"><strong>Total Tests:</strong> {report.total_tests}</div>
        <div class="metric passed"><strong>Passed:</strong> {report.passed}</div>
        <div class="metric failed"><strong>Failed:</strong> {report.failed}</div>
        <div class="metric skipped"><strong>Skipped:</strong> {report.skipped}</div>
        {f'<div class="metric"><strong>Coverage:</strong> {report.coverage_percent:.1f}%</div>' if report.coverage_percent else ''}
    </div>

    <h2>Test Results</h2>
    <table>
        <tr>
            <th>Test Name</th>
            <th>Status</th>
            <th>Duration (s)</th>
            <th>Error</th>
        </tr>
"""

        for test in report.test_results:
            status_class = test.status.value
            error_msg = test.error_message or "-"
            html_content += f"""
        <tr>
            <td>{test.test_name}</td>
            <td class="{status_class}">{test.status.value.upper()}</td>
            <td>{test.duration_seconds:.3f}</td>
            <td>{error_msg}</td>
        </tr>
"""

        html_content += """
    </table>
</body>
</html>
"""

        with open(output_file, "w") as f:
            f.write(html_content)

        self.logger.info(f"HTML report generated: {output_file}")


class TestDataManager:
    """
    테스트 데이터 관리자

    테스트용 데이터를 생성하고 정리합니다.
    """

    def __init__(self, data_dir: str = "tests/fixtures"):
        self.data_dir = data_dir
        self.logger = logger
        os.makedirs(data_dir, exist_ok=True)

    def create_test_db(self, db_name: str = "test.db") -> str:
        """테스트용 SQLite 데이터베이스를 생성합니다"""
        db_path = os.path.join(self.data_dir, db_name)

        # 기존 DB 삭제
        if os.path.exists(db_path):
            os.remove(db_path)

        self.logger.info(f"Created test database: {db_path}")
        return db_path

    def load_fixtures(self, fixture_file: str) -> Dict[str, Any]:
        """Fixture 파일을 로드합니다"""
        fixture_path = os.path.join(self.data_dir, fixture_file)

        if not os.path.exists(fixture_path):
            self.logger.warning(f"Fixture file not found: {fixture_path}")
            return {}

        with open(fixture_path, "r") as f:
            if fixture_file.endswith(".json"):
                return json.load(f)
            elif fixture_file.endswith(".yaml") or fixture_file.endswith(".yml"):
                import yaml
                return yaml.safe_load(f)

        return {}

    def cleanup(self):
        """테스트 데이터를 정리합니다"""
        import shutil
        if os.path.exists(self.data_dir):
            shutil.rmtree(self.data_dir)
            os.makedirs(self.data_dir)
        self.logger.info("Test data cleaned up")
