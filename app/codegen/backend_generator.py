"""
Backend API & Database Schema Generator

FastAPI Backend와 SQLAlchemy Database Schema 자동 생성
"""

from typing import Dict, Any, Optional
from app.codegen.artifact_generator import (
    BaseArtifactGenerator,
    GeneratedArtifact,
    ArtifactMetadata,
    ArtifactType,
)
from app.utils.logger import get_logger

logger = get_logger("backend_generator")


class FastAPIGenerator(BaseArtifactGenerator):
    """FastAPI Backend API 생성기"""

    def generate(
        self,
        requirement: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedArtifact:
        """FastAPI Backend을 생성합니다"""
        self.logger.info("Generating FastAPI Backend")

        # API 정보 추출
        backend_apis = requirement.get("backend_apis", [])
        project_name = requirement.get("project_name", "my_api")

        if not backend_apis:
            # 기본 API 엔드포인트 생성
            backend_apis = [
                {
                    "path": "/",
                    "method": "GET",
                    "description": "Root endpoint",
                },
                {
                    "path": "/health",
                    "method": "GET",
                    "description": "Health check",
                },
            ]

        # 코드 생성
        code_lines = [
            '"""',
            f'{project_name.replace("_", " ").title()} API',
            '"""',
            "",
            "app = FastAPI(",
            f'    title="{project_name.title()}",',
            f'    description="API for {project_name}",',
            '    version="1.0.0",',
            ")",
            "",
            "# Request/Response models",
            "class RequestModel(BaseModel):",
            '    input: str',
            "",
            "class ResponseModel(BaseModel):",
            '    output: str',
            '    status: str = "success"',
            "",
        ]

        # API 엔드포인트 생성
        for api in backend_apis:
            path = api.get("path", "/")
            method = api.get("method", "GET").lower()
            description = api.get("description", "API endpoint")

            if method == "get":
                code_lines.extend([
                    f'@app.get("{path}")',
                    f'async def {path.replace("/", "").replace("-", "_") or "root"}():',
                    f'    """{description}"""',
                    f'    return {{"message": "Success"}}',
                    "",
                ])
            elif method == "post":
                code_lines.extend([
                    f'@app.post("{path}")',
                    f'async def {path.replace("/", "").replace("-", "_")}(request: RequestModel):',
                    f'    """{description}"""',
                    f'    # Process request',
                    f'    return ResponseModel(output=f"Processed: {{request.input}}")',
                    "",
                ])

        # Health check (항상 포함)
        code_lines.extend([
            '@app.get("/health")',
            'async def health_check():',
            '    """Health check endpoint"""',
            '    return {"status": "healthy"}',
            "",
            "if __name__ == '__main__':",
            "    import uvicorn",
            '    uvicorn.run(app, host="0.0.0.0", port=8001)',
        ])

        code = "\n".join(code_lines)
        imports = self._build_imports(["fastapi"])

        metadata = ArtifactMetadata(
            type=ArtifactType.BACKEND_API,
            name=f"{project_name}_api",
            description="FastAPI Backend Service",
            framework="fastapi",
        )

        quality_score = self._calculate_quality_score(code)

        return GeneratedArtifact(
            metadata=metadata,
            file_path=f"{project_name}/api/main.py",
            code=code,
            imports=imports,
            quality_score=quality_score,
        )

    def validate(self, artifact: GeneratedArtifact) -> bool:
        """생성된 API 코드를 검증합니다"""
        code = artifact.code

        # FastAPI 필수 요소 확인
        if "FastAPI" not in code or "@app." not in code:
            self.logger.error("Missing FastAPI components")
            return False

        # 문법 검증
        try:
            compile(code, "<string>", "exec")
            return True
        except SyntaxError as e:
            self.logger.error(f"Syntax error: {e}")
            return False


class SQLAlchemySchemaGenerator(BaseArtifactGenerator):
    """SQLAlchemy Database Schema 생성기"""

    def generate(
        self,
        requirement: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedArtifact:
        """SQLAlchemy DB Schema를 생성합니다"""
        self.logger.info("Generating SQLAlchemy Schema")

        # Database 테이블 정보 추출
        database_tables = requirement.get("database_tables", [])
        project_name = requirement.get("project_name", "my_app")

        if not database_tables:
            # 기본 테이블 생성
            database_tables = ["user", "session", "log"]

        # 코드 생성
        code_lines = [
            '"""',
            f'{project_name.replace("_", " ").title()} Database Models',
            '"""',
            "",
            "Base = declarative_base()",
            "",
        ]

        # 각 테이블에 대한 모델 생성
        for table_name in database_tables:
            class_name = table_name.title().replace("_", "")

            code_lines.extend([
                f"class {class_name}(Base):",
                f'    __tablename__ = "{table_name}"',
                "",
                "    id = Column(Integer, primary_key=True, index=True)",
                f"    name = Column(String, index=True)",
                f"    created_at = Column(DateTime, default=datetime.utcnow)",
                f"    updated_at = Column(DateTime, onupdate=datetime.utcnow)",
                "",
                "    def __repr__(self):",
                f'        return f"<{class_name}(id={{self.id}}, name={{self.name}})>"',
                "",
            ])

        # Database 연결 설정
        code_lines.extend([
            "# Database setup",
            'DATABASE_URL = "sqlite:///./app.db"',
            "",
            "engine = create_engine(DATABASE_URL)",
            "SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)",
            "",
            "def init_db():",
            '    """Initialize database tables"""',
            "    Base.metadata.create_all(bind=engine)",
            "",
            "def get_db():",
            '    """Get database session"""',
            "    db = SessionLocal()",
            "    try:",
            "        yield db",
            "    finally:",
            "        db.close()",
        ])

        code = "\n".join(code_lines)

        imports = self._build_imports(["sqlalchemy"])
        imports.extend([
            "from datetime import datetime",
            "from sqlalchemy import create_engine",
            "from sqlalchemy.orm import sessionmaker",
        ])

        metadata = ArtifactMetadata(
            type=ArtifactType.DATABASE_SCHEMA,
            name=f"{project_name}_models",
            description="SQLAlchemy Database Models",
            framework="sqlalchemy",
            dependencies=["backend_api"],
        )

        quality_score = self._calculate_quality_score(code)

        return GeneratedArtifact(
            metadata=metadata,
            file_path=f"{project_name}/database/models.py",
            code=code,
            imports=imports,
            quality_score=quality_score,
        )

    def validate(self, artifact: GeneratedArtifact) -> bool:
        """생성된 Schema 코드를 검증합니다"""
        code = artifact.code

        # SQLAlchemy 필수 요소 확인
        required = ["Base", "Column", "Table"]
        for req in required:
            if req not in code:
                self.logger.error(f"Missing required element: {req}")
                return False

        # 문법 검증
        try:
            compile(code, "<string>", "exec")
            return True
        except SyntaxError as e:
            self.logger.error(f"Syntax error: {e}")
            return False
