"""
CAAS Code Validator

생성된 코드의 실행 가능성을 검증합니다.
"""

import ast
import re
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

from app.utils.logger import get_logger

logger = get_logger("codegen.validator")


class ValidationSeverity(str, Enum):
    """검증 오류 심각도"""
    ERROR = "error"      # 실행 불가
    WARNING = "warning"  # 실행 가능하지만 문제 있음
    INFO = "info"        # 개선 권장


@dataclass
class ValidationIssue:
    """검증 이슈"""
    severity: ValidationSeverity
    category: str  # syntax, import, dependency, security, style
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    code: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """검증 결과"""
    valid: bool
    issues: List[ValidationIssue]
    metrics: Dict[str, Any]  # LOC, complexity, etc.

    @property
    def errors(self) -> List[ValidationIssue]:
        """에러만 반환"""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """경고만 반환"""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def infos(self) -> List[ValidationIssue]:
        """정보만 반환"""
        return [i for i in self.issues if i.severity == ValidationSeverity.INFO]


class CodeValidator:
    """
    코드 검증기

    생성된 코드의 구문, 의존성, 보안, 스타일을 검증합니다.
    """

    # 위험한 함수/모듈 (보안 검증)
    DANGEROUS_PATTERNS = {
        "eval": "동적 코드 실행 (eval) 사용",
        "exec": "동적 코드 실행 (exec) 사용",
        "compile": "동적 코드 컴파일 사용",
        "__import__": "동적 import 사용",
        "os.system": "시스템 명령 실행",
        "subprocess.call": "서브프로세스 실행 (shell=True 주의)",
        "pickle.loads": "안전하지 않은 역직렬화",
    }

    # 하드코딩된 비밀 패턴
    SECRET_PATTERNS = {
        r"api[_-]?key\s*=\s*['\"][^'\"]{10,}['\"]": "API 키 하드코딩",
        r"password\s*=\s*['\"][^'\"]{3,}['\"]": "비밀번호 하드코딩",
        r"secret\s*=\s*['\"][^'\"]{10,}['\"]": "비밀 값 하드코딩",
        r"token\s*=\s*['\"][^'\"]{10,}['\"]": "토큰 하드코딩",
        r"sk-[a-zA-Z0-9]{32,}": "OpenAI API 키 패턴",
    }

    def __init__(self):
        self.issues: List[ValidationIssue] = []

    def validate_project(
        self,
        files: Dict[str, str],
        check_imports: bool = True,
        check_security: bool = True,
        check_style: bool = False,
    ) -> ValidationResult:
        """
        프로젝트 전체를 검증합니다.

        Args:
            files: 파일명 -> 내용 매핑
            check_imports: import 검증 여부
            check_security: 보안 검증 여부
            check_style: 스타일 검증 여부

        Returns:
            ValidationResult: 검증 결과
        """
        self.issues = []
        metrics = {}

        logger.info(f"코드 검증 시작: {len(files)}개 파일")

        # Python 파일만 검증
        python_files = {
            name: content
            for name, content in files.items()
            if name.endswith(".py")
        }

        # 1. 구문 검증
        self._validate_syntax(python_files)

        # 2. Import 검증
        if check_imports:
            self._validate_imports(python_files)

        # 3. 보안 검증
        if check_security:
            self._validate_security(python_files)

        # 4. 스타일 검증 (선택적)
        if check_style:
            self._validate_style(python_files)

        # 5. 의존성 검증
        if "requirements.txt" in files:
            self._validate_dependencies(files["requirements.txt"])

        # 6. 버전 호환성 검증 (P1-5)
        self._validate_version_compatibility()

        # 7. 메트릭 계산
        metrics = self._calculate_metrics(python_files)

        # 결과 판정 (에러가 없으면 valid)
        valid = len(self.errors) == 0

        logger.info(
            f"검증 완료: valid={valid}, "
            f"errors={len(self.errors)}, "
            f"warnings={len(self.warnings)}, "
            f"infos={len(self.infos)}"
        )

        return ValidationResult(
            valid=valid,
            issues=self.issues,
            metrics=metrics,
        )

    def _validate_syntax(self, files: Dict[str, str]) -> None:
        """구문 검증 (AST 파싱)"""
        for filename, content in files.items():
            try:
                ast.parse(content)
                logger.debug(f"✅ 구문 정상: {filename}")
            except SyntaxError as e:
                self.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="syntax",
                        message=f"구문 오류: {e.msg}",
                        file=filename,
                        line=e.lineno,
                        code=e.text.strip() if e.text else None,
                        suggestion="Python 구문을 확인하세요. 괄호, 들여쓰기, 콜론 등을 점검하세요.",
                    )
                )
                logger.error(f"❌ 구문 오류: {filename}:{e.lineno} - {e.msg}")

    def _validate_imports(self, files: Dict[str, str]) -> None:
        """Import 검증 (import 가능 여부)"""
        all_imports = set()
        from_imports = []  # (module, name) 튜플 저장

        # 로컬 모듈 (같은 프로젝트 내 파일) 추출
        local_modules = {
            Path(filename).stem  # 'agents.py' -> 'agents'
            for filename in files.keys()
            if filename.endswith('.py')
        }

        # 모든 파일에서 import 추출
        for filename, content in files.items():
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            all_imports.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module = node.module.split(".")[0]
                            all_imports.add(module)
                            # from X import Y 형태 저장
                            for alias in node.names:
                                from_imports.append((node.module, alias.name, filename))
            except SyntaxError:
                # 구문 오류는 이미 _validate_syntax에서 처리
                continue

        # 표준 라이브러리 제외
        stdlib_modules = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else {
            'os', 'sys', 'pathlib', 'json', 'datetime', 're', 'typing',
            'collections', 'itertools', 'functools', 'io', 'subprocess',
        }

        # 로컬 모듈 제외 (같은 프로젝트 내 파일은 검증하지 않음)
        external_imports = all_imports - stdlib_modules - local_modules

        # 필수 의존성 정의 (CrewAI 프로젝트 실행에 필수)
        critical_dependencies = {
            "crewai",
            "crewai_tools",
            "langchain",
            "langchain_core",
            "langchain_openai",
            "langchain_anthropic",
        }

        for module in external_imports:
            # 최상위 모듈명 추출 (langchain_openai -> langchain_openai)
            top_level_module = module.split(".")[0]
            is_critical = top_level_module in critical_dependencies

            try:
                __import__(module)
                logger.debug(f"✅ Import 가능: {module}")
            except ImportError:
                # 필수 의존성은 ERROR, 나머지는 WARNING
                severity = ValidationSeverity.ERROR if is_critical else ValidationSeverity.WARNING

                self.issues.append(
                    ValidationIssue(
                        severity=severity,
                        category="import",
                        message=f"{'[필수] ' if is_critical else ''}모듈 '{module}'을 import할 수 없습니다",
                        suggestion=f"pip install {module} 또는 requirements.txt에 추가하세요.",
                    )
                )

                if is_critical:
                    logger.error(f"❌ [필수 의존성] Import 불가: {module}")
                else:
                    logger.warning(f"⚠️ Import 불가: {module}")

        # from X import Y 형태 세밀 검증
        for module, name, filename in from_imports:
            # 로컬 모듈이면 건너뛰기
            if module.split(".")[0] in local_modules:
                continue

            # crewai_tools의 알려진 문제 체크
            if module == "crewai_tools":
                invalid_tools = ["FileWriteTool", "DirectoryWriteTool"]
                if name in invalid_tools:
                    self.issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category="import",
                            message=f"'{name}'은 crewai_tools에 존재하지 않습니다",
                            file=filename,
                            suggestion=f"{name}는 CrewAI에서 제공하지 않습니다. CodeInterpreterTool 또는 다른 도구를 사용하세요.",
                        )
                    )
                    logger.error(f"❌ Invalid import: from {module} import {name}")

            # 실제 import 시도 (가능한 경우)
            try:
                mod = __import__(module, fromlist=[name])
                if not hasattr(mod, name):
                    self.issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category="import",
                            message=f"'{module}'에 '{name}'이 존재하지 않습니다",
                            file=filename,
                            suggestion=f"모듈 '{module}'의 API 문서를 확인하세요.",
                        )
                    )
                    logger.error(f"❌ Import 실패: from {module} import {name}")
            except (ImportError, AttributeError):
                # 모듈 자체를 import할 수 없으면 이미 위에서 경고
                pass

    def _validate_security(self, files: Dict[str, str]) -> None:
        """보안 검증"""
        for filename, content in files.items():
            # 1. 위험한 함수 사용 검증 (함수 호출 패턴만 감지)
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                # 코멘트 제외
                if line.strip().startswith("#"):
                    continue

                for pattern, description in self.DANGEROUS_PATTERNS.items():
                    # 함수 호출 패턴 감지: pattern( 형태만 매칭
                    # 예: exec( 는 매칭, async_execution= 는 매칭 안됨
                    if "." not in pattern:  # 'eval', 'exec' 등 단순 함수명
                        # \b는 단어 경계, \s*는 공백 허용, \(는 여는 괄호
                        func_pattern = rf'\b{re.escape(pattern)}\s*\('
                        if re.search(func_pattern, line):
                            self.issues.append(
                                ValidationIssue(
                                    severity=ValidationSeverity.WARNING,
                                    category="security",
                                    message=f"위험한 함수 사용: {description}",
                                    file=filename,
                                    line=i,
                                    code=line.strip(),
                                    suggestion="안전한 대안을 사용하거나 입력 검증을 추가하세요.",
                                )
                            )
                    else:  # 'os.system', 'subprocess.call' 등 모듈.함수
                        # 모듈명과 함수명이 모두 있는 경우
                        if pattern in line:
                            self.issues.append(
                                ValidationIssue(
                                    severity=ValidationSeverity.WARNING,
                                    category="security",
                                    message=f"위험한 함수 사용: {description}",
                                    file=filename,
                                    line=i,
                                    code=line.strip(),
                                    suggestion="안전한 대안을 사용하거나 입력 검증을 추가하세요.",
                                )
                            )

            # 2. 하드코딩된 비밀 검증
            for pattern, description in self.SECRET_PATTERNS.items():
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count("\n") + 1
                    self.issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category="security",
                            message=f"보안 위험: {description}",
                            file=filename,
                            line=line_num,
                            suggestion="환경 변수(.env)를 사용하세요: os.getenv('API_KEY')",
                        )
                    )

    def _validate_style(self, files: Dict[str, str]) -> None:
        """스타일 검증 (간단한 PEP 8 체크)"""
        for filename, content in files.items():
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                # 1. 라인 길이 (79자 제한)
                if len(line) > 79 and not line.strip().startswith("#"):
                    self.issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.INFO,
                            category="style",
                            message=f"라인이 너무 깁니다 ({len(line)}자 > 79자)",
                            file=filename,
                            line=i,
                            suggestion="PEP 8 권장: 라인을 79자 이하로 유지하세요.",
                        )
                    )

                # 2. 탭 vs 스페이스
                if "\t" in line:
                    self.issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.INFO,
                            category="style",
                            message="탭 문자 사용 (스페이스 권장)",
                            file=filename,
                            line=i,
                            suggestion="PEP 8 권장: 들여쓰기는 스페이스 4개를 사용하세요.",
                        )
                    )

    def _validate_dependencies(self, requirements_content: str) -> None:
        """의존성 검증 (requirements.txt)"""
        lines = requirements_content.strip().split("\n")
        dependencies = [
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]

        for dep in dependencies:
            # 버전 정보 제거 (crewai==0.1.0 -> crewai)
            package_name = re.split(r"[=<>!]", dep)[0].strip()

            # pip show로 설치 여부 확인
            try:
                result = subprocess.run(
                    ["pip", "show", package_name],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    self.issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category="dependency",
                            message=f"패키지 '{package_name}'가 설치되지 않았습니다",
                            file="requirements.txt",
                            suggestion=f"pip install {dep}",
                        )
                    )
                else:
                    logger.debug(f"✅ 패키지 설치됨: {package_name}")
            except subprocess.TimeoutExpired:
                logger.warning(f"⚠️ pip show 타임아웃: {package_name}")
            except FileNotFoundError:
                logger.warning("⚠️ pip 명령을 찾을 수 없습니다")
                break

    def _validate_version_compatibility(self) -> None:
        """
        의존성 버전 호환성 검증 (P1-5)

        CrewAI, LangChain 등 핵심 패키지의 버전이 호환되는지 검증합니다.
        """
        try:
            from importlib import metadata
        except ImportError:
            # Python < 3.8: importlib_metadata 사용
            try:
                import importlib_metadata as metadata
            except ImportError:
                logger.warning("⚠️ importlib.metadata를 사용할 수 없습니다. 버전 검증을 건너뜁니다.")
                return

        # 버전 호환성 매트릭스 (Python 3.11 기준)
        COMPATIBILITY_MATRIX = {
            "crewai": {
                "min": "1.7.0",
                "max": "2.0.0",
                "compatible_with": {
                    "langchain": ("0.3.0", "0.5.0"),
                    "langchain-core": ("0.3.0", "1.0.0"),
                },
            },
            "langchain": {
                "min": "0.3.0",
                "max": "0.5.0",
                "compatible_with": {
                    "langchain-core": ("0.3.0", "1.0.0"),
                    "langchain-openai": ("0.2.0", "1.0.0"),
                },
            },
        }

        def parse_version(version_str: str) -> Tuple[int, ...]:
            """버전 문자열을 튜플로 변환 (1.2.3 -> (1, 2, 3))"""
            try:
                return tuple(int(x) for x in version_str.split(".")[:3])
            except (ValueError, AttributeError):
                return (0, 0, 0)

        def version_in_range(version: str, min_ver: str, max_ver: str) -> bool:
            """버전이 범위 내에 있는지 확인"""
            v = parse_version(version)
            v_min = parse_version(min_ver)
            v_max = parse_version(max_ver)
            return v_min <= v < v_max

        # 각 패키지 버전 확인
        for package, constraints in COMPATIBILITY_MATRIX.items():
            try:
                version = metadata.version(package)
                logger.debug(f"✅ {package} 버전: {version}")

                # 최소/최대 버전 검증
                min_ver = constraints.get("min", "0.0.0")
                max_ver = constraints.get("max", "999.0.0")

                if not version_in_range(version, min_ver, max_ver):
                    self.issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category="dependency",
                            message=(
                                f"'{package}' 버전 불일치: {version} "
                                f"(권장: {min_ver} ~ {max_ver} 미만)"
                            ),
                            suggestion=(
                                f"pip install '{package}>={min_ver},<{max_ver}' "
                                f"로 적절한 버전을 설치하세요."
                            ),
                        )
                    )
                    logger.warning(
                        f"⚠️ {package} 버전 불일치: {version} "
                        f"(권장: {min_ver} ~ {max_ver})"
                    )

                # 의존 패키지 호환성 검증
                compatible_with = constraints.get("compatible_with", {})
                for dep_package, (dep_min, dep_max) in compatible_with.items():
                    try:
                        dep_version = metadata.version(dep_package)

                        if not version_in_range(dep_version, dep_min, dep_max):
                            self.issues.append(
                                ValidationIssue(
                                    severity=ValidationSeverity.WARNING,
                                    category="dependency",
                                    message=(
                                        f"'{package} {version}'는 "
                                        f"'{dep_package} {dep_version}'와 호환되지 않을 수 있습니다 "
                                        f"(권장: {dep_min} ~ {dep_max} 미만)"
                                    ),
                                    suggestion=(
                                        f"'{dep_package}>={dep_min},<{dep_max}'로 "
                                        f"버전을 조정하세요."
                                    ),
                                )
                            )
                            logger.warning(
                                f"⚠️ 호환성 경고: {package} {version} <-> "
                                f"{dep_package} {dep_version}"
                            )
                    except Exception:
                        # 의존 패키지가 설치되지 않은 경우는 _validate_imports에서 처리
                        pass

            except Exception as e:
                # 패키지가 설치되지 않은 경우나 기타 오류
                if "No module named" not in str(e):
                    logger.error(f"❌ {package} 버전 확인 실패: {e}")
                else:
                    logger.debug(f"⏭️ {package}가 설치되지 않음 (버전 검증 건너뜀)")
                pass

    def _calculate_metrics(self, files: Dict[str, str]) -> Dict[str, Any]:
        """코드 메트릭 계산"""
        total_lines = 0
        total_code_lines = 0
        total_comment_lines = 0
        total_blank_lines = 0
        total_functions = 0
        total_classes = 0

        for filename, content in files.items():
            lines = content.split("\n")
            total_lines += len(lines)

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    total_blank_lines += 1
                elif stripped.startswith("#"):
                    total_comment_lines += 1
                else:
                    total_code_lines += 1

            # AST로 함수/클래스 수 계산
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        total_functions += 1
                    elif isinstance(node, ast.ClassDef):
                        total_classes += 1
            except SyntaxError:
                continue

        return {
            "total_lines": total_lines,
            "code_lines": total_code_lines,
            "comment_lines": total_comment_lines,
            "blank_lines": total_blank_lines,
            "functions": total_functions,
            "classes": total_classes,
            "files": len(files),
            "comment_ratio": (
                total_comment_lines / total_code_lines * 100
                if total_code_lines > 0
                else 0
            ),
        }

    @property
    def errors(self) -> List[ValidationIssue]:
        """에러만 반환"""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """경고만 반환"""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def infos(self) -> List[ValidationIssue]:
        """정보만 반환"""
        return [i for i in self.issues if i.severity == ValidationSeverity.INFO]
