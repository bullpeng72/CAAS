"""
Tool Registry

도구 등록 및 관리를 위한 모델입니다.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from app.utils.logger import get_logger

logger = get_logger("models.tool_registry")


class ToolMetadata(BaseModel):
    """도구 메타데이터"""

    name: str = Field(..., description="도구 이름")
    description: str = Field(..., description="도구 설명")
    source: str = Field(..., description="도구 출처 (mcp/crewai/custom)")
    category: str = Field(default="general", description="도구 카테고리")
    enabled: bool = Field(default=True, description="활성화 여부")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="도구 파라미터")
    requires_api_key: bool = Field(default=False, description="API 키 필요 여부")
    api_key_name: Optional[str] = Field(default=None, description="필요한 API 키 이름 (예: SERPER_API_KEY)")
    class_path: Optional[str] = Field(default=None, description="도구 클래스 경로 (예: SerperDevTool)")
    keywords: List[str] = Field(default_factory=list, description="도구 관련 키워드 (매칭용)")
    use_cases: List[str] = Field(default_factory=list, description="주요 사용 사례")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class MCPServerConfig(BaseModel):
    """MCP 서버 설정"""

    name: str = Field(..., description="서버 이름")
    transport_type: str = Field(..., description="전송 타입 (stdio/sse/http)")
    server_url: Optional[str] = Field(default=None, description="서버 URL (sse/http)")
    server_command: Optional[str] = Field(default=None, description="서버 명령어 (stdio)")
    server_args: List[str] = Field(default_factory=list, description="서버 인자 (stdio)")
    connect_timeout: int = Field(default=30, description="연결 타임아웃 (초)")
    enabled: bool = Field(default=True, description="활성화 여부")
    registered_tools: List[str] = Field(default_factory=list, description="등록된 도구 목록")


class ToolRegistry(BaseModel):
    """도구 저장소"""

    tools: Dict[str, ToolMetadata] = Field(default_factory=dict, description="등록된 도구들")
    mcp_servers: Dict[str, MCPServerConfig] = Field(default_factory=dict, description="MCP 서버 설정들")

    @classmethod
    def load(cls, file_path: Path) -> "ToolRegistry":
        """
        파일에서 저장소 로드

        Args:
            file_path: 저장소 파일 경로

        Returns:
            ToolRegistry: 도구 저장소
        """
        if not file_path.exists():
            logger.info(f"저장소 파일이 없습니다. 새로 생성합니다: {file_path}")
            registry = cls()
            registry.save(file_path)
            return registry

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.debug(f"저장소 로드 성공: {file_path}")
            return cls(**data)
        except Exception as e:
            logger.error(f"저장소 로드 실패: {e}")
            return cls()

    def save(self, file_path: Path) -> bool:
        """
        파일에 저장소 저장

        Args:
            file_path: 저장소 파일 경로

        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 디렉토리 생성
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 저장
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)

            logger.info(f"저장소 저장 성공: {file_path}")
            return True
        except Exception as e:
            logger.error(f"저장소 저장 실패: {e}")
            return False

    def add_tool(self, tool: ToolMetadata) -> bool:
        """
        도구 추가

        Args:
            tool: 도구 메타데이터

        Returns:
            bool: 추가 성공 여부
        """
        if tool.name in self.tools:
            logger.warning(f"도구가 이미 등록되어 있습니다: {tool.name}")
            return False

        self.tools[tool.name] = tool
        logger.info(f"도구 추가: {tool.name}")
        return True

    def remove_tool(self, tool_name: str) -> bool:
        """
        도구 제거

        Args:
            tool_name: 도구 이름

        Returns:
            bool: 제거 성공 여부
        """
        if tool_name not in self.tools:
            logger.warning(f"도구가 등록되어 있지 않습니다: {tool_name}")
            return False

        del self.tools[tool_name]
        logger.info(f"도구 제거: {tool_name}")
        return True

    def update_tool(self, tool_name: str, **updates) -> bool:
        """
        도구 업데이트

        Args:
            tool_name: 도구 이름
            **updates: 업데이트할 필드들

        Returns:
            bool: 업데이트 성공 여부
        """
        if tool_name not in self.tools:
            logger.warning(f"도구가 등록되어 있지 않습니다: {tool_name}")
            return False

        tool = self.tools[tool_name]
        for key, value in updates.items():
            if hasattr(tool, key):
                setattr(tool, key, value)

        tool.updated_at = datetime.now().isoformat()
        logger.info(f"도구 업데이트: {tool_name}")
        return True

    def get_tool(self, tool_name: str) -> Optional[ToolMetadata]:
        """
        도구 조회

        Args:
            tool_name: 도구 이름

        Returns:
            ToolMetadata: 도구 메타데이터 (없으면 None)
        """
        return self.tools.get(tool_name)

    def get_enabled_tools(self) -> List[ToolMetadata]:
        """
        활성화된 도구 목록 조회

        Returns:
            List[ToolMetadata]: 활성화된 도구 목록
        """
        return [tool for tool in self.tools.values() if tool.enabled]

    def get_tools_by_source(self, source: str) -> List[ToolMetadata]:
        """
        출처별 도구 목록 조회

        Args:
            source: 도구 출처 (mcp/crewai/custom)

        Returns:
            List[ToolMetadata]: 도구 목록
        """
        return [tool for tool in self.tools.values() if tool.source == source]

    def get_tools_by_category(self, category: str) -> List[ToolMetadata]:
        """
        카테고리별 도구 목록 조회

        Args:
            category: 도구 카테고리

        Returns:
            List[ToolMetadata]: 도구 목록
        """
        return [tool for tool in self.tools.values() if tool.category == category]

    def search_tools(self, query: str, search_fields: Optional[List[str]] = None) -> List[ToolMetadata]:
        """
        도구 검색

        Args:
            query: 검색어
            search_fields: 검색할 필드 목록 (기본: ['name', 'description', 'category'])

        Returns:
            List[ToolMetadata]: 검색 결과
        """
        if search_fields is None:
            search_fields = ['name', 'description', 'category']

        query_lower = query.lower()
        results = []

        for tool in self.tools.values():
            for field in search_fields:
                field_value = getattr(tool, field, "")
                if field_value and query_lower in str(field_value).lower():
                    results.append(tool)
                    break

        return results

    def filter_tools(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None,
        enabled: Optional[bool] = None,
        requires_api_key: Optional[bool] = None
    ) -> List[ToolMetadata]:
        """
        도구 필터링

        Args:
            source: 출처 필터
            category: 카테고리 필터
            enabled: 활성화 상태 필터
            requires_api_key: API 키 필요 여부 필터

        Returns:
            List[ToolMetadata]: 필터링된 도구 목록
        """
        results = list(self.tools.values())

        if source is not None:
            results = [t for t in results if t.source == source]

        if category is not None:
            results = [t for t in results if t.category == category]

        if enabled is not None:
            results = [t for t in results if t.enabled == enabled]

        if requires_api_key is not None:
            results = [t for t in results if t.requires_api_key == requires_api_key]

        return results

    def get_categories(self) -> List[str]:
        """
        등록된 모든 카테고리 조회

        Returns:
            List[str]: 카테고리 목록
        """
        categories = set()
        for tool in self.tools.values():
            categories.add(tool.category)
        return sorted(list(categories))

    def get_sources(self) -> List[str]:
        """
        등록된 모든 출처 조회

        Returns:
            List[str]: 출처 목록
        """
        sources = set()
        for tool in self.tools.values():
            sources.add(tool.source)
        return sorted(list(sources))

    def get_tool_count(self) -> Dict[str, int]:
        """
        도구 통계 정보 조회

        Returns:
            Dict[str, int]: 통계 정보 (전체, 활성화, 비활성화, 출처별, 카테고리별)
        """
        stats = {
            "total": len(self.tools),
            "enabled": len([t for t in self.tools.values() if t.enabled]),
            "disabled": len([t for t in self.tools.values() if not t.enabled]),
            "by_source": {},
            "by_category": {},
        }

        for tool in self.tools.values():
            # 출처별 집계
            if tool.source not in stats["by_source"]:
                stats["by_source"][tool.source] = 0
            stats["by_source"][tool.source] += 1

            # 카테고리별 집계
            if tool.category not in stats["by_category"]:
                stats["by_category"][tool.category] = 0
            stats["by_category"][tool.category] += 1

        return stats

    def add_mcp_server(self, server: MCPServerConfig) -> bool:
        """
        MCP 서버 추가

        Args:
            server: MCP 서버 설정

        Returns:
            bool: 추가 성공 여부
        """
        if server.name in self.mcp_servers:
            logger.warning(f"MCP 서버가 이미 등록되어 있습니다: {server.name}")
            return False

        self.mcp_servers[server.name] = server
        logger.info(f"MCP 서버 추가: {server.name}")
        return True

    def remove_mcp_server(self, server_name: str) -> bool:
        """
        MCP 서버 제거

        Args:
            server_name: 서버 이름

        Returns:
            bool: 제거 성공 여부
        """
        if server_name not in self.mcp_servers:
            logger.warning(f"MCP 서버가 등록되어 있지 않습니다: {server_name}")
            return False

        # 해당 서버의 도구들도 제거
        server = self.mcp_servers[server_name]
        for tool_name in server.registered_tools:
            self.remove_tool(tool_name)

        del self.mcp_servers[server_name]
        logger.info(f"MCP 서버 제거: {server_name}")
        return True

    def get_mcp_server(self, server_name: str) -> Optional[MCPServerConfig]:
        """
        MCP 서버 조회

        Args:
            server_name: 서버 이름

        Returns:
            MCPServerConfig: MCP 서버 설정 (없으면 None)
        """
        return self.mcp_servers.get(server_name)

    def get_enabled_mcp_servers(self) -> List[MCPServerConfig]:
        """
        활성화된 MCP 서버 목록 조회

        Returns:
            List[MCPServerConfig]: 활성화된 MCP 서버 목록
        """
        return [server for server in self.mcp_servers.values() if server.enabled]


