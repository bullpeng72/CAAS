"""
Tool API Key Requirements

Defines API key requirements for CrewAI and MCP tools.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class ToolAPIKeyRequirement(BaseModel):
    """API Key requirement for a tool"""
    env_var: str  # Environment variable name
    description: str  # Description of the API key
    optional: bool = False  # Whether the tool can work without this key
    signup_url: Optional[str] = None  # URL to sign up for the API
    param_name: Optional[str] = None  # Parameter name for tool initialization (if needed)


# API Key requirements for CrewAI tools
TOOL_API_KEY_REQUIREMENTS: Dict[str, ToolAPIKeyRequirement] = {
    # Search Tools
    "SerperDevTool": ToolAPIKeyRequirement(
        env_var="SERPER_API_KEY",
        description="Google Search API via Serper.dev",
        optional=False,
        signup_url="https://serper.dev/signup",
    ),
    "BraveSearchTool": ToolAPIKeyRequirement(
        env_var="BRAVE_API_KEY",
        description="Brave Search API Key",
        optional=False,
        signup_url="https://brave.com/search/api/",
    ),
    "TavilySearchTool": ToolAPIKeyRequirement(
        env_var="TAVILY_API_KEY",
        description="Tavily AI Search API Key",
        optional=False,
        signup_url="https://tavily.com/",
    ),
    "EXASearchTool": ToolAPIKeyRequirement(
        env_var="EXA_API_KEY",
        description="EXA Neural Search API Key",
        optional=False,
        signup_url="https://exa.ai/",
    ),

    # Code Tools
    "GithubSearchTool": ToolAPIKeyRequirement(
        env_var="GITHUB_TOKEN",
        description="GitHub Personal Access Token",
        optional=True,
        signup_url="https://github.com/settings/tokens",
        param_name="gh_token",
    ),

    # Web Scraping Tools
    "FirecrawlScrapeWebsiteTool": ToolAPIKeyRequirement(
        env_var="FIRECRAWL_API_KEY",
        description="Firecrawl API Key for advanced web scraping",
        optional=False,
        signup_url="https://www.firecrawl.dev/",
    ),
    "JinaScrapeWebsiteTool": ToolAPIKeyRequirement(
        env_var="JINA_API_KEY",
        description="Jina AI API Key for web scraping",
        optional=False,
        signup_url="https://jina.ai/",
    ),
    "SpiderTool": ToolAPIKeyRequirement(
        env_var="SPIDER_API_KEY",
        description="Spider Web Crawler API Key",
        optional=False,
        signup_url="https://spider.cloud/",
    ),

    # Communication Tools
    "TwilioTool": ToolAPIKeyRequirement(
        env_var="TWILIO_ACCOUNT_SID",
        description="Twilio Account SID (also needs TWILIO_AUTH_TOKEN)",
        optional=False,
        signup_url="https://www.twilio.com/try-twilio",
    ),

    # Analytics Tools
    "GoogleAnalyticsSearchTool": ToolAPIKeyRequirement(
        env_var="GOOGLE_ANALYTICS_CREDENTIALS",
        description="Google Analytics Service Account JSON credentials path",
        optional=False,
        signup_url="https://analytics.google.com/",
    ),
    "MixpanelSearchTool": ToolAPIKeyRequirement(
        env_var="MIXPANEL_API_SECRET",
        description="Mixpanel API Secret",
        optional=False,
        signup_url="https://mixpanel.com/",
    ),

    # Productivity Tools
    "GoogleCalendarSearchTool": ToolAPIKeyRequirement(
        env_var="GOOGLE_CALENDAR_CREDENTIALS",
        description="Google Calendar API credentials (OAuth JSON)",
        optional=False,
        signup_url="https://console.cloud.google.com/",
    ),
    "GoogleDocsSearchTool": ToolAPIKeyRequirement(
        env_var="GOOGLE_DOCS_CREDENTIALS",
        description="Google Docs API credentials (OAuth JSON)",
        optional=False,
        signup_url="https://console.cloud.google.com/",
    ),
    "GoogleSheetsSearchTool": ToolAPIKeyRequirement(
        env_var="GOOGLE_SHEETS_CREDENTIALS",
        description="Google Sheets API credentials (OAuth JSON)",
        optional=False,
        signup_url="https://console.cloud.google.com/",
    ),
    "NotionSearchTool": ToolAPIKeyRequirement(
        env_var="NOTION_API_KEY",
        description="Notion Integration Token",
        optional=False,
        signup_url="https://www.notion.so/my-integrations",
    ),

    # AI Tools
    "HuggingFaceModelTool": ToolAPIKeyRequirement(
        env_var="HUGGINGFACE_API_KEY",
        description="HuggingFace API Token",
        optional=True,
        signup_url="https://huggingface.co/settings/tokens",
    ),
    "OpenAITool": ToolAPIKeyRequirement(
        env_var="OPENAI_API_KEY",
        description="OpenAI API Key",
        optional=False,
        signup_url="https://platform.openai.com/api-keys",
    ),

    # Database Tools
    "MySQLSearchTool": ToolAPIKeyRequirement(
        env_var="MYSQL_CONNECTION_STRING",
        description="MySQL connection string (mysql://user:pass@host:port/db)",
        optional=False,
    ),
    "MongoDBVectorSearchTool": ToolAPIKeyRequirement(
        env_var="MONGODB_URI",
        description="MongoDB connection URI",
        optional=False,
        signup_url="https://www.mongodb.com/cloud/atlas",
    ),
    "SnowflakeSearchTool": ToolAPIKeyRequirement(
        env_var="SNOWFLAKE_ACCOUNT",
        description="Snowflake account identifier (also needs SNOWFLAKE_USER, SNOWFLAKE_PASSWORD)",
        optional=False,
        signup_url="https://www.snowflake.com/",
    ),

    # Other Tools
    "MultiOnTool": ToolAPIKeyRequirement(
        env_var="MULTION_API_KEY",
        description="MultiOn API Key for browser automation",
        optional=False,
        signup_url="https://www.multion.ai/",
    ),
    "ComposioTool": ToolAPIKeyRequirement(
        env_var="COMPOSIO_API_KEY",
        description="Composio API Key",
        optional=False,
        signup_url="https://composio.dev/",
    ),
}

# Additional API keys for specific tools (multiple keys needed)
TOOL_ADDITIONAL_API_KEYS: Dict[str, List[ToolAPIKeyRequirement]] = {
    "TwilioTool": [
        ToolAPIKeyRequirement(
            env_var="TWILIO_AUTH_TOKEN",
            description="Twilio Auth Token",
            optional=False,
        ),
        ToolAPIKeyRequirement(
            env_var="TWILIO_PHONE_NUMBER",
            description="Twilio Phone Number",
            optional=False,
        ),
    ],
    "SnowflakeSearchTool": [
        ToolAPIKeyRequirement(
            env_var="SNOWFLAKE_USER",
            description="Snowflake username",
            optional=False,
        ),
        ToolAPIKeyRequirement(
            env_var="SNOWFLAKE_PASSWORD",
            description="Snowflake password",
            optional=False,
        ),
        ToolAPIKeyRequirement(
            env_var="SNOWFLAKE_WAREHOUSE",
            description="Snowflake warehouse name",
            optional=True,
        ),
    ],
}

# MCP Server API Key requirements
MCP_API_KEY_REQUIREMENTS: Dict[str, ToolAPIKeyRequirement] = {
    "github": ToolAPIKeyRequirement(
        env_var="GITHUB_PERSONAL_ACCESS_TOKEN",
        description="GitHub Personal Access Token for MCP server",
        optional=False,
        signup_url="https://github.com/settings/tokens",
    ),
    "gdrive": ToolAPIKeyRequirement(
        env_var="GOOGLE_DRIVE_CREDENTIALS",
        description="Google Drive API credentials JSON",
        optional=False,
        signup_url="https://console.cloud.google.com/",
    ),
    "slack": ToolAPIKeyRequirement(
        env_var="SLACK_BOT_TOKEN",
        description="Slack Bot Token for MCP server",
        optional=False,
        signup_url="https://api.slack.com/",
    ),
}


def get_tool_api_key_requirements(tool_name: str) -> List[ToolAPIKeyRequirement]:
    """
    Get all API key requirements for a tool

    Args:
        tool_name: Name of the tool

    Returns:
        List of API key requirements
    """
    requirements = []

    # Primary API key
    if tool_name in TOOL_API_KEY_REQUIREMENTS:
        requirements.append(TOOL_API_KEY_REQUIREMENTS[tool_name])

    # Additional API keys
    if tool_name in TOOL_ADDITIONAL_API_KEYS:
        requirements.extend(TOOL_ADDITIONAL_API_KEYS[tool_name])

    return requirements


def get_all_required_env_vars(tool_names: List[str]) -> Dict[str, ToolAPIKeyRequirement]:
    """
    Get all required environment variables for a list of tools

    Args:
        tool_names: List of tool names

    Returns:
        Dictionary mapping env var names to their requirements
    """
    all_requirements = {}

    for tool_name in tool_names:
        requirements = get_tool_api_key_requirements(tool_name)
        for req in requirements:
            # Avoid duplicates
            if req.env_var not in all_requirements:
                all_requirements[req.env_var] = req

    return all_requirements


def is_tool_requires_api_key(tool_name: str) -> bool:
    """
    Check if a tool requires an API key

    Args:
        tool_name: Name of the tool

    Returns:
        bool: True if the tool requires an API key
    """
    return tool_name in TOOL_API_KEY_REQUIREMENTS or tool_name in TOOL_ADDITIONAL_API_KEYS
