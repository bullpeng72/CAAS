"""
CAAS Ontology Manager

OWL 기반 온톨로지를 관리합니다.
에이전트, 태스크, 도구 간의 의미적 관계를 정의합니다.
"""

from typing import Any, Dict, List, Set
from enum import Enum

from pydantic import BaseModel

from app.utils.logger import get_logger, LoggerMixin

logger = get_logger("knowledge.ontology")


# =============================================================================
# Ontology Models
# =============================================================================

class AgentRole(str, Enum):
    """에이전트 역할 온톨로지 (BMAD 확장)"""
    # 기존 역할
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    WRITER = "writer"
    REVIEWER = "reviewer"
    CODER = "coder"
    MANAGER = "manager"
    PLANNER = "planner"
    EXECUTOR = "executor"

    # BMAD 전문 역할 - Architecture
    ARCHITECT = "architect"
    TEST_ARCHITECT = "test_architect"
    SECURITY_ARCHITECT = "security_architect"

    # BMAD 전문 역할 - Product
    PRODUCT_MANAGER = "product_manager"
    TECH_WRITER = "tech_writer"
    QA_ENGINEER = "qa_engineer"

    # BMAD 전문 역할 - Development
    UX_DESIGNER = "ux_designer"
    BACKEND_DEVELOPER = "backend_developer"
    FRONTEND_DEVELOPER = "frontend_developer"
    DATA_ENGINEER = "data_engineer"

    # BMAD 전문 역할 - Leadership
    SCRUM_MASTER = "scrum_master"
    BMAD_MASTER = "bmad_master"
    DEVOPS_ENGINEER = "devops_engineer"

    # 기존 DEVELOPER 별칭
    DEVELOPER = "coder"
    COORDINATOR = "manager"


class TaskType(str, Enum):
    """태스크 유형 온톨로지 (BMAD 확장)"""
    # 기존 태스크
    RESEARCH = "research"
    ANALYSIS = "analysis"
    WRITING = "writing"
    CODING = "coding"
    REVIEW = "review"
    PLANNING = "planning"
    EXECUTION = "execution"
    SYNTHESIS = "synthesis"

    # BMAD 전문 태스크 - Architecture & Design
    SYSTEM_DESIGN = "system_design"
    API_DESIGN = "api_design"
    DATABASE_DESIGN = "database_design"
    UI_DESIGN = "ui_design"
    UX_RESEARCH = "ux_research"
    PROTOTYPING = "prototyping"

    # BMAD 전문 태스크 - Testing & Quality
    TEST_PLANNING = "test_planning"
    TEST_AUTOMATION = "test_automation"
    QUALITY_ASSURANCE = "quality_assurance"
    SECURITY_AUDIT = "security_audit"
    PERFORMANCE_TESTING = "performance_testing"

    # BMAD 전문 태스크 - Development
    FRONTEND_DEVELOPMENT = "frontend_development"
    BACKEND_DEVELOPMENT = "backend_development"
    DATA_PROCESSING = "data_processing"
    DATA_PIPELINE = "data_pipeline"

    # BMAD 전문 태스크 - Agile & Operations
    SPRINT_PLANNING = "sprint_planning"
    RETROSPECTIVE = "retrospective"
    TEAM_COORDINATION = "team_coordination"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    DOCUMENTATION = "documentation"

    # BMAD 전문 태스크 - Product
    PRODUCT_PLANNING = "product_planning"
    USER_STORY_WRITING = "user_story_writing"
    REQUIREMENT_ANALYSIS = "requirement_analysis"

    # 기타
    GENERAL = "general"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"


class ToolCapability(str, Enum):
    """도구 능력 온톨로지"""
    SEARCH = "search"
    READ = "read"
    WRITE = "write"
    COMPUTE = "compute"
    COMMUNICATE = "communicate"
    VISUALIZE = "visualize"


class DomainCategory(str, Enum):
    """도메인 카테고리"""
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    TECHNOLOGY = "technology"
    MARKETING = "marketing"
    RESEARCH = "research"
    LEGAL = "legal"
    GENERAL = "general"