# 기본 CrewAI 도구 정의
DEFAULT_CREWAI_TOOLS = {
    "web_search": ToolMetadata(
        name="web_search",
        description="웹 검색 (Serper API)",
        source="crewai",
        category="search",
        requires_api_key=True,
        api_key_name="SERPER_API_KEY",
        class_path="SerperDevTool",
        keywords=["검색", "search", "google", "웹", "web", "정보", "뉴스", "news", "조사", "research", "찾기"],
        use_cases=["실시간 정보 검색", "뉴스 수집", "웹 리서치", "최신 데이터 조회", "시장 동향 파악"],
    ),
    "scrape_website": ToolMetadata(
        name="scrape_website",
        description="웹사이트 크롤링",
        source="crewai",
        category="web",
        class_path="ScrapeWebsiteTool",
        keywords=["크롤링", "scrape", "crawl", "웹사이트", "website", "수집", "추출", "extract", "html", "페이지"],
        use_cases=["웹페이지 데이터 수집", "HTML 파싱", "콘텐츠 추출", "자동 데이터 수집"],
    ),
    "file_read": ToolMetadata(
        name="file_read",
        description="파일 읽기",
        source="crewai",
        category="file",
        class_path="FileReadTool",
        keywords=["파일", "file", "읽기", "read", "텍스트", "text", "문서", "document", "불러오기", "load"],
        use_cases=["텍스트 파일 읽기", "로그 파일 분석", "설정 파일 로드", "문서 내용 확인"],
    ),
    "file_write": ToolMetadata(
        name="file_write",
        description="Python 코드로 파일 쓰기 (CodeInterpreterTool 사용)",
        source="crewai",
        category="file",
        class_path="CodeInterpreterTool",
        keywords=["파일", "file", "쓰기", "write", "저장", "save", "생성", "create", "작성", "export"],
        use_cases=["결과 파일 저장", "리포트 생성", "데이터 내보내기", "로그 기록"],
    ),
    "directory_read": ToolMetadata(
        name="directory_read",
        description="디렉토리 구조 읽기",
        source="crewai",
        category="file",
        class_path="DirectoryReadTool",
        keywords=["디렉토리", "directory", "폴더", "folder", "구조", "structure", "파일목록", "list"],
        use_cases=["프로젝트 구조 분석", "파일 목록 확인", "디렉토리 탐색"],
    ),
    "code_interpreter": ToolMetadata(
        name="code_interpreter",
        description="Python 코드 실행",
        source="crewai",
        category="code",
        class_path="CodeInterpreterTool",
        keywords=["코드", "code", "python", "실행", "execute", "계산", "calculate", "분석", "analyze", "처리", "process"],
        use_cases=["데이터 분석", "수치 계산", "알고리즘 실행", "Python 스크립트 실행"],
    ),
    "pdf_search": ToolMetadata(
        name="pdf_search",
        description="PDF 문서 검색",
        source="crewai",
        category="document",
        class_path="PDFSearchTool",
        keywords=["pdf", "문서", "document", "논문", "paper", "보고서", "report", "검색", "search"],
        use_cases=["PDF 문서 내용 검색", "논문 분석", "보고서 검토", "문서 내 키워드 찾기"],
    ),
    "csv_search": ToolMetadata(
        name="csv_search",
        description="CSV 데이터 검색",
        source="crewai",
        category="data",
        class_path="CSVSearchTool",
        keywords=["csv", "데이터", "data", "엑셀", "excel", "표", "table", "분석", "analyze"],
        use_cases=["CSV 파일 데이터 검색", "표 형식 데이터 분석", "통계 데이터 조회"],
    ),
    "code_docs_search": ToolMetadata(
        name="code_docs_search",
        description="코드 문서 검색",
        source="crewai",
        category="code",
        class_path="CodeDocsSearchTool",
        keywords=["코드", "code", "문서", "documentation", "api", "레퍼런스", "reference", "가이드", "guide"],
        use_cases=["API 문서 검색", "코드 레퍼런스 조회", "개발 가이드 참조"],
    ),
    "github_search": ToolMetadata(
        name="github_search",
        description="GitHub 저장소 검색",
        source="crewai",
        category="search",
        requires_api_key=True,
        api_key_name="GITHUB_API_KEY",
        class_path="GithubSearchTool",
        keywords=["github", "git", "저장소", "repository", "코드", "code", "오픈소스", "opensource"],
        use_cases=["오픈소스 프로젝트 찾기", "코드 예제 검색", "GitHub 레포 조회"],
    ),
    "youtube_search": ToolMetadata(
        name="youtube_search",
        description="YouTube 동영상 검색",
        source="crewai",
        category="search",
        requires_api_key=True,
        api_key_name="YOUTUBE_API_KEY",
        class_path="YoutubeVideoSearchTool",
        keywords=["youtube", "유튜브", "동영상", "video", "영상", "검색", "search"],
        use_cases=["유튜브 영상 검색", "비디오 콘텐츠 조회", "강의 영상 찾기"],
    ),
    "json_search": ToolMetadata(
        name="json_search",
        description="JSON 파일 검색",
        source="crewai",
        category="data",
        class_path="JSONSearchTool",
        keywords=["json", "데이터", "data", "api", "설정", "config", "구조화"],
        use_cases=["JSON 파일 데이터 검색", "API 응답 분석", "설정 파일 조회"],
    ),
    "xml_search": ToolMetadata(
        name="xml_search",
        description="XML 파일 검색",
        source="crewai",
        category="data",
        class_path="XMLSearchTool",
        keywords=["xml", "데이터", "data", "문서", "document", "구조화"],
        use_cases=["XML 문서 검색", "구조화된 데이터 분석", "XML 설정 파일 조회"],
    ),
}


