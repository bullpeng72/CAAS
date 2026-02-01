"""
Multi-Artifact Code Generator

CrewAI 에이전트뿐만 아니라 Backend, Frontend, Database 등
전체 프로젝트 스택을 생성합니다.
"""

from typing import Dict, Tuple, Optional, List
import ast

from app.utils.logger import get_logger, LoggerMixin
from app.core.sdd.multi_spec import (
    MultiProjectSpec,
    BackendSpec,
    FrontendSpec,
    DatabaseSpec,
    BackendFramework,
    FrontendFramework,
)
from app.codegen.generator import CodeGenerator
from app.codegen.validator import ValidationResult
from app.codegen.formatter import CodeFormatter
from app.codegen.ast_generator import StreamlitASTGenerator
from app.codegen.frontend_logic import FrontendLogicGenerator
from app.codegen.backend_logic import BackendLogicGenerator
from app.models.domain_types import DomainType

logger = get_logger("codegen.multi")


class MultiArtifactGenerator(LoggerMixin):
    """
    Multi-Artifact 코드 생성기

    CrewAI 에이전트뿐만 아니라 Backend, Frontend, Database 등
    전체 프로젝트 스택을 생성합니다.
    """

    def __init__(self):
        self.agent_generator = CodeGenerator()
        self.formatter = CodeFormatter()
        self.ast_generator = StreamlitASTGenerator()
        self.frontend_logic = FrontendLogicGenerator()
        self.backend_logic = BackendLogicGenerator()
        self.domain_classification = None  # Will be set during generation

    def generate_full_project(
        self,
        project_spec: MultiProjectSpec,
        include_tests: bool = False
    ) -> Tuple[Dict[str, str], Optional[ValidationResult]]:
        """
        전체 프로젝트 생성

        Args:
            project_spec: 통합 프로젝트 스펙
            include_tests: 테스트 파일 포함 여부 (기본: False)

        Returns:
            Tuple[Dict[파일경로, 코드내용], Optional[ValidationResult]]:
                생성된 파일과 검증 결과
        """
        self.logger.info(f"프로젝트 생성 시작: {project_spec.project.name}")

        # Store domain classification for frontend logic generation
        self.domain_classification = project_spec.domain_classification
        if self.domain_classification:
            domain_type = self.domain_classification.get('domain_type')
            self.logger.info(f"🎯 Domain Classification: {domain_type}")

        all_files = {}
        validation_result = None

        # 1. CrewAI 에이전트 시스템
        if project_spec.agent_spec:
            self.logger.info("CrewAI 에이전트 생성 중...")
            agent_result = self.agent_generator.generate_from_spec(
                project_spec.agent_spec,
                include_tests=include_tests
            )
            all_files.update(self._prefix_paths(agent_result.files, "agents/"))

            # 검증 결과 저장 (에이전트 코드가 가장 중요하므로 이것을 저장)
            validation_result = agent_result.validation

        # 2. Backend API
        if project_spec.has_backend():
            self.logger.info("Backend API 생성 중...")
            # Get frontend port if frontend is enabled
            frontend_port = project_spec.frontend_spec.port if project_spec.has_frontend() else 8600
            backend_files = self._generate_backend(project_spec.backend_spec, frontend_port=frontend_port)
            all_files.update(self._prefix_paths(backend_files, "backend/"))

        # 3. Frontend UI
        if project_spec.has_frontend():
            self.logger.info("Frontend UI 생성 중...")
            # Backend 유무를 전달
            has_backend = project_spec.has_backend()
            frontend_files = self._generate_frontend(
                project_spec.frontend_spec,
                has_backend=has_backend
            )
            all_files.update(self._prefix_paths(frontend_files, "frontend/"))

        # 4. Database
        if project_spec.has_database():
            self.logger.info("Database 설정 생성 중...")
            db_files = self._generate_database(project_spec.database_spec)
            all_files.update(self._prefix_paths(db_files, "database/"))

        # 5. 통합 파일 (Docker Compose, README 등)
        self.logger.info("통합 파일 생성 중...")
        integration_files = self._generate_integration_files(project_spec)
        all_files.update(integration_files)

        # 6. 추가 파일
        if project_spec.additional_files:
            all_files.update(project_spec.additional_files)

        # 7. 생성된 모든 Python 파일 구문 검증 및 자동 수정
        self.logger.info("생성된 코드 검증 및 포맷팅 중...")
        all_files = self._validate_and_format_files(all_files)

        self.logger.info(f"프로젝트 생성 완료: {len(all_files)}개 파일")
        return all_files, validation_result

    def _generate_backend(self, spec: BackendSpec, frontend_port: int = 8600) -> Dict[str, str]:
        """Backend 코드 생성"""
        if spec.framework == BackendFramework.FASTAPI:
            return self._generate_fastapi(spec, frontend_port=frontend_port)
        elif spec.framework == BackendFramework.FLASK:
            return self._generate_flask(spec, frontend_port=frontend_port)
        else:
            self.logger.warning(f"지원하지 않는 Backend 프레임워크: {spec.framework}")
            return {}

    def _generate_fastapi(self, spec: BackendSpec, frontend_port: int = 8600) -> Dict[str, str]:
        """FastAPI 코드 생성"""
        files = {}

        # main.py
        files["main.py"] = self._generate_fastapi_main(spec)

        # routers/
        files["routers/__init__.py"] = ""
        files["routers/agents.py"] = self._generate_agent_router(spec)

        # models.py
        files["models.py"] = self._generate_pydantic_models(spec)

        # config.py
        files["config.py"] = self._generate_backend_config(spec, frontend_port=frontend_port)

        # requirements.txt
        files["requirements.txt"] = self._generate_backend_requirements(spec)

        # .env.example
        files[".env.example"] = self._generate_backend_env_example(spec, frontend_port=frontend_port)

        return files

    def _generate_fastapi_main(self, spec: BackendSpec) -> str:
        """FastAPI main.py 생성"""
        return f'''"""
Backend API

CrewAI 에이전트를 실행하는 FastAPI 백엔드
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import agents
from config import settings

app = FastAPI(
    title="Agent API",
    description="CrewAI 멀티에이전트 시스템 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])

@app.get("/")
async def root():
    return {{"message": "Agent Backend API", "version": "1.0.0"}}

@app.get("/health")
async def health():
    return {{"status": "healthy"}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
'''

    def _generate_agent_router(self, spec: BackendSpec) -> str:
        """에이전트 라우터 생성 (domain-aware)"""
        endpoints_code = []

        # Get domain type for domain-specific backend logic
        domain_type = None
        execution_pattern = None
        if self.domain_classification:
            try:
                domain_type = DomainType(self.domain_classification.get('domain_type'))
                execution_pattern_str = self.domain_classification.get('execution_pattern')
                if execution_pattern_str:
                    from app.models.domain_types import ExecutionPattern
                    execution_pattern = ExecutionPattern(execution_pattern_str)
                self.logger.info(f"🎯 Generating backend with domain: {domain_type}")
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Invalid domain type: {e}")

        # API 엔드포인트가 정의되어 있으면 사용
        if spec.api_endpoints:
            for endpoint in spec.api_endpoints:
                method = endpoint.method.value.lower()
                path = endpoint.path
                description = endpoint.description

                # Generate domain-specific endpoint
                endpoint_code = self.backend_logic.generate_endpoint_code(
                    endpoint_path=path,
                    endpoint_method=method,
                    endpoint_description=description,
                    domain_type=domain_type,
                    execution_pattern=execution_pattern
                )
                endpoints_code.append(endpoint_code)
        else:
            # 기본 엔드포인트 생성 (domain-specific)
            endpoint_code = self.backend_logic.generate_endpoint_code(
                endpoint_path="/run",
                endpoint_method="post",
                endpoint_description="CrewAI 에이전트 실행\n\n에이전트를 실행하고 결과를 반환합니다.",
                domain_type=domain_type,
                execution_pattern=execution_pattern
            )
            endpoints_code.append(endpoint_code)

        return f'''"""
Agent Router

CrewAI 에이전트 실행 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

router = APIRouter()

class AgentRequest(BaseModel):
    """에이전트 요청 모델"""
    input_data: Dict[str, Any]
    config: Dict[str, Any] = {{}}

class AgentResponse(BaseModel):
    """에이전트 응답 모델"""
    success: bool
    result: Any

{''.join(endpoints_code)}
'''

    def _generate_pydantic_models(self, spec: BackendSpec) -> str:
        """Pydantic 모델 생성"""
        return '''"""
Pydantic Models

API 요청/응답 모델 정의
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from datetime import datetime

class BaseResponse(BaseModel):
    """기본 응답 모델"""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    success: bool = False
    error: str
    detail: Optional[str] = None
'''

    def _generate_backend_config(self, spec: BackendSpec, frontend_port: int = 8600) -> str:
        """Backend 설정 파일 생성"""
        return f'''"""
Backend Configuration

환경 변수 및 설정 관리
"""

import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """애플리케이션 설정"""

    # API 설정
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # CORS 설정
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:{frontend_port}"]

    # 데이터베이스
    DATABASE_URL: str = "sqlite:///./app.db"

    # LLM API 키
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
'''

    def _generate_backend_requirements(self, spec: BackendSpec) -> str:
        """Backend requirements.txt 생성"""
        requirements = [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "pydantic>=2.0.0",
            "pydantic-settings>=2.0.0",
            "python-multipart>=0.0.6",
            # CrewAI 에이전트 실행을 위한 의존성 (Python 3.11+ 권장)
            # 검증된 버전 조합으로 의존성 충돌 방지 (Python 3.11 기준)
            "crewai>=1.7.0,<1.8.0",
            "crewai-tools>=1.7.0,<1.8.0",
            "langchain>=0.3.20,<0.4.0",
            "langchain-core>=0.3.70,<0.4.0",
            "langchain-openai>=0.3.20,<0.4.0",
            "openai>=1.0.0,<2.0.0",
            "python-dotenv>=1.0.0",
        ]

        if spec.dependencies:
            requirements.extend(spec.dependencies)

        return "\n".join(sorted(requirements))

    def _generate_backend_env_example(self, spec: BackendSpec, frontend_port: int = 8600) -> str:
        """.env.example 생성"""
        return f'''# Backend API 설정
API_HOST=0.0.0.0
API_PORT=8000

# CORS Origins (쉼표로 구분)
CORS_ORIGINS=http://localhost:3000,http://localhost:{frontend_port}

# 데이터베이스
DATABASE_URL=sqlite:///./app.db

# LLM API 키
OPENAI_API_KEY=your-openai-api-key-here
'''

    def _generate_flask(self, spec: BackendSpec, frontend_port: int = 8600) -> Dict[str, str]:
        """Flask 코드 생성"""
        files = {}

        # app.py
        files["app.py"] = self._generate_flask_app(spec, frontend_port)

        # routes/
        files["routes/__init__.py"] = ""
        files["routes/agents.py"] = self._generate_flask_agent_routes(spec)

        # models.py
        files["models.py"] = self._generate_pydantic_models(spec)

        # config.py
        files["config.py"] = self._generate_backend_config(spec, frontend_port=frontend_port)

        # requirements.txt
        files["requirements.txt"] = self._generate_flask_requirements(spec)

        # .env.example
        files[".env.example"] = self._generate_backend_env_example(spec, frontend_port=frontend_port)

        return files

    def _generate_flask_app(self, spec: BackendSpec, frontend_port: int) -> str:
        """Flask app.py 생성"""
        return f'''"""
Backend API

CrewAI 에이전트를 실행하는 Flask 백엔드
"""

from flask import Flask, jsonify
from flask_cors import CORS

from routes import agents
from config import settings

app = Flask(__name__)

# CORS 설정
CORS(app, origins=settings.CORS_ORIGINS.split(","))

# 라우터 등록
app.register_blueprint(agents.bp, url_prefix="/api/agents")

@app.route("/")
def root():
    return jsonify({{"message": "Agent Backend API", "version": "1.0.0"}})

@app.route("/health")
def health():
    return jsonify({{"status": "healthy"}})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True)
'''

    def _generate_flask_agent_routes(self, spec: BackendSpec) -> str:
        """Flask 에이전트 라우트 생성"""
        return f'''"""
Agent Routes

CrewAI 에이전트 실행을 위한 Flask 라우트
"""

from flask import Blueprint, request, jsonify
from crew import crew

bp = Blueprint("agents", __name__)

@bp.route("/run", methods=["POST"])
def run_agents():
    """에이전트 실행"""
    try:
        data = request.json
        inputs = data.get("inputs", {{}})

        # Crew 실행
        result = crew.kickoff(inputs=inputs)

        return jsonify({{
            "success": True,
            "result": result
        }})
    except Exception as e:
        return jsonify({{
            "success": False,
            "error": str(e)
        }}), 500

@bp.route("/status", methods=["GET"])
def get_status():
    """에이전트 상태 확인"""
    return jsonify({{
        "status": "ready",
        "agents": {len(spec.agents or [])}
    }})
'''

    def _generate_flask_requirements(self, spec: BackendSpec) -> str:
        """Flask requirements.txt 생성"""
        return '''# Flask 백엔드
flask==3.0.0
flask-cors==4.0.0

# CrewAI
crewai==0.28.8
crewai-tools==0.2.6

# LLM
openai==1.12.0

# 데이터베이스 (필요시)
sqlalchemy==2.0.25

# 유틸리티
python-dotenv==1.0.0
pydantic==2.6.0
'''

    def _generate_frontend(self, spec: FrontendSpec, has_backend: bool = False) -> Dict[str, str]:
        """Frontend 코드 생성"""
        if spec.framework == FrontendFramework.STREAMLIT:
            return self._generate_streamlit(spec, has_backend=has_backend)
        elif spec.framework == FrontendFramework.GRADIO:
            return self._generate_gradio(spec, has_backend=has_backend)
        else:
            self.logger.warning(f"지원하지 않는 Frontend 프레임워크: {spec.framework}")
            return {}

    def _generate_streamlit(self, spec: FrontendSpec, has_backend: bool = False) -> Dict[str, str]:
        """Streamlit 앱 생성"""
        files = {}

        # app.py
        files["app.py"] = self._generate_streamlit_main(spec, has_backend=has_backend)

        # requirements.txt
        files["requirements.txt"] = self._generate_frontend_requirements(spec, has_backend=has_backend)

        # .streamlit/config.toml
        files[".streamlit/config.toml"] = self._generate_streamlit_config(spec)

        # pages/
        for page in spec.pages:
            files[f"pages/{page.name}.py"] = self._generate_streamlit_page(page)

        return files

    def _generate_streamlit_main(self, spec: FrontendSpec, has_backend: bool = False) -> str:
        """Streamlit 메인 파일"""

        if has_backend:
            # Backend가 있는 경우: API 호출 방식
            api_url = spec.api_client.get('base_url', 'http://localhost:8000')
            return self._generate_streamlit_with_backend(spec, api_url)
        else:
            # Backend가 없는 경우: 직접 에이전트 실행
            return self._generate_streamlit_standalone(spec)

    def _generate_component_code_ast(self, component: dict, previous_components: List[dict] = None) -> List[ast.stmt]:
        """
        UIComponent를 AST Statement로 변환 (AST 기반)

        Args:
            component: UIComponent dict (component_id, component_type, label, description, props)
            previous_components: 이전에 생성된 컴포넌트 목록 (변수 추적용)

        Returns:
            AST statement 리스트
        """
        previous_components = previous_components or []

        comp_id = component.get("component_id", "component")
        comp_type = component.get("component_type", "text_input")
        label = component.get("label", "Label")
        description = component.get("description", "")
        props = component.get("props", {})

        # props에서 추가 옵션 추출
        placeholder = props.get("placeholder", "")
        height = props.get("height", 100)
        options = props.get("options", ["Option 1", "Option 2", "Option 3"])

        statements = []

        if comp_type == "text_input":
            kwargs = {"label": label}
            if placeholder:
                kwargs["placeholder"] = placeholder
            if description:
                kwargs["help"] = description

            statements.append(
                self.ast_generator.create_streamlit_component(
                    "text_input",
                    variable_name=comp_id,
                    kwargs=kwargs
                )
            )

        elif comp_type == "text_area":
            kwargs = {"label": label, "height": height}
            if placeholder:
                kwargs["placeholder"] = placeholder
            if description:
                kwargs["help"] = description

            statements.append(
                self.ast_generator.create_streamlit_component(
                    "text_area",
                    variable_name=comp_id,
                    kwargs=kwargs
                )
            )

        elif comp_type == "button":
            # Button with if statement
            button_call = self.ast_generator.create_method_call(
                "st",
                "button",
                args=[label],
                kwargs={"key": comp_id, "type": "primary"}
            )

            # Generate button handler using FrontendLogicGenerator
            domain_type = None
            if self.domain_classification:
                try:
                    domain_type = DomainType(self.domain_classification.get('domain_type'))
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid domain type: {self.domain_classification.get('domain_type')}")

            # Get available variables from previously created components
            available_vars = []
            for prev_comp in previous_components:
                prev_type = prev_comp.get("component_type", "")
                prev_id = prev_comp.get("component_id", "")

                # Input components create variables
                if prev_type in ["text_input", "text_area", "selectbox", "select", "number_input", "date_input"]:
                    available_vars.append(prev_id)

            # Generate domain-specific handler
            handler_body = self.frontend_logic.generate_button_handler(
                domain_type=domain_type,
                button_label=label,
                component_id=comp_id,
                available_variables=available_vars
            )

            # if st.button(...):
            #     [domain-specific handler]
            statements.append(
                self.ast_generator.create_if(
                    condition=button_call,
                    body=handler_body if handler_body else [ast.Pass()]
                )
            )

        elif comp_type == "select":
            kwargs = {"label": label, "options": options}
            if description:
                kwargs["help"] = description

            statements.append(
                self.ast_generator.create_streamlit_component(
                    "selectbox",
                    variable_name=comp_id,
                    kwargs=kwargs
                )
            )

        elif comp_type == "table":
            # Table display with domain-specific logic
            statements.append(
                ast.Expr(value=ast.Constant(value=f"# {label}"))
            )
            if description:
                statements.append(
                    ast.Expr(value=self.ast_generator.create_method_call("st", "caption", [description]))
                )

            # Generate domain-specific table display
            domain_type = None
            if self.domain_classification:
                try:
                    domain_type = DomainType(self.domain_classification.get('domain_type'))
                except (ValueError, TypeError):
                    pass

            table_display = self.frontend_logic.generate_table_display(
                domain_type=domain_type,
                table_label=label,
                component_id=comp_id
            )

            statements.extend(table_display)

        elif comp_type == "chart":
            # Comment + caption + TODO
            statements.append(
                ast.Expr(value=ast.Constant(value=f"# {label}"))
            )
            if description:
                statements.append(
                    ast.Expr(value=self.ast_generator.create_method_call("st", "caption", [description]))
                )
            statements.append(
                ast.Expr(value=ast.Constant(value="# TODO: 차트 데이터를 준비하고 표시"))
            )
            statements.append(
                ast.Expr(value=ast.Constant(value=f"# st.line_chart({comp_id}_data)"))
            )

        elif comp_type == "file_upload":
            kwargs = {"label": label}
            if description:
                kwargs["help"] = description

            statements.append(
                self.ast_generator.create_streamlit_component(
                    "file_uploader",
                    variable_name=comp_id,
                    kwargs=kwargs
                )
            )

        elif comp_type == "markdown":
            content = f"**{label}**"
            if description:
                content += f"\n\n{description}"

            statements.append(
                ast.Expr(value=self.ast_generator.create_method_call("st", "markdown", [content]))
            )

        else:
            # 기본값: text_input
            self.logger.warning(f"Unknown component type: {comp_type}, using text_input")
            statements.append(
                self.ast_generator.create_streamlit_component(
                    "text_input",
                    variable_name=comp_id,
                    kwargs={"label": label}
                )
            )

        return statements

    def _generate_component_code(self, component: dict, indent: str = "    ", previous_components: List[dict] = None) -> str:
        """
        UIComponent를 Streamlit 코드로 변환 (AST 기반)

        Args:
            component: UIComponent dict
            indent: 들여쓰기 레벨 (템플릿 삽입 위치의 기본 들여쓰기)
            previous_components: 이전에 생성된 컴포넌트 목록 (변수 추적용)

        Returns:
            생성된 Streamlit 코드
        """
        # AST 기반으로 생성
        statements = self._generate_component_code_ast(component, previous_components=previous_components)

        # AST를 코드로 변환
        if not statements:
            return ""

        code = self.ast_generator.generate_code(statements)

        # AST는 상대적인 블록 구조를 유지하므로, textwrap.indent()로 전체 블록을 이동
        # 이렇게 하면 if 블록 내부 등의 상대적 들여쓰기가 유지됩니다
        import textwrap
        indented_code = textwrap.indent(code, indent)

        return indented_code

    def _generate_streamlit_standalone(self, spec: FrontendSpec) -> str:
        """Backend 없이 직접 에이전트를 실행하는 Streamlit 앱 (동적 생성)"""

        # spec.pages가 있으면 첫 페이지의 컴포넌트를 사용
        has_custom_ui = spec.pages and len(spec.pages) > 0

        if has_custom_ui:
            first_page = spec.pages[0]
            components = first_page.components if hasattr(first_page, 'components') else []
            page_title = first_page.title if hasattr(first_page, 'title') else "Agent System"
            page_description = first_page.description if hasattr(first_page, 'description') else ""

            # 컴포넌트 코드 생성
            components_code = []
            components_dicts = [comp.dict() if hasattr(comp, 'dict') else comp for comp in components]
            for i, comp_dict in enumerate(components_dicts):
                # Pass previous components for variable tracking
                previous_comps = components_dicts[:i]
                components_code.append(self._generate_component_code(comp_dict, indent="    ", previous_components=previous_comps))

            ui_components = "\n\n".join(components_code) if components_code else '    st.text_area("입력", placeholder="요청 내용을 입력하세요...", height=150, key="user_input")'
        else:
            page_title = "Agent System"
            page_description = "CrewAI 멀티에이전트 시스템 (Standalone)"
            ui_components = '    user_input = st.text_area(\n        "입력",\n        placeholder="요청 내용을 입력하세요...",\n        height=150\n    )'

        return f'''"""
Agent UI

CrewAI 에이전트 실행 인터페이스 (Standalone - Backend 불필요)
"""

import streamlit as st
import sys
import os
from typing import Any

# CrewAI telemetry 비활성화 (Streamlit에서 signal handler 충돌 방지)
os.environ["OTEL_SDK_DISABLED"] = "true"

# agents 디렉토리를 Python 경로에 추가
agents_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agents")
if agents_path not in sys.path:
    sys.path.insert(0, agents_path)

# 페이지 설정
st.set_page_config(
    page_title="{page_title}",
    page_icon="🤖",
    layout="wide"
)

def run_agent_directly(user_input: str) -> Any:
    """에이전트를 직접 실행"""
    try:
        # agents/crew.py의 run_crew 함수 import
        from crew import run_crew

        # 에이전트 실행
        result = run_crew(inputs={{"text": user_input}})
        return result
    except ImportError as e:
        st.error(f"❌ **에이전트 모듈 import 실패**")
        st.error(f"agents/crew.py 파일이 존재하는지 확인하세요.")
        st.code(str(e))
        return None
    except Exception as e:
        st.error(f"❌ **에이전트 실행 중 오류 발생**")
        st.error(str(e))
        import traceback
        with st.expander("🔍 상세 오류 정보"):
            st.code(traceback.format_exc())
        return None

def main():
    st.title("🤖 {page_title}")
    {"st.markdown('" + page_description + "')" if page_description else ""}

    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        st.success("✅ Standalone 모드")
        st.caption("Backend 없이 직접 에이전트 실행")

        st.divider()
        st.info(
            "**실행 방법:**\\\\n\\\\n"
            "이 앱은 Backend 없이 직접 에이전트를 실행합니다.\\\\n"
            "터미널에서 다음 명령어로 실행하세요:\\\\n\\\\n"
            "```bash\\\\n"
            "cd frontend\\\\n"
            "streamlit run app.py\\\\n"
            "```"
        )

    # 메인 콘텐츠
    st.subheader("에이전트 실행")

    # 동적으로 생성된 UI 컴포넌트
{ui_components}

    # 실행 버튼
    if st.button("🚀 실행", type="primary", width='stretch'):
        # user_input 가져오기 (session_state 또는 변수에서)
        user_input = st.session_state.get("user_input", "") if "user_input" not in locals() else locals().get("user_input", "")

        if not user_input:
            st.warning("입력을 작성해주세요")
        else:
            with st.spinner("에이전트 실행 중... (시간이 걸릴 수 있습니다)"):
                result = run_agent_directly(user_input)

                if result:
                    st.session_state["result"] = result
                    st.success("✅ 완료!")
                    st.rerun()

    # 결과 표시
    st.divider()
    st.subheader("실행 결과")

    if "result" in st.session_state:
        result = st.session_state["result"]

        if isinstance(result, str):
            st.markdown(result)
        elif isinstance(result, dict):
            st.json(result)
        else:
            st.write(result)
    else:
        st.info("아직 실행된 결과가 없습니다")

if __name__ == "__main__":
    main()
'''

    def _generate_streamlit_with_backend(self, spec: FrontendSpec, api_url: str) -> str:
        """Backend API를 호출하는 Streamlit 앱 (동적 생성)"""

        # spec.pages가 있으면 첫 페이지의 컴포넌트를 사용
        has_custom_ui = spec.pages and len(spec.pages) > 0

        if has_custom_ui:
            first_page = spec.pages[0]
            components = first_page.components if hasattr(first_page, 'components') else []
            page_title = first_page.title if hasattr(first_page, 'title') else "Agent System"
            page_description = first_page.description if hasattr(first_page, 'description') else ""

            # 컴포넌트 코드 생성
            components_code = []
            components_dicts = [comp.dict() if hasattr(comp, 'dict') else comp for comp in components]
            for i, comp_dict in enumerate(components_dicts):
                # Pass previous components for variable tracking
                previous_comps = components_dicts[:i]
                components_code.append(self._generate_component_code(comp_dict, indent="    ", previous_components=previous_comps))

            ui_components = "\n\n".join(components_code) if components_code else '    user_input = st.text_area(\n        "입력",\n        placeholder="요청 내용을 입력하세요...",\n        height=150\n    )'
        else:
            page_title = "Agent System"
            page_description = "CrewAI 멀티에이전트 시스템"
            ui_components = '    user_input = st.text_area(\n        "입력",\n        placeholder="요청 내용을 입력하세요...",\n        height=150\n    )'

        return f'''"""
Agent UI

CrewAI 에이전트 실행 인터페이스
"""

import streamlit as st
import requests
from typing import Dict, Any, Optional

# 페이지 설정
st.set_page_config(
    page_title="{page_title}",
    page_icon="🤖",
    layout="wide"
)

# Backend API 설정
API_URL = "{api_url}"

def check_backend_health() -> bool:
    """Backend 서버 상태 확인"""
    try:
        response = requests.get(f"{{API_URL}}/health", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def call_agent_api(endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Backend API 호출"""
    try:
        response = requests.post(
            f"{{API_URL}}{{endpoint}}",
            json=data,
            timeout=300  # 5분 타임아웃
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError as e:
        st.error("❌ **Backend 서버 연결 실패**")
        st.error(
            "Backend API 서버가 실행되지 않았습니다. "
            "아래 단계를 확인하세요:"
        )
        st.markdown("""
        **해결 방법:**

        1. **새 터미널을 열고 Backend를 먼저 실행하세요:**

        ```bash
        cd backend
        uvicorn main:app --reload
        ```

        2. **Backend가 정상 실행되면 다음 메시지가 표시됩니다:**

        ```
        INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
        ```

        3. **Backend 실행 후 이 페이지를 새로고침하세요**

        **현재 API URL:** `{{API_URL}}`
        """)
        with st.expander("🔍 상세 오류 정보"):
            st.code(str(e))
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ **요청 시간 초과**")
        st.warning("Backend 서버가 응답하지 않습니다. 서버 로그를 확인하세요.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ **HTTP 오류 ({{e.response.status_code}})**")
        st.error(f"서버 응답: {{e.response.text}}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ **API 호출 실패**")
        st.error(str(e))
        return None

def main():
    st.title("🤖 {page_title}")
    {"st.markdown('" + page_description + "')" if page_description else ""}

    # Backend 상태 확인
    backend_status = check_backend_health()

    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        st.caption(f"**API URL:** {{API_URL}}")

        # Backend 상태 표시
        st.divider()
        st.subheader("서버 상태")
        if backend_status:
            st.success("✅ Backend 연결됨")
        else:
            st.error("❌ Backend 연결 안됨")
            st.warning(
                "Backend를 먼저 실행하세요:\\\\n"
                "```bash\\\\n"
                "cd backend\\\\n"
                "uvicorn main:app --reload\\\\n"
                "```"
            )

    # Backend 미연결 시 경고 배너
    if not backend_status:
        st.warning(
            "⚠️ **Backend 서버가 실행되지 않았습니다!** "
            "사이드바의 안내를 따라 Backend를 먼저 실행하세요."
        )

    # 메인 콘텐츠
    st.subheader("에이전트 실행")

    # 동적으로 생성된 UI 컴포넌트
{ui_components}

    # 실행 버튼
    if st.button(
        "🚀 실행",
        type="primary",
        width='stretch',
        disabled=not backend_status  # Backend 미연결 시 버튼 비활성화
    ):
        # user_input 가져오기 (session_state 또는 변수에서)
        user_input = st.session_state.get("user_input", "") if "user_input" not in locals() else locals().get("user_input", "")

        if not user_input:
            st.warning("입력을 작성해주세요")
        else:
            with st.spinner("에이전트 실행 중... (시간이 걸릴 수 있습니다)"):
                result = call_agent_api(
                    "/api/agents/run",
                    {{"input_data": {{"text": user_input}}}}
                )

                if result and result.get("success"):
                    st.session_state["result"] = result.get("result")
                    st.success("✅ 완료!")
                    st.rerun()
                elif result:
                    st.error("❌ 실행 실패")
                    if "error" in result:
                        st.error(f"오류: {{result['error']}}")

    # 결과 표시
    st.divider()
    st.subheader("실행 결과")

    if "result" in st.session_state:
        result = st.session_state["result"]

        if isinstance(result, str):
            st.markdown(result)
        elif isinstance(result, dict):
            st.json(result)
        else:
            st.write(result)
    else:
        st.info("아직 실행된 결과가 없습니다")

if __name__ == "__main__":
    main()
'''

    def _generate_streamlit_page(self, page) -> str:
        """Streamlit 페이지 생성 (동적 생성)"""

        # page 속성 추출
        title = page.title if hasattr(page, 'title') else page.get('title', 'Page')
        description = page.description if hasattr(page, 'description') else page.get('description', '')
        components = page.components if hasattr(page, 'components') else page.get('components', [])

        # 컴포넌트 코드 생성
        components_code = []
        if components:
            components_dicts = [comp.dict() if hasattr(comp, 'dict') else comp for comp in components]
            for i, comp_dict in enumerate(components_dicts):
                # Pass previous components for variable tracking
                previous_comps = components_dicts[:i]
                components_code.append(self._generate_component_code(comp_dict, indent="    ", previous_components=previous_comps))

            ui_code = "\n\n".join(components_code)
        else:
            ui_code = '    st.info("이 페이지에는 아직 컴포넌트가 정의되지 않았습니다.")'

        return f'''"""
{title}

{description}
"""

import streamlit as st

def render():
    st.title("{title}")
    {"st.markdown('" + description + "')" if description else ""}

    # 동적으로 생성된 페이지 컴포넌트
{ui_code}

if __name__ == "__main__":
    render()
'''

    def _generate_frontend_requirements(self, spec: FrontendSpec, has_backend: bool = False) -> str:
        """Frontend requirements.txt 생성"""
        requirements = [
            "streamlit>=1.28.0",
        ]

        # Backend가 있는 경우에만 requests 추가
        if has_backend:
            requirements.append("requests>=2.31.0")
        else:
            # Standalone 모드에서는 CrewAI 직접 사용 (Python 3.11+ 권장)
            # 검증된 버전 조합으로 의존성 충돌 방지 (Python 3.11 기준)
            requirements.extend([
                "crewai>=1.7.0,<1.8.0",
                "crewai-tools>=1.7.0,<1.8.0",
                "langchain>=0.3.20,<0.4.0",
                "langchain-core>=0.3.70,<0.4.0",
                "langchain-openai>=0.3.20,<0.4.0",
                "openai>=1.0.0,<2.0.0",
                "python-dotenv>=1.0.0",
            ])

        return "\n".join(sorted(requirements))

    def _generate_streamlit_config(self, spec: FrontendSpec) -> str:
        """.streamlit/config.toml 생성"""
        return f'''[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"

[server]
port = {spec.port}
headless = true
'''

    def _generate_gradio(self, spec: FrontendSpec, has_backend: bool = False) -> Dict[str, str]:
        """Gradio 앱 생성"""
        files = {}

        # app.py
        backend_url = f"http://localhost:{spec.port - 100}" if has_backend else None
        files["app.py"] = self._generate_gradio_app(spec, backend_url)

        # utils/api_client.py (if has backend)
        if has_backend:
            files["utils/__init__.py"] = ""
            files["utils/api_client.py"] = self._generate_gradio_api_client(backend_url)

        # requirements.txt
        files["requirements.txt"] = self._generate_gradio_requirements()

        # README.md
        files["README.md"] = self._generate_gradio_readme(spec.port)

        return files

    def _generate_gradio_app(self, spec: FrontendSpec, backend_url: str = None) -> str:
        """Gradio app.py 생성"""
        if backend_url:
            # With backend integration
            return f'''"""
Gradio Frontend Application

CrewAI 에이전트를 실행하는 Gradio 인터페이스
"""

import gradio as gr
from utils.api_client import call_agent_api

def run_agents(user_input):
    """에이전트 실행"""
    try:
        result = call_agent_api(
            "/api/agents/run",
            {{"input_data": {{"text": user_input}}}}
        )

        if result and result.get("success"):
            return result.get("result", "완료되었습니다")
        elif result:
            return f"❌ 오류: {{result.get('error', '알 수 없는 오류')}}"
        else:
            return "❌ API 호출 실패"
    except Exception as e:
        return f"❌ 에러 발생: {{str(e)}}"

# Gradio 인터페이스
with gr.Blocks(title="Agent Runner") as demo:
    gr.Markdown("# 🤖 Agent Runner")
    gr.Markdown("CrewAI 에이전트를 실행하세요")

    with gr.Row():
        with gr.Column():
            user_input = gr.Textbox(
                label="입력",
                placeholder="작업 내용을 입력하세요...",
                lines=5
            )
            run_button = gr.Button("실행", variant="primary")

        with gr.Column():
            output = gr.Textbox(
                label="결과",
                placeholder="결과가 여기에 표시됩니다",
                lines=10
            )

    run_button.click(
        fn=run_agents,
        inputs=[user_input],
        outputs=[output]
    )

if __name__ == "__main__":
    demo.launch(server_port={spec.port}, share=False)
'''
        else:
            # Standalone (no backend)
            return f'''"""
Gradio Frontend Application

Standalone Gradio 인터페이스
"""

import gradio as gr

def process_input(user_input):
    """입력 처리"""
    # 여기에 에이전트 로직을 직접 구현하세요
    return f"입력받은 내용: {{user_input}}"

# Gradio 인터페이스
with gr.Blocks(title="Agent Runner") as demo:
    gr.Markdown("# 🤖 Agent Runner")
    gr.Markdown("간단한 Gradio 인터페이스")

    with gr.Row():
        with gr.Column():
            user_input = gr.Textbox(
                label="입력",
                placeholder="내용을 입력하세요...",
                lines=5
            )
            run_button = gr.Button("실행", variant="primary")

        with gr.Column():
            output = gr.Textbox(
                label="결과",
                placeholder="결과가 여기에 표시됩니다",
                lines=10
            )

    run_button.click(
        fn=process_input,
        inputs=[user_input],
        outputs=[output]
    )

if __name__ == "__main__":
    demo.launch(server_port={spec.port}, share=False)
'''

    def _generate_gradio_api_client(self, backend_url: str) -> str:
        """Gradio API client 생성"""
        return f'''"""
API Client for Backend Communication
"""

import requests

BACKEND_URL = "{backend_url}"

def call_agent_api(endpoint, data):
    """Backend API 호출"""
    try:
        response = requests.post(
            f"{{BACKEND_URL}}{{endpoint}}",
            json=data,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API 호출 오류: {{e}}")
        return None
'''

    def _generate_gradio_requirements(self) -> str:
        """Gradio requirements.txt 생성"""
        return '''# Gradio Frontend
gradio==4.15.0

# API 통신
requests==2.31.0

# 유틸리티
python-dotenv==1.0.0
'''

    def _generate_gradio_readme(self, port: int) -> str:
        """Gradio README 생성"""
        return f'''# Gradio Frontend

## 설치

```bash
pip install -r requirements.txt
```

## 실행

```bash
python app.py
```

앱은 http://localhost:{port} 에서 실행됩니다.

## 기능

- 간단한 텍스트 입력 인터페이스
- 에이전트 실행 및 결과 표시
- 백엔드 API 연동 (backend가 있는 경우)
'''

    def _generate_database(self, spec: DatabaseSpec) -> Dict[str, str]:
        """Database 설정 생성"""
        files = {}

        # models.py
        files["models.py"] = self._generate_db_models(spec)

        # init.py
        files["__init__.py"] = self._generate_db_init(spec)

        return files

    def _generate_db_models(self, spec: DatabaseSpec) -> str:
        """Database 모델 생성"""
        models_code = []

        for model in spec.models:
            fields_code = []
            for field in model.fields:
                field_def = f"    {field.name}: Mapped[{field.field_type.value}]"
                if field.nullable:
                    field_def += " = mapped_column(nullable=True)"
                fields_code.append(field_def)

            models_code.append(f'''
class {model.model_name}(Base):
    """{ model.model_name} 모델"""
    __tablename__ = "{model.table_name}"

    id: Mapped[int] = mapped_column(primary_key=True)
{chr(10).join(fields_code)}
''')

        return f'''"""
Database Models

SQLAlchemy ORM 모델 정의
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime

class Base(DeclarativeBase):
    """Base 모델"""
    pass

{''.join(models_code)}
'''

    def _generate_db_init(self, spec: DatabaseSpec) -> str:
        """Database 초기화 코드"""
        return f'''"""
Database Initialization

데이터베이스 연결 및 초기화
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "{spec.database_url}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """데이터베이스 세션 가져오기"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''

    def _generate_integration_files(self, spec: MultiProjectSpec) -> Dict[str, str]:
        """통합 파일 생성"""
        files = {}

        # README.md
        files["README.md"] = self._generate_readme(spec)

        # .gitignore
        files[".gitignore"] = self._generate_gitignore()

        # Docker Compose
        if spec.deployment_config and spec.deployment_config.use_docker_compose:
            files["docker-compose.yml"] = self._generate_docker_compose(spec)

        # 전체 requirements.txt
        files["requirements.txt"] = "\n".join(spec.get_all_dependencies())

        return files

    def _generate_readme(self, spec: MultiProjectSpec) -> str:
        """README.md 생성 (개선된 버전)"""

        # Get frontend port if frontend exists
        frontend_port = spec.frontend_spec.port if spec.has_frontend() else 8600

        # 실행 순서 생성
        execution_steps = []
        if spec.has_backend() and spec.has_frontend():
            execution_steps = [
                "1️⃣ **Backend API 실행** (터미널 1)",
                "2️⃣ **Frontend UI 실행** (터미널 2)",
                "3️⃣ **브라우저에서 Frontend 접속**"
            ]
        elif spec.has_backend():
            execution_steps = ["1️⃣ **Backend API 실행**"]
        elif spec.has_frontend():
            execution_steps = ["1️⃣ **Frontend UI 실행**"]
        else:
            execution_steps = ["1️⃣ **에이전트 실행**"]

        # 프로젝트 정보 추출
        domain = spec.project.domain if hasattr(spec.project, 'domain') else "general"
        template_name = {
            "agent_only": "Agent-Only (에이전트만)",
            "agent_with_streamlit": "Agent + Streamlit UI",
            "full_stack": "Full-Stack (Backend + Frontend + Agent)",
            "chatbot": "Chatbot (대화형 인터페이스)"
        }.get(spec.template.value if hasattr(spec.template, 'value') else spec.template, spec.template)

        # 에이전트 정보 생성
        agents_section = ""
        if spec.agent_spec and spec.agent_spec.agents:
            agents_list = []
            for agent in spec.agent_spec.agents[:5]:  # 최대 5개만 표시
                role = agent.role
                goal = agent.goal[:80] + "..." if len(agent.goal) > 80 else agent.goal
                agents_list.append(f"- **{role}**: {goal}")
            agents_section = "\n".join(agents_list)
            if len(spec.agent_spec.agents) > 5:
                agents_section += f"\n- ... 외 {len(spec.agent_spec.agents) - 5}개 에이전트"
        else:
            agents_section = "- 에이전트 정보 없음"

        # 태스크 정보 생성
        tasks_section = ""
        if spec.agent_spec and spec.agent_spec.tasks:
            tasks_list = []
            for i, task in enumerate(spec.agent_spec.tasks[:5], 1):  # 최대 5개만 표시
                desc = task.description[:60] + "..." if len(task.description) > 60 else task.description
                tasks_list.append(f"{i}. {desc}")
            tasks_section = "\n".join(tasks_list)
            if len(spec.agent_spec.tasks) > 5:
                tasks_section += f"\n{len(spec.agent_spec.tasks) - 5}. ... 외 {len(spec.agent_spec.tasks) - 5}개 태스크"
        else:
            tasks_section = "1. 태스크 정보 없음"

        # API 엔드포인트 정보 생성
        api_endpoints_section = ""
        if spec.has_backend() and spec.backend_spec and spec.backend_spec.api_endpoints:
            api_list = []
            for endpoint in spec.backend_spec.api_endpoints:
                method = endpoint.method.value if hasattr(endpoint.method, 'value') else endpoint.method
                path = endpoint.path
                desc = endpoint.description[:60] + "..." if len(endpoint.description) > 60 else endpoint.description
                api_list.append(f"- `{method} {path}` - {desc}")
            api_endpoints_section = "\n".join(api_list)
        elif spec.has_backend():
            api_endpoints_section = "- `/api/run` (POST) - 에이전트 실행 및 결과 반환\n- `/api/health` (GET) - 서버 상태 확인"

        # UI 페이지 정보 생성
        ui_pages_section = ""
        if spec.has_frontend() and spec.frontend_spec and spec.frontend_spec.pages:
            pages_list = []
            for page in spec.frontend_spec.pages[:3]:  # 최대 3개만 표시
                title = page.title if hasattr(page, 'title') else page.get('title', 'Page')
                desc = page.description if hasattr(page, 'description') else page.get('description', '')
                desc = desc[:50] + "..." if desc and len(desc) > 50 else desc or "페이지 설명 없음"
                pages_list.append(f"- **{title}**: {desc}")
            ui_pages_section = "\n".join(pages_list)
            if len(spec.frontend_spec.pages) > 3:
                ui_pages_section += f"\n- ... 외 {len(spec.frontend_spec.pages) - 3}개 페이지"
        elif spec.has_frontend():
            ui_pages_section = "- **메인 페이지**: 에이전트 실행 및 결과 표시"

        # 워크플로우 타입
        workflow_type = ""
        if spec.agent_spec:
            wf = spec.agent_spec.workflow_type if hasattr(spec.agent_spec, 'workflow_type') else "sequential"
            workflow_type = {
                "sequential": "순차 실행 (Sequential)",
                "hierarchical": "계층적 실행 (Hierarchical)"
            }.get(wf, wf)

        # 기술 스택 생성
        tech_stack = []
        tech_stack.append("- **AI Framework**: CrewAI, LangChain")
        if spec.has_backend():
            framework = spec.backend_spec.framework.value if hasattr(spec.backend_spec.framework, 'value') else "fastapi"
            tech_stack.append(f"- **Backend**: {framework.upper()}, Uvicorn")
        if spec.has_frontend():
            framework = spec.frontend_spec.framework.value if hasattr(spec.frontend_spec.framework, 'value') else "streamlit"
            tech_stack.append(f"- **Frontend**: {framework.capitalize()}")
        if spec.has_database():
            db_type = spec.database_spec.db_type.value if hasattr(spec.database_spec.db_type, 'value') else "sqlite"
            tech_stack.append(f"- **Database**: {db_type.upper()}, SQLAlchemy")
        tech_stack.append("- **LLM**: OpenAI GPT")
        tech_stack_section = "\n".join(tech_stack)

        return f'''# {spec.project.name}

