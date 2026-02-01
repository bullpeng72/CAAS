"""
Tool Ontology Data Generator

Generates initial tool ontology data from the tool_generator mappings.
"""

from typing import List
from caas_framework.knowledge.ontology.tool_ontology import (
    ToolOntology,
    ConceptualTool,
    ToolImplementation,
    ToolCategory,
    ToolType
)


def generate_initial_ontology() -> ToolOntology:
    """Generate initial tool ontology with all available tools"""

    tools: List[ConceptualTool] = []

    # File Operations
    tools.append(ConceptualTool(
        id="tool_file_read",
        name="file_read",
        display_name="File Read",
        category=ToolCategory.FILE,
        description="Read contents from files on disk",
        use_cases=["Read configuration files", "Load data files", "Process text files"],
        implementations=[
            ToolImplementation(
                crewai_class="FileReadTool",
                name="CrewAI File Read Tool",
                description="Built-in file reading tool",
                requires_api_key=False
            )
        ],
        default_implementation="FileReadTool",
        compatible_roles=["Data Analyst", "Developer", "Researcher"],
        compatible_tasks=["data_analysis", "research", "file_processing"],
        tags=["file", "read", "io"]
    ))

    tools.append(ConceptualTool(
        id="tool_file_write",
        name="file_write",
        display_name="File Write",
        category=ToolCategory.FILE,
        description="Write content to files on disk",
        use_cases=["Save results", "Generate reports", "Export data"],
        implementations=[
            ToolImplementation(
                crewai_class="FileWriterTool",
                name="CrewAI File Writer Tool",
                description="Built-in file writing tool",
                requires_api_key=False
            )
        ],
        default_implementation="FileWriterTool",
        compatible_roles=["Data Analyst", "Writer", "Developer"],
        compatible_tasks=["reporting", "data_export", "documentation"],
        tags=["file", "write", "io", "save"]
    ))

    tools.append(ConceptualTool(
        id="tool_directory_read",
        name="directory_read",
        display_name="Directory Read",
        category=ToolCategory.FILE,
        description="List files and directories in a path",
        use_cases=["Explore file structure", "Find files", "List directories"],
        implementations=[
            ToolImplementation(
                crewai_class="DirectoryReadTool",
                name="CrewAI Directory Read Tool",
                description="List directory contents",
                requires_api_key=False
            )
        ],
        default_implementation="DirectoryReadTool",
        compatible_roles=["Developer", "Data Engineer"],
        compatible_tasks=["file_management", "exploration"],
        tags=["directory", "folder", "list"]
    ))

    tools.append(ConceptualTool(
        id="tool_directory_search",
        name="directory_search",
        display_name="Directory Search",
        category=ToolCategory.FILE,
        description="Search for files in directories",
        use_cases=["Find specific files", "Search by pattern", "Locate resources"],
        implementations=[
            ToolImplementation(
                crewai_class="DirectorySearchTool",
                name="CrewAI Directory Search Tool",
                description="Search for files in directories",
                requires_api_key=False
            )
        ],
        default_implementation="DirectorySearchTool",
        compatible_roles=["Developer", "Researcher"],
        compatible_tasks=["search", "file_finding"],
        tags=["directory", "search", "find"]
    ))

    # Web Search
    tools.append(ConceptualTool(
        id="tool_web_search",
        name="web_search",
        display_name="Web Search",
        category=ToolCategory.SEARCH,
        description="Search the web for information",
        use_cases=["Research topics", "Find latest information", "Gather data"],
        implementations=[
            ToolImplementation(
                crewai_class="SerperDevTool",
                name="Google Search (Serper)",
                description="Google search using Serper API",
                requires_api_key=True,
                api_key_env="SERPER_API_KEY",
                pros=["Most comprehensive results", "Google's search index"],
                cons=["Requires API key", "Costs money per query"]
            ),
            ToolImplementation(
                crewai_class="BraveSearchTool",
                name="Brave Search",
                description="Privacy-focused search using Brave Search API",
                requires_api_key=True,
                api_key_env="BRAVE_API_KEY",
                pros=["Privacy-focused", "No user tracking"],
                cons=["Smaller index than Google"]
            ),
            ToolImplementation(
                crewai_class="TavilySearchTool",
                name="Tavily AI Search",
                description="AI-optimized search using Tavily",
                requires_api_key=True,
                api_key_env="TAVILY_API_KEY",
                pros=["AI-optimized results", "Great for research"],
                cons=["Requires API key"]
            )
        ],
        default_implementation="SerperDevTool",
        compatible_roles=["Researcher", "Data Collector", "Analyst"],
        compatible_tasks=["research", "data_collection", "fact_checking"],
        tags=["search", "web", "google", "research"]
    ))

    # Web Scraping
    tools.append(ConceptualTool(
        id="tool_scrape_website",
        name="scrape_website",
        display_name="Website Scraper",
        category=ToolCategory.WEB_SCRAPING,
        description="Extract content from websites",
        use_cases=["Extract webpage content", "Scrape data", "Parse HTML"],
        implementations=[
            ToolImplementation(
                crewai_class="ScrapeWebsiteTool",
                name="Basic Website Scraper",
                description="Simple HTTP-based scraping",
                requires_api_key=False
            ),
            ToolImplementation(
                crewai_class="SeleniumScrapingTool",
                name="Selenium Scraper",
                description="Browser-based scraping with JavaScript support",
                requires_api_key=False,
                pros=["Handles JavaScript", "Can interact with pages"],
                cons=["Slower", "Requires browser"]
            ),
            ToolImplementation(
                crewai_class="FirecrawlScrapeWebsiteTool",
                name="Firecrawl Scraper",
                description="Advanced scraping with Firecrawl",
                requires_api_key=True,
                api_key_env="FIRECRAWL_API_KEY",
                pros=["Advanced features", "Clean data"],
                cons=["Requires API key"]
            )
        ],
        default_implementation="ScrapeWebsiteTool",
        compatible_roles=["Data Collector", "Researcher", "Web Scraper"],
        compatible_tasks=["data_collection", "web_scraping", "content_extraction"],
        tags=["scrape", "web", "extract", "crawl"]
    ))

    # Code Interpreter
    tools.append(ConceptualTool(
        id="tool_code_interpreter",
        name="code_interpreter",
        display_name="Code Interpreter",
        category=ToolCategory.CODE,
        description="Execute Python code in a sandbox",
        use_cases=["Run calculations", "Process data", "Generate code results"],
        implementations=[
            ToolImplementation(
                crewai_class="CodeInterpreterTool",
                name="CrewAI Code Interpreter",
                description="Execute Python code safely",
                requires_api_key=False
            )
        ],
        default_implementation="CodeInterpreterTool",
        compatible_roles=["Developer", "Data Analyst", "Researcher"],
        compatible_tasks=["coding", "data_processing", "calculation"],
        tags=["code", "python", "execute", "programming"]
    ))

    # Calculator (custom tool - no CrewAI implementation)
    tools.append(ConceptualTool(
        id="tool_calculator",
        name="calculator",
        display_name="Calculator",
        category=ToolCategory.CODE,
        type=ToolType.CUSTOM,
        description="Evaluate mathematical expressions safely",
        use_cases=["Mathematical calculations", "Formula evaluation", "Number processing"],
        implementations=[],  # Custom tool, no pre-built implementation
        default_implementation=None,
        compatible_roles=["Data Analyst", "Researcher", "Accountant"],
        compatible_tasks=["numerical_calculation", "mathematical_computation", "formula_evaluation"],
        tags=["calculator", "math", "calculation"]
    ))

    # Document Search Tools
    for doc_type, crewai_class in [
        ("pdf", "PDFSearchTool"),
        ("csv", "CSVSearchTool"),
        ("json", "JSONSearchTool"),
        ("docx", "DOCXSearchTool"),
        ("txt", "TXTSearchTool"),
        ("xml", "XMLSearchTool")
    ]:
        tools.append(ConceptualTool(
            id=f"tool_{doc_type}_search",
            name=f"{doc_type}_search",
            display_name=f"{doc_type.upper()} Search",
            category=ToolCategory.DOCUMENT,
            description=f"Search and query {doc_type.upper()} files",
            use_cases=[f"Search {doc_type} documents", f"Extract data from {doc_type}"],
            implementations=[
                ToolImplementation(
                    crewai_class=crewai_class,
                    name=f"CrewAI {doc_type.upper()} Search",
                    description=f"Search tool for {doc_type} files",
                    requires_api_key=False
                )
            ],
            default_implementation=crewai_class,
            compatible_roles=["Researcher", "Data Analyst"],
            compatible_tasks=["document_search", "data_extraction"],
            tags=["document", doc_type, "search"]
        ))

    # Database Tools
    tools.append(ConceptualTool(
        id="tool_mysql_search",
        name="mysql_search",
        display_name="MySQL Search",
        category=ToolCategory.DATABASE,
        description="Query MySQL databases",
        use_cases=["Database queries", "Data retrieval", "SQL operations"],
        implementations=[
            ToolImplementation(
                crewai_class="MySQLSearchTool",
                name="MySQL Query Tool",
                description="Execute SQL queries on MySQL",
                requires_api_key=False
            )
        ],
        default_implementation="MySQLSearchTool",
        compatible_roles=["Data Analyst", "Data Engineer", "Database Admin"],
        compatible_tasks=["database_query", "data_retrieval"],
        tags=["database", "mysql", "sql", "query"]
    ))

    tools.append(ConceptualTool(
        id="tool_mongodb_search",
        name="mongodb_search",
        display_name="MongoDB Search",
        category=ToolCategory.DATABASE,
        description="Vector search in MongoDB",
        use_cases=["Vector similarity search", "MongoDB queries", "Document retrieval"],
        implementations=[
            ToolImplementation(
                crewai_class="MongoDBVectorSearchTool",
                name="MongoDB Vector Search",
                description="Vector search in MongoDB",
                requires_api_key=False
            )
        ],
        default_implementation="MongoDBVectorSearchTool",
        compatible_roles=["Data Engineer", "ML Engineer"],
        compatible_tasks=["vector_search", "database_query"],
        tags=["database", "mongodb", "vector", "nosql"]
    ))

    # Vision Tools
    tools.append(ConceptualTool(
        id="tool_vision",
        name="vision",
        display_name="Vision AI",
        category=ToolCategory.VISION,
        description="Image analysis and understanding",
        use_cases=["Analyze images", "Detect objects", "Understand visual content"],
        implementations=[
            ToolImplementation(
                crewai_class="VisionTool",
                name="CrewAI Vision Tool",
                description="AI-powered image analysis",
                requires_api_key=True,
                api_key_env="OPENAI_API_KEY"
            )
        ],
        default_implementation="VisionTool",
        compatible_roles=["Image Analyst", "ML Engineer"],
        compatible_tasks=["image_analysis", "vision"],
        tags=["vision", "image", "ai", "visual"]
    ))

    # YouTube
    tools.append(ConceptualTool(
        id="tool_youtube_search",
        name="youtube_search",
        display_name="YouTube Search",
        category=ToolCategory.YOUTUBE,
        description="Search YouTube videos",
        use_cases=["Find videos", "Research content", "Collect video data"],
        implementations=[
            ToolImplementation(
                crewai_class="YoutubeVideoSearchTool",
                name="YouTube Video Search",
                description="Search for YouTube videos",
                requires_api_key=False
            )
        ],
        default_implementation="YoutubeVideoSearchTool",
        compatible_roles=["Researcher", "Content Analyst"],
        compatible_tasks=["video_search", "content_research"],
        tags=["youtube", "video", "search"]
    ))

    # RAG Tool
    tools.append(ConceptualTool(
        id="tool_rag",
        name="rag_tool",
        display_name="RAG (Retrieval Augmented Generation)",
        category=ToolCategory.OTHER,
        description="Retrieval Augmented Generation for knowledge-based responses",
        use_cases=["Knowledge base queries", "Document QA", "Context-aware responses"],
        implementations=[
            ToolImplementation(
                crewai_class="RagTool",
                name="RAG Tool",
                description="Combine retrieval and generation",
                requires_api_key=False
            )
        ],
        default_implementation="RagTool",
        compatible_roles=["Researcher", "Knowledge Manager"],
        compatible_tasks=["qa", "knowledge_retrieval"],
        tags=["rag", "retrieval", "knowledge", "ai"]
    ))

    return ToolOntology(version="1.0.0", tools=tools)
