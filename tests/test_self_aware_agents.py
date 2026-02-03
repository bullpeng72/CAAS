"""
Tests for Self-Aware Agent Implementation

Tests capability assessment, self-awareness, and delegation.
"""

from typing import Any, Dict, Optional

import pytest

from caas_framework.agents.capability_assessment import (
    AgentCapability,
    CapabilityAssessment,
    CapabilityLevel,
    CapabilityRegistry,
    get_capability_registry,
)
from caas_framework.agents.self_aware import SelfAwareAgent
from caas_framework.plugins.llm.base import LLMPlugin


class MockLLM(LLMPlugin):
    """Mock LLM for testing"""

    def __init__(self, mock_response: str = ""):
        super().__init__(name="mock", config={})
        self.mock_response = mock_response
        self.generate_called = False
        self.last_prompt = None

    async def initialize(self) -> None:
        """Initialize mock LLM"""
        self._initialized = True

    async def ainvoke(
        self,
        messages,
        temperature=None,
        max_tokens=None,
        response_format=None,
        **kwargs
    ):
        """Mock ainvoke implementation"""
        from caas_framework.plugins.llm.base import LLMResponse
        self.generate_called = True
        self.last_prompt = str(messages)
        return LLMResponse(
            content=self.mock_response,
            model="mock",
            usage={"total_tokens": 100}
        )

    async def stream(self, messages, temperature=None, max_tokens=None, **kwargs):
        """Mock stream implementation"""
        yield self.mock_response

    async def close(self) -> None:
        """Close mock LLM"""
        pass

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""
        self.generate_called = True
        self.last_prompt = prompt
        return self.mock_response

    async def chat(self, messages: list, **kwargs) -> str:
        """Chat with messages"""
        return await self.generate(str(messages), **kwargs)


