"""
LLM-Based Code Generator

Uses LLM to generate actual business logic code for agents, tasks, and tools.
"""

from typing import Dict, List, Optional

from caas_framework.models.specifications import (
    AgentSpecModel,
    ConcretizedRequirement,
    TaskSpecModel,
)
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils.logger import get_logger


class LLMCodeGenerator:
    """
    LLM-powered code generator that creates actual business logic code.

    This generator uses LLM to create:
    - Custom tool implementations
    - Task execution logic
    - Domain-specific business logic
    - API endpoints (for CRUD strategies)
    """

    def __init__(self, llm_plugin: LLMPlugin):
        """
        Initialize LLM code generator.

        Args:
            llm_plugin: LLM plugin for code generation
        """
        self.llm = llm_plugin
        self.logger = get_logger(__name__)

    async def generate_custom_tools(
        self,
        agents: List[AgentSpecModel],
        golden_data: Optional[ConcretizedRequirement] = None,
    ) -> str:
        """
        Generate custom tool implementations for agents with fallback.

        Args:
            agents: Agent specifications
            golden_data: Golden Data for context

        Returns:
            Python code for custom tools
        """
        # 1. Extract all unique tools from agents
        all_tools = set()
        for agent in agents:
            if agent.tools:
                all_tools.update(agent.tools)

        # 2. Check if empty
        if not all_tools:
            self.logger.warning(
                "⚠️  No tools found in agents, generating empty tools file"
            )
            return self._generate_empty_tools()

        self.logger.info(
            f"🔨 Generating {len(all_tools)} custom tools: {', '.join(all_tools)}"
        )

        # 3. Try LLM generation
        try:
            # Sanitize tool names
            sanitized_tools = {self._sanitize_tool_name(t): t for t in all_tools}

            # Build context and prompt
            context = self._build_tool_generation_context(
                agents, all_tools, golden_data
            )
            prompt = self._build_prompt(sanitized_tools, context)

            # Call LLM
            self.logger.info("🤖 Calling LLM for tool generation...")
            from caas_framework.plugins.llm.base import LLMMessage

            response = await self.llm.ainvoke(
                messages=[LLMMessage(role="user", content=prompt)],
                temperature=0.3,  # Lower temperature for code generation
                max_tokens=4000,
            )

            # Extract and validate code
            code = self._extract_code_from_response(response.content)

            if not code or len(code.strip()) < 50:
                self.logger.warning(
                    "⚠️  LLM returned empty/invalid code, using fallback"
                )
                return self._generate_fallback_tools(sanitized_tools)

            # Validate it's valid Python with BaseTool
            if "BaseTool" not in code:
                self.logger.warning(
                    "⚠️  Generated code missing BaseTool, using fallback"
                )
                return self._generate_fallback_tools(sanitized_tools)

            self.logger.info(f"✅ Successfully generated {len(all_tools)} tools")
            return code

        except Exception as e:
            self.logger.error(f"❌ LLM generation failed: {e}")
            self.logger.warning("Using fallback tool generation")
            return self._generate_fallback_tools(sanitized_tools)

    async def generate_task_logic(
        self,
        task: TaskSpecModel,
        agent: AgentSpecModel,
        golden_data: Optional[ConcretizedRequirement] = None,
    ) -> Dict[str, str]:
        """
        Generate business logic code for a specific task.

        Args:
            task: Task specification
            agent: Associated agent
            golden_data: Golden Data for context

        Returns:
            Dict with additional code snippets for the task
        """
        context = self._build_task_logic_context(task, agent, golden_data)

        prompt = f"""Generate Python business logic for the following CrewAI task.

**Context:**
{context}

**Task Details:**
- ID: {task.id}
- Description: {task.description}
- Expected Output: {task.expected_output}
- Agent: {agent.role}

**Requirements:**
1. Generate a helper function that implements the core logic for this task
2. The function should be called by the task's agent
3. Include proper error handling and validation
4. Add docstrings
5. Return appropriate data structures

Generate ONLY the Python code for the helper function, no explanations.

Example:
```python
def process_user_data(data: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"Process user data and return results.

    Args:
        data: Input data dictionary

    Returns:
        Processed data dictionary
    \"\"\"
    # Implementation here
    return result
```

Now generate the logic:
"""

        from caas_framework.plugins.llm.base import LLMMessage

        response = await self.llm.ainvoke(
            messages=[LLMMessage(role="user", content=prompt)],
            temperature=0.3,
            max_tokens=2000,
        )

        code = self._extract_code_from_response(response.content)

        return {"task_logic": code, "task_id": task.id}

    async def generate_crud_api(
        self,
        golden_data: ConcretizedRequirement,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
    ) -> Dict[str, str]:
        """
        Generate CRUD API endpoints for CRUD-based strategies.

        Args:
            golden_data: Golden Data with data models
            agents: Agent specifications
            tasks: Task specifications

        Returns:
            Dict of API files (api.py, models.py, database.py, etc.)
        """
        files = {}

        # Generate database models
        files["src/models.py"] = await self._generate_database_models(golden_data)

        # Generate database setup
        files["src/database.py"] = self._generate_database_setup()

        # Generate API endpoints
        files["src/api.py"] = await self._generate_api_endpoints(golden_data)

        return files

    async def _generate_database_models(
        self, golden_data: ConcretizedRequirement
    ) -> str:
        """Generate SQLAlchemy database models from Golden Data."""
        if not golden_data.data_models:
            return self._generate_empty_models()

        # Build context from data models
        models_context = []
        for dm in golden_data.data_models[:10]:  # Limit to 10 models
            attrs = [
                f"  - {attr.name}: {attr.type} ({'required' if attr.required else 'optional'})"
                for attr in dm.attributes[:20]  # Limit attributes
            ]
            models_context.append(
                f"Entity: {dm.entity_name}\n"
                f"Description: {dm.description}\n"
                f"Attributes:\n" + "\n".join(attrs)
            )

        context = "\n\n".join(models_context)

        prompt = f"""Generate SQLAlchemy database models for the following entities.

**Entities:**
{context}

**Requirements:**
1. Use SQLAlchemy ORM with declarative_base
2. Include proper column types, constraints, and relationships
3. Add __repr__ methods
4. Include created_at and updated_at timestamps
5. Add proper indexes

Generate ONLY the Python code, no explanations.

Example:
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={{self.id}}, name={{self.name}})>"
```

Now generate the models:
"""

        from caas_framework.plugins.llm.base import LLMMessage

        response = await self.llm.ainvoke(
            messages=[LLMMessage(role="user", content=prompt)],
            temperature=0.2,
            max_tokens=4000,
        )

        return self._extract_code_from_response(response.content)

    async def _generate_api_endpoints(self, golden_data: ConcretizedRequirement) -> str:
        """Generate FastAPI endpoints from Golden Data."""
        if not golden_data.features:
            return self._generate_empty_api()

        # Build context from features
        features_context = []
        for feature in golden_data.features[:10]:  # Limit to 10 features
            features_context.append(
                f"Feature: {feature.name}\n"
                f"Description: {feature.description}\n"
                f"Functional Requirements: {', '.join(feature.functional_requirements[:5])}"
            )

        context = "\n\n".join(features_context)

        prompt = f"""Generate FastAPI REST API endpoints for the following features.

**Features:**
{context}

**Requirements:**
1. Use FastAPI with proper route decorators
2. Include Pydantic models for request/response
3. Add proper status codes and error handling
4. Include dependency injection for database
5. Add API documentation strings
6. Implement CRUD operations where applicable

Generate ONLY the Python code, no explanations.

Example:
```python
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from src.database import get_db
from src.models import User

app = FastAPI()

class UserCreate(BaseModel):
    name: str
    email: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True

@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    \"\"\"Create a new user.\"\"\"
    db_user = User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db)):
    \"\"\"List all users.\"\"\"
    return db.query(User).all()
```

Now generate the API:
"""

        response = await self.llm.generate(
            prompt=prompt, temperature=0.3, max_tokens=4000
        )

        return self._extract_code_from_response(response)

    def _generate_database_setup(self) -> str:
        """Generate database setup code."""
        return '''"""
Database Setup

SQLAlchemy database configuration and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

# Database URL from environment or default to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from src.models import Base
    Base.metadata.create_all(bind=engine)
'''

    def _generate_empty_models(self) -> str:
        """Generate empty models file."""
        return '''"""
Database Models

SQLAlchemy models for the application.
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


# Add your models here
'''

    def _generate_empty_api(self) -> str:
        """Generate empty API file."""
        return '''"""
API Endpoints

FastAPI REST API endpoints.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Generated API",
    description="Auto-generated REST API",
    version="1.0.0"
)


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "API is running"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Add your endpoints here
'''

    def _build_tool_generation_context(
        self,
        agents: List[AgentSpecModel],
        tools: set,
        golden_data: Optional[ConcretizedRequirement],
    ) -> str:
        """Build context for tool generation."""
        context_parts = []

        # Add agent context
        context_parts.append("**Agents requiring these tools:**")
        for agent in agents:
            if agent.tools:
                context_parts.append(f"- {agent.role}: {agent.goal}")

        # Add domain context
        if golden_data:
            context_parts.append(f"\n**Domain:** {golden_data.domain or 'General'}")
            context_parts.append(
                f"**Project:** {golden_data.project_name or 'Unnamed'}"
            )
            context_parts.append(f"**Description:** {golden_data.description}")

        return "\n".join(context_parts)

    def _build_task_logic_context(
        self,
        task: TaskSpecModel,
        agent: AgentSpecModel,
        golden_data: Optional[ConcretizedRequirement],
    ) -> str:
        """Build context for task logic generation."""
        context_parts = []

        context_parts.append(f"**Agent:** {agent.role}")
        context_parts.append(f"**Agent Goal:** {agent.goal}")
        context_parts.append(f"**Agent Backstory:** {agent.backstory}")

        if golden_data:
            context_parts.append(f"\n**Domain:** {golden_data.domain or 'General'}")
            context_parts.append(
                f"**Project:** {golden_data.project_name or 'Unnamed'}"
            )

        return "\n".join(context_parts)

    def _extract_code_from_response(self, response: str) -> str:
        """Extract code from LLM response."""
        # Remove markdown code blocks if present
        if "```python" in response:
            # Extract content between ```python and ```
            start = response.find("```python") + len("```python")
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        elif "```" in response:
            # Extract content between ``` and ```
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()

        # Return as-is if no code blocks
        return response.strip()

    def _sanitize_tool_name(self, tool_name: str) -> str:
        """
        Convert abstract tool names to valid Python class names.

        Args:
            tool_name: Original tool name (may contain Korean, special chars)

        Returns:
            Valid Python class name
        """
        # Korean translation map
        translation_map = {
            "키보드": "KeyboardTool",
            "마우스": "MouseTool",
            "웹 크롤러": "WebScraperTool",
            "데이터 분석 도구": "DataAnalysisTool",
            "인터넷 검색": "InternetSearchTool",
            "보고서 생성": "ReportGeneratorTool",
        }

        # Check translation map first
        if tool_name in translation_map:
            return translation_map[tool_name]

        # Fallback: Remove special chars, convert to CamelCase
        import re

        clean_name = re.sub(r"[^a-zA-Z0-9가-힣\s]", "", tool_name)
        clean_name = clean_name.strip()

        # If still contains Korean, use hash
        if re.search(r"[가-힣]", clean_name):
            import hashlib

            hash_suffix = hashlib.md5(tool_name.encode()).hexdigest()[:8]
            return f"CustomTool_{hash_suffix}"

        # Convert to CamelCase
        words = clean_name.split()
        class_name = "".join(word.capitalize() for word in words)

        # Ensure it ends with 'Tool'
        if not class_name.endswith("Tool"):
            class_name += "Tool"

        return class_name

    def _build_prompt(self, sanitized_tools: dict, context: str) -> str:
        """Build improved prompt with clear tool name mapping."""
        tool_list = []
        for class_name, original_name in sanitized_tools.items():
            tool_list.append(f"- {class_name} (for '{original_name}')")

        tools_str = "\n".join(tool_list)

        return f"""Generate Python code for the following custom tools for a CrewAI project.

**Context:**
{context}

**Tools to implement:**
{tools_str}

**Requirements:**
1. Each tool MUST inherit from crewai.tools.BaseTool
2. Implement the _run() method with actual business logic
3. Add proper error handling and validation
4. Include docstrings
5. Make tools reusable and production-ready
6. DO NOT override __init__() - tools are instantiated without arguments
7. Use Pydantic fields with default values for configuration

**SECURITY REQUIREMENTS:**
1. Use parameterized queries for SQL (NEVER string formatting)
2. Never use eval(), exec(), or compile() on user input
3. Validate and sanitize all inputs
4. Use prepared statements for database operations

Generate ONLY valid Python code with all necessary imports. No explanations.

Example:
```python
from crewai.tools import BaseTool
from typing import Any

class MyTool(BaseTool):
    name: str = "my_tool"
    description: str = "Tool description"

    def _run(self, input_param: str) -> Any:
        \"\"\"Execute the tool.\"\"\"
        # Implementation here
        return result
```

Now generate the tools:
"""

    def _generate_empty_tools(self) -> str:
        """Generate empty tools.py file when no tools are needed."""
        return '''"""
Custom Tools

CrewAI custom tool implementations.
"""

from crewai.tools import BaseTool
from typing import Any


# No tools were defined in the agent specifications.
# Add your custom tools here as needed.
'''

    def _generate_fallback_tools(self, sanitized_tools: dict) -> str:
        """
        Generate fallback tools when LLM fails.

        This is now a thin wrapper around the centralized tool generation utility.

        Call Path (Legacy Mode):
            BMADEngine.run() [use_expert_agents=False]
              → BMADEngine._phase_5_delivery()
              → CodeGenerationEngine.generate()
              → LLMCodeGenerator.generate_custom_tools()
              → (on LLM failure) LLMCodeGenerator._generate_fallback_tools() ← YOU ARE HERE
              → tool_utils.generate_fallback_tools_code()

        Args:
            sanitized_tools: Dict of {class_name: original_name}

        Returns:
            Python code for tools.py with stub implementations

        Configuration:
            - Fallback warning: Enabled (shows "LLM generation failed" message)
            - Helper functions: Disabled (no get_all_tools() or instances)
            - Return type: dict (tools return dicts from _run method)

        See Also:
            caas_framework.codegen.tool_utils.generate_fallback_tools_code
            CodeGeneratorAgent._generate_tools_file_fallback (alternative Expert Agent path)
        """
        from caas_framework.codegen.tool_utils import generate_fallback_tools_code

        return generate_fallback_tools_code(
            tools=sanitized_tools,
            include_header=True,
            fallback_warning=True,  # Add "LLM generation failed" warning
            include_helper_functions=False,  # LLM path doesn't include helpers
            return_type="dict",  # Return dict from _run method
        )