class OntologyEntity(BaseModel):
    """온톨로지 엔티티 기본 모델"""
    id: str
    name: str
    description: str
    properties: Dict[str, Any] = {}


class OntologyRelation(BaseModel):
    """온톨로지 관계 모델"""
    subject: str
    predicate: str
    object: str


# =============================================================================
# Role-Task-Tool Mappings
# =============================================================================

# 역할에 적합한 태스크 유형 (BMAD 확장)
ROLE_TASK_MAPPINGS: Dict[AgentRole, List[TaskType]] = {
    # 기존 역할
    AgentRole.RESEARCHER: [TaskType.RESEARCH, TaskType.ANALYSIS, TaskType.UX_RESEARCH],
    AgentRole.ANALYST: [TaskType.ANALYSIS, TaskType.SYNTHESIS, TaskType.DATA_PROCESSING],
    AgentRole.WRITER: [TaskType.WRITING, TaskType.SYNTHESIS, TaskType.DOCUMENTATION],
    AgentRole.REVIEWER: [TaskType.REVIEW, TaskType.ANALYSIS, TaskType.QUALITY_ASSURANCE],
    AgentRole.CODER: [TaskType.CODING, TaskType.EXECUTION, TaskType.BACKEND_DEVELOPMENT],
    AgentRole.MANAGER: [TaskType.PLANNING, TaskType.REVIEW, TaskType.TEAM_COORDINATION],
    AgentRole.PLANNER: [TaskType.PLANNING, TaskType.ANALYSIS, TaskType.SPRINT_PLANNING],
    AgentRole.EXECUTOR: [TaskType.EXECUTION, TaskType.CODING, TaskType.DEPLOYMENT],

    # BMAD 전문 역할 - Architecture
    AgentRole.ARCHITECT: [
        TaskType.SYSTEM_DESIGN,
        TaskType.API_DESIGN,
        TaskType.DATABASE_DESIGN,
        TaskType.PLANNING,
    ],
    AgentRole.TEST_ARCHITECT: [
        TaskType.TEST_PLANNING,
        TaskType.TEST_AUTOMATION,
        TaskType.QUALITY_ASSURANCE,
    ],
    AgentRole.SECURITY_ARCHITECT: [
        TaskType.SECURITY_AUDIT,
        TaskType.SYSTEM_DESIGN,
        TaskType.REVIEW,
    ],

    # BMAD 전문 역할 - Product
    AgentRole.PRODUCT_MANAGER: [
        TaskType.PRODUCT_PLANNING,
        TaskType.USER_STORY_WRITING,
        TaskType.REQUIREMENT_ANALYSIS,
        TaskType.SPRINT_PLANNING,
    ],
    AgentRole.TECH_WRITER: [
        TaskType.DOCUMENTATION,
        TaskType.WRITING,
        TaskType.TRANSLATION,
    ],
    AgentRole.QA_ENGINEER: [
        TaskType.QUALITY_ASSURANCE,
        TaskType.TEST_AUTOMATION,
        TaskType.REVIEW,
    ],

    # BMAD 전문 역할 - Development
    AgentRole.UX_DESIGNER: [
        TaskType.UI_DESIGN,
        TaskType.UX_RESEARCH,
        TaskType.PROTOTYPING,
    ],
    AgentRole.BACKEND_DEVELOPER: [
        TaskType.BACKEND_DEVELOPMENT,
        TaskType.API_DESIGN,
        TaskType.DATABASE_DESIGN,
        TaskType.CODING,
        TaskType.EXECUTION,
    ],
    AgentRole.FRONTEND_DEVELOPER: [
        TaskType.FRONTEND_DEVELOPMENT,
        TaskType.UI_DESIGN,
        TaskType.CODING,
        TaskType.EXECUTION,
    ],
    AgentRole.DATA_ENGINEER: [
        TaskType.DATA_PROCESSING,
        TaskType.DATA_PIPELINE,
        TaskType.DATABASE_DESIGN,
    ],

    # BMAD 전문 역할 - Leadership
    AgentRole.SCRUM_MASTER: [
        TaskType.SPRINT_PLANNING,
        TaskType.RETROSPECTIVE,
        TaskType.TEAM_COORDINATION,
    ],
    AgentRole.BMAD_MASTER: [
        TaskType.PLANNING,
        TaskType.TEAM_COORDINATION,
        TaskType.REQUIREMENT_ANALYSIS,
        TaskType.QUALITY_ASSURANCE,
    ],
    AgentRole.DEVOPS_ENGINEER: [
        TaskType.DEPLOYMENT,
        TaskType.MONITORING,
        TaskType.PERFORMANCE_OPTIMIZATION,
    ],
}

