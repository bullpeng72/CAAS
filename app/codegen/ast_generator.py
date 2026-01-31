"""
AST-based Code Generator

AST(Abstract Syntax Tree)를 사용하여 정확하고 안전한 Python 코드를 생성합니다.
문자열 조합 방식의 들여쓰기 문제를 근본적으로 해결합니다.
"""

import ast
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from app.utils.logger import get_logger

logger = get_logger("codegen.ast_generator")


@dataclass
class ASTCodeBlock:
    """AST 기반 코드 블록"""
    statements: List[ast.stmt]
    imports: List[ast.Import | ast.ImportFrom] = None

    def __post_init__(self):
        if self.imports is None:
            self.imports = []


class ASTCodeGenerator:
    """AST 기반 코드 생성기"""

    def __init__(self):
        self.logger = logger

    def generate_code(self, statements: List[ast.stmt], imports: Optional[List] = None) -> str:
        """
        AST 노드 리스트를 Python 코드로 변환

        Args:
            statements: AST statement 노드 리스트
            imports: import 문 리스트 (선택)

        Returns:
            str: 생성된 Python 코드
        """
        module = ast.Module(body=imports + statements if imports else statements, type_ignores=[])

        # AST 노드에 위치 정보 추가 (lineno, col_offset 등)
        ast.fix_missing_locations(module)

        # Python 3.9+에서 ast.unparse 사용
        try:
            code = ast.unparse(module)
            return code
        except AttributeError:
            # Python 3.8 이하 fallback
            self.logger.warning("ast.unparse not available, using astor")
            try:
                import astor
                return astor.to_source(module)
            except ImportError:
                raise RuntimeError("Python 3.9+ 필요 또는 astor 패키지 설치 필요")

    # ============================================================================
    # Import 생성
    # ============================================================================

    def create_import(self, module: str, names: Optional[List[str]] = None) -> ast.Import | ast.ImportFrom:
        """
        import 문 생성

        Examples:
            create_import("os") → import os
            create_import("os", ["path", "environ"]) → from os import path, environ
        """
        if names:
            return ast.ImportFrom(
                module=module,
                names=[ast.alias(name=name, asname=None) for name in names],
                level=0
            )
        else:
            return ast.Import(names=[ast.alias(name=module, asname=None)])

    # ============================================================================
    # 변수 할당
    # ============================================================================

    def create_assign(self, target: str, value: Any) -> ast.Assign:
        """
        변수 할당문 생성

        Examples:
            create_assign("x", 10) → x = 10
            create_assign("name", "John") → name = "John"
        """
        return ast.Assign(
            targets=[ast.Name(id=target, ctx=ast.Store())],
            value=self._value_to_ast(value)
        )

    # ============================================================================
    # 함수 호출
    # ============================================================================

    def create_call(
        self,
        func_name: str,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        attribute: Optional[str] = None
    ) -> ast.Call:
        """
        함수 호출 생성

        Examples:
            create_call("print", ["Hello"]) → print("Hello")
            create_call("st.text_input", kwargs={"label": "Name"}, attribute="text_input")
        """
        # 함수 참조 생성 (module.function 형태 지원)
        if '.' in func_name:
            parts = func_name.split('.')
            func_ref = ast.Name(id=parts[0], ctx=ast.Load())
            for part in parts[1:]:
                func_ref = ast.Attribute(value=func_ref, attr=part, ctx=ast.Load())
        else:
            func_ref = ast.Name(id=func_name, ctx=ast.Load())

        # 인자 처리
        call_args = [self._value_to_ast(arg) for arg in (args or [])]
        call_kwargs = [
            ast.keyword(arg=key, value=self._value_to_ast(value))
            for key, value in (kwargs or {}).items()
        ]

        return ast.Call(func=func_ref, args=call_args, keywords=call_kwargs)

    def create_method_call(
        self,
        obj: str,
        method: str,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None
    ) -> ast.Call:
        """
        메서드 호출 생성

        Examples:
            create_method_call("st", "title", ["My App"]) → st.title("My App")
        """
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=obj, ctx=ast.Load()),
                attr=method,
                ctx=ast.Load()
            ),
            args=[self._value_to_ast(arg) for arg in (args or [])],
            keywords=[
                ast.keyword(arg=key, value=self._value_to_ast(value))
                for key, value in (kwargs or {}).items()
            ]
        )

    # ============================================================================
    # 제어문
    # ============================================================================

    def create_if(
        self,
        condition: ast.expr,
        body: List[ast.stmt],
        orelse: Optional[List[ast.stmt]] = None
    ) -> ast.If:
        """
        if 문 생성

        Examples:
            create_if(
                condition=ast.Name(id="x", ctx=ast.Load()),
                body=[create_call("print", ["Yes"])]
            ) → if x: print("Yes")
        """
        return ast.If(test=condition, body=body, orelse=orelse or [])

    def create_for(
        self,
        target: str,
        iter_expr: ast.expr,
        body: List[ast.stmt]
    ) -> ast.For:
        """
        for 문 생성

        Examples:
            create_for("item", ast.Name(id="items"), [...]) → for item in items: ...
        """
        return ast.For(
            target=ast.Name(id=target, ctx=ast.Store()),
            iter=iter_expr,
            body=body,
            orelse=[]
        )

    # ============================================================================
    # 함수 정의
    # ============================================================================

    def create_function(
        self,
        name: str,
        args: Optional[List[str]] = None,
        body: Optional[List[ast.stmt]] = None,
        decorators: Optional[List[str]] = None,
        returns: Optional[str] = None,
        docstring: Optional[str] = None
    ) -> ast.FunctionDef:
        """
        함수 정의 생성

        Examples:
            create_function("greet", ["name"], [...]) → def greet(name): ...
        """
        # 인자 정의
        arguments = ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg=arg, annotation=None) for arg in (args or [])],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[]
        )

        # body 처리 (docstring 포함)
        func_body = []
        if docstring:
            func_body.append(ast.Expr(value=ast.Constant(value=docstring)))
        if body:
            func_body.extend(body)
        if not func_body:
            func_body = [ast.Pass()]

        # 데코레이터 처리
        decorator_list = []
        if decorators:
            for dec in decorators:
                decorator_list.append(ast.Name(id=dec, ctx=ast.Load()))

        return ast.FunctionDef(
            name=name,
            args=arguments,
            body=func_body,
            decorator_list=decorator_list,
            returns=ast.Name(id=returns, ctx=ast.Load()) if returns else None
        )

    # ============================================================================
    # Streamlit 특화 생성
    # ============================================================================

    def create_streamlit_component(
        self,
        component_type: str,
        variable_name: Optional[str] = None,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None
    ) -> ast.stmt:
        """
        Streamlit 컴포넌트 생성

        Examples:
            create_streamlit_component("title", args=["My App"])
            → st.title("My App")

            create_streamlit_component("text_input", "user_name", kwargs={"label": "Name"})
            → user_name = st.text_input(label="Name")
        """
        call = self.create_method_call("st", component_type, args, kwargs)

        if variable_name:
            return ast.Assign(
                targets=[ast.Name(id=variable_name, ctx=ast.Store())],
                value=call
            )
        else:
            return ast.Expr(value=call)

    # ============================================================================
    # 유틸리티
    # ============================================================================

    def _value_to_ast(self, value: Any) -> ast.expr:
        """Python 값을 AST 노드로 변환"""
        if isinstance(value, ast.expr):
            return value
        elif isinstance(value, str):
            return ast.Constant(value=value)
        elif isinstance(value, (int, float, bool)):
            return ast.Constant(value=value)
        elif isinstance(value, list):
            return ast.List(
                elts=[self._value_to_ast(v) for v in value],
                ctx=ast.Load()
            )
        elif isinstance(value, dict):
            return ast.Dict(
                keys=[ast.Constant(value=k) for k in value.keys()],
                values=[self._value_to_ast(v) for v in value.values()]
            )
        elif value is None:
            return ast.Constant(value=None)
        else:
            raise ValueError(f"Unsupported value type: {type(value)}")

    def create_comment(self, text: str) -> ast.Expr:
        """
        주석 생성 (실제로는 문자열 표현식으로 생성됨)

        Note: AST는 주석을 직접 지원하지 않으므로 docstring 형태로 생성
        """
        return ast.Expr(value=ast.Constant(value=f"# {text}"))


