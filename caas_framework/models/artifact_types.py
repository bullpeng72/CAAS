"""
Artifact Types

개발 산출물 타입 정의
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    """산출물 타입"""

    PROJECT_PROPOSAL = "project_proposal"
    """프로젝트 기획서 - 초기 요구사항 기반"""

    REQUIREMENTS_SPEC = "requirements_spec"
    """요구사항 명세서 - Golden Data 기반"""

    ARCHITECTURE_DESIGN = "architecture_design"
    """아키텍처 설계서 - BMAD 매핑 기반"""

    DATA_DESIGN = "data_design"
    """데이터 설계서 - 데이터 모델 기반"""

    API_DESIGN = "api_design"
    """API 설계서 - 인터페이스 설계"""

    AGENT_DESIGN = "agent_design"
    """에이전트 설계서 - Agent/Task 상세"""

    TEST_PLAN = "test_plan"
    """테스트 계획서 - 테스트 전략"""

    TEST_REPORT = "test_report"
    """테스트 결과 리포트 - 실행 결과 및 커버리지"""

    CODE_REVIEW = "code_review"
    """코드 리뷰 리포트 - 품질, 보안, 성능 분석"""

    DEPLOYMENT_GUIDE = "deployment_guide"
    """배포 가이드 - 배포 절차"""


class ArtifactFormat(str, Enum):
    """산출물 포맷"""

    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    JSON = "json"


class ArtifactMetadata(BaseModel):
    """산출물 메타데이터"""

    artifact_type: ArtifactType = Field(..., description="산출물 타입")
    format: ArtifactFormat = Field(default=ArtifactFormat.MARKDOWN, description="산출물 포맷")
    title: str = Field(..., description="산출물 제목")
    version: str = Field(default="1.0.0", description="버전")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시각")
    created_by: str = Field(default="CAAS", description="생성자")
    project_name: Optional[str] = Field(default=None, description="프로젝트 이름")
    description: Optional[str] = Field(default=None, description="설명")
    tags: List[str] = Field(default_factory=list, description="태그")


class Artifact(BaseModel):
    """산출물"""

    metadata: ArtifactMetadata = Field(..., description="메타데이터")
    content: str = Field(..., description="산출물 내용")
    file_path: Optional[str] = Field(default=None, description="저장된 파일 경로")
    related_artifacts: List[str] = Field(default_factory=list, description="관련 산출물 ID")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ArtifactGenerationConfig(BaseModel):
    """산출물 생성 설정"""

    enabled: bool = Field(default=False, description="산출물 생성 활성화")

    # 생성할 산출물 타입 선택
    generate_project_proposal: bool = Field(default=True, description="프로젝트 기획서 생성")
    generate_requirements_spec: bool = Field(default=True, description="요구사항 명세서 생성")
    generate_architecture_design: bool = Field(default=True, description="아키텍처 설계서 생성")
    generate_data_design: bool = Field(default=True, description="데이터 설계서 생성")
    generate_api_design: bool = Field(default=False, description="API 설계서 생성")
    generate_agent_design: bool = Field(default=True, description="에이전트 설계서 생성")
    generate_test_plan: bool = Field(default=False, description="테스트 계획서 생성")
    generate_test_report: bool = Field(default=False, description="테스트 결과 리포트 생성")
    generate_code_review: bool = Field(default=False, description="코드 리뷰 리포트 생성")
    generate_deployment_guide: bool = Field(default=False, description="배포 가이드 생성")

    # 포맷 설정
    output_format: ArtifactFormat = Field(default=ArtifactFormat.MARKDOWN, description="출력 포맷")
    output_directory: str = Field(default="./artifacts", description="출력 디렉토리")

    # 추가 옵션
    include_diagrams: bool = Field(default=True, description="다이어그램 포함")
    include_code_samples: bool = Field(default=True, description="코드 샘플 포함")
    language: str = Field(default="ko", description="언어 (ko/en)")

    def get_enabled_artifact_types(self) -> List[ArtifactType]:
        """활성화된 산출물 타입 목록 반환"""
        if not self.enabled:
            return []

        enabled_types = []

        if self.generate_project_proposal:
            enabled_types.append(ArtifactType.PROJECT_PROPOSAL)
        if self.generate_requirements_spec:
            enabled_types.append(ArtifactType.REQUIREMENTS_SPEC)
        if self.generate_architecture_design:
            enabled_types.append(ArtifactType.ARCHITECTURE_DESIGN)
        if self.generate_data_design:
            enabled_types.append(ArtifactType.DATA_DESIGN)
        if self.generate_api_design:
            enabled_types.append(ArtifactType.API_DESIGN)
        if self.generate_agent_design:
            enabled_types.append(ArtifactType.AGENT_DESIGN)
        if self.generate_test_plan:
            enabled_types.append(ArtifactType.TEST_PLAN)
        if self.generate_test_report:
            enabled_types.append(ArtifactType.TEST_REPORT)
        if self.generate_code_review:
            enabled_types.append(ArtifactType.CODE_REVIEW)
        if self.generate_deployment_guide:
            enabled_types.append(ArtifactType.DEPLOYMENT_GUIDE)

        return enabled_types


def get_artifact_description(artifact_type: ArtifactType) -> str:
    """산출물 타입 설명 반환"""
    descriptions = {
        ArtifactType.PROJECT_PROPOSAL: "프로젝트 기획서 - 프로젝트 목적, 범위, 목표를 정의",
        ArtifactType.REQUIREMENTS_SPEC: "요구사항 명세서 - 기능/비기능 요구사항 상세 정의",
        ArtifactType.ARCHITECTURE_DESIGN: "아키텍처 설계서 - 시스템 구조 및 컴포넌트 설계",
        ArtifactType.DATA_DESIGN: "데이터 설계서 - 데이터 모델 및 스키마 정의",
        ArtifactType.API_DESIGN: "API 설계서 - REST API 엔드포인트 및 인터페이스 정의",
        ArtifactType.AGENT_DESIGN: "에이전트 설계서 - AI 에이전트 역할 및 태스크 상세",
        ArtifactType.TEST_PLAN: "테스트 계획서 - 테스트 전략 및 시나리오",
        ArtifactType.TEST_REPORT: "테스트 결과 리포트 - 테스트 실행 결과 및 커버리지 분석",
        ArtifactType.CODE_REVIEW: "코드 리뷰 리포트 - 코드 품질, 보안, 성능 분석",
        ArtifactType.DEPLOYMENT_GUIDE: "배포 가이드 - 배포 절차 및 환경 설정",
    }
    return descriptions.get(artifact_type, "알 수 없는 산출물")


def get_artifact_template_name(artifact_type: ArtifactType) -> str:
    """산출물 템플릿 파일명 반환"""
    templates = {
        ArtifactType.PROJECT_PROPOSAL: "project_proposal.md.j2",
        ArtifactType.REQUIREMENTS_SPEC: "requirements_spec.md.j2",
        ArtifactType.ARCHITECTURE_DESIGN: "architecture_design.md.j2",
        ArtifactType.DATA_DESIGN: "data_design.md.j2",
        ArtifactType.API_DESIGN: "api_design.md.j2",
        ArtifactType.AGENT_DESIGN: "agent_design.md.j2",
        ArtifactType.TEST_PLAN: "test_plan.md.j2",
        ArtifactType.TEST_REPORT: "test_report.md.j2",
        ArtifactType.CODE_REVIEW: "code_review.md.j2",
        ArtifactType.DEPLOYMENT_GUIDE: "deployment_guide.md.j2",
    }
    return templates.get(artifact_type, "default.md.j2")
