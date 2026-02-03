"""
Tests for Agent Registry System

Verifies:
1. Agent registration via decorator
2. Dynamic agent discovery by phase
3. Singleton pattern works correctly
4. Factory function creates agents correctly
5. No hard-coded dependencies in collaboration
6. Registry-based DIP implementation
"""

from typing import List

import pytest

from caas_framework.agents.base import AgentPhase, BaseExpertAgent
from caas_framework.agents.registry import (
    create_agent,
    discover_agents,
    get_agent_registry,
    register_agent,
)


class TestAgentRegistry:
    """Test Agent Registry core functionality"""

    def setup_method(self):
        """Reset registry before each test"""
        registry = get_agent_registry()
        registry.clear()

    def test_singleton_pattern(self):
        """Test that registry is a singleton"""
        registry1 = get_agent_registry()
        registry2 = get_agent_registry()

        # Should be same instance
        assert registry1 is registry2

    def test_register_decorator(self):
        """Test that @register_agent decorator works"""
        registry = get_agent_registry()

        # Create a test agent
        @register_agent(phase=AgentPhase.DISCOVERY)
        class TestAgent(BaseExpertAgent):
            @property
            def agent_name(self) -> str:
                return "TestAgent"

            @property
            def agent_role(self) -> str:
                return "Test Role"

            @property
            def agent_expertise(self) -> List[str]:
                return ["Testing"]

            async def _do_work(self, requirement, context, previous_outputs):
                return {"result": "test"}

            async def _refine_implementation(self, output, issues, context, iteration):
                return output

        # Check registration
        assert registry.is_registered(AgentPhase.DISCOVERY)
        agent_class = registry.get_agent_class(AgentPhase.DISCOVERY)
        assert agent_class is TestAgent

    def test_get_agent_class_by_phase(self):
        """Test getting agent class by phase"""
        registry = get_agent_registry()

        @register_agent(phase=AgentPhase.ARCHITECTURE)
        class ArchitectAgent(BaseExpertAgent):
            @property
            def agent_name(self) -> str:
                return "ArchitectAgent"

            @property
            def agent_role(self) -> str:
                return "Architect"

            @property
            def agent_expertise(self) -> List[str]:
                return ["Architecture"]

            async def _do_work(self, requirement, context, previous_outputs):
                return {"result": "architecture"}

            async def _refine_implementation(self, output, issues, context, iteration):
                return output

        agent_class = registry.get_agent_class(AgentPhase.ARCHITECTURE)
        assert agent_class.__name__ == "ArchitectAgent"

    def test_get_agent_by_name(self):
        """Test getting agent by class name"""
        registry = get_agent_registry()

        @register_agent(phase=AgentPhase.DESIGN)
        class DesignerAgent(BaseExpertAgent):
            @property
            def agent_name(self) -> str:
                return "DesignerAgent"

            @property
            def agent_role(self) -> str:
                return "Designer"

            @property
            def agent_expertise(self) -> List[str]:
                return ["Design"]

            async def _do_work(self, requirement, context, previous_outputs):
                return {"result": "design"}

            async def _refine_implementation(self, output, issues, context, iteration):
                return output

        agent_class = registry.get_agent_by_name("DesignerAgent")
        assert agent_class.__name__ == "DesignerAgent"

    def test_registry_raises_on_duplicate_phase_without_override(self):
        """Test that registering same phase twice raises error"""
        registry = get_agent_registry()

        @register_agent(phase=AgentPhase.DISCOVERY)
        class Agent1(BaseExpertAgent):
            @property
            def agent_name(self) -> str:
                return "Agent1"

            @property
            def agent_role(self) -> str:
                return "Role1"

            @property
            def agent_expertise(self) -> List[str]:
                return ["Expertise1"]

            async def _do_work(self, requirement, context, previous_outputs):
                return {}

            async def _refine_implementation(self, output, issues, context, iteration):
                return output

        # Try to register another agent for same phase
        with pytest.raises(ValueError, match="already has registered agent"):
            @register_agent(phase=AgentPhase.DISCOVERY)
            class Agent2(BaseExpertAgent):
                @property
                def agent_name(self) -> str:
                    return "Agent2"

                @property
                def agent_role(self) -> str:
                    return "Role2"

                @property
                def agent_expertise(self) -> List[str]:
                    return ["Expertise2"]

                async def _do_work(self, requirement, context, previous_outputs):
                    return {}

                async def _refine_implementation(self, output, issues, context, iteration):
                    return output

    def test_registry_allows_override(self):
        """Test that override=True allows replacing agent"""
        registry = get_agent_registry()

        @register_agent(phase=AgentPhase.DISCOVERY)
        class Agent1(BaseExpertAgent):
            @property
            def agent_name(self) -> str:
                return "Agent1"

            @property
            def agent_role(self) -> str:
                return "Role1"

            @property
            def agent_expertise(self) -> List[str]:
                return ["Expertise1"]

            async def _do_work(self, requirement, context, previous_outputs):
                return {}

            async def _refine_implementation(self, output, issues, context, iteration):
                return output

        # Override with new agent
        @register_agent(phase=AgentPhase.DISCOVERY, override=True)
        class Agent2(BaseExpertAgent):
            @property
            def agent_name(self) -> str:
                return "Agent2"

            @property
            def agent_role(self) -> str:
                return "Role2"

            @property
            def agent_expertise(self) -> List[str]:
                return ["Expertise2"]

            async def _do_work(self, requirement, context, previous_outputs):
                return {}

            async def _refine_implementation(self, output, issues, context, iteration):
                return output

        # Should get Agent2 now
        agent_class = registry.get_agent_class(AgentPhase.DISCOVERY)
        assert agent_class.__name__ == "Agent2"

    def test_get_all_phases(self):
        """Test getting all registered phases"""
        registry = get_agent_registry()

        @register_agent(phase=AgentPhase.DISCOVERY)
        class Agent1(BaseExpertAgent):
            @property
            def agent_name(self) -> str:
                return "Agent1"

            @property
            def agent_role(self) -> str:
                return "Role1"

            @property
            def agent_expertise(self) -> List[str]:
                return ["Expertise1"]

            async def _do_work(self, requirement, context, previous_outputs):
                return {}

            async def _refine_implementation(self, output, issues, context, iteration):
                return output

        @register_agent(phase=AgentPhase.ARCHITECTURE)
        class Agent2(BaseExpertAgent):
            @property
            def agent_name(self) -> str:
                return "Agent2"

            @property
            def agent_role(self) -> str:
                return "Role2"

            @property
            def agent_expertise(self) -> List[str]:
                return ["Expertise2"]

            async def _do_work(self, requirement, context, previous_outputs):
                return {}

            async def _refine_implementation(self, output, issues, context, iteration):
                return output

        phases = registry.get_all_phases()
        assert AgentPhase.DISCOVERY in phases
        assert AgentPhase.ARCHITECTURE in phases
        assert len(phases) == 2

    def test_registry_info(self):
        """Test getting registry information"""
        registry = get_agent_registry()

        @register_agent(phase=AgentPhase.DISCOVERY)
        class TestAgent(BaseExpertAgent):
            @property
            def agent_name(self) -> str:
                return "TestAgent"

            @property
            def agent_role(self) -> str:
                return "Test Role"

            @property
            def agent_expertise(self) -> List[str]:
                return ["Testing"]

            async def _do_work(self, requirement, context, previous_outputs):
                return {}

            async def _refine_implementation(self, output, issues, context, iteration):
                return output

        info = registry.get_registry_info()

        assert info["total_agents"] == 1
        assert info["phases_covered"] == 1
        assert AgentPhase.DISCOVERY.value in info["registered_phases"]
        assert "TestAgent" in info["registered_agents"]