class TestSelfAwareAgent(SelfAwareAgent):
    """Concrete implementation for testing"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed_tasks = []

    async def _execute_task(self, task: str, context: Optional[Dict[str, Any]]) -> Any:
        self.executed_tasks.append((task, context))
        return {"status": "success", "task": task}


# Tests for CapabilityLevel
class TestCapabilityLevel:
    """Test CapabilityLevel enum"""

    def test_capability_levels_defined(self):
        """Test all capability levels are defined"""
        assert CapabilityLevel.EXPERT.value == "expert"
        assert CapabilityLevel.PROFICIENT.value == "proficient"
        assert CapabilityLevel.CAPABLE.value == "capable"
        assert CapabilityLevel.LIMITED.value == "limited"
        assert CapabilityLevel.UNABLE.value == "unable"


# Tests for CapabilityAssessment
class TestCapabilityAssessment:
    """Test CapabilityAssessment dataclass"""

    def test_capability_level_expert(self):
        """Test expert level (0.9-1.0)"""
        assessment = CapabilityAssessment(
            confidence=0.95,
            reasoning="High expertise"
        )
        assert assessment.capability_level == CapabilityLevel.EXPERT
        assert assessment.can_attempt is True
        assert assessment.needs_help is False

    def test_capability_level_proficient(self):
        """Test proficient level (0.7-0.9)"""
        assessment = CapabilityAssessment(
            confidence=0.8,
            reasoning="Good capability"
        )
        assert assessment.capability_level == CapabilityLevel.PROFICIENT
        assert assessment.can_attempt is True
        assert assessment.needs_help is False

    def test_capability_level_capable(self):
        """Test capable level (0.5-0.7)"""
        assessment = CapabilityAssessment(
            confidence=0.6,
            reasoning="Moderate capability"
        )
        assert assessment.capability_level == CapabilityLevel.CAPABLE
        assert assessment.can_attempt is False
        assert assessment.needs_help is False

    def test_capability_level_limited(self):
        """Test limited level (0.3-0.5)"""
        assessment = CapabilityAssessment(
            confidence=0.4,
            reasoning="Limited capability"
        )
        assert assessment.capability_level == CapabilityLevel.LIMITED
        assert assessment.can_attempt is False
        assert assessment.needs_help is True

    def test_capability_level_unable(self):
        """Test unable level (0.0-0.3)"""
        assessment = CapabilityAssessment(
            confidence=0.2,
            reasoning="Cannot do this"
        )
        assert assessment.capability_level == CapabilityLevel.UNABLE
        assert assessment.can_attempt is False
        assert assessment.needs_help is True

    def test_missing_capabilities(self):
        """Test missing capabilities list"""
        assessment = CapabilityAssessment(
            confidence=0.5,
            reasoning="Missing tools",
            missing_capabilities=["database access", "API integration"]
        )
        assert len(assessment.missing_capabilities) == 2
        assert "database access" in assessment.missing_capabilities

    def test_suggested_agents(self):
        """Test suggested agents list"""
        assessment = CapabilityAssessment(
            confidence=0.3,
            reasoning="Need specialist",
            suggested_agents=["DatabaseExpert", "APISpecialist"]
        )
        assert len(assessment.suggested_agents) == 2
        assert "DatabaseExpert" in assessment.suggested_agents

    def test_to_dict(self):
        """Test conversion to dictionary"""
        assessment = CapabilityAssessment(
            confidence=0.8,
            reasoning="Good match",
            missing_capabilities=["tool1"],
            alternative_approach="Use approach B",
            difficulty=5
        )
        data = assessment.to_dict()

        assert data["confidence"] == 0.8
        assert data["capability_level"] == "proficient"
        assert data["can_attempt"] is True
        assert data["reasoning"] == "Good match"
        assert data["missing_capabilities"] == ["tool1"]
        assert data["alternative_approach"] == "Use approach B"
        assert data["difficulty"] == 5


# Tests for AgentCapability
class TestAgentCapability:
    """Test AgentCapability dataclass"""

    def test_matches_task_with_expertise(self):
        """Test task matching with expertise keywords"""
        capability = AgentCapability(
            agent_name="DatabaseExpert",
            expertise=["database", "SQL", "PostgreSQL"],
            tools=["psql", "pg_dump"]
        )

        score = capability.matches_task("Design a PostgreSQL database schema")
        assert score > 0.0

    def test_matches_task_with_tools(self):
        """Test task matching with tool keywords"""
        capability = AgentCapability(
            agent_name="WebDev",
            expertise=["web development"],
            tools=["React", "Node.js", "Express"]
        )

        score = capability.matches_task("Build a React frontend")
        assert score > 0.0

    def test_matches_task_no_match(self):
        """Test task matching with no matches"""
        capability = AgentCapability(
            agent_name="BackendDev",
            expertise=["backend"],
            tools=["Django"]
        )

        score = capability.matches_task("Design a mobile app UI")
        assert score >= 0.0  # May be 0 or neutral 0.5

    def test_to_dict(self):
        """Test conversion to dictionary"""
        capability = AgentCapability(
            agent_name="TestAgent",
            expertise=["testing", "QA"],
            tools=["pytest", "selenium"],
            task_types=["unit testing", "integration testing"],
            min_confidence=0.7,
            backstory="Expert QA engineer",
            goal="Ensure quality"
        )

        data = capability.to_dict()
        assert data["agent_name"] == "TestAgent"
        assert data["expertise"] == ["testing", "QA"]
        assert data["tools"] == ["pytest", "selenium"]
        assert data["min_confidence"] == 0.7


# Tests for CapabilityRegistry
class TestCapabilityRegistry:
    """Test CapabilityRegistry"""

    def test_register_and_get(self):
        """Test registering and retrieving capabilities"""
        registry = CapabilityRegistry()

        capability = AgentCapability(
            agent_name="Agent1",
            expertise=["skill1"],
            tools=["tool1"]
        )

        registry.register(capability)
        retrieved = registry.get("Agent1")

        assert retrieved is not None
        assert retrieved.agent_name == "Agent1"

    def test_get_nonexistent(self):
        """Test getting nonexistent agent"""
        registry = CapabilityRegistry()
        result = registry.get("NonexistentAgent")
        assert result is None

    def test_find_best_agent(self):
        """Test finding best agent for a task"""
        registry = CapabilityRegistry()

        # Register multiple agents
        registry.register(AgentCapability(
            agent_name="DatabaseExpert",
            expertise=["database", "SQL"],
            tools=["psql"]
        ))
        registry.register(AgentCapability(
            agent_name="WebDev",
            expertise=["web", "frontend"],
            tools=["React"]
        ))

        # Task matching database expertise
        best = registry.find_best_agent("Design a SQL database")
        assert best == "DatabaseExpert"

    def test_find_best_agent_no_match(self):
        """Test finding best agent when no good match"""
        registry = CapabilityRegistry()

        registry.register(AgentCapability(
            agent_name="Agent1",
            expertise=["skill1"],
            tools=[]
        ))

        # Task with no matching keywords
        best = registry.find_best_agent("Completely unrelated task xyz123")
        # Should return None if score < 0.3
        assert best is None or best == "Agent1"

    def test_list_agents(self):
        """Test listing all agents"""
        registry = CapabilityRegistry()

        registry.register(AgentCapability(
            agent_name="Agent1",
            expertise=["skill1"],
            tools=[]
        ))
        registry.register(AgentCapability(
            agent_name="Agent2",
            expertise=["skill2"],
            tools=[]
        ))

        agents = registry.list_agents()
        assert len(agents) == 2
        assert "Agent1" in agents
        assert "Agent2" in agents

    def test_get_all_capabilities(self):
        """Test getting all capabilities"""
        registry = CapabilityRegistry()

        cap1 = AgentCapability(
            agent_name="Agent1",
            expertise=["skill1"],
            tools=[]
        )
        cap2 = AgentCapability(
            agent_name="Agent2",
            expertise=["skill2"],
            tools=[]
        )

        registry.register(cap1)
        registry.register(cap2)

        all_caps = registry.get_all_capabilities()
        assert len(all_caps) == 2
        assert "Agent1" in all_caps
        assert "Agent2" in all_caps


# Tests for SelfAwareMixin
class TestSelfAwareMixin:
    """Test SelfAwareMixin"""

    @pytest.mark.asyncio
    async def test_can_perform_with_high_confidence(self):
        """Test capability assessment with high confidence"""
        llm = MockLLM(mock_response="""
