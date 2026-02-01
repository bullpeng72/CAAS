"""
Multi-Artifact Code Generator

다양한 타입의 코드 아티팩트(Agent, UI, Backend, DB Schema 등)를 생성하는 통합 시스템
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

from app.utils.logger import get_logger

logger = get_logger("artifact_generator")


class ArtifactType(str, Enum):
    """생성 가능한 아티팩트 타입"""
    CREWAI_AGENT = "crewai_agent"  # CrewAI Agent 코드
    UI_COMPONENT = "ui_component"  # UI 컴포넌트 (Streamlit/React)
    BACKEND_API = "backend_api"  # Backend API (FastAPI)
    DATABASE_SCHEMA = "database_schema"  # DB Schema (SQLAlchemy)
    TEST_CODE = "test_code"  # 테스트 코드
    DOCKER_CONFIG = "docker_config"  # Docker 설정
    CI_CD_CONFIG = "ci_cd_config"  # CI/CD 설정


class ArtifactMetadata(BaseModel):
    """아티팩트 메타데이터"""
    type: ArtifactType
    name: str
    description: str
    dependencies: List[str] = []  # 의존하는 다른 아티팩트
    framework: Optional[str] = None  # 사용 프레임워크 (streamlit, fastapi 등)
    language: str = "python"


class GeneratedArtifact(BaseModel):
    """생성된 아티팩트"""
    metadata: ArtifactMetadata
    file_path: str
    code: str
    imports: List[str] = []
    quality_score: float = Field(default=0.8, ge=0.0, le=1.0)


class BaseArtifactGenerator(ABC):
    """
    아티팩트 생성기 기본 클래스

    모든 아티팩트 생성기가 상속해야 하는 추상 클래스
    """

    def __init__(self):
        self.logger = logger

    @abstractmethod
    def generate(
        self,
        requirement: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedArtifact:
        """
        아티팩트를 생성합니다.

        Args:
            requirement: 요구사항 (RequirementAnalysis, ArchitectureDesign 등)
            context: 추가 컨텍스트 (다른 아티팩트 정보 등)

        Returns:
            GeneratedArtifact: 생성된 아티팩트
        """

    @abstractmethod
    def validate(self, artifact: GeneratedArtifact) -> bool:
        """
        생성된 아티팩트를 검증합니다.

        Args:
            artifact: 생성된 아티팩트

        Returns:
            bool: 검증 성공 여부
        """

    def _build_imports(self, dependencies: List[str]) -> List[str]:
        """필요한 import 문을 생성합니다"""
        imports = []
        for dep in dependencies:
            if dep == "crewai":
                imports.extend([
                    "from crewai import Agent, Task, Crew, Process",
                    "from crewai.tools import BaseTool",
                ])
            elif dep == "langchain":
                imports.append("from langchain.tools import Tool")
            elif dep == "pydantic":
                imports.append("from pydantic import BaseModel, Field")
            elif dep == "fastapi":
                imports.extend([
                    "from fastapi import FastAPI, HTTPException",
                    "from pydantic import BaseModel",
                ])
            elif dep == "streamlit":
                imports.append("import streamlit as st")
            elif dep == "sqlalchemy":
                imports.extend([
                    "from sqlalchemy import Column, Integer, String, DateTime",
                    "from sqlalchemy.ext.declarative import declarative_base",
                ])

        return imports

    def _calculate_quality_score(self, code: str) -> float:
        """생성된 코드의 품질 점수를 계산합니다"""
        score = 1.0

        # 기본 품질 검사
        if len(code) < 100:
            score -= 0.3  # 너무 짧음

        if "TODO" in code or "FIXME" in code:
            score -= 0.1  # TODO 있음

        if code.count("import") > 20:
            score -= 0.1  # import 너무 많음

        # 코드 구조 검사
        if "class" not in code and "def" not in code:
            score -= 0.2  # 구조 없음

        return max(0.0, min(1.0, score))


class MultiArtifactOrchestrator:
    """
    Multi-Artifact 생성 조율기

    여러 타입의 아티팩트를 순서대로 생성하고 의존성을 관리합니다.
    """

    def __init__(self):
        self.generators: Dict[ArtifactType, BaseArtifactGenerator] = {}
        self.logger = logger

    def register_generator(
        self,
        artifact_type: ArtifactType,
        generator: BaseArtifactGenerator,
    ):
        """아티팩트 생성기를 등록합니다"""
        self.generators[artifact_type] = generator
        self.logger.info(f"Generator registered: {artifact_type}")

    def generate_all(
        self,
        requirement: Dict[str, Any],
        artifact_types: List[ArtifactType],
    ) -> Dict[ArtifactType, GeneratedArtifact]:
        """
        여러 아티팩트를 생성합니다.

        Args:
            requirement: 요구사항
            artifact_types: 생성할 아티팩트 타입 목록

        Returns:
            Dict[ArtifactType, GeneratedArtifact]: 생성된 아티팩트 맵
        """
        self.logger.info(f"Generating {len(artifact_types)} artifacts")

        generated = {}
        context = {"requirement": requirement}

        # 의존성 순서로 정렬 (간단한 버전)
        sorted_types = self._sort_by_dependencies(artifact_types)

        for artifact_type in sorted_types:
            if artifact_type not in self.generators:
                self.logger.warning(f"No generator for {artifact_type}")
                continue

            generator = self.generators[artifact_type]

            try:
                # 이전에 생성된 아티팩트를 컨텍스트에 추가
                context["generated_artifacts"] = generated

                artifact = generator.generate(requirement, context)

                # 검증
                if generator.validate(artifact):
                    generated[artifact_type] = artifact
                    self.logger.info(f"✓ Generated: {artifact_type}")
                else:
                    self.logger.warning(f"✗ Validation failed: {artifact_type}")

            except Exception as e:
                self.logger.error(f"Error generating {artifact_type}: {e}")

        self.logger.info(f"Generation complete: {len(generated)}/{len(artifact_types)} succeeded")
        return generated

    def _sort_by_dependencies(
        self,
        artifact_types: List[ArtifactType],
    ) -> List[ArtifactType]:
        """
        의존성 순서로 아티팩트 타입을 정렬합니다.

        간단한 구현: 미리 정의된 순서 사용
        """
        # 우선순위 정의
        priority = {
            ArtifactType.DATABASE_SCHEMA: 1,  # DB 스키마가 먼저
            ArtifactType.BACKEND_API: 2,  # Backend가 그 다음
            ArtifactType.CREWAI_AGENT: 3,  # Agent
            ArtifactType.UI_COMPONENT: 4,  # UI가 마지막
            ArtifactType.TEST_CODE: 5,
            ArtifactType.DOCKER_CONFIG: 6,
            ArtifactType.CI_CD_CONFIG: 7,
        }

        return sorted(artifact_types, key=lambda t: priority.get(t, 99))

    def export_artifacts(
        self,
        artifacts: Dict[ArtifactType, GeneratedArtifact],
        output_dir: str,
    ) -> List[str]:
        """
        생성된 아티팩트를 파일로 저장합니다.

        Args:
            artifacts: 생성된 아티팩트 맵
            output_dir: 출력 디렉토리

        Returns:
            List[str]: 생성된 파일 경로 목록
        """
        import os

        file_paths = []

        for artifact_type, artifact in artifacts.items():
            file_path = os.path.join(output_dir, artifact.file_path)

            # 디렉토리 생성
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 파일 쓰기
            with open(file_path, "w", encoding="utf-8") as f:
                # imports 먼저 작성
                if artifact.imports:
                    f.write("\n".join(artifact.imports))
                    f.write("\n\n")

                # 코드 작성
                f.write(artifact.code)

            file_paths.append(file_path)
            self.logger.info(f"Exported: {file_path}")

        return file_paths


class CrewAIAgentGenerator(BaseArtifactGenerator):
    """CrewAI Agent 코드 생성기"""

    def generate(
        self,
        requirement: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedArtifact:
        """CrewAI Agent 코드를 생성합니다"""
        self.logger.info("Generating CrewAI Agent code")

        # Agent 정보 추출
        agents = requirement.get("agents", [])
        tasks = requirement.get("tasks", [])
        project_name = requirement.get("project_name", "my_crew")

        # 코드 생성
        code_lines = [
            '"""',
            f'{project_name.replace("_", " ").title()} - CrewAI Agent System',
            '"""',
            "",
            "# Agent definitions",
        ]

        # Agent 생성 코드
        for agent in agents:
            agent_id = agent.get("id", "agent")
            role = agent.get("role", "Agent")
            goal = agent.get("goal", "Perform tasks")

            code_lines.extend([
                f"",
                f"{agent_id} = Agent(",
                f'    role="{role}",',
                f'    goal="{goal}",',
                f'    backstory="""Your backstory here.""",',
                f"    allow_delegation=False,",
                f"    verbose=True,",
                f")",
            ])

        # Task 생성 코드
        code_lines.append("\n# Task definitions")
        for task in tasks:
            task_id = task.get("id", "task")
            description = task.get("description", "Task description")
            agent_ref = task.get("agent", "agent")

            code_lines.extend([
                f"",
                f"{task_id} = Task(",
                f'    description="{description}",',
                f'    expected_output="Expected output here",',
                f"    agent={agent_ref},",
                f")",
            ])

        # Crew 생성 코드
        task_ids = [t.get("id", "task") for t in tasks]
        code_lines.extend([
            "",
            "# Create Crew",
            "crew = Crew(",
            f"    agents=[{', '.join([a.get('id', 'agent') for a in agents])}],",
            f"    tasks=[{', '.join(task_ids)}],",
            "    process=Process.sequential,",
            "    verbose=True,",
            ")",
            "",
            "# Run the crew",
            "if __name__ == '__main__':",
            '    result = crew.kickoff()',
            "    print(result)",
        ])

        code = "\n".join(code_lines)
        imports = self._build_imports(["crewai"])

        metadata = ArtifactMetadata(
            type=ArtifactType.CREWAI_AGENT,
            name=project_name,
            description="CrewAI Multi-Agent System",
            framework="crewai",
        )

        quality_score = self._calculate_quality_score(code)

        return GeneratedArtifact(
            metadata=metadata,
            file_path=f"{project_name}/crew.py",
            code=code,
            imports=imports,
            quality_score=quality_score,
        )

    def validate(self, artifact: GeneratedArtifact) -> bool:
        """생성된 코드를 검증합니다"""
        code = artifact.code

        # 기본 검증
        required_keywords = ["Agent", "Task", "Crew"]
        for keyword in required_keywords:
            if keyword not in code:
                self.logger.error(f"Missing required keyword: {keyword}")
                return False

        # 문법 검증 (간단한 버전)
        try:
            compile(artifact.code, "<string>", "exec")
            return True
        except SyntaxError as e:
            self.logger.error(f"Syntax error: {e}")
            return False