# 태스크 유형에 필요한 도구 능력 (BMAD 확장)
# NOTE: COMPUTE는 명시적인 수치 계산이 필요한 태스크에만 할당
TASK_TOOL_MAPPINGS: Dict[TaskType, List[ToolCapability]] = {
    # 기존 태스크
    TaskType.RESEARCH: [ToolCapability.SEARCH, ToolCapability.READ],
    TaskType.ANALYSIS: [ToolCapability.READ, ToolCapability.VISUALIZE],  # COMPUTE 제거 (텍스트 분석 위주)
    TaskType.WRITING: [ToolCapability.WRITE, ToolCapability.READ],
    TaskType.CODING: [ToolCapability.COMPUTE, ToolCapability.WRITE],
    TaskType.REVIEW: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.PLANNING: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.EXECUTION: [ToolCapability.COMPUTE, ToolCapability.WRITE],
    TaskType.SYNTHESIS: [ToolCapability.READ, ToolCapability.WRITE],

    # BMAD 전문 태스크
    TaskType.SYSTEM_DESIGN: [ToolCapability.READ, ToolCapability.WRITE, ToolCapability.VISUALIZE],
    TaskType.API_DESIGN: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.DATABASE_DESIGN: [ToolCapability.READ, ToolCapability.WRITE, ToolCapability.COMPUTE],
    TaskType.UI_DESIGN: [ToolCapability.VISUALIZE, ToolCapability.WRITE],
    TaskType.UX_RESEARCH: [ToolCapability.SEARCH, ToolCapability.READ, ToolCapability.VISUALIZE],
    TaskType.PROTOTYPING: [ToolCapability.WRITE, ToolCapability.VISUALIZE],
    TaskType.TEST_PLANNING: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.TEST_AUTOMATION: [ToolCapability.COMPUTE, ToolCapability.WRITE],
    TaskType.QUALITY_ASSURANCE: [ToolCapability.READ, ToolCapability.COMPUTE],
    TaskType.SECURITY_AUDIT: [ToolCapability.READ, ToolCapability.COMPUTE],
    TaskType.PERFORMANCE_TESTING: [ToolCapability.COMPUTE, ToolCapability.VISUALIZE],
    TaskType.FRONTEND_DEVELOPMENT: [ToolCapability.WRITE, ToolCapability.COMPUTE],
    TaskType.BACKEND_DEVELOPMENT: [ToolCapability.WRITE, ToolCapability.COMPUTE],
    TaskType.DATA_PROCESSING: [ToolCapability.COMPUTE, ToolCapability.READ, ToolCapability.WRITE],
    TaskType.DATA_PIPELINE: [ToolCapability.COMPUTE, ToolCapability.WRITE],
    TaskType.SPRINT_PLANNING: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.RETROSPECTIVE: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.TEAM_COORDINATION: [ToolCapability.COMMUNICATE, ToolCapability.WRITE],
    TaskType.DEPLOYMENT: [ToolCapability.COMPUTE, ToolCapability.WRITE],
    TaskType.MONITORING: [ToolCapability.COMPUTE, ToolCapability.VISUALIZE],
    TaskType.DOCUMENTATION: [ToolCapability.WRITE, ToolCapability.READ],
    TaskType.PRODUCT_PLANNING: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.USER_STORY_WRITING: [ToolCapability.WRITE],
    TaskType.REQUIREMENT_ANALYSIS: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.GENERAL: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.SUMMARIZATION: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.TRANSLATION: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.PERFORMANCE_OPTIMIZATION: [ToolCapability.COMPUTE, ToolCapability.READ, ToolCapability.WRITE],
}