class TestCreateAgentFactory:
    """Test create_agent factory function"""

    def setup_method(self):
        """Reset registry before each test"""
        registry = get_agent_registry()
        registry.clear()

    def test_create_agent_instantiates_correctly(self):
        """Test that create_agent instantiates agent with correct parameters"""

        @register_agent(phase=AgentPhase.DISCOVERY)
        class TestAgent(BaseExpertAgent):
            @property
            def agent_name(self) -> str:
                return "TestAgent"

            @property
            def agent_role(self) -> str:
                return "Test Role"

            @property
            def agent_expertise(self) -> List[str]:
                return ["Testing"]

            async def _do_work(self, requirement, context, previous_outputs):
                return {"result": "test"}

            async def _refine_implementation(self, output, issues, context, iteration):
                return output

        # Mock LLM plugin
        class MockLLM:
            async def ainvoke(self, **kwargs):
                return "Mock response"

        llm_plugin = MockLLM()

        # Create agent via factory
        agent = create_agent(
            phase=AgentPhase.DISCOVERY,
            llm_plugin=llm_plugin,
            golden_data=None
        )

        assert isinstance(agent, BaseExpertAgent)
        assert isinstance(agent, TestAgent)
        assert agent.phase == AgentPhase.DISCOVERY
        assert agent.llm is llm_plugin


