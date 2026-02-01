"""
Tool Generator for CrewAI Code Generation

Generates tool imports and initializations for CrewAI agents.
"""

from typing import List, Dict, Tuple, Optional
from caas_framework.utils.logger import get_logger


# CrewAI 기본 도구 매핑 (카테고리별)
CREWAI_TOOLS_BY_CATEGORY = {
    "file": [
        "FileReadTool",
        "FileWriterTool",
        "DirectoryReadTool",
        "DirectorySearchTool",
    ],
    "search": [
        "SerperDevTool",
        "WebsiteSearchTool",
        "ScrapeWebsiteTool",
        "BraveSearchTool",
        "TavilySearchTool",
    ],
    "document": [
        "PDFSearchTool",
        "DOCXSearchTool",
        "CSVSearchTool",
        "JSONSearchTool",
        "XMLSearchTool",
        "TXTSearchTool",
        "MDXSearchTool",
    ],
    "code": [
        "CodeInterpreterTool",
        "CodeDocsSearchTool",
        "GithubSearchTool",
    ],
    "database": [
        "MySQLSearchTool",
        "MongoDBVectorSearchTool",
        "SingleStoreSearchTool",
        "SnowflakeSearchTool",
    ],
    "web_scraping": [
        "SeleniumScrapingTool",
        "FirecrawlScrapeWebsiteTool",
        "JinaScrapeWebsiteTool",
        "ScrapeElementFromWebsiteTool",
    ],
    "vision": [
        "VisionTool",
    ],
    "youtube": [
        "YoutubeChannelSearchTool",
        "YoutubeVideoSearchTool",
    ],
}

# Legacy hardcoded mapping removed - now dynamically generated from Tool Ontology
# Use get_tool_name_to_crewai() and get_crewai_to_tool_name() functions instead

_TOOL_NAME_TO_CREWAI_CACHE = None
_CREWAI_TO_TOOL_NAME_CACHE = None


def get_tool_name_to_crewai() -> Dict[str, Optional[str]]:
    """
    Tool Ontology에서 동적으로 tool name → CrewAI class 매핑을 생성합니다.

    Returns:
        Dict[str, Optional[str]]: 도구 이름 → CrewAI 클래스 매핑 (None은 커스텀 도구)
    """
    global _TOOL_NAME_TO_CREWAI_CACHE

    if _TOOL_NAME_TO_CREWAI_CACHE is not None:
        return _TOOL_NAME_TO_CREWAI_CACHE

    mapping = {}

    try:
        from app.core.ontology import get_tool_ontology_manager
        tool_manager = get_tool_ontology_manager()
        all_tools = tool_manager.get_all_tools(enabled_only=False)  # Include disabled for completeness

        for tool in all_tools:
            # Get default implementation
            if tool.default_implementation:
                mapping[tool.name] = tool.default_implementation
            elif tool.implementations:
                # Use first implementation as default
                mapping[tool.name] = tool.implementations[0].crewai_class
            else:
                # Custom tool (no implementation)
                mapping[tool.name] = None

    except Exception as e:
        logger = get_logger("tool_generator")
        logger.warning(f"Tool Ontology 로드 실패: {e}, 빈 매핑 반환")

    _TOOL_NAME_TO_CREWAI_CACHE = mapping
    return mapping


def get_crewai_to_tool_name() -> Dict[str, str]:
    """
    Tool Ontology에서 동적으로 CrewAI class → tool name 역매핑을 생성합니다.

    Returns:
        Dict[str, str]: CrewAI 클래스 → 도구 이름 매핑
    """
    global _CREWAI_TO_TOOL_NAME_CACHE

    if _CREWAI_TO_TOOL_NAME_CACHE is not None:
        return _CREWAI_TO_TOOL_NAME_CACHE

    tool_to_crewai = get_tool_name_to_crewai()
    reverse_mapping = {v: k for k, v in tool_to_crewai.items() if v is not None}

    _CREWAI_TO_TOOL_NAME_CACHE = reverse_mapping
    return reverse_mapping


# Module-level variables that get populated on first import
# These provide backward compatibility with existing code
def _initialize_mappings():
    """Initialize module-level mapping variables on first import"""
    global TOOL_NAME_TO_CREWAI, CREWAI_TO_TOOL_NAME
    TOOL_NAME_TO_CREWAI = get_tool_name_to_crewai()
    CREWAI_TO_TOOL_NAME = get_crewai_to_tool_name()