# Legacy hardcoded tool capabilities removed - now dynamically generated from Tool Ontology
# See OntologyManager._build_tool_capabilities_from_ontology() for dynamic generation


# =============================================================================
# Ontology Manager
# =============================================================================

class OntologyManager(LoggerMixin):
    """
    온톨로지 관리자

    에이전트-태스크-도구 간의 의미적 관계를 관리하고
    적절한 매핑을 추천합니다.
    """

    def __init__(self):
        self.role_task_map = ROLE_TASK_MAPPINGS
        self.task_tool_map = TASK_TOOL_MAPPINGS

        # Tool Ontology에서 동적으로 tool capabilities 생성
        self.tool_capabilities = self._build_tool_capabilities_from_ontology()
    
    def get_suitable_roles(self, task_type: TaskType) -> List[AgentRole]:
        """
        태스크 유형에 적합한 역할을 반환합니다.
        
        Args:
            task_type: 태스크 유형
        
        Returns:
            List[AgentRole]: 적합한 역할 목록
        """
        suitable_roles = []
        for role, tasks in self.role_task_map.items():
            if task_type in tasks:
                suitable_roles.append(role)
        return suitable_roles
    
    def get_suitable_tasks(self, role: AgentRole) -> List[TaskType]:
        """
        역할에 적합한 태스크 유형을 반환합니다.
        
        Args:
            role: 에이전트 역할
        
        Returns:
            List[TaskType]: 적합한 태스크 유형 목록
        """
        return self.role_task_map.get(role, [])
    
    def get_required_capabilities(self, task_type: TaskType) -> List[ToolCapability]:
        """
        태스크 유형에 필요한 도구 능력을 반환합니다.
        
        Args:
            task_type: 태스크 유형
        
        Returns:
            List[ToolCapability]: 필요한 능력 목록
        """
        return self.task_tool_map.get(task_type, [])
    
    def get_suitable_tools(self, task_type: TaskType) -> List[str]:
        """
        태스크 유형에 적합한 도구를 반환합니다.
        
        Args:
            task_type: 태스크 유형
        
        Returns:
            List[str]: 적합한 도구 ID 목록
        """
        required_caps = set(self.get_required_capabilities(task_type))
        suitable_tools = []
        
        for tool, caps in self.tool_capabilities.items():
            if required_caps & set(caps):  # 교집합이 있으면
                suitable_tools.append(tool)
        
        return suitable_tools
    
    def recommend_agent_tools(
        self,
        role: AgentRole,
        assigned_tasks: List[TaskType],
    ) -> List[str]:
        """
        에이전트에게 필요한 도구를 추천합니다.
        
        Args:
            role: 에이전트 역할
            assigned_tasks: 할당된 태스크 유형
        
        Returns:
            List[str]: 추천 도구 목록
        """
        all_tools: Set[str] = set()
        
        for task_type in assigned_tasks:
            tools = self.get_suitable_tools(task_type)
            all_tools.update(tools)
        
        return list(all_tools)
    
    def infer_role_from_description(self, description: str) -> AgentRole:
        """
        설명에서 역할을 추론합니다.

        Args:
            description: 역할/태스크 설명

        Returns:
            AgentRole: 추론된 역할
        """
        description_lower = description.lower()

        # ⚠️ CRITICAL: 역할 이름이 정확히 포함되어 있으면 우선 반환 (키워드 매칭보다 우선)
        # 예: "data_engineer Ensure proper storage..." → data_engineer 반환
        for role in AgentRole:
            # 언더스코어와 하이픈 모두 지원
            role_variants = [
                role.value,
                role.value.replace("_", " "),
                role.value.replace("_", "-"),
            ]
            for variant in role_variants:
                # 단어 경계를 고려하여 정확히 매칭
                if f" {variant} " in f" {description_lower} " or description_lower.startswith(f"{variant} "):
                    return role

        role_keywords = {
            AgentRole.RESEARCHER: [
                "research", "investigate", "find", "search", "discover", "explore", "gather", "collect", "retrieve", "lookup", "query",
                "연구", "조사", "탐색", "검색", "발견", "탐구", "수집", "찾기", "조회", "정보수집"
            ],
            AgentRole.ANALYST: [
                "analyze", "analyse", "examine", "study", "evaluate", "assess", "interpret", "measure", "compare", "inspect",
                "분석", "검토", "평가", "연구", "해석", "측정", "비교", "조사"
            ],
            AgentRole.WRITER: [
                "write", "create", "compose", "draft", "author", "document", "generate", "produce", "edit", "content",
                "작성", "쓰기", "창작", "저술", "문서화", "생성", "편집", "콘텐츠"
            ],
            AgentRole.REVIEWER: [
                "review", "check", "verify", "validate", "assess", "audit", "critique", "feedback", "approve", "quality",
                "리뷰", "검토", "확인", "검증", "평가", "감사", "피드백", "승인", "품질"
            ],
            AgentRole.CODER: [
                "code", "program", "develop", "implement", "build", "debug", "test", "deploy", "software", "application",
                "코드", "코딩", "프로그래밍", "개발", "구현", "빌드", "디버그", "테스트", "배포", "소프트웨어"
            ],
            AgentRole.MANAGER: [
                "manage", "coordinate", "oversee", "lead", "direct", "supervise", "control", "delegate", "organize",
                "관리", "관리자", "조정", "감독", "리드", "지휘", "통제", "위임", "조직"
            ],
            AgentRole.PLANNER: [
                "plan", "schedule", "organize", "strategize", "design", "architect", "structure", "roadmap", "blueprint",
                "계획", "기획", "일정", "전략", "설계", "구조화", "로드맵", "청사진"
            ],
            AgentRole.EXECUTOR: [
                "execute", "run", "perform", "accomplish", "carry out", "complete", "finish", "deliver", "process", "handle",
                "실행", "수행", "처리", "완료", "달성", "진행"
            ],
            # BMAD 전문 역할 키워드 추가
            AgentRole.FRONTEND_DEVELOPER: [
                "frontend", "front-end", "ui", "user interface", "streamlit", "react", "vue", "angular", "html", "css", "javascript",
                "프론트엔드", "프론트", "사용자인터페이스", "화면개발", "웹개발"
            ],
            AgentRole.BACKEND_DEVELOPER: [
                "backend", "back-end", "api", "server", "fastapi", "flask", "django", "endpoint", "rest", "graphql",
                "백엔드", "백", "서버개발", "API개발", "엔드포인트"
            ],
            AgentRole.DATA_ENGINEER: [
                "data engineer", "data engineering", "data pipeline", "etl", "data processing", "data storage",
                "database", "sql", "nosql", "data warehouse", "data lake", "conversation data", "storage",
                "데이터엔지니어", "데이터처리", "데이터파이프라인", "데이터저장", "데이터베이스", "저장소"
            ],
            AgentRole.UX_DESIGNER: [
                "ux", "user experience", "ui design", "ux design", "interface design", "wireframe", "mockup", "prototype",
                "사용자경험", "UX디자인", "UI디자인", "인터페이스디자인", "와이어프레임", "프로토타입"
            ],
            AgentRole.ARCHITECT: [
                "architect", "architecture", "system design", "technical architecture", "solution architect",
                "아키텍트", "아키텍처", "시스템설계", "기술아키텍처", "솔루션아키텍트"
            ],
            AgentRole.QA_ENGINEER: [
                "qa", "quality assurance", "tester", "testing", "test automation", "quality control",
                "품질보증", "QA엔지니어", "테스터", "품질관리", "테스트자동화"
            ],
            AgentRole.DEVOPS_ENGINEER: [
                "devops", "deployment", "ci/cd", "infrastructure", "kubernetes", "docker", "automation",
                "데브옵스", "배포", "인프라", "자동화"
            ],
        }

        scores: Dict[AgentRole, int] = {role: 0 for role in AgentRole}

        for role, keywords in role_keywords.items():
            for keyword in keywords:
                if keyword in description_lower:
                    scores[role] += 1

        # 가장 높은 점수의 역할 반환
        best_role = max(scores, key=scores.get)

        # 매칭된 키워드가 없으면 더 관대하게 추론
        if scores[best_role] == 0:
            # 역할 이름 자체가 포함되어 있는지 확인
            for role in AgentRole:
                if role.value in description_lower:
                    return role
            # 그래도 없으면 EXECUTOR 반환
            return AgentRole.EXECUTOR

        return best_role
    
    def infer_task_type_from_description(self, description: str) -> TaskType:
        """
        설명에서 태스크 유형을 추론합니다.

        Args:
            description: 태스크 설명

        Returns:
            TaskType: 추론된 태스크 유형
        """
        description_lower = description.lower()

        # CRITICAL: 우선순위 기반 추론
        # Level 1: 구체적인 전문 타입 (BMAD roles)
        # Level 2: 일반적인 타입 (기본 roles)

        priority_keywords = {
            TaskType.BACKEND_DEVELOPMENT: [
                "backend development", "backend logic", "backend api", "server development", "backend implementation",
                "백엔드개발", "백엔드로직", "서버개발", "백엔드구현"
            ],
            TaskType.FRONTEND_DEVELOPMENT: [
                "frontend development", "ui development", "streamlit", "web interface", "user interface development",
                "frontend implementation", "프론트엔드개발", "UI개발", "화면개발", "인터페이스개발"
            ],
            TaskType.DATA_PIPELINE: [
                "data pipeline", "etl pipeline", "데이터파이프라인", "ETL파이프라인"
            ],
            TaskType.UI_DESIGN: [
                "ui design", "interface design", "ux design", "design ui", "design interface", "design layout",
                "UI디자인", "인터페이스디자인", "레이아웃디자인", "화면디자인"
            ],
            TaskType.API_DESIGN: [
                "api design", "endpoint design", "rest api design", "design api", "API디자인", "엔드포인트설계"
            ],
            TaskType.DATABASE_DESIGN: [
                "database design", "schema design", "data model", "데이터베이스설계", "스키마설계", "데이터모델"
            ],
            TaskType.SYSTEM_DESIGN: [
                "system design", "architecture design", "technical design", "시스템설계", "아키텍처설계", "기술설계"
            ],
            TaskType.TEST_AUTOMATION: [
                "test automation", "automated testing", "테스트자동화", "자동화테스트"
            ],
        }

        general_keywords = {
            TaskType.RESEARCH: [
                "research", "find", "search", "gather", "collect", "explore", "investigate", "discover", "retrieve", "lookup", "query",
                "연구", "조사", "탐색", "검색", "발견", "탐구", "수집", "찾기", "조회", "정보수집"
            ],
            TaskType.ANALYSIS: [
                "analyze", "analyse", "examine", "study", "evaluate", "assess", "interpret", "measure", "compare", "inspect",
                "분석", "검토", "평가", "연구", "해석", "측정", "비교", "조사"
            ],
            TaskType.WRITING: [
                "write", "create", "compose", "draft", "author", "document", "generate", "produce", "edit", "content",
                "작성", "쓰기", "창작", "저술", "문서화", "생성", "편집", "콘텐츠"
            ],
            TaskType.CODING: [
                "code", "program", "implement", "develop", "build", "debug", "test", "deploy", "software", "application",
                "코드", "코딩", "프로그래밍", "개발", "구현", "빌드", "디버그", "테스트", "배포", "소프트웨어"
            ],
            TaskType.REVIEW: [
                "review", "check", "verify", "validate", "audit", "critique", "feedback", "approve", "quality",
                "리뷰", "검토", "확인", "검증", "평가", "감사", "피드백", "승인", "품질"
            ],
            TaskType.PLANNING: [
                "plan", "schedule", "organize", "strategize", "design", "architect", "structure", "roadmap", "blueprint",
                "계획", "기획", "일정", "전략", "설계", "구조화", "로드맵", "청사진"
            ],
            TaskType.EXECUTION: [
                "execute", "run", "perform", "accomplish", "carry out", "complete", "finish", "deliver",
                "실행", "수행", "완료", "달성"
            ],
            TaskType.SYNTHESIS: [
                "synthesize", "combine", "integrate", "summarize", "merge", "consolidate", "compile", "aggregate",
                "종합", "통합", "결합", "요약", "합성", "병합", "취합"
            ],
            TaskType.DATA_PROCESSING: [
                "data processing", "data pipeline", "etl", "data storage", "store data",
                "conversation data", "conversation history", "data management", "storage management",
                "store and manage", "데이터처리", "데이터파이프라인", "데이터저장", "데이터관리", "저장소관리", "대화데이터", "대화기록"
            ],
            TaskType.DEPLOYMENT: [
                "deployment", "deploy", "release", "배포", "릴리스"
            ],
            TaskType.DOCUMENTATION: [
                "documentation", "document", "write docs", "문서화", "문서작성"
            ],
        }

        # Level 1: 구체적인 전문 타입 우선 확인
        priority_scores: Dict[TaskType, int] = {tt: 0 for tt in priority_keywords.keys()}
        for task_type, keywords in priority_keywords.items():
            for keyword in keywords:
                if keyword in description_lower:
                    priority_scores[task_type] += 1

        best_priority = max(priority_scores, key=priority_scores.get) if priority_scores else None
        if best_priority and priority_scores[best_priority] > 0:
            return best_priority

        # Level 2: 일반적인 타입 확인
        general_scores: Dict[TaskType, int] = {tt: 0 for tt in general_keywords.keys()}
        for task_type, keywords in general_keywords.items():
            for keyword in keywords:
                if keyword in description_lower:
                    general_scores[task_type] += 1

        best_general = max(general_scores, key=general_scores.get) if general_scores else None
        if best_general and general_scores[best_general] > 0:
            return best_general

        # 매칭된 키워드가 없으면 태스크 이름 자체 확인
        for task_type in TaskType:
            if task_type.value in description_lower:
                return task_type

        # 그래도 없으면 EXECUTION 반환
        return TaskType.EXECUTION
    
    def validate_assignment(
        self,
        role: AgentRole,
        task_type: TaskType,
    ) -> bool:
        """
        역할-태스크 할당이 적절한지 검증합니다.

        Args:
            role: 에이전트 역할
            task_type: 태스크 유형

        Returns:
            bool: 적절 여부
        """
        suitable_tasks = self.get_suitable_tasks(role)
        return task_type in suitable_tasks

    def _build_tool_capabilities_from_ontology(self) -> Dict[str, List[ToolCapability]]:
        """
        Tool Ontology에서 동적으로 tool capabilities를 생성합니다.

        Returns:
            Dict[str, List[ToolCapability]]: 도구별 capabilities 매핑
        """
        capabilities_map = {}

        try:
            from app.core.ontology import get_tool_ontology_manager
            tool_manager = get_tool_ontology_manager()
            all_tools = tool_manager.get_all_tools(enabled_only=True)

            for tool in all_tools:
                capabilities = self._infer_tool_capabilities_from_metadata(
                    tool.name,
                    tool.category.value,
                    tool.tags,
                    tool.compatible_tasks
                )
                capabilities_map[tool.name] = capabilities

            self.logger.info(f"Tool capabilities 동적 생성 완료: {len(capabilities_map)}개 도구")

        except Exception as e:
            self.logger.warning(f"Tool Ontology 로드 실패: {e}, 기본 추론 사용")
            # Fallback: Tool registry에서 기본 도구 목록 가져오기
            from app.models.tool_registry import get_all_tools_dict
            all_tools = get_all_tools_dict()
            for tool_id in all_tools.keys():
                capabilities_map[tool_id] = self._infer_tool_capabilities(tool_id)

        return capabilities_map

    def _infer_tool_capabilities_from_metadata(
        self,
        tool_name: str,
        category: str,
        tags: List[str],
        compatible_tasks: List[str]
    ) -> List[ToolCapability]:
        """
        도구 메타데이터에서 capability를 추론합니다.

        Args:
            tool_name: 도구 이름
            category: 도구 카테고리
            tags: 도구 태그 목록
            compatible_tasks: 호환 가능한 태스크 목록

        Returns:
            List[ToolCapability]: 추론된 capabilities
        """
        capabilities = set()

        # Category 기반 매핑
        category_mapping = {
            "search": [ToolCapability.SEARCH],
            "file": [ToolCapability.READ, ToolCapability.WRITE],
            "web_scraping": [ToolCapability.SEARCH, ToolCapability.READ],
            "code": [ToolCapability.COMPUTE, ToolCapability.WRITE],
            "document": [ToolCapability.READ],
            "database": [ToolCapability.READ, ToolCapability.WRITE],
            "vision": [ToolCapability.READ, ToolCapability.VISUALIZE],
            "ai": [ToolCapability.COMPUTE],
            "communication": [ToolCapability.COMMUNICATE],
        }

        if category.lower() in category_mapping:
            capabilities.update(category_mapping[category.lower()])

        # Tags 기반 추론
        all_keywords = " ".join(tags + compatible_tasks + [tool_name]).lower()

        if any(kw in all_keywords for kw in ["search", "find", "query", "lookup"]):
            capabilities.add(ToolCapability.SEARCH)
        if any(kw in all_keywords for kw in ["read", "fetch", "get", "load", "extract"]):
            capabilities.add(ToolCapability.READ)
        if any(kw in all_keywords for kw in ["write", "save", "create", "update", "generate"]):
            capabilities.add(ToolCapability.WRITE)
        # NOTE: "calculation", "computation"만 COMPUTE로 매핑 ("analysis"는 제외)
        if any(kw in all_keywords for kw in ["calculation", "compute", "computation", "execute", "interpret"]):
            capabilities.add(ToolCapability.COMPUTE)
        if any(kw in all_keywords for kw in ["visual", "chart", "graph", "plot", "image"]):
            capabilities.add(ToolCapability.VISUALIZE)
        if any(kw in all_keywords for kw in ["communicate", "send", "notify", "message", "slack"]):
            capabilities.add(ToolCapability.COMMUNICATE)

        # 기본값: READ (최소한의 capability)
        return list(capabilities) if capabilities else [ToolCapability.READ]

    def _infer_tool_capabilities(self, tool_id: str) -> List[ToolCapability]:
        """
        도구 이름에서 capability를 추론합니다 (Fallback용)

        Args:
            tool_id: 도구 ID

        Returns:
            List[ToolCapability]: 추론된 capabilities
        """
        tool_lower = tool_id.lower()
        capabilities = []

        # 키워드 기반 capability 추론
        if any(kw in tool_lower for kw in ["search", "find", "query", "lookup"]):
            capabilities.append(ToolCapability.SEARCH)
        if any(kw in tool_lower for kw in ["read", "fetch", "get", "load"]):
            capabilities.append(ToolCapability.READ)
        if any(kw in tool_lower for kw in ["write", "save", "create", "update"]):
            capabilities.append(ToolCapability.WRITE)
        if any(kw in tool_lower for kw in ["compute", "calculate", "process"]):
            capabilities.append(ToolCapability.COMPUTE)
        if any(kw in tool_lower for kw in ["visual", "chart", "graph", "plot"]):
            capabilities.append(ToolCapability.VISUALIZE)
        if any(kw in tool_lower for kw in ["communicate", "send", "notify", "message"]):
            capabilities.append(ToolCapability.COMMUNICATE)

        # 기본값: READ (최소한의 capability)
        return capabilities if capabilities else [ToolCapability.READ]