class TestRealAgentRegistration:
    """Test that real agents are properly registered"""

    # NOTE: No setup_method here - we want to keep existing registrations

    def test_all_bmad_agents_registered(self):
        """Test that all 5 BMAD agents are registered"""
        import importlib
        import sys

        # Force reload of agent modules to trigger re-registration
        registry = get_agent_registry()
        registry.clear()  # Clear before reloading

        # Reload all agent modules to trigger decorators
        for module_name in [
            'caas_framework.agents.requirement_analyst',
            'caas_framework.agents.system_architect',
            'caas_framework.agents.agent_designer',
            'caas_framework.agents.code_generator',
            'caas_framework.agents.qa_specialist'
        ]:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            else:
                importlib.import_module(module_name)

        # Now import the classes

        # Check all 5 phases are covered
        assert registry.is_registered(AgentPhase.DISCOVERY), "DISCOVERY phase not registered"
        assert registry.is_registered(AgentPhase.ARCHITECTURE), "ARCHITECTURE phase not registered"
        assert registry.is_registered(AgentPhase.DESIGN), "DESIGN phase not registered"
        assert registry.is_registered(AgentPhase.DELIVERY), "DELIVERY phase not registered"
        assert registry.is_registered(AgentPhase.QUALITY_ASSURANCE), "QA phase not registered"

        # Check correct agent classes
        assert registry.get_agent_class(AgentPhase.DISCOVERY).__name__ == "RequirementAnalystAgent"
        assert registry.get_agent_class(AgentPhase.ARCHITECTURE).__name__ == "SystemArchitectAgent"
        assert registry.get_agent_class(AgentPhase.DESIGN).__name__ == "AgentDesignerAgent"
        assert registry.get_agent_class(AgentPhase.DELIVERY).__name__ == "CodeGeneratorAgent"
        assert registry.get_agent_class(AgentPhase.QUALITY_ASSURANCE).__name__ == "QASpecialistAgent"

    def test_discover_agents_function(self):
        """Test that discover_agents imports all agents"""
        import importlib
        import sys

        registry = get_agent_registry()
        registry.clear()  # Clear before discovery

        # Force reload to trigger registration
        for module_name in [
            'caas_framework.agents.requirement_analyst',
            'caas_framework.agents.system_architect',
            'caas_framework.agents.agent_designer',
            'caas_framework.agents.code_generator',
            'caas_framework.agents.qa_specialist'
        ]:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])

        registry = discover_agents()

        # Should have all 5 agents registered
        info = registry.get_registry_info()
        assert info["total_agents"] >= 5, f"Expected >= 5 agents, got {info['total_agents']}: {info}"
        assert info["phases_covered"] >= 5, f"Expected >= 5 phases, got {info['phases_covered']}: {info}"


class TestDependencyInversionPrinciple:
    """
    Critical test: Verify DIP is properly implemented

    This ensures the fundamental redesign goal is met:
    - High-level module (Collaboration) should not depend on low-level modules (concrete agents)
    - Both should depend on abstractions (BaseExpertAgent + Registry)
    """

    def test_collaboration_uses_registry_not_imports(self):
        """Test that ExpertAgentCollaboration module uses registry, not hard-coded imports"""
        # Read the source file directly to check module-level imports
        with open('caas_framework/agents/collaboration.py', 'r') as f:
            source = f.read()

        # Get just the import section (first 50 lines typically contain all imports)
        import_section = '\n'.join(source.split('\n')[:50])

        # Check that collaboration.py no longer imports concrete agent classes at module level
        assert "from caas_framework.agents.requirement_analyst import RequirementAnalystAgent" not in import_section, \
            "RequirementAnalystAgent should not be imported"
        assert "from caas_framework.agents.system_architect import SystemArchitectAgent" not in import_section, \
            "SystemArchitectAgent should not be imported"
        assert "from caas_framework.agents.agent_designer import AgentDesignerAgent" not in import_section, \
            "AgentDesignerAgent should not be imported"
        assert "from caas_framework.agents.code_generator import CodeGeneratorAgent" not in import_section, \
            "CodeGeneratorAgent should not be imported"
        assert "from caas_framework.agents.qa_specialist import QASpecialistAgent" not in import_section, \
            "QASpecialistAgent should not be imported"

        # Check that it DOES import registry
        assert "from caas_framework.agents.registry import" in import_section, \
            "Registry should be imported"

    def test_collaboration_creates_agents_via_factory(self):
        """Test that collaboration uses create_agent factory"""
        import inspect

        from caas_framework.agents.collaboration import ExpertAgentCollaboration

        source = inspect.getsource(ExpertAgentCollaboration.__init__)

        # Should use create_agent factory
        assert "create_agent" in source

        # Should NOT directly instantiate concrete classes
        assert "RequirementAnalystAgent(" not in source
        assert "SystemArchitectAgent(" not in source
        assert "AgentDesignerAgent(" not in source
        assert "CodeGeneratorAgent(" not in source
        assert "QASpecialistAgent(" not in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