# Initialize immediately on module import
_initialize_mappings()


def is_custom_tool(tool_name: str) -> bool:
    """
    도구가 커스텀 도구인지 확인합니다.

    커스텀 도구는 crewai_tools 패키지에서 import할 수 없고,
    @tool 데코레이터를 사용하여 정의해야 합니다.

    Args:
        tool_name: 도구 이름 (예: "calculator", "web_search")

    Returns:
        bool: 커스텀 도구이면 True, CrewAI 기본 도구이면 False

    Examples:
        >>> is_custom_tool("calculator")
        True
        >>> is_custom_tool("web_search")
        False
        >>> is_custom_tool("SerperDevTool")
        False
    """
    tool_name_lower = tool_name.lower().strip()

    # TOOL_NAME_TO_CREWAI에 있는지 확인
    if tool_name_lower in TOOL_NAME_TO_CREWAI:
        # None이면 커스텀 도구
        return TOOL_NAME_TO_CREWAI[tool_name_lower] is None

    # 이미 CrewAI 클래스 이름인 경우 (예: "SerperDevTool")
    if tool_name in TOOL_NAME_TO_CREWAI.values():
        return False

    # 매핑에 없으면 커스텀 도구로 간주
    return True


def get_crewai_tool_class(tool_name: str) -> str:
    """
    도구 이름을 CrewAI 도구 클래스 이름으로 변환합니다.

    Args:
        tool_name: 도구 이름

    Returns:
        str: CrewAI 도구 클래스 이름, 또는 커스텀 도구인 경우 원래 이름

    Examples:
        >>> get_crewai_tool_class("web_search")
        'SerperDevTool'
        >>> get_crewai_tool_class("calculator")
        'calculator'
    """
    tool_name_lower = tool_name.lower().strip()

    # 이미 CrewAI 클래스 이름인 경우
    if tool_name in TOOL_NAME_TO_CREWAI.values():
        return tool_name

    # 매핑에서 찾기
    mapped_class = TOOL_NAME_TO_CREWAI.get(tool_name_lower, tool_name)

    # None이면 커스텀 도구이므로 원래 이름 반환
    if mapped_class is None:
        return tool_name

    return mapped_class