{spec.project.description}

**Generated by CAAS - Multi-Artifact Code Generation**

---

## 📊 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **도메인** | {domain} |
| **템플릿** | {template_name} |
| **워크플로우** | {workflow_type if workflow_type else "N/A"} |
| **에이전트 수** | {len(spec.agent_spec.agents) if spec.agent_spec and spec.agent_spec.agents else 0}개 |
| **태스크 수** | {len(spec.agent_spec.tasks) if spec.agent_spec and spec.agent_spec.tasks else 0}개 |

### 🎯 주요 기능

{tasks_section}

### 🤖 에이전트 구성

{agents_section}

{"### 🌐 API 엔드포인트" if spec.has_backend() else ""}
{"" if not spec.has_backend() else ""}
{api_endpoints_section if spec.has_backend() else ""}

{"### 🎨 UI 페이지" if spec.has_frontend() else ""}
{"" if not spec.has_frontend() else ""}
{ui_pages_section if spec.has_frontend() else ""}

### 🛠️ 기술 스택

{tech_stack_section}

---

## 📁 프로젝트 구조

```
{spec.project.name}/
├── agents/          # CrewAI 에이전트 시스템
{"├── backend/        # FastAPI 백엔드 API" if spec.has_backend() else ""}
{"├── frontend/       # Streamlit UI" if spec.has_frontend() else ""}
{"├── database/       # 데이터베이스 모델 및 마이그레이션" if spec.has_database() else ""}
├── requirements.txt # Python 패키지 의존성
├── .env.example     # 환경 변수 예제
└── README.md
```