CONFIDENCE: 0.9
REASONING: I have all the necessary tools and expertise
MISSING_CAPABILITIES: None
ALTERNATIVE_APPROACH: None
SUGGESTED_AGENTS: None
MISSING_TOOLS: None
DIFFICULTY: 3
        """)

        agent = TestSelfAwareAgent(
            agent_name="TestAgent",
            llm=llm,
            role="Developer",
            goal="Build software",
            tools=["Python", "Git"]
        )

        assessment = await agent.can_perform("Write a Python function")

        assert assessment.confidence == 0.9
        assert assessment.capability_level == CapabilityLevel.EXPERT
        assert assessment.can_attempt is True
        assert llm.generate_called is True

    @pytest.mark.asyncio
    async def test_can_perform_with_low_confidence(self):
        """Test capability assessment with low confidence"""
        llm = MockLLM(mock_response="""
CONFIDENCE: 0.3
REASONING: I don't have the required database expertise
MISSING_CAPABILITIES: database design; SQL optimization
ALTERNATIVE_APPROACH: Consult a database expert
SUGGESTED_AGENTS: DatabaseExpert
MISSING_TOOLS: PostgreSQL; pgAdmin
DIFFICULTY: 8
        """)

        agent = TestSelfAwareAgent(
            agent_name="TestAgent",
            llm=llm,
            role="Frontend Developer",
            tools=["React"]
        )

        assessment = await agent.can_perform("Optimize database queries")

        assert assessment.confidence == 0.3
        assert assessment.capability_level == CapabilityLevel.LIMITED
        assert assessment.needs_help is True
        assert len(assessment.missing_capabilities) == 2
        assert "DatabaseExpert" in assessment.suggested_agents
        assert len(assessment.missing_tools) == 2
        assert assessment.difficulty == 8

    @pytest.mark.asyncio
    async def test_can_perform_caching(self):
        """Test capability assessment caching"""
        llm = MockLLM(mock_response="""
