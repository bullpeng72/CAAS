"""
GoldenDataEnhancer - Unified Golden Data Enhancement

Eliminates duplicate Golden Data alignment logic across 3+ agents.
Provides standardized traceability mapping and coverage calculation.
"""

from typing import Any, Dict, List, Optional

from caas_framework.utils.logger import get_logger

logger = get_logger()


class GoldenDataEnhancer:
    """
    Handles Golden Data enhancement for agent outputs.

    Consolidates duplicate enhancement patterns found in:
    - RequirementAnalyst._enhance_with_golden_data() (lines 211-247)
    - SystemArchitect._align_with_golden_data() (lines 237-277)
    - AgentDesigner._enhance_with_golden_data() (lines 282-324)

    Total: ~100 lines of duplicate code eliminated.
    """

    def __init__(self, golden_data: Optional[Any] = None):
        """
        Initialize enhancer.

        Args:
            golden_data: ConcretizedRequirement or similar Golden Data object
        """
        self.golden_data = golden_data

    def enhance_with_traceability(
        self,
        output: Dict[str, Any],
        items_key: str,
        item_text_keys: List[str],
        item_id_key: str = "id",
        trace_key: str = "traceability_map",
        alignment_key: str = "golden_data_alignment",
    ) -> Dict[str, Any]:
        """
        Enhance output with Golden Data traceability mapping.

        Standard flow:
        1. Safety check: ensure items is a list
        2. Build traceability map using GoldenDataMatcher
        3. Calculate coverage metrics
        4. Add traceability and alignment metadata

        Args:
            output: Agent output to enhance
            items_key: Key in output containing items to trace (e.g., "functional_requirements")
            item_text_keys: List of keys in each item to match against features
            item_id_key: Key in each item for ID (default "id")
            trace_key: Key to store traceability map (default "traceability_map")
            alignment_key: Key to store alignment metrics (default "golden_data_alignment")

        Returns:
            Enhanced output dictionary

        Example:
            enhancer = GoldenDataEnhancer(golden_data=self.golden_data)

            enhanced = enhancer.enhance_with_traceability(
                output=analysis,
                items_key="functional_requirements",
                item_text_keys=["description"],
                item_id_key="id"
            )
        """
        if not self.golden_data:
            return output

        if not hasattr(self.golden_data, "features") or not self.golden_data.features:
            return output

        # Step 1: Safety check - ensure items is a list
        items = output.get(items_key)
        if not isinstance(items, list):
            logger.warning(
                f"Expected list for {items_key}, got {type(items)}. Using empty list."
            )
            items = []

        if not items:
            return output

        # Step 2: Build traceability map
        try:
            from caas_framework.utils import GoldenDataMatcher

            traceability_map = GoldenDataMatcher.build_traceability_map(
                features=self.golden_data.features,
                items=items,
                item_text_keys=item_text_keys,
                item_id_key=item_id_key,
            )
        except ImportError:
            logger.warning("GoldenDataMatcher not available, skipping traceability")
            return output

        # Step 3: Calculate coverage metrics
        covered_features = len(
            [traced_items for traced_items in traceability_map.values() if traced_items]
        )
        total_features = len(self.golden_data.features)

        try:
            coverage_percentage = GoldenDataMatcher.calculate_percentage(
                covered=covered_features, total=total_features
            )
        except (ZeroDivisionError, AttributeError, TypeError):
            coverage_percentage = (
                (covered_features / total_features * 100.0)
                if total_features > 0
                else 0.0
            )

        # Step 4: Add metadata
        output[trace_key] = traceability_map
        output[alignment_key] = {
            "total_features": total_features,
            "covered_features": covered_features,
            "coverage_percentage": coverage_percentage,
        }

        logger.info(
            f"✅ Golden Data traceability: {covered_features}/{total_features} features covered "
            f"({coverage_percentage:.1f}%)"
        )

        return output

    def enhance_with_data_models(
        self,
        output: Dict[str, Any],
        components_key: str = "components",
        alignment_key: str = "golden_data_alignment",
    ) -> Dict[str, Any]:
        """
        Enhance architecture/design with Golden Data model alignment.

        Specialized for SystemArchitect and similar agents that work with data models.

        Args:
            output: Agent output to enhance
            components_key: Key containing architecture components
            alignment_key: Key to store alignment info

        Returns:
            Enhanced output dictionary

        Example:
            enhancer = GoldenDataEnhancer(golden_data=self.golden_data)

            enhanced = enhancer.enhance_with_data_models(
                output=architecture,
                components_key="components"
            )
        """
        if not self.golden_data:
            return output

        if (
            not hasattr(self.golden_data, "data_models")
            or not self.golden_data.data_models
        ):
            return output

        # Extract component names from architecture
        components = output.get(components_key, [])
        if not isinstance(components, list):
            components = []

        component_names = set()
        for comp in components:
            if isinstance(comp, dict):
                name = comp.get("name") or comp.get("component_name")
                if name:
                    component_names.add(name.lower())

        # Match with Golden Data models
        golden_model_names = set()
        for model in self.golden_data.data_models:
            if hasattr(model, "entity_name"):
                golden_model_names.add(model.entity_name.lower())

        # Calculate alignment
        matched_models = component_names & golden_model_names
        missing_models = golden_model_names - component_names
        extra_components = component_names - golden_model_names

        total_models = len(self.golden_data.data_models)
        covered_models = len(matched_models)
        coverage_percentage = (
            (covered_models / total_models * 100.0) if total_models > 0 else 0.0
        )

        # Add alignment info
        output[alignment_key] = {
            "total_golden_models": total_models,
            "matched_models": covered_models,
            "coverage_percentage": coverage_percentage,
            "missing_models": list(missing_models),
            "extra_components": list(extra_components),
        }

        logger.info(
            f"✅ Data model alignment: {covered_models}/{total_models} models matched "
            f"({coverage_percentage:.1f}%)"
        )

        return output

    def enhance_with_feature_task_mapping(
        self,
        output: Dict[str, Any],
        agents_key: str = "agents",
        tasks_key: str = "tasks",
        alignment_key: str = "golden_data_alignment",
    ) -> Dict[str, Any]:
        """
        Enhance agent design with Golden Data feature-task mapping.

        Specialized for AgentDesigner output.

        Args:
            output: Agent design output
            agents_key: Key containing agents list
            tasks_key: Key containing tasks list
            alignment_key: Key to store alignment info

        Returns:
            Enhanced output dictionary

        Example:
            enhancer = GoldenDataEnhancer(golden_data=self.golden_data)

            enhanced = enhancer.enhance_with_feature_task_mapping(
                output=design,
                agents_key="agents",
                tasks_key="tasks"
            )
        """
        if not self.golden_data:
            return output

        if not hasattr(self.golden_data, "features") or not self.golden_data.features:
            return output

        # Safety checks
        tasks = output.get(tasks_key)
        if not isinstance(tasks, list):
            tasks = []

        agents = output.get(agents_key)
        if not isinstance(agents, list):
            agents = []

        if not tasks:
            return output

        # Build traceability using GoldenDataMatcher
        try:
            from caas_framework.utils import GoldenDataMatcher

            # Match tasks to features
            traceability_map = GoldenDataMatcher.build_traceability_map(
                features=self.golden_data.features,
                items=tasks,
                item_text_keys=["description", "expected_output"],
                item_id_key="id",
            )

            # Calculate coverage
            covered_features = len(
                [items for items in traceability_map.values() if items]
            )
            total_features = len(self.golden_data.features)
            coverage_percentage = GoldenDataMatcher.calculate_percentage(
                covered=covered_features, total=total_features
            )

            # Add metadata
            output["feature_task_traceability"] = traceability_map
            output[alignment_key] = {
                "total_features": total_features,
                "covered_features": covered_features,
                "coverage_percentage": coverage_percentage,
                "total_agents": len(agents),
                "total_tasks": len(tasks),
            }

            logger.info(
                f"✅ Feature-task traceability: {covered_features}/{total_features} features covered "
                f"({coverage_percentage:.1f}%) with {len(agents)} agents and {len(tasks)} tasks"
            )

        except ImportError:
            logger.warning(
                "GoldenDataMatcher not available, skipping feature-task mapping"
            )

        return output

    @staticmethod
    def create_for_agent(agent) -> "GoldenDataEnhancer":
        """
        Factory method to create GoldenDataEnhancer for an agent.

        Args:
            agent: Agent instance (must have golden_data attribute)

        Returns:
            Configured GoldenDataEnhancer

        Example:
            enhancer = GoldenDataEnhancer.create_for_agent(self)
            enhanced = enhancer.enhance_with_traceability(output, ...)
        """
        return GoldenDataEnhancer(golden_data=getattr(agent, "golden_data", None))