## 🏗️ 아키텍처

{self._generate_architecture_diagram(spec)}

## 🚀 빠른 시작

### 1. 환경 설정

#### ⚠️ Python 버전 요구사항

이 프로젝트는 **Python 3.11**이 필요합니다.

```bash
# Python 버전 확인
python --version  # Python 3.11.x 이어야 함

# Python 3.11이 설치되어 있지 않다면:
# - Windows: https://www.python.org/downloads/
# - macOS: brew install python@3.11
# - Linux: sudo apt install python3.11 python3.11-venv
```

#### Python 가상환경 생성 (권장)

```bash
# Python 3.11로 가상환경 생성
python3.11 -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\\Scripts\\activate
```

#### 패키지 설치

```bash
pip install -r requirements.txt
```

#### 환경 변수 설정

`.env` 파일을 생성하고 API 키를 설정하세요:

```bash
cp .env.example .env
```

`.env` 파일 편집:

```env
# LLM API 키
OPENAI_API_KEY=sk-your-openai-api-key-here

# Backend 설정 (해당하는 경우)
{"API_HOST=0.0.0.0" if spec.has_backend() else ""}
{"API_PORT=8000" if spec.has_backend() else ""}

# Database 설정 (해당하는 경우)
{"DATABASE_URL=sqlite:///./app.db" if spec.has_database() else ""}
```

