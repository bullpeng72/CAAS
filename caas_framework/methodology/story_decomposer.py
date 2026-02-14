"""
Story Decomposition Engine for CAAS-E

Converts epics into manageable stories following BMAD methodology:
- 1 Epic = 5-10 Stories
- 1 Story = 3-7 Features
- Story dependency detection
- Complexity estimation

Author: CAAS Framework Team
Version: 0.6.0 (CAAS-E Implementation)
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.exceptions import AgentExecutionError
import logging
import json
import re

logger = logging.getLogger(__name__)


@dataclass
class Story:
    """Represents a user story in BMAD methodology"""
    id: str
    name: str
    description: str
    features: List[str] = field(default_factory=list)  # Feature IDs
    dependencies: List[str] = field(default_factory=list)  # Story IDs this depends on
    estimated_complexity: str = "medium"  # low, medium, high
    acceptance_criteria: List[str] = field(default_factory=list)
    business_value: str = "medium"  # low, medium, high

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "features": self.features,
            "dependencies": self.dependencies,
            "estimated_complexity": self.estimated_complexity,
            "acceptance_criteria": self.acceptance_criteria,
            "business_value": self.business_value
        }


@dataclass
class Epic:
    """Represents an epic (collection of stories)"""
    name: str
    description: str
    estimated_features: int
    recommended_stories: int
    stories: List[Story] = field(default_factory=list)
    business_value: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "epic": {
                "name": self.name,
                "description": self.description,
                "estimated_features": self.estimated_features,
                "recommended_stories": self.recommended_stories,
                "business_value": self.business_value
            },
            "stories": [s.to_dict() for s in self.stories]
        }


class StoryDecomposer:
    """
    Decomposes large requirements (epics) into smaller stories.

    Algorithm:
    1. Estimate total feature count from requirement text
    2. If features > 15, recommend story decomposition
    3. Use LLM to identify feature clusters (related features)
    4. Group clusters into stories (3-7 features per story)
    5. Detect story dependencies based on feature relationships
    6. Estimate complexity based on feature count and type
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        max_features_per_story: int = 5,
        max_stories_per_epic: int = 10,
        logger: Optional[logging.Logger] = None
    ):
        self.llm = llm_plugin
        self.max_features_per_story = max_features_per_story
        self.max_stories_per_epic = max_stories_per_epic
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    async def decompose_epic(
        self,
        requirement_text: str,
        domain_hint: Optional[str] = None
    ) -> Epic:
        """
        Main entry point for epic decomposition.

        Args:
            requirement_text: Natural language requirement
            domain_hint: Optional domain hint (e.g., "e_commerce", "healthcare")

        Returns:
            Epic object with decomposed stories

        Raises:
            AgentExecutionError: If decomposition fails
        """
        try:
            # Step 1: Estimate feature count
            feature_count = await self._estimate_feature_count(requirement_text)
            self.logger.info(f"Estimated {feature_count} features in requirement")

            # Step 2: Decide if decomposition needed
            if feature_count <= self.max_features_per_story:
                # Small enough for single story
                self.logger.info("Requirement small enough for single story")
                return await self._create_single_story_epic(requirement_text, domain_hint)

            # Step 3: Extract feature list
            self.logger.info("Extracting features from requirement")
            features = await self._extract_features(requirement_text, domain_hint)

            if not features:
                self.logger.warning("No features extracted, creating single story")
                return await self._create_single_story_epic(requirement_text, domain_hint)

            # Step 4: Cluster features into stories
            self.logger.info(f"Clustering {len(features)} features into stories")
            stories = await self._cluster_features_into_stories(features)

            # Step 5: Detect dependencies
            self.logger.info("Detecting story dependencies")
            stories = await self._detect_story_dependencies(stories)

            # Step 6: Create epic
            epic_name = await self._extract_epic_name(requirement_text)
            business_value = await self._estimate_business_value(requirement_text)

            epic = Epic(
                name=epic_name,
                description=requirement_text[:500] + ("..." if len(requirement_text) > 500 else ""),
                estimated_features=len(features),
                recommended_stories=len(stories),
                stories=stories,
                business_value=business_value
            )

            self.logger.info(f"Epic decomposed into {len(stories)} stories")
            return epic

        except Exception as e:
            self.logger.error(f"Epic decomposition failed: {e}")
            raise AgentExecutionError(
                f"Failed to decompose epic: {e}",
                details={"requirement_text": requirement_text[:200]}
            ) from e

    async def _estimate_feature_count(self, requirement_text: str) -> int:
        """Use LLM to estimate number of features in requirement"""
        prompt = f"""Analyze this requirement and estimate the number of distinct features it contains.

Requirement:
{requirement_text}

Count each distinct user-facing capability as one feature.
Examples of features: "user login", "product search", "payment processing", "order tracking".

Return ONLY a JSON object:
{{
  "estimated_features": <number>,
  "reasoning": "<brief explanation>"
}}"""

        try:
            response = await self.llm.ainvoke(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )

            # Parse JSON response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return max(1, data.get("estimated_features", 10))

        except Exception as e:
            self.logger.warning(f"Feature count estimation failed, using heuristic: {e}")

        # Fallback: heuristic estimation (rough estimate)
        word_count = len(requirement_text.split())
        estimated = max(1, word_count // 20)
        self.logger.info(f"Heuristic feature estimate: {estimated} (based on {word_count} words)")
        return estimated

    async def _extract_features(
        self,
        requirement_text: str,
        domain_hint: Optional[str]
    ) -> List[Dict]:
        """Extract explicit feature list from requirement"""
        prompt = f"""Extract distinct features from this requirement.

Requirement:
{requirement_text}

Domain: {domain_hint or "General"}

Return a JSON array of features:
[
  {{
    "id": "feature_1",
    "name": "Feature Name",
    "description": "Brief description",
    "category": "authentication|data|ui|integration|business_logic"
  }},
  ...
]

Each feature should be a distinct user-facing capability.
Aim for {self.max_features_per_story * 3} to {self.max_features_per_story * 7} features maximum."""

        try:
            response = await self.llm.ainvoke(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=2000
            )

            # Parse JSON array
            json_match = re.search(r'\[.*\]', response.content, re.DOTALL)
            if json_match:
                features = json.loads(json_match.group())
                self.logger.info(f"Extracted {len(features)} features")
                return features

        except Exception as e:
            self.logger.warning(f"Feature extraction failed: {e}")

        return []

    async def _cluster_features_into_stories(
        self,
        features: List[Dict]
    ) -> List[Story]:
        """
        Group features into stories based on:
        - Related functionality
        - Technical dependencies
        - User workflows

        Constraints:
        - 3-7 features per story (ideal: 3-5)
        - Similar categories clustered together
        """
        prompt = f"""Group these features into user stories.

Features:
{json.dumps(features, indent=2)}

Constraints:
- Each story should have 3-7 features (ideal: 3-5)
- Group related features together
- Consider technical dependencies
- Aim for {self.max_stories_per_epic} or fewer stories
- Use clear, concise story names (3-6 words)

Return JSON:
{{
  "stories": [
    {{
      "id": "story_1",
      "name": "Story Name",
      "description": "What this story delivers",
      "feature_ids": ["feature_1", "feature_2"],
      "estimated_complexity": "low|medium|high",
      "acceptance_criteria": ["criterion 1", "criterion 2"],
      "business_value": "low|medium|high"
    }}
  ]
}}"""

        try:
            response = await self.llm.ainvoke(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=3000
            )

            # Parse response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                stories = []

                for s in data.get("stories", []):
                    story = Story(
                        id=s.get("id", f"story_{len(stories) + 1}"),
                        name=s.get("name", "Unnamed Story"),
                        description=s.get("description", ""),
                        features=s.get("feature_ids", []),
                        dependencies=[],  # Will be filled in next step
                        estimated_complexity=s.get("estimated_complexity", "medium"),
                        acceptance_criteria=s.get("acceptance_criteria", []),
                        business_value=s.get("business_value", "medium")
                    )
                    stories.append(story)

                self.logger.info(f"Clustered features into {len(stories)} stories")
                return stories

        except Exception as e:
            self.logger.warning(f"Feature clustering failed: {e}")

        # Fallback: create single story with all features
        return [
            Story(
                id="story_1",
                name="Main Story",
                description="Primary functionality",
                features=[f.get("id", f"feature_{i}") for i, f in enumerate(features)],
                dependencies=[],
                estimated_complexity="high" if len(features) > 5 else "medium",
                acceptance_criteria=[],
                business_value="high"
            )
        ]

    async def _detect_story_dependencies(
        self,
        stories: List[Story]
    ) -> List[Story]:
        """Detect which stories depend on others"""
        if len(stories) <= 1:
            return stories

        prompt = f"""Analyze story dependencies.

Stories:
{json.dumps([{
    "id": s.id,
    "name": s.name,
    "features": s.features
} for s in stories], indent=2)}

Identify which stories depend on others (must be implemented first).
For example, "Shopping Cart" depends on "User Authentication" and "Product Catalog".

Return JSON:
{{
  "dependencies": [
    {{"story_id": "story_3", "depends_on": ["story_1", "story_2"]}},
    ...
  ]
}}

If no dependencies, return empty array."""

        try:
            response = await self.llm.ainvoke(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )

            # Parse dependencies
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                dep_map = {
                    dep["story_id"]: dep["depends_on"]
                    for dep in data.get("dependencies", [])
                }

                # Update story objects
                for story in stories:
                    story.dependencies = dep_map.get(story.id, [])

                deps_count = sum(1 for s in stories if s.dependencies)
                self.logger.info(f"Detected dependencies for {deps_count} stories")

        except Exception as e:
            self.logger.warning(f"Dependency detection failed: {e}")

        return stories

    async def _create_single_story_epic(
        self,
        requirement_text: str,
        domain_hint: Optional[str]
    ) -> Epic:
        """For small requirements, create a single-story epic"""
        epic_name = await self._extract_epic_name(requirement_text)
        feature_count = await self._estimate_feature_count(requirement_text)
        business_value = await self._estimate_business_value(requirement_text)

        story = Story(
            id="story_1",
            name=epic_name,
            description=requirement_text[:200] + ("..." if len(requirement_text) > 200 else ""),
            features=[],  # Will be filled by Phase 0 (Golden Data)
            dependencies=[],
            estimated_complexity="low" if feature_count <= 3 else "medium",
            acceptance_criteria=[],
            business_value=business_value
        )

        return Epic(
            name=epic_name,
            description=requirement_text[:500] + ("..." if len(requirement_text) > 500 else ""),
            estimated_features=feature_count,
            recommended_stories=1,
            stories=[story],
            business_value=business_value
        )

    async def _extract_epic_name(self, requirement_text: str) -> str:
        """Extract a concise epic/story name"""
        prompt = f"""Generate a concise name (3-6 words) for this requirement:

{requirement_text[:300]}

Return ONLY the name, no quotes or extra text.
Examples: "E-Commerce Platform", "User Authentication System", "Data Analytics Dashboard"""

        try:
            response = await self.llm.ainvoke(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=50
            )

            name = response.content.strip().strip('"\'')
            if len(name) > 100:  # Sanity check
                name = name[:100]

            return name

        except Exception as e:
            self.logger.warning(f"Epic name extraction failed: {e}")
            return "Project Epic"

    async def _estimate_business_value(self, requirement_text: str) -> str:
        """Estimate business value (low/medium/high)"""
        # Keywords indicating high business value
        high_value_keywords = ["critical", "essential", "important", "revenue", "customer", "core", "primary"]
        medium_value_keywords = ["useful", "beneficial", "helpful", "improve", "enhance"]

        text_lower = requirement_text.lower()

        high_count = sum(1 for kw in high_value_keywords if kw in text_lower)
        medium_count = sum(1 for kw in medium_value_keywords if kw in text_lower)

        if high_count >= 2:
            return "high"
        elif medium_count >= 2 or high_count >= 1:
            return "medium"
        else:
            return "low"


def topological_sort(stories: List[Story]) -> List[Story]:
    """
    Sort stories by dependencies (topological order).

    Stories with no dependencies come first.
    """
    from collections import deque

    if not stories:
        return []

    # Build in-degree map
    in_degree = {s.id: len(s.dependencies) for s in stories}
    story_map = {s.id: s for s in stories}

    # Queue for stories with no dependencies
    queue = deque([s for s in stories if in_degree[s.id] == 0])
    result = []

    while queue:
        story = queue.popleft()
        result.append(story)

        # Reduce in-degree for dependent stories
        for other in stories:
            if story.id in other.dependencies:
                in_degree[other.id] -= 1
                if in_degree[other.id] == 0:
                    queue.append(other)

    # Check for cycles (if result length < stories length)
    if len(result) < len(stories):
        # Add remaining stories (circular dependencies)
        remaining = [s for s in stories if s not in result]
        logger.warning(f"Circular dependencies detected in {len(remaining)} stories")
        result.extend(remaining)

    return result
