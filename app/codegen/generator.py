"""
CAAS Code Generator

Jinja2 템플릿을 사용하여 CrewAI 코드를 생성합니다.
"""

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional
import subprocess

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel

from app.utils.logger import get_logger, LoggerMixin
from app.utils.config import get_settings, PROJECT_ROOT
from app.utils.security import (
    sanitize_relative_path,
    validate_project_name,
    PathTraversalError,
)
from app.core.sdd import CrewAISpec
from app.core.factory import CrewAssembler
from app.codegen.validator import CodeValidator, ValidationResult
from app.codegen.api_key_validator import ApiKeyValidator, validate_and_warn

logger = get_logger("codegen.generator")


class GeneratedProject(BaseModel):
    """생성된 프로젝트"""
    name: str
    output_dir: Path
    files: Dict[str, str]  # filename -> content
    validation: Optional[ValidationResult] = None  # 코드 검증 결과

    class Config:
        arbitrary_types_allowed = True


class CodeGenerator(LoggerMixin):
    """
    코드 생성기
    
    CrewAI 스펙을 기반으로 실행 가능한 Python 프로젝트를 생성합니다.
    """
    
    def __init__(self, template_dir: Optional[Path] = None):
        self.settings = get_settings()
        self.template_dir = template_dir or PROJECT_ROOT / "data" / "templates"
        self.crew_assembler = CrewAssembler()
        self.validator = CodeValidator()

        # 템플릿 검증 (P0-3: 템플릿 존재 확인)
        self._validate_templates()

        # Jinja2 환경 설정
        if self.template_dir.exists():
            self.env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            self.env = None

    def _validate_templates(self) -> None:
        """
        필수 템플릿 파일 존재 확인

        CrewAssembler와 Factory 클래스에서 사용하는 템플릿이 모두 존재하는지 검증합니다.

        Raises:
            FileNotFoundError: 필수 템플릿 파일이 없는 경우
        """
        # 템플릿 디렉토리 존재 확인
        if not self.template_dir.exists():
            raise FileNotFoundError(
                f"템플릿 디렉토리를 찾을 수 없습니다: {self.template_dir}\n"
                f"템플릿 디렉토리를 생성하거나 올바른 경로를 지정하세요."
            )

        # CrewAssembler와 Factory에서 사용하는 필수 템플릿 목록
        required_templates = [
            "main_with_error_handling.py.j2",      # crew_assembler.py:251
            "streamlit_main.py.j2",                # crew_assembler.py:283
            "agents_with_error_handling.py.j2",    # agent_factory.py:182
            "tasks_with_error_handling.py.j2",     # task_factory.py:136
        ]

        # 누락된 템플릿 확인
        missing_templates = []
        for template_name in required_templates:
            template_path = self.template_dir / template_name
            if not template_path.exists():
                missing_templates.append(template_name)

        # 누락된 템플릿이 있으면 에러
        if missing_templates:
            missing_list = "\n  - ".join(missing_templates)
            raise FileNotFoundError(
                f"필수 템플릿 파일이 누락되었습니다:\n  - {missing_list}\n\n"
                f"템플릿 디렉토리: {self.template_dir}\n"
                f"누락된 파일을 추가하거나 템플릿 디렉토리를 확인하세요."
            )

        self.logger.debug(f"템플릿 검증 완료: {len(required_templates)}개 필수 템플릿 확인")

    def generate_from_spec(
        self,
        spec: CrewAISpec,
        output_dir: Optional[Path] = None,
        validate_code: bool = True,
        include_tests: bool = False,
        check_api_keys: bool = True,
    ) -> GeneratedProject:
        """
        CrewAI 스펙에서 프로젝트를 생성합니다.

        Args:
            spec: CrewAI 스펙
            output_dir: 출력 디렉토리
            validate_code: 코드 검증 여부 (기본: True)
            include_tests: 테스트 파일 포함 여부 (기본: False)
            check_api_keys: API 키 확인 여부 (기본: True)

        Returns:
            GeneratedProject: 생성된 프로젝트

        Raises:
            ValueError: 유효하지 않은 프로젝트 이름 또는 API 키 누락
            PathTraversalError: 경로 탐색 시도 감지
        """
        self.logger.info(f"코드 생성 시작: {spec.project.name}")

        # API 키 검증 (선택적)
        if check_api_keys:
            all_tools = []
            for agent in spec.agents:
                all_tools.extend(agent.tools)

            if all_tools:
                self.logger.info(f"API 키 검증 중: {len(set(all_tools))}개 도구")
                api_key_result = validate_and_warn(list(set(all_tools)), raise_on_missing=False)

                if api_key_result.has_missing_required:
                    self.logger.warning(
                        f"⚠️  {len(api_key_result.missing_required)}개의 필수 API 키가 설정되지 않았습니다. "
                        f"생성된 프로젝트를 실행하기 전에 .env 파일에 API 키를 추가하세요."
                    )

                if api_key_result.has_warnings:
                    self.logger.info(
                        f"💡 {len(api_key_result.missing_optional)}개의 선택적 API 키가 설정되지 않았습니다."
                    )

        # SECURITY: 프로젝트 이름 검증
        try:
            validated_name = validate_project_name(spec.project.name)
        except ValueError as e:
            self.logger.error(f"유효하지 않은 프로젝트 이름: {e}")
            raise ValueError(f"프로젝트 이름이 유효하지 않습니다: {e}")

        # 출력 디렉토리 설정
        if output_dir is None:
            base_output = Path(self.settings.app.output_dir).resolve()
            # SECURITY: 검증된 이름을 직접 사용 (이미 안전함)
            output_dir = base_output / validated_name
        else:
            # SECURITY: 제공된 output_dir 검증
            base_output = Path(self.settings.app.output_dir).resolve()
            output_dir = sanitize_relative_path(
                str(output_dir),
                base_dir=base_output,
            )

        # CrewAssembler를 사용하여 코드 생성
        files = self.crew_assembler.assemble_full_project(spec, include_tests=include_tests)

        # LLM 사용 파일에 dotenv 자동 주입
        files = self._auto_inject_dotenv(files)

        # 생성 직후 즉시 구문 검증 및 자동 수정
        files = self._validate_and_fix_syntax(files)

        # 코드 검증
        validation_result = None
        if validate_code:
            self.logger.info("생성된 코드 검증 중...")
            validation_result = self.validator.validate_project(
                files=files,
                check_imports=True,
                check_security=True,
                check_style=False,  # PEP 8 스타일은 선택적
            )

            self.logger.info(
                f"검증 완료: valid={validation_result.valid}, "
                f"errors={len(validation_result.errors)}, "
                f"warnings={len(validation_result.warnings)}"
            )

        return GeneratedProject(
            name=validated_name,
            output_dir=output_dir,
            files=files,
            validation=validation_result,
        )
    
    def save_project(self, project: GeneratedProject) -> Path:
        """
        생성된 프로젝트를 디스크에 저장합니다.

        Args:
            project: 생성된 프로젝트

        Returns:
            Path: 프로젝트 디렉토리 경로

        Raises:
            PathTraversalError: 경로 탐색 시도 감지
        """
        output_dir = project.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        for filename, content in project.files.items():
            # SECURITY: 각 파일명 새니타이즈 및 검증
            try:
                safe_path = sanitize_relative_path(
                    filename,
                    base_dir=output_dir,
                    max_depth=3,  # src/utils/helpers.py 구조 허용
                )
            except (ValueError, PathTraversalError) as e:
                self.logger.error(f"유효하지 않은 파일명 '{filename}': {e}")
                raise PathTraversalError(f"파일 이름이 유효하지 않습니다: {filename}")

            # 부모 디렉토리 생성 (이제 안전함)
            safe_path.parent.mkdir(parents=True, exist_ok=True)

            # 파일 작성
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.logger.debug(f"파일 저장: {safe_path}")

        self.logger.info(f"프로젝트 저장 완료: {output_dir}")
        return output_dir
    
    def format_code(self, code: str) -> str:
        """
        Python 코드를 포맷팅합니다 (Black 사용).
        
        Args:
            code: Python 코드
        
        Returns:
            str: 포맷팅된 코드
        """
        try:
            import black
            
            mode = black.Mode(
                target_versions={black.TargetVersion.PY311},
                line_length=100,
            )
            return black.format_str(code, mode=mode)
        except Exception as e:
            self.logger.warning(f"코드 포맷팅 실패: {e}")
            return code
    
    def validate_syntax(self, code: str) -> bool:
        """
        Python 코드 문법을 검증합니다.

        Args:
            code: Python 코드

        Returns:
            bool: 유효 여부
        """
        try:
            compile(code, "<string>", "exec")
            return True
        except SyntaxError as e:
            self.logger.error(f"문법 오류: {e}")
            return False

    def _validate_and_fix_syntax(self, files: Dict[str, str]) -> Dict[str, str]:
        """
        생성된 코드의 구문을 즉시 검증하고 자동으로 수정합니다.

        Args:
            files: 파일명 -> 내용 매핑

        Returns:
            Dict[str, str]: 수정된 파일 매핑

        Raises:
            ValueError: 자동 수정이 불가능한 구문 오류가 있는 경우
        """
        fixed_files = {}

        for filename, content in files.items():
            if not filename.endswith('.py'):
                # Python 파일이 아니면 그대로 유지
                fixed_files[filename] = content
                continue

            try:
                # 구문 검증
                ast.parse(content)
                self.logger.debug(f"✅ 구문 검증 통과: {filename}")
                fixed_files[filename] = content

            except SyntaxError as e:
                self.logger.warning(
                    f"⚠️ 생성된 코드에 구문 오류 발견: {filename}:{e.lineno} - {e.msg}"
                )

                # 자동 포맷팅으로 수정 시도
                try:
                    self.logger.info(f"🔧 자동 포맷팅 시도: {filename}")
                    formatted = self.format_code(content)

                    # 포맷팅 후 재검증
                    ast.parse(formatted)
                    self.logger.info(f"✅ 자동 포맷팅으로 수정 완료: {filename}")
                    fixed_files[filename] = formatted

                except SyntaxError as e2:
                    # 포맷팅으로도 수정 불가
                    error_context = ""
                    if e2.text:
                        error_context = f"\n코드: {e2.text.strip()}"

                    self.logger.error(
                        f"❌ 자동 수정 실패: {filename}:{e2.lineno}\n"
                        f"오류: {e2.msg}{error_context}"
                    )

                    raise ValueError(
                        f"생성된 코드에 수정 불가능한 구문 오류가 있습니다.\n"
                        f"파일: {filename}\n"
                        f"줄 번호: {e2.lineno}\n"
                        f"오류: {e2.msg}{error_context}\n\n"
                        f"이는 코드 생성 로직의 버그일 수 있습니다. "
                        f"개발팀에 보고해주세요."
                    )

                except Exception as fmt_error:
                    # 포맷팅 자체가 실패
                    self.logger.error(f"❌ 포맷팅 실패: {filename} - {fmt_error}")

                    # 원본 오류 정보로 예외 발생
                    error_context = ""
                    if e.text:
                        error_context = f"\n코드: {e.text.strip()}"

                    raise ValueError(
                        f"생성된 코드에 구문 오류가 있습니다.\n"
                        f"파일: {filename}\n"
                        f"줄 번호: {e.lineno}\n"
                        f"오류: {e.msg}{error_context}\n\n"
                        f"자동 수정을 시도했으나 실패했습니다."
                    )

        return fixed_files

    def _auto_inject_dotenv(self, files: Dict[str, str]) -> Dict[str, str]:
        """
        LLM API 키를 사용하는 Python 파일에 load_dotenv() 자동 추가

        CrewAI 프로젝트는 OpenAI API 키 등이 필요하므로,
        .env 파일을 로드하는 코드가 없으면 런타임 오류가 발생합니다.
        이 메서드는 LLM 관련 import가 있는 파일을 감지하여
        자동으로 load_dotenv()를 추가합니다.

        Args:
            files: 파일명 -> 내용 매핑

        Returns:
            Dict[str, str]: dotenv가 추가된 파일 매핑
        """
        updated_files = {}

        for filename, content in files.items():
            if not filename.endswith('.py'):
                updated_files[filename] = content
                continue

            # LLM 관련 import 패턴 감지
            llm_patterns = [
                'ChatOpenAI',
                'ChatAnthropic',
                'Ollama',
                'from langchain_openai',
                'from langchain_anthropic',
                'from langchain.llms',
                'from langchain.chat_models',
            ]

            needs_dotenv = any(pattern in content for pattern in llm_patterns)
            has_dotenv = 'load_dotenv' in content

            if needs_dotenv and not has_dotenv:
                self.logger.info(f"🔧 Auto-injecting load_dotenv() to {filename}")

                # AST를 사용하여 안전하게 추가
                try:
                    tree = ast.parse(content)

                    # import 구간 찾기
                    last_import_idx = -1
                    for i, node in enumerate(tree.body):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            last_import_idx = i
                        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                            # Docstring은 건너뛰기
                            continue
                        else:
                            break

                    # dotenv import와 호출 노드 생성
                    dotenv_import = ast.ImportFrom(
                        module='dotenv',
                        names=[ast.alias(name='load_dotenv', asname=None)],
                        level=0
                    )
                    dotenv_call = ast.Expr(
                        value=ast.Call(
                            func=ast.Name(id='load_dotenv', ctx=ast.Load()),
                            args=[],
                            keywords=[]
                        )
                    )

                    # import 다음에 삽입
                    insert_pos = last_import_idx + 1
                    tree.body.insert(insert_pos, dotenv_import)
                    tree.body.insert(insert_pos + 1, dotenv_call)

                    # AST를 코드로 변환
                    ast.fix_missing_locations(tree)
                    new_content = ast.unparse(tree)
                    updated_files[filename] = new_content

                    self.logger.debug(f"✅ Successfully injected load_dotenv() to {filename}")

                except SyntaxError as e:
                    self.logger.warning(
                        f"⚠️ Failed to inject load_dotenv() to {filename} due to syntax error: {e}. "
                        f"Using original content."
                    )
                    updated_files[filename] = content

            else:
                updated_files[filename] = content

        return updated_files

    def generate_and_save(
        self,
        spec: CrewAISpec,
        output_dir: Optional[Path] = None,
        format_code: bool = True,
    ) -> Path:
        """
        스펙에서 코드를 생성하고 저장합니다.

        Args:
            spec: CrewAI 스펙
            output_dir: 출력 디렉토리
            format_code: 코드 포맷팅 여부 (기본: True, 권장)

        Returns:
            Path: 프로젝트 디렉토리
        """
        project = self.generate_from_spec(spec, output_dir)

        # 코드 포맷팅 (구문 오류 방지를 위해 강력히 권장)
        if format_code:
            self.logger.info("코드 포맷팅 적용 중...")
            formatted_files = {}
            format_success_count = 0
            format_skip_count = 0

            for filename, content in project.files.items():
                if filename.endswith(".py"):
                    try:
                        formatted = self.format_code(content)
                        formatted_files[filename] = formatted
                        format_success_count += 1
                        self.logger.debug(f"✅ 포맷팅 완료: {filename}")
                    except Exception as e:
                        self.logger.warning(f"⚠️ 포맷팅 실패 (원본 사용): {filename} - {e}")
                        formatted_files[filename] = content
                        format_skip_count += 1
                else:
                    formatted_files[filename] = content

            project.files = formatted_files
            self.logger.info(
                f"포맷팅 완료: {format_success_count}개 성공, {format_skip_count}개 스킵"
            )
        else:
            self.logger.warning(
                "⚠️ 코드 포맷팅이 비활성화되었습니다. "
                "구문 오류가 발생할 수 있으므로 format_code=True 사용을 권장합니다."
            )

        return self.save_project(project)


class TemplateCodeGenerator(LoggerMixin):
    """
    Jinja2 템플릿 기반 코드 생성기
    
    사전 정의된 템플릿을 사용하여 코드를 생성합니다.
    """
    
    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir or PROJECT_ROOT / "data" / "templates"
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    
    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any],
    ) -> str:
        """
        템플릿을 렌더링합니다.
        
        Args:
            template_name: 템플릿 파일명
            context: 컨텍스트 변수
        
        Returns:
            str: 렌더링된 코드
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            self.logger.error(f"템플릿 렌더링 실패: {e}")
            raise
    
    def list_templates(self) -> List[str]:
        """사용 가능한 템플릿 목록을 반환합니다."""
        return self.env.list_templates()
