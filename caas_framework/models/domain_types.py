"""
Domain Types

요구사항의 실제 도메인 타입 분류 시스템
"""

import json
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DomainType(str, Enum):
    """요구사항의 실제 도메인 타입"""

    # Conversation & Communication
    CONVERSATIONAL_AI = "conversational_ai"
    """대화형 AI - 챗봇, Q&A 시스템, AI 어시스턴트"""

    CUSTOMER_SUPPORT = "customer_support"
    """고객 지원 - 고객 문의 처리, 티켓 관리"""

    # Task & Workflow Management
    TASK_MANAGEMENT = "task_management"
    """작업 관리 - Todo 앱, 작업 추적, 스케줄링"""

    WORKFLOW_AUTOMATION = "workflow_automation"
    """업무 자동화 - 프로세스 자동화, 알림, 이메일 전송"""

    # Data & Analytics
    DATA_ANALYSIS = "data_analysis"
    """데이터 분석 - 데이터 분석, 통계, 인사이트 추출"""

    REPORT_GENERATION = "report_generation"
    """리포트 생성 - 보고서 자동 생성, 문서 생성"""

    DASHBOARD = "dashboard"
    """대시보드 - 실시간 모니터링, KPI 대시보드"""

    # Content & Documentation
    CONTENT_CREATION = "content_creation"
    """콘텐츠 생성 - 글쓰기, 마케팅 콘텐츠, 소셜 미디어"""

    DOCUMENT_PROCESSING = "document_processing"
    """문서 처리 - 문서 읽기/변환/요약, PDF 처리"""

    KNOWLEDGE_BASE = "knowledge_base"
    """지식베이스 - 문서 검색, Q&A, RAG 시스템"""

    # Integration & API
    API_INTEGRATION = "api_integration"
    """API 통합 - 외부 시스템 연동, 데이터 동기화"""

    WEBHOOK_HANDLER = "webhook_handler"
    """Webhook 처리 - 이벤트 수신 및 처리"""

    # Domain-Specific
    E_COMMERCE = "e_commerce"
    """전자상거래 - 쇼핑몰, 주문 관리, 결제"""

    EDUCATION = "education"
    """교육 - 학습 관리, 퀴즈, 과제 관리"""

    HEALTHCARE = "healthcare"
    """헬스케어 - 환자 관리, 진료 기록, 예약"""

    FINANCE = "finance"
    """금융 - 회계, 예산 관리, 금융 분석"""

    # Other
    CUSTOM = "custom"
    """커스텀/기타 - 특정 분류에 속하지 않는 요구사항"""


class ExecutionPattern(str, Enum):
    """실행 패턴"""

    CRUD_APPLICATION = "crud_application"
    """CRUD 애플리케이션 - 생성/조회/수정/삭제"""

    CONVERSATIONAL_FLOW = "conversational_flow"
    """대화형 플로우 - 대화 기반 상호작용"""

    BATCH_PROCESSING = "batch_processing"
    """배치 처리 - 대량 데이터 일괄 처리"""

    REAL_TIME_PROCESSING = "real_time_processing"
    """실시간 처리 - 스트림 데이터 처리"""

    EVENT_DRIVEN = "event_driven"
    """이벤트 기반 - 이벤트 트리거 동작"""

    SCHEDULED_TASK = "scheduled_task"
    """스케줄 작업 - 주기적/예약 실행"""

    API_ORCHESTRATION = "api_orchestration"
    """API 오케스트레이션 - 여러 API 조합"""


class DomainClassification(BaseModel):
    """도메인 분류 결과"""

    domain_type: DomainType = Field(description="분류된 도메인 타입")

    confidence: float = Field(ge=0.0, le=1.0, description="분류 신뢰도 (0.0-1.0)")

    reasoning: str = Field(description="분류 근거 설명")

    core_entities: List[str] = Field(
        default_factory=list, description="핵심 엔티티 (예: User, Task, Message)"
    )

    core_operations: List[str] = Field(
        default_factory=list, description="핵심 동작 (예: create, read, update, delete)"
    )

    execution_pattern: ExecutionPattern = Field(
        default=ExecutionPattern.CRUD_APPLICATION, description="실행 패턴"
    )

    keywords: List[str] = Field(default_factory=list, description="요구사항에서 추출한 주요 키워드")

    alternate_types: List[DomainType] = Field(
        default_factory=list, description="대안 도메인 타입 (신뢰도 낮은 경우)"
    )