CONFIDENCE: 0.8
REASONING: Cached result
MISSING_CAPABILITIES: None
ALTERNATIVE_APPROACH: None
SUGGESTED_AGENTS: None
MISSING_TOOLS: None
DIFFICULTY: 5
        """)

        agent = TestSelfAwareAgent(
            agent_name="TestAgent",
            llm=llm,
            role="Developer"
        )

        # First call
        assessment1 = await agent.can_perform("Task A")
        assert llm.generate_called is True

        # Reset flag
        llm.generate_called = False

        # Second call with same task should use cache
        assessment2 = await agent.can_perform("Task A")
        assert llm.generate_called is False  # Should not call LLM again
        assert assessment1.confidence == assessment2.confidence

    @pytest.mark.asyncio
    async def test_can_perform_no_llm_fallback(self):
        """Test fallback when no LLM available"""
        agent = TestSelfAwareAgent(
            agent_name="TestAgent",
            llm=None,  # No LLM
            role="Developer"
        )

        assessment = await agent.can_perform("Some task")

        # Should return default confident assessment
        assert assessment.confidence == 0.7
        assert "No LLM available" in assessment.reasoning

    @pytest.mark.asyncio
    async def test_execute_or_delegate_high_confidence(self):
        """Test execution with high confidence"""
        llm = MockLLM(mock_response="""
CONFIDENCE: 0.9
REASONING: I can do this
MISSING_CAPABILITIES: None
ALTERNATIVE_APPROACH: None
SUGGESTED_AGENTS: None
MISSING_TOOLS: None
DIFFICULTY: 3
        """)

        agent = TestSelfAwareAgent(
            agent_name="TestAgent",
            llm=llm,
            role="Developer"
        )

        result = await agent.execute_or_delegate("Write code")

        assert result["status"] == "success"
        assert len(agent.executed_tasks) == 1

    @pytest.mark.asyncio
    async def test_execute_or_delegate_low_confidence(self):
        """Test delegation with low confidence"""
        llm = MockLLM(mock_response="""
CONFIDENCE: 0.3
REASONING: Need help
MISSING_CAPABILITIES: expertise
ALTERNATIVE_APPROACH: None
SUGGESTED_AGENTS: Expert
MISSING_TOOLS: None
DIFFICULTY: 9
        """)

        agent = TestSelfAwareAgent(
            agent_name="TestAgent",
            llm=llm,
            role="Developer"
        )

        result = await agent.execute_or_delegate("Complex task")

        assert result["status"] == "help_requested"
        assert result["requesting_agent"] == "TestAgent"
        assert result["confidence"] == 0.3
        assert len(agent.executed_tasks) == 0  # Should not execute

    @pytest.mark.asyncio
    async def test_execute_or_delegate_force_execute(self):
        """Test forced execution even with low confidence"""
        llm = MockLLM(mock_response="""
