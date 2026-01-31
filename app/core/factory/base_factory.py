"""
CAAS Base Factory

팩토리 클래스들의 공통 기능을 제공하는 기본 클래스
"""

from typing import Any, Dict, Optional, TypeVar, Generic
from pathlib import Path
from abc import ABC, abstractmethod

from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader, Template

from app.utils.logger import get_logger, LoggerMixin
from app.utils.config import get_settings, PROJECT_ROOT

# Type variables for generic factory
SpecModel = TypeVar('SpecModel', bound=BaseModel)
Definition = TypeVar('Definition', bound=BaseModel)

logger = get_logger("factory.base")


class BaseFactory(LoggerMixin, ABC, Generic[SpecModel, Definition]):
    """
    팩토리 기본 클래스

    공통 기능:
    - Jinja2 템플릿 환경 초기화
    - 설정 관리
    - 로깅
    - 템플릿 렌더링

    하위 클래스는 다음 메서드를 구현해야 합니다:
    - create_definition(spec: SpecModel) -> Definition
    - create_code(definition: Definition) -> str
    """

    def __init__(self, template_dir: Optional[Path] = None):
        """
        팩토리 초기화

        Args:
            template_dir: 템플릿 디렉토리 경로 (기본값: PROJECT_ROOT/data/templates)
        """
        self.settings = get_settings()

        # Jinja2 템플릿 환경 초기화
        if template_dir is None:
            template_dir = PROJECT_ROOT / "data" / "templates"

        self.template_dir = template_dir
        self.template_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        self.log_info(f"Factory initialized with template_dir={template_dir}")

    def load_template(self, template_name: str) -> Template:
        """
        템플릿 로드

        Args:
            template_name: 템플릿 파일명

        Returns:
            Jinja2 Template 객체

        Raises:
            jinja2.TemplateNotFound: 템플릿을 찾을 수 없는 경우
        """
        try:
            template = self.template_env.get_template(template_name)
            self.log_debug(f"Template loaded: {template_name}")
            return template
        except Exception as e:
            self.log_error(f"Failed to load template {template_name}: {e}")
            raise

    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any],
        strip: bool = True
    ) -> str:
        """
        템플릿 렌더링

        Args:
            template_name: 템플릿 파일명
            context: 템플릿 컨텍스트 변수
            strip: 결과 문자열의 앞뒤 공백 제거 여부

        Returns:
            렌더링된 문자열
        """
        template = self.load_template(template_name)
        result = template.render(**context)

        if strip:
            result = result.strip()

        self.log_debug(f"Template rendered: {template_name}")
        return result

    def validate_spec(self, spec: SpecModel) -> bool:
        """
        스펙 유효성 검증 (기본 구현)

        하위 클래스에서 오버라이드하여 추가 검증 로직 구현 가능

        Args:
            spec: 검증할 스펙

        Returns:
            유효성 여부
        """
        if not spec:
            self.log_warning("Spec is None or empty")
            return False

        # Pydantic 모델이므로 생성 시점에 이미 검증됨
        return True

    @abstractmethod
    def create_definition(self, spec: SpecModel) -> Definition:
        """
        Spec에서 Definition을 생성 (추상 메서드)

        하위 클래스에서 반드시 구현해야 합니다.

        Args:
            spec: 입력 스펙

        Returns:
            생성된 정의 객체
        """
        raise NotImplementedError("Subclasses must implement create_definition()")

    @abstractmethod
    def create_code(self, definition: Definition, **kwargs) -> str:
        """
        Definition에서 코드를 생성 (추상 메서드)

        하위 클래스에서 반드시 구현해야 합니다.

        Args:
            definition: 정의 객체
            **kwargs: 추가 파라미터

        Returns:
            생성된 코드 문자열
        """
        raise NotImplementedError("Subclasses must implement create_code()")

    def create_from_spec(self, spec: SpecModel, **kwargs) -> str:
        """
        Spec에서 직접 코드 생성 (편의 메서드)

        create_definition()과 create_code()를 순차적으로 호출합니다.

        Args:
            spec: 입력 스펙
            **kwargs: create_code()에 전달할 추가 파라미터

        Returns:
            생성된 코드 문자열
        """
        if not self.validate_spec(spec):
            raise ValueError(f"Invalid spec: {spec}")

        definition = self.create_definition(spec)
        code = self.create_code(definition, **kwargs)

        return code

    def get_template_path(self, template_name: str) -> Path:
        """
        템플릿 파일의 전체 경로 반환

        Args:
            template_name: 템플릿 파일명

        Returns:
            템플릿 파일의 Path 객체
        """
        return self.template_dir / template_name

    def template_exists(self, template_name: str) -> bool:
        """
        템플릿 파일 존재 여부 확인

        Args:
            template_name: 템플릿 파일명

        Returns:
            존재 여부
        """
        return self.get_template_path(template_name).exists()


class CodeGenerationError(Exception):
    """코드 생성 중 발생하는 예외"""
    pass


class TemplateRenderError(Exception):
    """템플릿 렌더링 중 발생하는 예외"""
    pass
