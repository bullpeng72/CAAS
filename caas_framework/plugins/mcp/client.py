"""
CAAS MCP (Model Context Protocol) Client

CrewAI의 공식 MCPServerAdapter를 사용하여 MCP 서버와 통합합니다.
"""

import os
from contextlib import contextmanager
from typing import Any, List, Optional

from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

from caas_framework.config.settings import get_settings
from caas_framework.utils.logger import get_logger

logger = get_logger("tools.mcp")


@contextmanager
def get_mcp_adapter(
    transport_type: str = "http",
    server_url: Optional[str] = None,
    server_command: Optional[str] = None,
    server_args: Optional[List[str]] = None,
    tool_names: Optional[List[str]] = None,
    connect_timeout: int = 30,
):
    """
    MCP 서버 어댑터를 생성하는 컨텍스트 매니저

    Args:
        transport_type: 전송 타입 ("stdio", "sse", "http")
        server_url: 서버 URL (sse/http용)
        server_command: 서버 실행 명령어 (stdio용)
        server_args: 서버 실행 인자 (stdio용)
        tool_names: 사용할 도구 이름 목록 (None이면 전체)
        connect_timeout: 연결 타임아웃 (초)

    Yields:
        MCPServerAdapter: MCP 서버 어댑터
    """
    try:
        if transport_type == "stdio":
            # Stdio 전송: 로컬 프로세스
            if not server_command:
                raise ValueError("stdio 전송에는 server_command가 필요합니다")

            server_params = StdioServerParameters(
                command=server_command,
                args=server_args or [],
                env={**os.environ},
            )
            logger.info(f"MCP Stdio 서버 연결: {server_command}")

        elif transport_type == "sse":
            # SSE 전송: Server-Sent Events
            if not server_url:
                raise ValueError("sse 전송에는 server_url이 필요합니다")

            server_params = {
                "url": server_url,
                "transport": "sse",
            }
            logger.info(f"MCP SSE 서버 연결: {server_url}")

        elif transport_type == "http":
            # Streamable HTTP 전송
            if not server_url:
                raise ValueError("http 전송에는 server_url이 필요합니다")

            server_params = {
                "url": server_url,
                "transport": "streamable-http",
            }
            logger.info(f"MCP HTTP 서버 연결: {server_url}")

        else:
            raise ValueError(f"지원하지 않는 전송 타입: {transport_type}")

        # MCPServerAdapter 생성
        if tool_names:
            adapter = MCPServerAdapter(
                server_params,
                *tool_names,
                connect_timeout=connect_timeout,
            )
        else:
            adapter = MCPServerAdapter(
                server_params,
                connect_timeout=connect_timeout,
            )

        # 컨텍스트 매니저로 어댑터 반환
        with adapter as mcp_tools:
            logger.info(f"MCP 도구 로드 성공: {len(mcp_tools)}개")
            yield mcp_tools

    except Exception as e:
        logger.error(f"MCP 서버 연결 실패: {e}")
        yield []


def get_mcp_tools_from_settings() -> List[Any]:
    """
    설정 파일에서 MCP 도구를 로드합니다.

    Returns:
        List: MCP 도구 리스트 (MCPServerAdapter에서 제공)
    """
    settings = get_settings()

    if not settings.mcp.mcp_enabled:
        logger.debug("MCP가 비활성화되어 있습니다")
        return []

    try:
        # 설정에서 전송 타입 결정
        transport_type = settings.mcp.mcp_transport_type

        if transport_type == "stdio":
            # Stdio 전송
            with get_mcp_adapter(
                transport_type="stdio",
                server_command=settings.mcp.mcp_server_command,
                server_args=settings.mcp.mcp_server_args_list,
                tool_names=settings.mcp.mcp_tools_list or None,
                connect_timeout=settings.mcp.mcp_connect_timeout,
            ) as mcp_tools:
                return list(mcp_tools)

        else:
            # HTTP/SSE 전송
            with get_mcp_adapter(
                transport_type=transport_type,
                server_url=settings.mcp.mcp_server_url,
                tool_names=settings.mcp.mcp_tools_list or None,
                connect_timeout=settings.mcp.mcp_connect_timeout,
            ) as mcp_tools:
                return list(mcp_tools)

    except Exception as e:
        logger.error(f"MCP 도구 로드 실패: {e}")
        return []