class DynamicToolRegistry:
    """
    런타임 도구 등록 시스템

    하드코딩 대신 동적으로 도구를 등록하고 조회할 수 있습니다.
    """

    _registry_cache: Optional[ToolRegistry] = None
    _registry_path: Optional[Path] = None

    @classmethod
    def _get_registry(cls) -> ToolRegistry:
        """내부 레지스트리 인스턴스 반환 (캐싱)"""
        if cls._registry_cache is None:
            if cls._registry_path is None:
                from app.utils.config import PROJECT_ROOT
                cls._registry_path = PROJECT_ROOT / "data" / "tools_registry.json"
            cls._registry_cache = get_tool_registry(cls._registry_path)
        return cls._registry_cache

    @classmethod
    def register_tool(
        cls,
        tool_name: str,
        class_path: str,
        description: str = "",
        source: str = "custom",
        category: str = "general",
        requires_api_key: bool = False,
        api_key_name: Optional[str] = None,
    ) -> bool:
        """
        새 도구 등록

        Args:
            tool_name: 도구 이름
            class_path: 도구 클래스 경로 (예: SerperDevTool)
            description: 도구 설명
            source: 도구 출처 (mcp/crewai/custom)
            category: 도구 카테고리
            requires_api_key: API 키 필요 여부
            api_key_name: 필요한 API 키 이름

        Returns:
            bool: 등록 성공 여부
        """
        registry = cls._get_registry()

        tool = ToolMetadata(
            name=tool_name,
            description=description or f"{tool_name} tool",
            source=source,
            category=category,
            class_path=class_path,
            requires_api_key=requires_api_key,
            api_key_name=api_key_name,
        )

        # 도구 추가 (이미 존재하면 업데이트)
        if tool_name in registry.tools:
            logger.info(f"도구가 이미 존재합니다. 업데이트합니다: {tool_name}")
            registry.tools[tool_name] = tool
        else:
            success = registry.add_tool(tool)
            if not success:
                return False

        # 레지스트리 저장
        if cls._registry_path:
            registry.save(cls._registry_path)

        logger.info(f"도구 등록 완료: {tool_name} -> {class_path}")
        return True

    @classmethod
    def get_tool_class(cls, tool_name: str) -> Optional[str]:
        """
        도구 클래스 경로 조회

        Args:
            tool_name: 도구 이름

        Returns:
            str: 도구 클래스 경로 (예: SerperDevTool) 또는 None
        """
        registry = cls._get_registry()
        tool = registry.get_tool(tool_name)

        if tool is None:
            logger.warning(f"도구를 찾을 수 없습니다: {tool_name}")
            return None

        if not tool.class_path:
            logger.warning(f"도구 '{tool_name}'의 class_path가 설정되지 않았습니다")
            return None

        return tool.class_path

    @classmethod
    def get_all_tool_mappings(cls) -> Dict[str, str]:
        """
        모든 도구의 {이름: 클래스경로} 매핑 반환

        Returns:
            Dict[str, str]: {tool_name: class_path} 매핑
        """
        registry = cls._get_registry()
        mappings = {}

        for tool_name, tool_metadata in registry.tools.items():
            if tool_metadata.class_path:
                mappings[tool_name] = tool_metadata.class_path

        return mappings

    @classmethod
    def unregister_tool(cls, tool_name: str) -> bool:
        """
        도구 등록 해제

        Args:
            tool_name: 도구 이름

        Returns:
            bool: 해제 성공 여부
        """
        registry = cls._get_registry()
        success = registry.remove_tool(tool_name)

        if success and cls._registry_path:
            registry.save(cls._registry_path)

        return success

    @classmethod
    def reload_registry(cls) -> None:
        """레지스트리 캐시 새로고침"""
        cls._registry_cache = None
        logger.info("도구 레지스트리 캐시를 새로고침했습니다")


