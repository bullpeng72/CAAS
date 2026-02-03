"""
Golden Data Matcher Utility

Unified utility for matching Golden Data features to various items
(functional requirements, tasks, etc.) and calculating coverage metrics.

Consolidates duplicate feature matching logic from:
- requirement_analyst.py
- agent_designer.py
- qa_specialist.py
"""

from typing import Any, Dict, List, Optional, Set, Union

from caas_framework.models.specifications import (
    ConcretizedRequirement,
    DataModel,
    FeatureSpec,
)


class GoldenDataMatcher:
    """
    Unified Golden Data matching and coverage calculation utility.

    Provides standardized methods for:
    - Feature matching (text-based matching between features and items)
    - Coverage calculation (percentage of features covered)
    - Traceability mapping (feature -> items and items -> features)
    """

    @staticmethod
    def match_features_to_items(
        features: List[FeatureSpec],
        items: List[Union[Dict[str, Any], Any]],
        item_text_keys: List[str],
        item_id_key: str = "id",
    ) -> Dict[str, List[str]]:
        """
        Match Golden Data features to items (FRs, tasks, components, etc.)

        Uses case-insensitive text matching to find feature references in items.

        Args:
            features: List of FeatureSpec objects from Golden Data
            items: List of items (dicts or objects) to match against
            item_text_keys: Keys/attributes to search for feature references
                           (e.g., ["description"], ["description", "goal"])
            item_id_key: Key/attribute name for item ID

        Returns:
            Dict mapping item_id -> [matched_feature_ids]

        Example:
            >>> features = [FeatureSpec(id="F1", name="User Login", ...)]
            >>> frs = [{"id": "FR-001", "description": "Implement user login"}]
            >>> match_features_to_items(features, frs, ["description"])
            {"FR-001": ["F1"]}
        """
        from caas_framework.utils import ObjectAccessor

        item_feature_map: Dict[str, List[str]] = {}

        for item in items:
            item_id = ObjectAccessor.get_value(item, item_id_key, "unknown")
            matched_features: List[str] = []

            # Get all text fields from item
            item_texts: List[str] = []
            for key in item_text_keys:
                text = ObjectAccessor.get_value(item, key, "")
                if text:
                    item_texts.append(str(text).lower())

            # Match features against item texts
            for feature in features:
                feature_name_lower = feature.name.lower()
                feature_id_lower = feature.id.lower()

                # Check if feature name or ID appears in any item text
                for item_text in item_texts:
                    if feature_name_lower in item_text or feature_id_lower in item_text:
                        matched_features.append(feature.id)
                        break  # Feature matched, no need to check other texts

            item_feature_map[item_id] = matched_features

        return item_feature_map

    @staticmethod
    def build_traceability_map(
        features: List[FeatureSpec],
        items: List[Union[Dict[str, Any], Any]],
        item_text_keys: List[str],
        item_id_key: str = "id",
    ) -> Dict[str, List[str]]:
        """
        Build traceability map: feature_id -> [item_ids]

        Inverse of match_features_to_items().

        Args:
            features: List of FeatureSpec objects
            items: List of items to match
            item_text_keys: Keys to search for feature references
            item_id_key: Key for item ID

        Returns:
            Dict mapping feature_id -> [item_ids]

        Example:
            >>> features = [FeatureSpec(id="F1", name="User Login", ...)]
            >>> frs = [{"id": "FR-001", "description": "User login feature"}]
            >>> build_traceability_map(features, frs, ["description"])
            {"F1": ["FR-001"]}
        """
        # First get item -> features mapping
        item_feature_map = GoldenDataMatcher.match_features_to_items(
            features, items, item_text_keys, item_id_key
        )

        # Invert to get feature -> items mapping
        traceability_map: Dict[str, List[str]] = {f.id: [] for f in features}

        for item_id, feature_ids in item_feature_map.items():
            for feature_id in feature_ids:
                if feature_id in traceability_map:
                    traceability_map[feature_id].append(item_id)

        return traceability_map

    @staticmethod
    def calculate_coverage(
        features: List[FeatureSpec], item_feature_map: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Calculate Golden Data coverage metrics.

        Args:
            features: List of FeatureSpec objects from Golden Data
            item_feature_map: Dict mapping item_id -> [feature_ids]
                             (from match_features_to_items)

        Returns:
            Dict with:
            - total_features: Total number of features
            - covered_features: Number of features covered by items
            - uncovered_features: List of uncovered feature IDs
            - coverage_percentage: Coverage percentage (0-100)

        Example:
            >>> features = [FeatureSpec(id="F1", ...), FeatureSpec(id="F2", ...)]
            >>> item_map = {"FR-001": ["F1"], "FR-002": ["F1"]}
            >>> calculate_coverage(features, item_map)
            {
                "total_features": 2,
                "covered_features": 1,
                "uncovered_features": ["F2"],
                "coverage_percentage": 50.0
            }
        """
        total_features = len(features)

        # Get unique covered feature IDs
        covered_feature_ids: Set[str] = set()
        for feature_ids in item_feature_map.values():
            covered_feature_ids.update(feature_ids)

        covered_count = len(covered_feature_ids)

        # Identify uncovered features
        uncovered_features = [f.id for f in features if f.id not in covered_feature_ids]

        coverage_percentage = GoldenDataMatcher.calculate_percentage(covered_count, total_features)

        return {
            "total_features": total_features,
            "covered_features": covered_count,
            "uncovered_features": uncovered_features,
            "coverage_percentage": coverage_percentage,
        }

    @staticmethod
    def calculate_percentage(covered: int, total: int) -> float:
        """
        Safe percentage calculation with zero handling.

        Args:
            covered: Number of covered items
            total: Total number of items

        Returns:
            Percentage (0-100), or 0.0 if total is 0
        """
        return (covered / total * 100.0) if total > 0 else 0.0

    @staticmethod
    def count_covered_items(item_map: Dict[str, List[str]]) -> int:
        """
        Count items with non-empty feature mappings.

        Args:
            item_map: Dict mapping item_id -> [feature_ids]

        Returns:
            Count of items with at least one matched feature
        """
        return len([features for features in item_map.values() if features])

    @staticmethod
    def create_alignment_metadata(
        golden_data: ConcretizedRequirement, coverage_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create Golden Data alignment metadata.

        Args:
            golden_data: ConcretizedRequirement object
            coverage_metrics: Optional coverage metrics from calculate_coverage()

        Returns:
            Dict with alignment metadata
        """
        features = golden_data.features if golden_data.features else []
        data_models = golden_data.data_models if golden_data.data_models else []
        ui_components = golden_data.ui_components if golden_data.ui_components else []

        metadata = {
            "domain": golden_data.domain,
            "project_name": golden_data.project_name,
            "total_features": len(features),
            "total_data_models": len(data_models),
            "total_ui_components": len(ui_components),
            "deployment_target": golden_data.deployment_target,
            "workflow_type": golden_data.workflow_type,
        }

        # Add coverage metrics if provided
        if coverage_metrics:
            metadata.update(
                {
                    "covered_features": coverage_metrics.get("covered_features", 0),
                    "coverage_percentage": coverage_metrics.get("coverage_percentage", 0.0),
                    "uncovered_features": coverage_metrics.get("uncovered_features", []),
                }
            )

        return metadata

    @staticmethod
    def format_feature_list(
        features: List[FeatureSpec],
        max_features: Optional[int] = None,
        include_priority: bool = True,
    ) -> str:
        """
        Format feature list for display or logging.

        Args:
            features: List of FeatureSpec objects
            max_features: Maximum number of features to include (None = all)
            include_priority: Include priority in output

        Returns:
            Formatted string with feature list
        """
        features_to_show = features[:max_features] if max_features else features

        lines = []
        for f in features_to_show:
            if include_priority:
                lines.append(f"- {f.id}: {f.name} (Priority: {f.priority})")
            else:
                lines.append(f"- {f.id}: {f.name}")

        if max_features and len(features) > max_features:
            lines.append(f"... and {len(features) - max_features} more features")

        return "\n".join(lines)

    @staticmethod
    def format_data_model_list(
        data_models: List[DataModel], max_models: Optional[int] = None, max_attributes: int = 5
    ) -> str:
        """
        Format data model list for display or logging.

        Args:
            data_models: List of DataModel objects
            max_models: Maximum number of models to include (None = all)
            max_attributes: Maximum number of attributes to show per model

        Returns:
            Formatted string with data model list
        """
        models_to_show = data_models[:max_models] if max_models else data_models

        lines = []
        for dm in models_to_show:
            attr_names = [attr.name for attr in dm.attributes[:max_attributes]]
            attr_str = ", ".join(attr_names)
            if len(dm.attributes) > max_attributes:
                attr_str += f", ... ({len(dm.attributes) - max_attributes} more)"
            lines.append(f"- {dm.entity_name}: {attr_str}")

        if max_models and len(data_models) > max_models:
            lines.append(f"... and {len(data_models) - max_models} more models")

        return "\n".join(lines)