class StreamlitASTGenerator(ASTCodeGenerator):
    """Streamlit 전용 AST 코드 생성기"""

    def generate_streamlit_app(
        self,
        title: str,
        components: List[Dict[str, Any]],
        imports: Optional[List[str]] = None
    ) -> str:
        """
        완전한 Streamlit 앱 생성

        Args:
            title: 앱 제목
            components: 컴포넌트 정의 리스트
            imports: 추가 import 리스트

        Returns:
            str: 생성된 Streamlit 앱 코드
        """
        statements = []

        # Imports
        import_statements = [
            self.create_import("streamlit", ["st"] if imports and "st" in imports else None)
        ]
        if imports:
            for imp in imports:
                if imp != "streamlit":
                    import_statements.append(self.create_import(imp))

        # Main function
        main_body = []

        # Title
        main_body.append(
            ast.Expr(value=self.create_method_call("st", "title", [title]))
        )

        # Components
        for comp in components:
            comp_stmt = self._generate_component_from_dict(comp)
            if comp_stmt:
                main_body.append(comp_stmt)

        # Create main function
        main_func = self.create_function(
            name="main",
            body=main_body,
            docstring="Main Streamlit application"
        )

        statements.append(main_func)

        # if __name__ == "__main__"
        statements.append(
            ast.If(
                test=ast.Compare(
                    left=ast.Name(id="__name__", ctx=ast.Load()),
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value="__main__")]
                ),
                body=[ast.Expr(value=self.create_call("main"))],
                orelse=[]
            )
        )

        return self.generate_code(statements, import_statements)

    def _generate_component_from_dict(self, comp_dict: Dict[str, Any]) -> Optional[ast.stmt]:
        """컴포넌트 딕셔너리에서 AST 생성"""
        comp_type = comp_dict.get("type")
        comp_id = comp_dict.get("id")

        if not comp_type:
            return None

        # 컴포넌트별 처리
        if comp_type == "text_input":
            return self.create_streamlit_component(
                "text_input",
                variable_name=comp_id,
                kwargs={
                    "label": comp_dict.get("label", "Input"),
                    "help": comp_dict.get("help", "")
                }
            )

        elif comp_type == "button":
            return self.create_streamlit_component(
                "button",
                variable_name=comp_id,
                args=[comp_dict.get("label", "Button")],
                kwargs={
                    "key": comp_dict.get("key"),
                    "type": comp_dict.get("button_type", "secondary")
                }
            )

        elif comp_type == "selectbox":
            return self.create_streamlit_component(
                "selectbox",
                variable_name=comp_id,
                args=[comp_dict.get("label", "Select")],
                kwargs={
                    "options": comp_dict.get("options", []),
                    "key": comp_dict.get("key")
                }
            )

        elif comp_type == "text_area":
            return self.create_streamlit_component(
                "text_area",
                variable_name=comp_id,
                args=[comp_dict.get("label", "Text Area")],
                kwargs={
                    "height": comp_dict.get("height", 200),
                    "key": comp_dict.get("key")
                }
            )

        elif comp_type == "markdown":
            return ast.Expr(
                value=self.create_method_call(
                    "st",
                    "markdown",
                    [comp_dict.get("content", "")]
                )
            )

        elif comp_type == "divider":
            return ast.Expr(value=self.create_method_call("st", "divider", []))

        else:
            self.logger.warning(f"Unknown component type: {comp_type}")
            return None


# ============================================================================
# 편의 함수
# ============================================================================

def generate_streamlit_code(
    title: str,
    components: List[Dict[str, Any]],
    imports: Optional[List[str]] = None
) -> str:
    """
    Streamlit 앱 코드를 AST 기반으로 생성

    Args:
        title: 앱 제목
        components: 컴포넌트 리스트
        imports: 추가 imports

    Returns:
        str: 생성된 Python 코드
    """
    generator = StreamlitASTGenerator()
    return generator.generate_streamlit_app(title, components, imports)