### 2. 실행 방법

{"#### ⚠️ 중요: 실행 순서" if spec.has_backend() and spec.has_frontend() else ""}
{"" if not (spec.has_backend() and spec.has_frontend()) else ""}
{"**반드시 아래 순서대로 실행하세요!**" if spec.has_backend() and spec.has_frontend() else ""}
{"" if not (spec.has_backend() and spec.has_frontend()) else ""}
{chr(10).join(execution_steps)}

{"#### 1️⃣ Backend API 실행 (터미널 1)" if spec.has_backend() else ""}
{chr(10) if spec.has_backend() else ""}
{"**먼저 Backend를 실행해야 합니다!**" if spec.has_backend() and spec.has_frontend() else ""}
{chr(10) if spec.has_backend() and spec.has_frontend() else ""}
{"```bash" if spec.has_backend() else ""}
{"cd backend" if spec.has_backend() else ""}
{"uvicorn main:app --reload" if spec.has_backend() else ""}
{"```" if spec.has_backend() else ""}
{chr(10) if spec.has_backend() else ""}
{"Backend가 실행되면 다음 메시지가 표시됩니다:" if spec.has_backend() else ""}
{"```" if spec.has_backend() else ""}
{"INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)" if spec.has_backend() else ""}
{"INFO:     Started reloader process" if spec.has_backend() else ""}
{"```" if spec.has_backend() else ""}
{chr(10) if spec.has_backend() else ""}
{"✅ API 문서: http://localhost:8000/docs" if spec.has_backend() else ""}
{chr(10) if spec.has_backend() else ""}