def get_tool_registry(registry_path: Optional[Path] = None) -> ToolRegistry:
    """
    도구 저장소 싱글톤 인스턴스 반환

    Args:
        registry_path: 저장소 파일 경로 (기본: ./data/tools_registry.json)

    Returns:
        ToolRegistry: 도구 저장소
    """
    if registry_path is None:
        from app.utils.config import PROJECT_ROOT
        registry_path = PROJECT_ROOT / "data" / "tools_registry.json"

    registry = ToolRegistry.load(registry_path)

    # 기본 CrewAI 도구가 없으면 추가
    tools_added = False
    for tool_name, tool_metadata in DEFAULT_CREWAI_TOOLS.items():
        if tool_name not in registry.tools:
            registry.add_tool(tool_metadata)
            tools_added = True

    # 변경사항이 있을 때만 저장
    if tools_added:
        registry.save(registry_path)

    return registry


def get_enabled_tools_dict() -> Dict[str, str]:
    """
    활성화된 도구를 {name: description} 딕셔너리로 반환

    Returns:
        Dict[str, str]: {도구명: 설명} 딕셔너리
    """
    registry = get_tool_registry()
    enabled_tools = registry.get_enabled_tools()

    return {
        tool.name: tool.description
        for tool in enabled_tools
    }