def generate_tool_imports(tool_names: List[str], use_mcp: bool = False) -> Tuple[List[str], List[str]]:
    """
    도구 이름 목록에서 import 문과 도구 초기화 코드를 생성합니다.

    Args:
        tool_names: 도구 이름 목록 (예: ["file_read", "web_search", "calculator"])
        use_mcp: MCP 도구 사용 여부

    Returns:
        (import_lines, tool_init_lines): Import 문 리스트와 도구 초기화 코드 리스트
    """
    import_lines = []
    tool_init_lines = []
    crewai_tools = set()
    custom_tools = []

    # 도구 이름을 CrewAI 도구로 매핑
    for tool_name in tool_names:
        tool_name_lower = tool_name.lower().strip()

        # CrewAI 기본 도구인지 확인
        if tool_name_lower in TOOL_NAME_TO_CREWAI:
            crewai_tool = TOOL_NAME_TO_CREWAI[tool_name_lower]
            # None인 경우는 커스텀 도구이므로 제외
            if crewai_tool is not None:
                crewai_tools.add(crewai_tool)
            else:
                # 커스텀 도구로 처리
                custom_tools.append(tool_name_lower)
        elif tool_name in TOOL_NAME_TO_CREWAI.values():
            # 이미 CrewAI 도구 이름 (None이 아닌 경우만)
            if tool_name is not None:
                crewai_tools.add(tool_name)
        else:
            # 커스텀 도구로 처리
            custom_tools.append(tool_name_lower)

    # CrewAI 도구 import
    if crewai_tools:
        tools_str = ", ".join(sorted(crewai_tools))
        import_lines.append(f"from crewai_tools import {tools_str}")

    # MCP import (필요 시)
    if use_mcp:
        import_lines.extend([
            "from crewai_tools import MCPServerAdapter",
            "from mcp import StdioServerParameters",
            "import os",
        ])

    # 커스텀 도구를 위한 import
    if custom_tools:
        import_lines.append("from crewai import tool")

    # 도구 초기화 코드 생성
    tool_init_lines.append("# Initialize Tools")

    # CrewAI 기본 도구 초기화
    for crewai_tool in sorted(crewai_tools):
        tool_var = crewai_tool.replace("Tool", "").lower()
        tool_init_lines.append(f"{tool_var}_tool = {crewai_tool}()")

    # MCP 도구 초기화
    if use_mcp:
        tool_init_lines.extend([
            "",
            "# Initialize MCP Tools",
            "try:",
            "    # MCP 서버 설정 (예시: filesystem MCP 서버)",
            "    mcp_server_params = StdioServerParameters(",
            "        command=\"npx\",",
            "        args=[\"-y\", \"@modelcontextprotocol/server-filesystem\", \".\"],",
            "        env={**os.environ}",
            "    )",
            "    ",
            "    # MCP 서버 어댑터 생성",
            "    mcp_adapter = MCPServerAdapter(mcp_server_params)",
            "    mcp_tools = list(mcp_adapter.__enter__())",
            "except Exception as e:",
            "    print(f'Warning: MCP tools initialization failed: {e}')",
            "    mcp_tools = []",
        ])

    # 커스텀 도구 정의 (데코레이터 방식)
    if custom_tools:
        tool_init_lines.extend([
            "",
            "# Define Custom Tools with @tool decorator",
        ])

        for custom_tool in custom_tools:
            # Calculator에 대한 특별한 구현
            if custom_tool == "calculator":
                tool_init_lines.extend([
                    '@tool("calculator")',
                    'def calculator_tool(expression: str) -> str:',
                    '    """',
                    '    Evaluate mathematical expressions safely',
                    '    ',
                    '    Args:',
                    '        expression: Mathematical expression to evaluate (e.g., "2 + 2", "sqrt(16)")',
                    '    ',
                    '    Returns:',
                    '        Result of the calculation',
                    '    """',
                    '    import math',
                    '    import re',
                    '    ',
                    '    # Whitelist of safe operations',
                    '    safe_dict = {',
                    '        "abs": abs, "round": round, "min": min, "max": max,',
                    '        "sum": sum, "pow": pow,',
                    '        "sqrt": math.sqrt, "log": math.log, "log10": math.log10,',
                    '        "sin": math.sin, "cos": math.cos, "tan": math.tan,',
                    '        "pi": math.pi, "e": math.e',
                    '    }',
                    '    ',
                    '    try:',
                    '        # Remove any potentially dangerous characters',
                    '        if re.search(r"[^0-9+\\-*/.()\\s,a-z]", expression, re.IGNORECASE):',
                    '            return f"Error: Expression contains invalid characters"',
                    '        ',
                    '        result = eval(expression, {"__builtins__": {}}, safe_dict)',
                    '        return f"Result: {result}"',
                    '    except Exception as e:',
                    '        return f"Error: {str(e)}"',
                    "",
                ])
            else:
                # 다른 custom tool들은 기본 템플릿 사용
                tool_init_lines.extend([
                    f'@tool("{custom_tool}")',
                    f'def {custom_tool}_tool(input_data: str) -> str:',
                    f'    """',
                    f'    Custom tool: {custom_tool}',
                    f'    ',
                    f'    Args:',
                    f'        input_data: Input data for the tool',
                    f'    ',
                    f'    Returns:',
                    f'        Result of the tool execution',
                    f'    """',
                    f'    # TODO: Implement {custom_tool} logic',
                    f'    return f"Executed {custom_tool} with input: {{input_data}}"',
                    "",
                ])

    tool_init_lines.append("")

    return import_lines, tool_init_lines


def generate_tools_list(tool_names: List[str], use_mcp: bool = False) -> str:
    """
    Agent의 tools 파라미터에 들어갈 도구 리스트를 생성합니다.

    Args:
        tool_names: 도구 이름 목록
        use_mcp: MCP 도구 사용 여부

    Returns:
        tools 리스트 문자열 (예: "[file_read_tool, web_search_tool]")
    """
    tool_vars = []

    # CrewAI 도구
    for tool_name in tool_names:
        tool_name_lower = tool_name.lower().strip()

        if tool_name_lower in TOOL_NAME_TO_CREWAI:
            crewai_tool = TOOL_NAME_TO_CREWAI[tool_name_lower]
            # None인 경우는 커스텀 도구
            if crewai_tool is not None:
                tool_var = crewai_tool.replace("Tool", "").lower()
                tool_vars.append(f"{tool_var}_tool")
            else:
                # 커스텀 도구
                tool_vars.append(f"{tool_name_lower}_tool")
        elif tool_name in TOOL_NAME_TO_CREWAI.values():
            if tool_name is not None:
                tool_var = tool_name.replace("Tool", "").lower()
                tool_vars.append(f"{tool_var}_tool")
        else:
            # 커스텀 도구
            tool_vars.append(f"{tool_name_lower}_tool")

    # MCP 도구 추가
    if use_mcp:
        tool_vars.append("*mcp_tools")

    if not tool_vars:
        return "[]"

    return "[" + ", ".join(tool_vars) + "]"