{"#### 2️⃣ Frontend UI 실행 (터미널 2)" if spec.has_frontend() else ""}
{chr(10) if spec.has_frontend() else ""}
{"**새 터미널을 열고 실행하세요:**" if spec.has_frontend() and spec.has_backend() else ""}
{chr(10) if spec.has_frontend() and spec.has_backend() else ""}
{"```bash" if spec.has_frontend() else ""}
{"cd frontend" if spec.has_frontend() else ""}
{"streamlit run app.py" if spec.has_frontend() else ""}
{"```" if spec.has_frontend() else ""}
{chr(10) if spec.has_frontend() else ""}
{"Frontend가 실행되면 자동으로 브라우저가 열립니다:" if spec.has_frontend() else ""}
{"```" if spec.has_frontend() else ""}
{"You can now view your Streamlit app in your browser." if spec.has_frontend() else ""}
{chr(10) if spec.has_frontend() else ""}
{f"  Local URL: http://localhost:{frontend_port}" if spec.has_frontend() else ""}
{f"  Network URL: http://192.168.x.x:{frontend_port}" if spec.has_frontend() else ""}
{"```" if spec.has_frontend() else ""}
{chr(10) if spec.has_frontend() else ""}
{f"✅ Frontend URL: http://localhost:{frontend_port}" if spec.has_frontend() else ""}
{chr(10) if spec.has_frontend() else ""}