def get_all_tools_dict() -> Dict[str, str]:
    """
    모든 도구를 {name: description} 딕셔너리로 반환 (활성화 여부 무관)

    Returns:
        Dict[str, str]: {도구명: 설명} 딕셔너리
    """
    registry = get_tool_registry()

    return {
        tool.name: tool.description
        for tool in registry.tools.values()
    }


def get_tool_api_key_status() -> Dict[str, Dict[str, Any]]:
    """
    도구별 API 키 설정 상태 조회

    Returns:
        Dict[str, Dict]: {도구명: {api_key_name, is_configured, value_preview}}
    """
    from app.utils.config import get_api_key

    registry = get_tool_registry()
    status = {}

    for tool_name, tool in registry.tools.items():
        if tool.requires_api_key and tool.api_key_name:
            api_key_value = get_api_key(tool.api_key_name)
            is_configured = bool(api_key_value and not api_key_value.startswith("your-"))

            status[tool_name] = {
                "api_key_name": tool.api_key_name,
                "is_configured": is_configured,
                "value_preview": _mask_api_key(api_key_value) if api_key_value else None,
            }

    return status


def _mask_api_key(key: str) -> str:
    """API 키 마스킹"""
    if not key or key.startswith("your-"):
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


def get_required_api_keys() -> List[Dict[str, Any]]:
    """
    API 키가 필요한 모든 도구 목록 반환

    Returns:
        List[Dict]: [{tool_name, api_key_name, description, is_configured}]
    """
    from app.utils.config import get_api_key

    registry = get_tool_registry()
    required_keys = []

    for tool_name, tool in registry.tools.items():
        if tool.requires_api_key and tool.api_key_name:
            api_key_value = get_api_key(tool.api_key_name)
            is_configured = bool(api_key_value and not api_key_value.startswith("your-"))

            required_keys.append({
                "tool_name": tool_name,
                "api_key_name": tool.api_key_name,
                "description": tool.description,
                "is_configured": is_configured,
                "category": tool.category,
            })

    return required_keys


