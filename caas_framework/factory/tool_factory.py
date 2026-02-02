"""
CAAS Tool Factory

CrewAI 도구 생성 및 연결을 담당합니다.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("caas_framework.factory.tool")


class ToolType(str, Enum):
    """도구 유형"""

    BUILTIN = "builtin"
    CUSTOM = "custom"
    LANGCHAIN = "langchain"


class ToolCapability(str, Enum):
    """도구 기능"""

    WEB_SEARCH = "web_search"
    WEB_SCRAPE = "web_scrape"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    CODE_EXECUTE = "code_execute"
    CALCULATION = "calculation"
    DATABASE = "database"
    API_CALL = "api_call"


class ToolDefinition(BaseModel):
    """도구 정의"""

    id: str
    name: str
    description: str
    tool_type: ToolType = ToolType.BUILTIN
    capabilities: List[ToolCapability] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    requires_api_key: bool = False
    import_path: str = ""
    class_name: str = ""


class ToolFactory:
    """
    도구 팩토리

    CrewAI 도구 인스턴스를 생성하고 관리합니다.

    Note:
        Tool Ontology (`data/ontology/tools.json`)를 단일 진실 공급원으로 사용합니다.
        하드코딩된 도구 매핑은 제거되었으며, 모든 도구 정의는 동적으로 생성됩니다.
    """

    # Legacy hardcoded mappings removed - now dynamically generated from Tool Ontology
    _builtin_tools_cache: Optional[Dict[str, ToolDefinition]] = None
    _capability_tool_map_cache: Optional[Dict[ToolCapability, List[str]]] = None

    def __init__(self):
        self.logger = logger
        self.custom_tools: Dict[str, ToolDefinition] = {}

        # Dynamically build tool definitions from Tool Ontology on first access
        if ToolFactory._builtin_tools_cache is None:
            ToolFactory._builtin_tools_cache = self._build_tools_from_ontology()
        if ToolFactory._capability_tool_map_cache is None:
            ToolFactory._capability_tool_map_cache = self._build_capability_map()

    @property
    def BUILTIN_TOOLS(self) -> Dict[str, ToolDefinition]:
        """Tool Ontology에서 동적으로 생성된 도구 정의"""
        if ToolFactory._builtin_tools_cache is None:
            ToolFactory._builtin_tools_cache = self._build_tools_from_ontology()
        return ToolFactory._builtin_tools_cache

    @property
    def CAPABILITY_TOOL_MAP(self) -> Dict[ToolCapability, List[str]]:
        """Tool capabilities에서 동적으로 생성된 매핑"""
        if ToolFactory._capability_tool_map_cache is None:
            ToolFactory._capability_tool_map_cache = self._build_capability_map()
        return ToolFactory._capability_tool_map_cache

    def _build_tools_from_ontology(self) -> Dict[str, ToolDefinition]:
        """Tool Ontology에서 ToolDefinition 객체를 동적으로 생성합니다."""
        tools_map = {}

        try:
            from caas_framework.knowledge.ontology import get_tool_ontology_manager
            from caas_framework.knowledge.ontology.tool_ontology import ToolType as OntologyToolType

            tool_manager = get_tool_ontology_manager()
            all_tools = tool_manager.get_all_tools(enabled_only=False)

            # Capability keyword mapping
            capability_keywords = {
                ToolCapability.WEB_SEARCH: ["search", "google", "youtube", "github"],
                ToolCapability.WEB_SCRAPE: ["scrape", "crawl", "extract"],
                ToolCapability.FILE_READ: [
                    "read",
                    "file",
                    "pdf",
                    "directory",
                    "csv",
                    "json",
                    "xml",
                ],
                ToolCapability.FILE_WRITE: ["write", "save", "create"],
                ToolCapability.CODE_EXECUTE: ["code", "python", "execute", "interpreter"],
                ToolCapability.CALCULATION: ["calculator", "calculation", "math"],
                ToolCapability.DATABASE: ["database", "sql", "query"],
                ToolCapability.API_CALL: ["api", "rest", "http"],
            }

            for tool in all_tools:
                # Determine tool_type and import_path from ontology type
                if tool.type == OntologyToolType.BUILT_IN:
                    tool_type = ToolType.BUILTIN
                    import_path = "crewai_tools"
                elif tool.type == OntologyToolType.CUSTOM:
                    tool_type = ToolType.CUSTOM
                    import_path = ""  # Custom tools don't have import path
                elif tool.type == OntologyToolType.MCP:
                    tool_type = ToolType.CUSTOM  # Treat MCP as custom for now
                    import_path = ""
                else:
                    tool_type = ToolType.CUSTOM
                    import_path = ""

                # Get class name from default_implementation or first implementation
                class_name = tool.default_implementation or ""
                if not class_name and tool.implementations:
                    class_name = tool.implementations[0].crewai_class

                # Check for API key requirements
                requires_api_key = False
                api_key_env = None
                if tool.implementations:
                    # Use first implementation's API key info
                    impl = tool.implementations[0]
                    requires_api_key = impl.requires_api_key
                    api_key_env = impl.api_key_env

                # Infer capabilities from category and tags
                capabilities = []
                all_keywords = " ".join([tool.category.value] + tool.tags + [tool.name]).lower()

                for cap, keywords in capability_keywords.items():
                    if any(kw in all_keywords for kw in keywords):
                        capabilities.append(cap)

                # Build parameters for API key requirements
                parameters = {}
                if requires_api_key and api_key_env:
                    parameters = {
                        "env_var": api_key_env,
                        "param_name": None,
                        "optional": False,
                    }

                tools_map[tool.name] = ToolDefinition(
                    id=tool.name,
                    name=class_name or tool.name,
                    description=tool.description,
                    tool_type=tool_type,
                    capabilities=capabilities,
                    parameters=parameters,
                    requires_api_key=requires_api_key,
                    import_path=import_path,
                    class_name=class_name,
                )

            self.logger.info(f"Tool Ontology에서 {len(tools_map)}개 도구 정의 생성 완료")

        except Exception as e:
            self.logger.error(f"Tool Ontology 로드 실패: {e}")
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")
            # Return empty dict as fallback
            return {}

        return tools_map

    def _build_capability_map(self) -> Dict[ToolCapability, List[str]]:
        """도구 capabilities에서 capability → tool 매핑을 동적으로 생성합니다."""
        cap_map: Dict[ToolCapability, List[str]] = {cap: [] for cap in ToolCapability}

        for tool_id, tool_def in self.BUILTIN_TOOLS.items():
            for capability in tool_def.capabilities:
                if capability in cap_map:
                    cap_map[capability].append(tool_id)

        # Remove empty capabilities
        cap_map = {k: v for k, v in cap_map.items() if v}

        self.logger.debug(f"Capability map 생성 완료: {len(cap_map)}개 capability")
        return cap_map

    def get_tool_definition(self, tool_id: str) -> Optional[ToolDefinition]:
        """
        도구 정의를 조회합니다.

        Args:
            tool_id: 도구 ID

        Returns:
            Optional[ToolDefinition]: 도구 정의
        """
        # 내장 도구에서 먼저 검색
        if tool_id in self.BUILTIN_TOOLS:
            return self.BUILTIN_TOOLS[tool_id]

        # 커스텀 도구에서 검색
        return self.custom_tools.get(tool_id)

    def register_custom_tool(self, definition: ToolDefinition) -> None:
        """
        커스텀 도구를 등록합니다.

        Args:
            definition: 도구 정의
        """
        self.custom_tools[definition.id] = definition
        self.logger.info(f"커스텀 도구 등록: {definition.id}")

    def recommend_tools(
        self,
        capabilities: List[ToolCapability],
        max_tools: int = 5,
    ) -> List[str]:
        """
        필요한 기능에 맞는 도구를 추천합니다.

        Args:
            capabilities: 필요한 기능 목록
            max_tools: 최대 도구 수

        Returns:
            List[str]: 추천 도구 ID 목록
        """
        recommended = set()

        for cap in capabilities:
            if cap in self.CAPABILITY_TOOL_MAP:
                tools = self.CAPABILITY_TOOL_MAP[cap]
                # 첫 번째 도구를 우선 추천
                if tools:
                    recommended.add(tools[0])

        return list(recommended)[:max_tools]

    def create_tool_import_code(self, tool_ids: List[str]) -> str:
        """
        도구 임포트 코드를 생성합니다.

        Args:
            tool_ids: 도구 ID 목록

        Returns:
            str: 임포트 코드
        """
        imports = {}

        for tool_id in tool_ids:
            definition = self.get_tool_definition(tool_id)
            if definition:
                if definition.import_path not in imports:
                    imports[definition.import_path] = []
                imports[definition.import_path].append(definition.class_name)

        lines = []
        for import_path, class_names in imports.items():
            classes = ", ".join(sorted(set(class_names)))
            lines.append(f"from {import_path} import {classes}")

        return "\n".join(sorted(lines))

    def create_tool_instantiation_code(
        self,
        tool_ids: List[str],
        variable_prefix: str = "tool_",
    ) -> str:
        """
        도구 인스턴스화 코드를 생성합니다.

        Args:
            tool_ids: 도구 ID 목록
            variable_prefix: 변수 접두사

        Returns:
            str: 인스턴스화 코드
        """
        lines = []

        for tool_id in tool_ids:
            definition = self.get_tool_definition(tool_id)
            if definition:
                var_name = f"{variable_prefix}{tool_id}"

                # 파라미터 처리
                params = ""
                if definition.parameters:
                    param_items = [f"{k}={repr(v)}" for k, v in definition.parameters.items()]
                    params = ", ".join(param_items)

                lines.append(f"{var_name} = {definition.class_name}({params})")

        return "\n".join(lines)

    def create_tool_list_code(
        self,
        tool_ids: List[str],
        variable_prefix: str = "tool_",
    ) -> str:
        """
        도구 리스트 코드를 생성합니다.

        Args:
            tool_ids: 도구 ID 목록
            variable_prefix: 변수 접두사

        Returns:
            str: 리스트 코드
        """
        var_names = [f"{variable_prefix}{tid}" for tid in tool_ids]
        return f"[{', '.join(var_names)}]"

    def get_all_tools(self) -> Dict[str, ToolDefinition]:
        """모든 도구 정의 반환"""
        all_tools = dict(self.BUILTIN_TOOLS)
        all_tools.update(self.custom_tools)
        return all_tools

    def get_tools_by_capability(
        self,
        capability: ToolCapability,
    ) -> List[ToolDefinition]:
        """
        기능별 도구 목록 반환

        Args:
            capability: 도구 기능

        Returns:
            List[ToolDefinition]: 도구 정의 목록
        """
        tool_ids = self.CAPABILITY_TOOL_MAP.get(capability, [])
        return [self.BUILTIN_TOOLS[tid] for tid in tool_ids if tid in self.BUILTIN_TOOLS]

    def validate_tools(self, tool_ids: List[str]) -> Dict[str, Any]:
        """
        도구 유효성 검증

        Args:
            tool_ids: 도구 ID 목록

        Returns:
            Dict: 검증 결과
        """
        valid = []
        invalid = []
        warnings = []

        for tool_id in tool_ids:
            definition = self.get_tool_definition(tool_id)

            if definition is None:
                invalid.append(f"Unknown tool: {tool_id}")
            else:
                valid.append(tool_id)

                if definition.requires_api_key:
                    warnings.append(f"Tool '{tool_id}' requires API key configuration")

        return {
            "valid": len(invalid) == 0,
            "valid_tools": valid,
            "invalid_tools": invalid,
            "warnings": warnings,
        }


# 도구 별칭 매핑
TOOL_ALIASES: Dict[str, str] = {
    "search": "web_search",
    "serper": "web_search",
    "scraper": "scrape_website",
    "scrape": "scrape_website",
    "read": "file_read",
    "read_file": "file_read",
    "write": "file_write",
    "write_file": "file_write",
    "python": "code_interpreter",
    "code": "code_interpreter",
    "interpreter": "code_interpreter",
    "calc": "calculator",
    "math": "calculator",
    "pdf": "pdf_search",
    "youtube": "youtube_search",
    "github": "github_search",
    "dir": "directory_read",
    "directory": "directory_read",
}


def resolve_tool_alias(tool_name: str) -> str:
    """
    도구 별칭을 실제 도구 ID로 변환합니다.

    Args:
        tool_name: 도구 이름 또는 별칭

    Returns:
        str: 도구 ID
    """
    normalized = tool_name.lower().replace("-", "_").replace(" ", "_")
    return TOOL_ALIASES.get(normalized, normalized)