{"#### 3️⃣ 에이전트만 실행 (Backend/Frontend 없이)" if not spec.has_backend() and not spec.has_frontend() else ""}
{chr(10) if not spec.has_backend() and not spec.has_frontend() else ""}
{"```bash" if not spec.has_backend() and not spec.has_frontend() else ""}
{"cd agents" if not spec.has_backend() and not spec.has_frontend() else ""}
{"python main.py" if not spec.has_backend() and not spec.has_frontend() else ""}
{"```" if not spec.has_backend() and not spec.has_frontend() else ""}

## 💡 사용 예제

{"### API 호출 예제" if spec.has_backend() else ""}
{"" if not spec.has_backend() else ""}
{self._generate_api_usage_example(spec) if spec.has_backend() else ""}

{"### UI 사용 방법" if spec.has_frontend() else ""}
{"" if not spec.has_frontend() else ""}
{self._generate_ui_usage_guide(spec, frontend_port) if spec.has_frontend() else ""}

{"### Python 코드에서 에이전트 직접 실행" if spec.agent_spec else ""}
{"" if not spec.agent_spec else ""}
{self._generate_agent_usage_example(spec) if spec.agent_spec else ""}

## 🛠️ 트러블슈팅

### Backend 연결 오류

Frontend에서 "Connection refused" 오류가 발생하면:

1. **Backend가 실행 중인지 확인**
   ```bash
   # 다른 터미널에서
   curl http://localhost:8000/health
   ```

2. **포트가 이미 사용 중인지 확인**
   ```bash
   # macOS/Linux
   lsof -i :8000

   # Windows
   netstat -ano | findstr :8000
   ```

3. **Backend를 먼저 실행했는지 확인**
   - Frontend보다 Backend를 먼저 실행해야 합니다

### Frontend 포트 변경

기본 포트({frontend_port})를 변경하려면:

```bash
cd frontend
streamlit run app.py --server.port {frontend_port + 1}
```

### 환경 변수 로드 안됨

`.env` 파일이 프로젝트 루트에 있는지 확인하세요:

```bash
ls -la .env  # macOS/Linux
dir .env     # Windows
```

### CrewAI Signal Handler 오류 (Streamlit)

Streamlit에서 "ValueError: signal only works in main thread" 오류가 발생하면:

**해결 방법 1: 환경 변수 설정 (권장)**

`.env` 파일에 다음을 추가:
```env
OTEL_SDK_DISABLED=true
```

**해결 방법 2: 이미 코드에 적용됨**

생성된 `frontend/app.py`에는 이미 다음 코드가 포함되어 있습니다:
```python
os.environ["OTEL_SDK_DISABLED"] = "true"
```

이 설정은 CrewAI telemetry를 비활성화하여 Streamlit과의 signal handler 충돌을 방지합니다.

## 📝 라이센스

