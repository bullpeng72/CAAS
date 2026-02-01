"""
Hierarchical Feature Extraction

Phase 0 Enhancement: Complete and comprehensive feature extraction
from requirements using hierarchical decomposition.
"""

from typing import List, Optional
import logging

from caas_framework.models.specifications import FeatureSpec
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils import ResponseParser, PromptBuilder
from caas_framework.config.settings import LLMConstants


logger = logging.getLogger(__name__)


class HierarchicalFeatureExtractor:
    """
    계층적 기능 추출기

    요구사항에서 모든 기능을 빠짐없이 추출하기 위해
    계층적 분해 방식을 사용합니다.

    Process:
    1. 주요 기능 영역 식별 (예: 인증, 게시판, 댓글)
    2. 각 영역별로 상세 기능 추출
    3. 누락 기능 교차 검증
    4. 우선순위 및 의존성 설정
    """

    def __init__(self, llm_plugin: LLMPlugin):
        """
        Args:
            llm_plugin: LLM plugin for feature extraction
        """
        self.llm = llm_plugin
        self.logger = logging.getLogger(__name__)

    async def extract_complete_features(
        self,
        requirement: str,
        domain: Optional[str] = None
    ) -> List[FeatureSpec]:
        """
        모든 기능을 계층적으로 추출

        Args:
            requirement: Natural language requirement
            domain: Optional domain hint

        Returns:
            Complete list of features
        """
        self.logger.info("Starting hierarchical feature extraction...")

        # Step 1: 주요 기능 영역 식별
        self.logger.info("Step 1/4: Identifying functional areas...")
        functional_areas = await self._identify_functional_areas(requirement, domain)
        self.logger.info(f"Found {len(functional_areas)} functional areas: {functional_areas}")

        all_features = []

        # Step 2: 각 영역별로 상세 기능 추출
        self.logger.info("Step 2/4: Extracting features per area...")
        for area in functional_areas:
            self.logger.info(f"Extracting features for area: {area}")
            area_features = await self._extract_area_features(
                requirement, area, domain
            )
            self.logger.info(f"Found {len(area_features)} features in {area}")
            all_features.extend(area_features)

        # Step 3: 누락 기능 검증 (교차 검증)
        self.logger.info("Step 3/4: Verifying completeness...")
        missing_features = await self._verify_completeness(
            requirement, all_features
        )

        if missing_features:
            self.logger.warning(f"Found {len(missing_features)} missing features")
            for feature in missing_features:
                self.logger.warning(f"  - {feature.name}: {feature.description}")
            all_features.extend(missing_features)
        else:
            self.logger.info("No missing features detected")

        # Step 4: 우선순위 및 의존성 설정
        self.logger.info("Step 4/4: Prioritizing features...")
        prioritized_features = self._prioritize_features(all_features)

        self.logger.info(f"✓ Extracted {len(prioritized_features)} total features")
        return prioritized_features

    async def _identify_functional_areas(
        self,
        requirement: str,
        domain: Optional[str] = None
    ) -> List[str]:
        """
        주요 기능 영역 식별

        Args:
            requirement: Natural language requirement
            domain: Optional domain hint

        Returns:
            List of functional area names
        """
        prompt = PromptBuilder(
            "identify all functional areas from requirements"
        ).add_task(
            """You are an expert requirements analyst.
Identify ALL major functional areas from the given requirements.

Each functional area should be a distinct category of features.
Examples: User Authentication, Content Management, Payment Processing, etc.

Be comprehensive - don't miss any area mentioned in the requirements."""
        ).add_input(
            requirement=requirement,
            domain=domain or "General"
        ).add_output_format(
            {
                "functional_areas": [
                    "Area Name 1",
                    "Area Name 2"
                ]
            },
            "Return all functional areas in JSON format:"
        ).add_guidelines([
            "Use clear, descriptive names for each area",
            "Each area should represent a cohesive set of features",
            "Include all areas mentioned or implied in the requirements",
            "Use noun phrases (e.g., 'User Management' not 'Manage Users')",
            "Return only valid JSON"
        ]).build()

        response = await self.llm.ainvoke(
            messages=[{"role": "user", "content": prompt}],
            response_format=LLMConstants.RESPONSE_FORMAT_JSON,
            temperature=LLMConstants.TEMPERATURE_BALANCED
        )

        result = ResponseParser.parse_structured_response(
            response,
            expected_fields=['functional_areas'],
            fallback_factory=lambda: {"functional_areas": ["General Features"]}
        )

        areas = result.get("functional_areas", ["General Features"])

        # Ensure at least one area
        if not areas:
            areas = ["General Features"]

        return areas

    async def _extract_area_features(
        self,
        requirement: str,
        area: str,
        domain: Optional[str] = None
    ) -> List[FeatureSpec]:
        """
        특정 영역의 모든 기능 추출

        Args:
            requirement: Natural language requirement
            area: Functional area name
            domain: Optional domain hint

        Returns:
            List of features for this area
        """
        prompt = PromptBuilder(
            f"extract all features for the '{area}' functional area"
        ).add_task(
            f"""You are an expert requirements analyst.
Extract ALL features related to "{area}" from the given requirements.

For each feature, provide:
1. Unique ID (snake_case, descriptive)
2. Feature name (clear, concise)
3. Detailed description
4. Input data required
5. Output data produced
6. Priority (high/medium/low)

Be thorough - extract every feature related to {area}, even if small."""
        ).add_input(
            requirement=requirement,
            functional_area=area,
            domain=domain or "General"
        ).add_output_format(
            {
                "features": [
                    {
                        "id": "user_login",
                        "name": "User Login",
                        "description": "Allow users to log in with email and password",
                        "inputs": ["email", "password"],
                        "outputs": ["auth_token", "user_profile"],
                        "priority": "high",
                        "acceptance_criteria": [
                            "User can login with valid credentials",
                            "Invalid credentials show error message"
                        ]
                    }
                ]
            },
            f"Extract all features for {area} in JSON format:"
        ).add_guidelines([
            f"Focus only on features related to {area}",
            "Each feature should be specific and implementable",
            "Include all CRUD operations if applicable",
            "Don't miss edge cases or error handling features",
            "Priority: high = critical, medium = important, low = nice-to-have",
            "Return only valid JSON"
        ]).build()

        response = await self.llm.ainvoke(
            messages=[{"role": "user", "content": prompt}],
            response_format=LLMConstants.RESPONSE_FORMAT_JSON,
            temperature=LLMConstants.TEMPERATURE_BALANCED
        )

        result = ResponseParser.parse_structured_response(
            response,
            expected_fields=['features'],
            fallback_factory=lambda: {"features": []}
        )

        features = []
        for feature_data in result.get("features", []):
            try:
                # Normalize ID
                from caas_framework.utils import TextNormalizer
                feature_id = TextNormalizer.normalize_id(
                    feature_data.get("id", f"{area}_feature")
                )

                # Create FeatureSpec
                feature = FeatureSpec(
                    id=feature_id,
                    name=feature_data.get("name", "Unnamed Feature"),
                    description=feature_data.get("description", ""),
                    priority=feature_data.get("priority", "medium"),
                    acceptance_criteria=feature_data.get("acceptance_criteria", []),
                    functional_requirements=feature_data.get("inputs", []),
                    user_stories=[]
                )

                # Store additional metadata (not in FeatureSpec base model)
                # These will be used by TraceabilityMatrix later
                feature.__dict__['functional_area'] = area
                feature.__dict__['inputs'] = feature_data.get("inputs", [])
                feature.__dict__['outputs'] = feature_data.get("outputs", [])

                features.append(feature)

            except Exception as e:
                self.logger.warning(f"Failed to parse feature: {e}")
                continue

        return features

    async def _verify_completeness(
        self,
        requirement: str,
        extracted_features: List[FeatureSpec]
    ) -> List[FeatureSpec]:
        """
        누락된 기능 검증 (교차 검증)

        Args:
            requirement: Original requirement
            extracted_features: Features extracted so far

        Returns:
            List of missing features (empty if complete)
        """
        # Build summary of extracted features
        features_summary = "\n".join([
            f"- {f.name} ({f.id}): {f.description}"
            for f in extracted_features
        ])

        prompt = PromptBuilder(
            "verify completeness of feature extraction"
        ).add_task(
            """You are an expert requirements auditor.
Compare the original requirements with the extracted features.

Your task is to identify ANY features that are:
1. Mentioned in requirements but NOT in extracted features
2. Implied by requirements but not explicitly extracted
3. Common/standard features for this type of system that are missing

Be critical and thorough. If everything is covered, return empty list."""
        ).add_input(
            original_requirement=requirement
        ).add_context(
            "Extracted Features",
            features_summary
        ).add_output_format(
            {
                "missing_features": [
                    {
                        "id": "feature_id",
                        "name": "Feature Name",
                        "description": "Detailed description",
                        "reason": "Why this feature was missed",
                        "priority": "high"
                    }
                ],
                "analysis": "Brief explanation of completeness"
            },
            "Identify missing features in JSON format:"
        ).add_guidelines([
            "Be thorough - check for any gaps",
            "Consider edge cases and error handling",
            "Think about security, validation, and non-functional aspects",
            "If no features are missing, return empty array",
            "Return only valid JSON"
        ]).build()

        response = await self.llm.ainvoke(
            messages=[{"role": "user", "content": prompt}],
            response_format=LLMConstants.RESPONSE_FORMAT_JSON,
            temperature=LLMConstants.TEMPERATURE_PRECISE  # Lower temperature for accuracy
        )

        result = ResponseParser.parse_structured_response(
            response,
            expected_fields=['missing_features'],
            fallback_factory=lambda: {"missing_features": []}
        )

        missing = []
        for feature_data in result.get("missing_features", []):
            try:
                from caas_framework.utils import TextNormalizer
                feature_id = TextNormalizer.normalize_id(
                    feature_data.get("id", "missing_feature")
                )

                feature = FeatureSpec(
                    id=feature_id,
                    name=feature_data.get("name", "Missing Feature"),
                    description=feature_data.get("description", ""),
                    priority=feature_data.get("priority", "high"),  # Missing features are high priority
                    acceptance_criteria=[
                        f"Reason missed: {feature_data.get('reason', 'Unknown')}"
                    ]
                )

                feature.__dict__['functional_area'] = "Additional Features"
                feature.__dict__['missed_reason'] = feature_data.get('reason', 'Unknown')

                missing.append(feature)

            except Exception as e:
                self.logger.warning(f"Failed to parse missing feature: {e}")
                continue

        # Log analysis
        analysis = result.get("analysis", "")
        if analysis:
            self.logger.info(f"Completeness analysis: {analysis}")

        return missing

    def _prioritize_features(
        self,
        features: List[FeatureSpec]
    ) -> List[FeatureSpec]:
        """
        우선순위 및 의존성 설정

        Args:
            features: List of features

        Returns:
            Prioritized and sorted features
        """
        # Priority mapping for sorting
        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3
        }

        # Sort by priority
        sorted_features = sorted(
            features,
            key=lambda f: priority_order.get(f.priority.lower(), 2)
        )

        # Log priority distribution
        priority_dist = {}
        for feature in sorted_features:
            priority = feature.priority.lower()
            priority_dist[priority] = priority_dist.get(priority, 0) + 1

        self.logger.info("Feature priority distribution:")
        for priority, count in sorted(priority_dist.items(), key=lambda x: priority_order.get(x[0], 2)):
            self.logger.info(f"  - {priority}: {count} features")

        return sorted_features
