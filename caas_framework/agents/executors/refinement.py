"""
RefinementExecutor - Unified Agent Refinement Pattern

Eliminates duplicate refinement logic across 4+ agents.
Provides standardized workflow for LLM-based refinement with validation feedback.
"""

from typing import Dict, Any, List, Optional, Callable
import logging

from caas_framework.models.validation import ValidationIssue
from caas_framework.agents.mixins import PromptBuildingMixin

logger = logging.getLogger(__name__)


class RefinementExecutor:
    """
    Handles common refinement workflow for expert agents.
    
    Consolidates duplicate refinement patterns found in:
    - RequirementAnalyst._refine_implementation() (lines 249-294)
    - SystemArchitect._refine_implementation() (lines 279-323)
    - AgentDesigner._refine_implementation() (lines 328-370)
    - CodeGenerator._refine_implementation() (lines 420-462)
    
    Total: ~160 lines of duplicate code eliminated.
    """
    
    def __init__(
        self,
        agent_role: str,
        output_type: str,
        llm_invoke_func: Callable,
        golden_data: Optional[Any] = None,
        prompt_builder: Optional[PromptBuildingMixin] = None
    ):
        """
        Initialize refinement executor.
        
        Args:
            agent_role: Role description for refinement prompt
            output_type: Type of output being refined (e.g., "analysis", "architecture")
            llm_invoke_func: Function to invoke LLM (async callable)
            golden_data: Optional Golden Data reference
            prompt_builder: Optional PromptBuildingMixin instance
        """
        self.agent_role = agent_role
        self.output_type = output_type
        self.llm_invoke_func = llm_invoke_func
        self.golden_data = golden_data
        self.prompt_builder = prompt_builder or PromptBuildingMixin()
    
    async def refine_output(
        self,
        output: Dict[str, Any],
        issues: List[ValidationIssue],
        iteration: int = 1,
        guidelines: Optional[List[str]] = None,
        issue_formatter: Optional[Callable] = None,
        output_merger: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Refine output based on validation issues.
        
        Standard flow:
        1. Format validation issues
        2. Extract Golden Data context (if available)
        3. Build refinement prompt
        4. Invoke LLM
        5. Merge refined output with original
        
        Args:
            output: Current output to refine
            issues: Validation issues to address
            iteration: Refinement iteration number
            guidelines: Optional refinement guidelines
            issue_formatter: Optional custom issue formatter (callable)
            output_merger: Optional custom merger (callable)
            
        Returns:
            Refined output dictionary
            
        Example:
            executor = RefinementExecutor(
                agent_role="Requirements Analyst",
                output_type="analysis",
                llm_invoke_func=self._invoke_llm_structured,
                golden_data=self.golden_data
            )
            
            refined = await executor.refine_output(
                output=current_output,
                issues=validation_issues,
                iteration=1,
                guidelines=["Ensure all requirements are clear", ...]
            )
        """
        # Step 1: Format validation issues
        if issue_formatter:
            issues_summary = issue_formatter(issues)
        else:
            issues_summary = self._format_issues_default(issues)
        
        # Step 2: Extract Golden Data context
        golden_data_info = self._extract_golden_data_context()
        golden_data_context_desc = self._get_golden_data_description()
        
        # Step 3: Build refinement prompt
        prompt = self.prompt_builder.build_refinement_prompt(
            role=self.agent_role,
            original_output=output,
            validation_issues=issues,
            context={
                "golden_data": golden_data_info,
                "iteration": iteration
            } if golden_data_info else {"iteration": iteration}
        )
        
        # Step 4: Invoke LLM for refinement
        logger.info(f"🔄 Refining {self.output_type} (iteration {iteration}, {len(issues)} issues)")
        
        try:
            refined = await self.llm_invoke_func(
                prompt=prompt,
                expected_fields=list(output.keys()),
                fallback_factory=lambda: output
            )
        except Exception as e:
            logger.error(f"Refinement LLM invocation failed: {e}")
            return output
        
        # Step 5: Merge outputs
        if output_merger:
            return output_merger(refined, output)
        else:
            return self._merge_outputs_default(refined, output)
    
    def _format_issues_default(self, issues: List[ValidationIssue]) -> str:
        """
        Default issue formatting.
        
        Uses ValidationIssueFactory if available, otherwise simple formatting.
        """
        try:
            from caas_framework.validation.issue_factory import ValidationIssueFactory
            return ValidationIssueFactory.format_for_agent(issues)
        except ImportError:
            # Fallback: simple formatting
            if not issues:
                return "No issues identified."
            
            lines = ["## Validation Issues"]
            for i, issue in enumerate(issues, 1):
                severity = issue.severity if hasattr(issue, 'severity') else "medium"
                message = issue.message if hasattr(issue, 'message') else str(issue)
                lines.append(f"{i}. [{severity.upper()}] {message}")
            
            return "\n".join(lines)
    
    def _extract_golden_data_context(self) -> Optional[Dict[str, Any]]:
        """
        Extract relevant Golden Data context for refinement.
        
        Returns:
            Dictionary with Golden Data info or None
        """
        if not self.golden_data:
            return None
        
        context = {}
        
        # Extract features
        if hasattr(self.golden_data, 'features') and self.golden_data.features:
            context['features'] = [
                {"name": f.name, "description": f.description}
                if hasattr(f, 'name') and hasattr(f, 'description')
                else str(f)
                for f in self.golden_data.features[:10]  # Limit to prevent prompt overflow
            ]
        
        # Extract data models
        if hasattr(self.golden_data, 'data_models') and self.golden_data.data_models:
            context['data_models'] = [
                dm.entity_name if hasattr(dm, 'entity_name') else str(dm)
                for dm in self.golden_data.data_models[:10]
            ]
        
        # Extract domain info
        if hasattr(self.golden_data, 'domain'):
            context['domain'] = self.golden_data.domain
        
        if hasattr(self.golden_data, 'subdomain'):
            context['subdomain'] = self.golden_data.subdomain
        
        return context if context else None
    
    def _get_golden_data_description(self) -> str:
        """Get human-readable description of Golden Data type."""
        if not self.golden_data:
            return ""
        
        parts = []
        if hasattr(self.golden_data, 'features') and self.golden_data.features:
            parts.append("Features")
        if hasattr(self.golden_data, 'data_models') and self.golden_data.data_models:
            parts.append("Data Models")
        
        return ", ".join(parts) if parts else "Golden Data"
    
    def _merge_outputs_default(
        self,
        refined: Dict[str, Any],
        original: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Default output merger.
        
        Strategy:
        1. Start with original
        2. Update with refined values (prefer refined)
        3. Preserve original if refined is empty/None
        
        Args:
            refined: Refined output from LLM
            original: Original output
            
        Returns:
            Merged output dictionary
        """
        if not refined:
            return original
        
        merged = original.copy()
        
        for key, value in refined.items():
            # Skip None values
            if value is None:
                continue
            
            # Skip empty lists/dicts (prefer original if present)
            if isinstance(value, (list, dict)) and not value:
                if key in original and original[key]:
                    continue
            
            # Use refined value
            merged[key] = value
        
        return merged
    
    @staticmethod
    def create_for_agent(
        agent,
        agent_role: str,
        output_type: str
    ) -> 'RefinementExecutor':
        """
        Factory method to create RefinementExecutor for an agent.
        
        Args:
            agent: Agent instance (must have llm and golden_data attributes)
            agent_role: Role description
            output_type: Output type name
            
        Returns:
            Configured RefinementExecutor
            
        Example:
            executor = RefinementExecutor.create_for_agent(
                agent=self,
                agent_role="Expert Requirements Analyst",
                output_type="requirements analysis"
            )
        """
        # Get LLM invocation function
        llm_invoke_func = (
            agent._invoke_llm_structured
            if hasattr(agent, '_invoke_llm_structured')
            else None
        )
        
        if not llm_invoke_func:
            raise ValueError("Agent must have _invoke_llm_structured method")
        
        # Get prompt builder if available
        prompt_builder = None
        if isinstance(agent, PromptBuildingMixin):
            prompt_builder = agent
        
        return RefinementExecutor(
            agent_role=agent_role,
            output_type=output_type,
            llm_invoke_func=llm_invoke_func,
            golden_data=getattr(agent, 'golden_data', None),
            prompt_builder=prompt_builder
        )


class StandardRefinementGuidelines:
    """
    Standard refinement guidelines for different agent types.
    
    Provides consistent guidelines to eliminate duplication.
    """
    
    REQUIREMENT_ANALYSIS = [
        "Ensure all functional requirements have clear acceptance criteria",
        "Verify non-functional requirements are measurable",
        "Align with Golden Data features when provided",
        "Include proper traceability to features"
    ]
    
    ARCHITECTURE = [
        "Ensure architectural components match requirements",
        "Verify data flow is complete and logical",
        "Align with Golden Data data models when provided",
        "Include proper rationale for design decisions"
    ]
    
    AGENT_DESIGN = [
        "Ensure agents have distinct, non-overlapping roles",
        "Verify task dependencies are correct",
        "Align with Golden Data features and tasks",
        "Include appropriate tools for each agent"
    ]
    
    CODE_GENERATION = [
        "Ensure code is executable without modifications",
        "Verify all imports and dependencies are correct",
        "Include proper error handling",
        "Add docstrings and type hints"
    ]
    
    QA_TESTING = [
        "Ensure test coverage is comprehensive",
        "Verify test cases cover edge cases",
        "Align tests with acceptance criteria",
        "Include both unit and integration tests"
    ]
    
    @classmethod
    def get_for_phase(cls, phase_name: str) -> List[str]:
        """
        Get guidelines for a specific phase.
        
        Args:
            phase_name: Phase name (discovery, architecture, design, etc.)
            
        Returns:
            List of guideline strings
        """
        mapping = {
            "discovery": cls.REQUIREMENT_ANALYSIS,
            "architecture": cls.ARCHITECTURE,
            "design": cls.AGENT_DESIGN,
            "development": cls.CODE_GENERATION,
            "quality_assurance": cls.QA_TESTING,
        }
        
        return mapping.get(phase_name.lower(), [])