MIT License
'''

    def _generate_gitignore(self) -> str:
        """.gitignore 생성"""
        return '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/

# Environment
.env
.env.local

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Database
*.db
*.sqlite
*.sqlite3

# Logs
*.log

# OS
.DS_Store
Thumbs.db
'''

    def _generate_docker_compose(self, spec: MultiProjectSpec) -> str:
        """docker-compose.yml 생성"""
        services = []

        if spec.has_backend():
            services.append('''  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./backend:/app''')

        if spec.has_frontend():
            frontend_port = spec.frontend_spec.port
            services.append(f'''  frontend:
    build: ./frontend
    ports:
      - "{frontend_port}:{frontend_port}"
    depends_on:
      - backend''')

        return f'''version: '3.8'

services:
{chr(10).join(services)}
'''

    def _generate_architecture_diagram(self, spec: MultiProjectSpec) -> str:
        """아키텍처 다이어그램 생성"""

        # Get frontend port if frontend exists
        frontend_port = spec.frontend_spec.port if spec.has_frontend() else 8600

        # Full Stack 구조
        if spec.has_backend() and spec.has_frontend():
            return f'''
```
┌─────────────────┐
│   Frontend UI   │  Streamlit (Port {frontend_port})
│   (Streamlit)   │  - 사용자 입력 받기
└────────┬────────┘  - 결과 표시
         │
         │ HTTP Request
         ↓
┌─────────────────┐
│  Backend API    │  FastAPI (Port 8000)
│   (FastAPI)     │  - API 엔드포인트 제공
└────────┬────────┘  - 요청 검증
         │
         │ Function Call
         ↓
┌─────────────────┐
│ CrewAI Agents   │  Multi-Agent System
│   (agents/)     │  - 태스크 실행
└─────────────────┘  - 협업 워크플로우
```

**데이터 흐름:**
1. 사용자가 Frontend UI에서 입력
2. Frontend → Backend API 호출 (HTTP POST)
3. Backend → CrewAI 에이전트 실행
4. 에이전트가 태스크 수행
5. Backend ← 결과 반환
6. Frontend ← API 응답
7. 사용자에게 결과 표시
'''
        # Backend + Agent (UI 없음)
        elif spec.has_backend():
            return '''
```
┌─────────────────┐
│  External App   │  외부 클라이언트
│  (API Client)   │  - curl, Python, etc.
└────────┬────────┘
         │
         │ HTTP Request
         ↓
┌─────────────────┐
│  Backend API    │  FastAPI (Port 8000)
│   (FastAPI)     │  - RESTful API 제공
└────────┬────────┘  - 요청 처리
         │
         │ Function Call
         ↓
┌─────────────────┐
│ CrewAI Agents   │  Multi-Agent System
│   (agents/)     │  - 태스크 실행
└─────────────────┘  - 협업 워크플로우
```

**API 중심 아키텍처:**
- RESTful API로 에이전트 기능 제공
- 외부 시스템과 통합 가능
'''
        # Frontend + Agent (Standalone)
        elif spec.has_frontend():
            return f'''
```
┌─────────────────┐
│   Frontend UI   │  Streamlit (Port {frontend_port})
│   (Streamlit)   │  - 사용자 입력 받기
└────────┬────────┘  - 결과 표시
         │
         │ Direct Import
         ↓
┌─────────────────┐
│ CrewAI Agents   │  Multi-Agent System
│   (agents/)     │  - 태스크 실행
└─────────────────┘  - 협업 워크플로우
```

**Standalone 구조:**
- Backend API 없이 직접 에이전트 실행
- 단순하고 빠른 프로토타입에 적합
'''
        # Agent Only
        else:
            return '''
```
┌─────────────────┐
│ Python Script   │  CLI 또는 스크립트
│   (main.py)     │  - 직접 실행
└────────┬────────┘
         │
         │ Function Call
         ↓
┌─────────────────┐
│ CrewAI Agents   │  Multi-Agent System
│   (agents/)     │  - 태스크 실행
└─────────────────┘  - 협업 워크플로우
```

**Python 라이브러리 구조:**
- 다른 프로젝트에서 import하여 사용
- 재사용 가능한 에이전트 모듈
'''

    def _generate_api_usage_example(self, spec: MultiProjectSpec) -> str:
        """API 사용 예제 생성"""
        if not spec.has_backend():
            return ""

        # 첫 번째 API 엔드포인트 찾기
        if spec.backend_spec and spec.backend_spec.api_endpoints:
            endpoint = spec.backend_spec.api_endpoints[0]
            path = endpoint.path
            method = endpoint.method.value if hasattr(endpoint.method, 'value') else endpoint.method
        else:
            path = "/api/run"
            method = "POST"

        if method == "POST":
            return f'''
**curl 예제:**

```bash
curl -X POST http://localhost:8000{path} \\
  -H "Content-Type: application/json" \\
  -d '{{"input_data": {{"text": "your input here"}}}}'
```

**Python 예제:**

```python
import requests

response = requests.post(
    "http://localhost:8000{path}",
    json={{"input_data": {{"text": "your input here"}}}}
)

result = response.json()
print(result)
```

**응답 형식:**

```json
{{
  "success": true,
  "result": "에이전트 실행 결과..."
}}
```
'''
        else:
            return f'''
**curl 예제:**

```bash
curl http://localhost:8000{path}
```

**Python 예제:**

```python
import requests

response = requests.get("http://localhost:8000{path}")
result = response.json()
print(result)
```
'''

    def _generate_ui_usage_guide(self, spec: MultiProjectSpec, frontend_port: int = 8600) -> str:
        """UI 사용 가이드 생성"""
        if not spec.has_frontend():
            return ""

        # UI 페이지가 있으면 첫 페이지 정보 사용
        if spec.frontend_spec and spec.frontend_spec.pages:
            page = spec.frontend_spec.pages[0]
            title = page.title if hasattr(page, 'title') else "Main Page"

            steps = [
                f"1. 브라우저에서 http://localhost:{frontend_port} 접속",
                f"2. **{title}** 페이지가 표시됩니다",
                "3. 입력 필드에 데이터를 입력하세요",
                "4. 실행 버튼을 클릭하여 에이전트를 실행합니다",
                "5. 결과가 화면에 표시됩니다"
            ]
        else:
            steps = [
                f"1. 브라우저에서 http://localhost:{frontend_port} 접속",
                "2. 입력 필드에 요청 내용을 입력하세요",
                "3. '🚀 실행' 버튼을 클릭합니다",
                "4. 에이전트가 작업을 수행하는 동안 로딩 표시가 나타납니다",
                "5. 완료되면 결과가 화면에 표시됩니다"
            ]

        return "\n".join(steps)

    def _generate_agent_usage_example(self, spec: MultiProjectSpec) -> str:
        """에이전트 직접 실행 예제 생성"""
        if not spec.agent_spec:
            return ""

        return '''
**agents/crew.py에서 직접 실행:**

```python
from crew import run_crew

# 에이전트 실행
result = run_crew(inputs={{"text": "your input here"}})
print(result)
```

**커스텀 입력으로 실행:**

```python
from crew import run_crew

# 커스텀 입력
custom_input = {{
    "text": "분석할 내용",
    "additional_param": "추가 파라미터"
}}

result = run_crew(inputs=custom_input)
print(f"결과: {{result}}")
```
'''

    def _validate_and_format_files(self, files: Dict[str, str]) -> Dict[str, str]:
        """
        생성된 모든 Python 파일의 구문을 검증하고 포맷팅합니다.

        Args:
            files: 파일명 -> 내용 매핑

        Returns:
            Dict[str, str]: 검증 및 포맷팅된 파일 매핑
        """
        fixed_files = {}
        total_python_files = 0
        fixed_count = 0
        error_count = 0

        for filename, content in files.items():
            if not filename.endswith('.py'):
                # Python 파일이 아니면 그대로 유지
                fixed_files[filename] = content
                continue

            total_python_files += 1

            try:
                # 1. 구문 검증
                ast.parse(content)
                self.logger.debug(f"✅ 구문 정상: {filename}")

                # 2. 포맷팅 적용
                try:
                    formatted = self.formatter.format_code(content)
                    fixed_files[filename] = formatted
                except Exception as e:
                    self.logger.warning(f"⚠️ 포맷팅 실패 (원본 사용): {filename} - {e}")
                    fixed_files[filename] = content

            except SyntaxError as e:
                self.logger.warning(
                    f"⚠️ 구문 오류 발견: {filename}:{e.lineno} - {e.msg}"
                )

                # 자동 포맷팅으로 수정 시도
                try:
                    self.logger.info(f"🔧 자동 포맷팅 시도: {filename}")
                    formatted = self.formatter.format_code(content)

                    # 포맷팅 후 재검증
                    ast.parse(formatted)
                    self.logger.info(f"✅ 자동 수정 완료: {filename}")
                    fixed_files[filename] = formatted
                    fixed_count += 1

                except SyntaxError as e2:
                    # 포맷팅으로도 수정 불가
                    error_context = f"\n코드: {e2.text.strip()}" if e2.text else ""

                    self.logger.error(
                        f"❌ 자동 수정 실패: {filename}:{e2.lineno}\n"
                        f"오류: {e2.msg}{error_context}"
                    )

                    # 원본 유지하되 오류 카운트 증가
                    fixed_files[filename] = content
                    error_count += 1

                    # 경고 메시지 출력 (예외는 발생시키지 않음)
                    self.logger.warning(
                        f"⚠️ {filename}에 수정 불가능한 구문 오류가 있습니다. "
                        f"생성된 파일을 수동으로 검토하세요."
                    )

                except Exception as fmt_error:
                    # 포맷팅 자체가 실패
                    self.logger.error(f"❌ 포맷팅 실패: {filename} - {fmt_error}")
                    fixed_files[filename] = content
                    error_count += 1

        # 요약 로그
        self.logger.info(
            f"코드 검증 완료: Python 파일 {total_python_files}개, "
            f"자동 수정 {fixed_count}개, 오류 {error_count}개"
        )

        if error_count > 0:
            self.logger.warning(
                f"⚠️ {error_count}개 파일에 구문 오류가 있습니다. "
                f"생성된 코드를 반드시 검토하세요."
            )

        return fixed_files

    def _prefix_paths(self, files: Dict[str, str], prefix: str) -> Dict[str, str]:
        """파일 경로에 접두사 추가"""
        return {f"{prefix}{path}": content for path, content in files.items()}