# Domain keywords cache
_DOMAIN_KEYWORDS_CACHE: Optional[Dict[DomainType, List[str]]] = None


def load_domain_keywords() -> Dict[DomainType, List[str]]:
    """
    Domain keywords를 JSON 파일에서 로드합니다.

    Returns:
        Dict[DomainType, List[str]]: Domain type별 키워드 매핑
    """
    global _DOMAIN_KEYWORDS_CACHE

    if _DOMAIN_KEYWORDS_CACHE is not None:
        return _DOMAIN_KEYWORDS_CACHE

    try:
        # Try to load from data/ontology/domain_keywords.json
        from pathlib import Path

        keywords_path = Path.cwd() / "data" / "ontology" / "domain_keywords.json"

        if keywords_path.exists():
            with open(keywords_path, "r", encoding="utf-8") as f:
                keywords_data = json.load(f)

            # Convert string keys to DomainType enums
            keywords_map = {}
            for domain_str, keywords in keywords_data.items():
                try:
                    domain_type = DomainType(domain_str)
                    keywords_map[domain_type] = keywords
                except ValueError:
                    # Skip unknown domain types
                    continue

            _DOMAIN_KEYWORDS_CACHE = keywords_map
            return keywords_map
        else:
            # Fallback to empty dict if file not found
            _DOMAIN_KEYWORDS_CACHE = {}
            return {}

    except Exception as e:
        # Fallback on error
        print(f"Warning: Failed to load domain keywords: {e}")
        _DOMAIN_KEYWORDS_CACHE = {}
        return {}


def get_domain_keywords(domain_type: DomainType) -> List[str]:
    """
    특정 Domain Type의 키워드를 반환합니다.

    Args:
        domain_type: Domain Type

    Returns:
        List[str]: 키워드 목록
    """
    keywords_map = load_domain_keywords()
    return keywords_map.get(domain_type, [])


def get_domain_description(domain_type: DomainType) -> str:
    """도메인 타입 설명 반환"""
    descriptions = {
        DomainType.CONVERSATIONAL_AI: "대화형 AI 시스템 (챗봇, Q&A)",
        DomainType.CUSTOMER_SUPPORT: "고객 지원 시스템 (티켓, 문의 처리)",
        DomainType.TASK_MANAGEMENT: "작업 관리 시스템 (Todo, 스케줄)",
        DomainType.WORKFLOW_AUTOMATION: "업무 자동화 (알림, 이메일)",
        DomainType.DATA_ANALYSIS: "데이터 분석 (통계, 시각화)",
        DomainType.REPORT_GENERATION: "리포트 생성 (보고서, 문서)",
        DomainType.DASHBOARD: "대시보드 (모니터링, KPI)",
        DomainType.CONTENT_CREATION: "콘텐츠 생성 (글쓰기, 마케팅)",
        DomainType.DOCUMENT_PROCESSING: "문서 처리 (PDF, 변환, 요약)",
        DomainType.KNOWLEDGE_BASE: "지식베이스 (검색, RAG)",
        DomainType.API_INTEGRATION: "API 통합 (외부 연동)",
        DomainType.WEBHOOK_HANDLER: "Webhook 처리 (이벤트 수신)",
        DomainType.E_COMMERCE: "전자상거래 (쇼핑몰, 주문)",
        DomainType.EDUCATION: "교육 (학습, 퀴즈, 과제)",
        DomainType.HEALTHCARE: "헬스케어 (환자, 진료)",
        DomainType.FINANCE: "금융 (회계, 예산)",
        DomainType.CUSTOM: "커스텀 (기타)",
    }
    return descriptions.get(domain_type, "알 수 없는 도메인")