def get_valid_tools(tool_names: List[str]) -> List[str]:
    """
    도구 목록에서 유효한 도구만 필터링합니다.

    존재하지 않는 도구는 제거됩니다.

    Args:
        tool_names: 도구 이름 목록

    Returns:
        유효한 도구 목록
    """
    # 존재하지 않는 도구 목록 (하드코딩)
    INVALID_TOOLS = {
        "slack_search", "slacksearchtool",
        "email_search", "emailsearchtool",
        "ocr", "ocrtool",
        "dalle", "dalletool",
        "stable_diffusion", "stablediffusiontool"
    }

    valid_tools = []
    for tool in tool_names:
        tool_lower = tool.lower().strip()
        if tool_lower not in INVALID_TOOLS:
            valid_tools.append(tool)

    return valid_tools


def get_recommended_tools_for_task(task_description: str, agent_role: str) -> List[str]:
    """
    태스크 설명과 에이전트 역할에 따라 추천 도구를 반환합니다.

    Args:
        task_description: 태스크 설명
        agent_role: 에이전트 역할

    Returns:
        추천 도구 목록
    """
    recommended = []

    desc_lower = task_description.lower()
    role_lower = agent_role.lower()

    # 파일 관련
    if any(word in desc_lower or word in role_lower for word in ["file", "read", "write", "파일", "읽기", "쓰기"]):
        recommended.extend(["file_read", "file_write"])
    if any(word in desc_lower or word in role_lower for word in ["directory", "folder", "디렉토리", "폴더"]):
        recommended.extend(["directory_read", "directory_search"])

    # 웹 검색
    if any(word in desc_lower or word in role_lower for word in ["search", "web", "website", "검색", "웹"]):
        recommended.append("web_search")
    if any(word in desc_lower or word in role_lower for word in ["brave"]):
        recommended.append("brave_search")
    if any(word in desc_lower or word in role_lower for word in ["tavily", "ai search"]):
        recommended.append("tavily_search")

    # 웹 스크래핑
    if any(word in desc_lower or word in role_lower for word in ["scrape", "crawl", "extract", "스크래핑", "크롤링"]):
        recommended.append("scrape_website")
    if "selenium" in desc_lower:
        recommended.append("selenium_scraping")

    # 코드 해석
    if any(word in desc_lower or word in role_lower for word in ["code", "python", "execute", "코드", "실행"]):
        recommended.append("code_interpreter")
    if any(word in desc_lower or word in role_lower for word in ["calculate", "math", "계산", "수학"]):
        recommended.append("calculator")
    if "github" in desc_lower or "github" in role_lower:
        recommended.append("github_search")

    # 문서 검색
    if "pdf" in desc_lower or "pdf" in role_lower:
        recommended.append("pdf_search")
    if "csv" in desc_lower or "csv" in role_lower:
        recommended.append("csv_search")
    if "json" in desc_lower or "json" in role_lower:
        recommended.append("json_search")
    if "docx" in desc_lower or "word" in desc_lower:
        recommended.append("docx_search")
    if "xml" in desc_lower:
        recommended.append("xml_search")

    # 데이터베이스
    if any(word in desc_lower or word in role_lower for word in ["database", "sql", "mysql", "데이터베이스"]):
        recommended.append("mysql_search")
    if "mongodb" in desc_lower or "mongo" in desc_lower:
        recommended.append("mongodb_search")
    if "snowflake" in desc_lower:
        recommended.append("snowflake_search")

    # 비전/이미지
    if any(word in desc_lower or word in role_lower for word in ["image", "vision", "visual", "이미지", "시각", "ocr", "text extraction", "문자 인식"]):
        recommended.append("vision")

    # 유튜브
    if "youtube" in desc_lower or "유튜브" in role_lower:
        recommended.append("youtube_search")

    # RAG
    if any(word in desc_lower or word in role_lower for word in ["rag", "retrieval", "knowledge base", "검색 증강"]):
        recommended.append("rag_tool")

    return list(set(recommended))  # 중복 제거
