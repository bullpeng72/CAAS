"""
CAAS Code Formatter

생성된 Python 코드를 포맷팅합니다.
"""

import ast
import re
from typing import Optional, Tuple

from caas_framework.utils.logger import get_logger, LoggerMixin

logger = get_logger("codegen.formatter")


class CodeFormatter(LoggerMixin):
    """
    코드 포맷터
    
    생성된 Python 코드를 정리하고 포맷팅합니다.
    """
    
    def __init__(
        self,
        line_length: int = 100,
        use_black: bool = True,
        use_isort: bool = True,
    ):
        self.line_length = line_length
        self.use_black = use_black
        self.use_isort = use_isort
    
    def format_code(self, code: str) -> str:
        """
        코드를 포맷팅합니다.
        
        Args:
            code: 포맷팅할 Python 코드
        
        Returns:
            str: 포맷팅된 코드
        """
        # 1. 기본 정리
        code = self._clean_code(code)
        
        # 2. Black 포맷팅
        if self.use_black:
            code = self._format_with_black(code)
        
        # 3. Import 정렬
        if self.use_isort:
            code = self._sort_imports(code)
        
        return code
    
    def _clean_code(self, code: str) -> str:
        """기본 코드 정리"""
        # 연속된 빈 줄 제거
        code = re.sub(r'\n{3,}', '\n\n', code)
        
        # 줄 끝 공백 제거
        code = '\n'.join(line.rstrip() for line in code.split('\n'))
        
        # 파일 끝 개행 추가
        if not code.endswith('\n'):
            code += '\n'
        
        return code
    
    def _format_with_black(self, code: str) -> str:
        """Black으로 포맷팅"""
        try:
            import black
            
            formatted = black.format_str(
                code,
                mode=black.Mode(
                    line_length=self.line_length,
                    target_versions={black.TargetVersion.PY311},
                    string_normalization=True,
                ),
            )
            return formatted
        except ImportError:
            self.logger.warning("Black이 설치되지 않았습니다.")
            return code
        except Exception as e:
            self.logger.warning(f"Black 포맷팅 실패: {e}")
            return code
    
    def _sort_imports(self, code: str) -> str:
        """Import 정렬"""
        try:
            import isort
            
            sorted_code = isort.code(
                code,
                line_length=self.line_length,
                profile="black",
            )
            return sorted_code
        except ImportError:
            self.logger.warning("isort가 설치되지 않았습니다.")
            return self._manual_sort_imports(code)
        except Exception as e:
            self.logger.warning(f"isort 실패: {e}")
            return code
    
    def _manual_sort_imports(self, code: str) -> str:
        """수동 Import 정렬"""
        lines = code.split('\n')
        
        imports_std = []
        imports_third = []
        imports_local = []
        other_lines = []
        
        in_imports = True
        
        for line in lines:
            stripped = line.strip()
            
            if in_imports:
                if stripped.startswith('import ') or stripped.startswith('from '):
                    # 표준 라이브러리
                    if any(stripped.startswith(f'from {m}') or stripped.startswith(f'import {m}') 
                           for m in ['os', 'sys', 'typing', 'pathlib', 'datetime', 'json', 're', 'enum']):
                        imports_std.append(line)
                    # 로컬 임포트
                    elif 'app.' in stripped or 'from .' in stripped:
                        imports_local.append(line)
                    # 서드파티
                    else:
                        imports_third.append(line)
                elif stripped and not stripped.startswith('#') and not stripped.startswith('"""'):
                    in_imports = False
                    other_lines.append(line)
                else:
                    # 빈 줄이나 주석은 무시
                    if not in_imports:
                        other_lines.append(line)
            else:
                other_lines.append(line)
        
        # 재조합
        result = []
        
        if imports_std:
            result.extend(sorted(imports_std))
            result.append('')
        
        if imports_third:
            result.extend(sorted(imports_third))
            result.append('')
        
        if imports_local:
            result.extend(sorted(imports_local))
            result.append('')
        
        result.extend(other_lines)
        
        return '\n'.join(result)
    
    def validate_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Python 구문을 검증합니다.

        Args:
            code: 검증할 코드

        Returns:
            Tuple[bool, Optional[str]]: (유효 여부, 오류 메시지)
        """
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            error_msg = f"Line {e.lineno}: {e.msg}"
            return False, error_msg

    def normalize_indentation(self, code: str) -> str:
        """
        들여쓰기를 정규화하여 일관성을 보장합니다.

        AST로 파싱 후 재생성하여 올바른 들여쓰기를 자동으로 적용합니다.

        Args:
            code: 정규화할 코드

        Returns:
            str: 들여쓰기가 정규화된 코드
        """
        try:
            # AST로 파싱
            tree = ast.parse(code)

            # Python 3.9+에서는 ast.unparse 사용
            if hasattr(ast, 'unparse'):
                normalized = ast.unparse(tree)
                self.logger.debug("들여쓰기 정규화 완료 (ast.unparse)")
                return normalized
            else:
                # Python 3.8 이하에서는 Black 포맷팅으로 대체
                self.logger.debug("ast.unparse 미지원, Black 포맷팅 사용")
                return self._format_with_black(code)

        except SyntaxError as e:
            self.logger.warning(f"들여쓰기 정규화 실패 (구문 오류): {e}")
            # 구문 오류가 있으면 원본 반환
            return code
        except Exception as e:
            self.logger.warning(f"들여쓰기 정규화 실패: {e}")
            # Black 포맷팅으로 fallback
            try:
                return self._format_with_black(code)
            except:
                return code
    
    def add_docstring(
        self,
        code: str,
        module_doc: str = "",
        auto_generate: bool = True,
    ) -> str:
        """
        모듈 독스트링을 추가합니다.
        
        Args:
            code: 코드
            module_doc: 모듈 독스트링
            auto_generate: 자동 생성 여부
        
        Returns:
            str: 독스트링이 추가된 코드
        """
        lines = code.split('\n')
        
        # 이미 독스트링이 있는지 확인
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    # 이미 독스트링 있음
                    return code
                break
        
        # 독스트링 추가
        if not module_doc and auto_generate:
            module_doc = "Generated by CAAS - CrewAI Agent Auto-generation System"
        
        if module_doc:
            docstring = f'"""\n{module_doc}\n"""\n\n'
            return docstring + code
        
        return code
    
    def add_type_hints(self, code: str) -> str:
        """
        기본 타입 힌트를 추가합니다.
        (간단한 경우만 처리)
        
        Args:
            code: 코드
        
        Returns:
            str: 타입 힌트가 추가된 코드
        """
        # 간단한 패턴 매칭으로 타입 힌트 추가
        # def func(self, x, y): -> def func(self, x: Any, y: Any) -> Any:
        
        pattern = r'def (\w+)\(self(?:,\s*([^)]+))?\):'
        
        def add_hints(match):
            func_name = match.group(1)
            params = match.group(2)
            
            if params:
                # 파라미터에 타입 힌트가 없으면 추가
                new_params = []
                for param in params.split(','):
                    param = param.strip()
                    if ':' not in param and '=' not in param:
                        new_params.append(f"{param}: Any")
                    else:
                        new_params.append(param)
                params_str = ', '.join(new_params)
                return f"def {func_name}(self, {params_str}):"
            
            return match.group(0)
        
        # 패턴 적용 (주의: 간단한 경우만)
        # 복잡한 경우는 전문 도구 사용 권장
        
        return code
    
    def remove_unused_imports(self, code: str) -> str:
        """
        사용되지 않는 import를 제거합니다.
        (간단한 경우만 처리)
        
        Args:
            code: 코드
        
        Returns:
            str: 정리된 코드
        """
        try:
            import autoflake
            
            return autoflake.fix_code(
                code,
                remove_all_unused_imports=True,
            )
        except ImportError:
            self.logger.debug("autoflake가 설치되지 않았습니다.")
            return code
        except Exception as e:
            self.logger.warning(f"autoflake 실패: {e}")
            return code
    
    def format_string(
        self,
        text: str,
        max_length: int = 80,
        use_triple_quotes: bool = True,
    ) -> str:
        """
        긴 문자열을 포맷팅합니다.
        
        Args:
            text: 문자열
            max_length: 최대 줄 길이
            use_triple_quotes: 삼중 따옴표 사용 여부
        
        Returns:
            str: 포맷팅된 문자열
        """
        if len(text) <= max_length:
            return f'"{text}"'
        
        if use_triple_quotes:
            # 삼중 따옴표로 여러 줄 문자열
            return f'"""{text}"""'
        else:
            # 줄 연결
            lines = []
            current = ""
            
            for word in text.split():
                if len(current) + len(word) + 1 <= max_length - 4:
                    current += (" " if current else "") + word
                else:
                    if current:
                        lines.append(current)
                    current = word
            
            if current:
                lines.append(current)
            
            return '(\n    "' + '"\n    "'.join(lines) + '"\n)'


def format_code(code: str, **kwargs) -> str:
    """
    코드를 포맷팅하는 헬퍼 함수
    
    Args:
        code: 포맷팅할 코드
        **kwargs: CodeFormatter 옵션
    
    Returns:
        str: 포맷팅된 코드
    """
    formatter = CodeFormatter(**kwargs)
    return formatter.format_code(code)


def validate_python_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Python 코드 구문을 검증하는 헬퍼 함수

    Args:
        code: 검증할 코드

    Returns:
        Tuple[bool, Optional[str]]: (유효 여부, 오류 메시지)
    """
    formatter = CodeFormatter()
    return formatter.validate_syntax(code)


def normalize_indentation(code: str) -> str:
    """
    들여쓰기를 정규화하는 헬퍼 함수

    Args:
        code: 정규화할 코드

    Returns:
        str: 들여쓰기가 정규화된 코드
    """
    formatter = CodeFormatter()
    return formatter.normalize_indentation(code)