def recommend_tools_by_keywords(requirement_text: str, top_n: int = 5) -> List[Dict[str, Any]]:
    """
    요구사항 텍스트를 분석하여 적합한 도구 추천

    Args:
        requirement_text: 요구사항 텍스트
        top_n: 추천할 도구 개수

    Returns:
        List[Dict]: [{tool_name, score, matched_keywords, use_cases}] (점수 순)
    """
    registry = get_tool_registry()
    enabled_tools = registry.get_enabled_tools()

    requirement_lower = requirement_text.lower()

    tool_scores = []

    for tool in enabled_tools:
        score = 0
        matched_keywords = []

        # 키워드 매칭
        for keyword in tool.keywords:
            if keyword.lower() in requirement_lower:
                score += 1
                matched_keywords.append(keyword)

        # 사용 사례 매칭 (가중치 더 높음)
        for use_case in tool.use_cases:
            if any(word in requirement_lower for word in use_case.lower().split()):
                score += 0.5

        # 카테고리 매칭 (보너스)
        if tool.category in requirement_lower:
            score += 0.5

        if score > 0:
            tool_scores.append({
                "tool_name": tool.name,
                "score": score,
                "matched_keywords": matched_keywords,
                "use_cases": tool.use_cases,
                "category": tool.category,
                "description": tool.description,
            })

    # 점수 순으로 정렬
    tool_scores.sort(key=lambda x: x["score"], reverse=True)

    return tool_scores[:top_n]


def get_tools_info_for_llm(include_keywords: bool = True, include_use_cases: bool = True) -> str:
    """
    LLM에게 제공할 도구 정보를 포맷팅된 문자열로 반환

    Args:
        include_keywords: 키워드 포함 여부
        include_use_cases: 사용 사례 포함 여부

    Returns:
        str: 포맷팅된 도구 정보
    """
    registry = get_tool_registry()
    enabled_tools = registry.get_enabled_tools()

    if not enabled_tools:
        return "사용 가능한 도구가 없습니다."

    # 카테고리별로 그룹화
    tools_by_category = {}
    for tool in enabled_tools:
        category = tool.category
        if category not in tools_by_category:
            tools_by_category[category] = []
        tools_by_category[category].append(tool)

    # 포맷팅
    lines = []
    for category, tools in sorted(tools_by_category.items()):
        lines.append(f"\n[{category.upper()}]")
        for tool in tools:
            lines.append(f"- {tool.name}: {tool.description}")

            if include_keywords and tool.keywords:
                keywords_str = ", ".join(tool.keywords[:5])  # 처음 5개만
                lines.append(f"  Keywords: {keywords_str}")

            if include_use_cases and tool.use_cases:
                use_cases_str = "; ".join(tool.use_cases[:3])  # 처음 3개만
                lines.append(f"  Use cases: {use_cases_str}")

    return "\n".join(lines)