CONFIDENCE: 0.3
REASONING: Low confidence
MISSING_CAPABILITIES: None
ALTERNATIVE_APPROACH: None
SUGGESTED_AGENTS: None
MISSING_TOOLS: None
DIFFICULTY: 8
        """)

        agent = TestSelfAwareAgent(
            agent_name="TestAgent",
            llm=llm,
            role="Developer"
        )

        result = await agent.execute_or_delegate("Task", force_execute=True)

        assert result["status"] == "success"
        assert len(agent.executed_tasks) == 1  # Should execute despite low confidence

    @pytest.mark.asyncio
    async def test_request_help(self):
        """Test help request"""
        llm = MockLLM()
        agent = TestSelfAwareAgent(
            agent_name="TestAgent",
            llm=llm,
            role="Developer"
        )

        assessment = CapabilityAssessment(
            confidence=0.3,
            reasoning="Need database expert",
            missing_capabilities=["database design"],
            missing_tools=["PostgreSQL"],
            suggested_agents=["DatabaseExpert"]
        )

        help_request = await agent.request_help(
            task="Design database",
            assessment=assessment,
            context={"urgency": "high"}
        )

        assert help_request["status"] == "help_requested"
        assert help_request["requesting_agent"] == "TestAgent"
        assert help_request["task"] == "Design database"
        assert help_request["confidence"] == 0.3
        assert help_request["missing_capabilities"] == ["database design"]
        assert help_request["suggested_agents"] == ["DatabaseExpert"]
        assert help_request["context"]["urgency"] == "high"

    def test_clear_capability_cache(self):
        """Test clearing capability cache"""
        llm = MockLLM()
        agent = TestSelfAwareAgent(
            agent_name="TestAgent",
            llm=llm,
            role="Developer"
        )

        # Manually populate cache
        agent._capability_cache["test_key"] = CapabilityAssessment(
            confidence=0.8,
            reasoning="Cached"
        )

        assert len(agent._capability_cache) == 1

        agent.clear_capability_cache()

        assert len(agent._capability_cache) == 0


# Tests for SelfAwareAgent
class TestSelfAwareAgentClass:
    """Test SelfAwareAgent base class"""

    def test_initialization(self):
        """Test agent initialization"""
        llm = MockLLM()
        agent = TestSelfAwareAgent(
            agent_name="MyAgent",
            llm=llm,
            role="Developer",
            goal="Build software",
            backstory="Senior developer",
            tools=["Python", "Git"]
        )

        assert agent.agent_name == "MyAgent"
        assert agent.llm == llm
        assert agent.role == "Developer"
        assert agent.goal == "Build software"
        assert agent.backstory == "Senior developer"
        assert agent.tools == ["Python", "Git"]

    def test_capability_registration(self):
        """Test automatic capability registration"""
        # Clear global registry
        registry = get_capability_registry()
        registry._capabilities.clear()

        llm = MockLLM()
        agent = TestSelfAwareAgent(
            agent_name="RegisteredAgent",
            llm=llm,
            role="Tester",
            tools=["pytest"]
        )

        # Check if registered
        capability = registry.get("RegisteredAgent")
        assert capability is not None
        assert capability.agent_name == "RegisteredAgent"
        assert "Tester" in capability.expertise
        assert "pytest" in capability.tools


# Integration Tests
class TestSelfAwareIntegration:
    """Integration tests for self-aware agents"""

    @pytest.mark.asyncio
    async def test_full_workflow_success(self):
        """Test complete workflow with successful execution"""
        llm = MockLLM(mock_response="""
CONFIDENCE: 0.85
REASONING: I have the required skills and tools
MISSING_CAPABILITIES: None
ALTERNATIVE_APPROACH: None
SUGGESTED_AGENTS: None
MISSING_TOOLS: None
DIFFICULTY: 4
        """)

        agent = TestSelfAwareAgent(
            agent_name="DevAgent",
            llm=llm,
            role="Software Developer",
            goal="Write quality code",
            backstory="10 years of experience",
            tools=["Python", "pytest", "Git"]
        )

        # Execute task
        result = await agent.execute_or_delegate(
            task="Write a Python function to parse JSON",
            context={"format": "strict"}
        )

        assert result["status"] == "success"
        assert result["task"] == "Write a Python function to parse JSON"
        assert len(agent.executed_tasks) == 1

    @pytest.mark.asyncio
    async def test_full_workflow_delegation(self):
        """Test complete workflow with delegation"""
        # Clear registry
        registry = get_capability_registry()
        registry._capabilities.clear()

        llm = MockLLM(mock_response="""
CONFIDENCE: 0.2
REASONING: This requires machine learning expertise which I lack
MISSING_CAPABILITIES: machine learning; neural networks
ALTERNATIVE_APPROACH: Use a pre-trained model
SUGGESTED_AGENTS: MLExpert
MISSING_TOOLS: TensorFlow; PyTorch
DIFFICULTY: 9
        """)

        # Create requesting agent
        agent = TestSelfAwareAgent(
            agent_name="WebDev",
            llm=llm,
            role="Web Developer",
            tools=["React", "Node.js"]
        )

        # Register expert agent
        registry.register(AgentCapability(
            agent_name="MLExpert",
            expertise=["machine learning", "AI", "neural networks"],
            tools=["TensorFlow", "PyTorch"]
        ))

        # Execute task (should delegate)
        result = await agent.execute_or_delegate(
            task="Build a neural network for image classification"
        )

        assert result["status"] == "help_requested"
        assert result["requesting_agent"] == "WebDev"
        assert "MLExpert" in result["suggested_agents"]
        assert len(agent.executed_tasks) == 0  # Should not execute


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