class EnhancementRegistry:
    """
    Registry for enhancement strategies by agent type/phase.

    Provides consistent enhancement approach based on agent role.
    """

    @staticmethod
    def enhance_for_phase(
        phase_name: str, output: Dict[str, Any], golden_data: Optional[Any]
    ) -> Dict[str, Any]:
        """
        Apply appropriate enhancement based on phase.

        Args:
            phase_name: Phase name (discovery, architecture, design, etc.)
            output: Agent output to enhance
            golden_data: Golden Data reference

        Returns:
            Enhanced output

        Example:
            enhanced = EnhancementRegistry.enhance_for_phase(
                phase_name="discovery",
                output=analysis,
                golden_data=self.golden_data
            )
        """
        if not golden_data:
            return output

        enhancer = GoldenDataEnhancer(golden_data)

        # Phase-specific enhancement
        if phase_name.lower() == "discovery":
            # Requirement analysis - trace functional requirements
            if "functional_requirements" in output:
                output = enhancer.enhance_with_traceability(
                    output=output,
                    items_key="functional_requirements",
                    item_text_keys=["description"],
                    item_id_key="id",
                )

        elif phase_name.lower() == "architecture":
            # Architecture - align with data models
            if "components" in output or "data_models" in output:
                output = enhancer.enhance_with_data_models(
                    output=output, components_key="components"
                )

        elif phase_name.lower() == "design":
            # Agent design - feature-task mapping
            if "agents" in output and "tasks" in output:
                output = enhancer.enhance_with_feature_task_mapping(
                    output=output, agents_key="agents", tasks_key="tasks"
                )

        return output
