"""
Golden Data Pipeline

Phase 0: Requirement Concretization
Converts natural language requirements into structured Golden Data.
"""

from typing import Any, Dict, Optional
import json
import logging

from caas_framework.models.specifications import (
    ConcretizedRequirement,
    FeatureSpec,
    DataModel,
    UIComponent,
    NonFunctionalRequirements,
    BoundariesSpec,
    CommandsSpec,
    CodeStyleSpec,
    GitWorkflowSpec,
)
from caas_framework.plugins.llm.base import LLMPlugin


class RequirementConcretizer:
    """
    Requirement Concretizer

    Converts natural language requirements into structured Golden Data
    using LLM-based extraction and analysis.
    """

    def __init__(self, llm_plugin: LLMPlugin):
        """
        Args:
            llm_plugin: LLM plugin for text generation
        """
        self.llm = llm_plugin
        self.logger = logging.getLogger(__name__)

    async def concretize(
        self,
        requirement: str,
        domain: Optional[str] = None
    ) -> ConcretizedRequirement:
        """
        Concretize requirement into Golden Data.

        Args:
            requirement: Natural language requirement
            domain: Optional domain hint

        Returns:
            ConcretizedRequirement (Golden Data)
        """
        # Build prompt for LLM
        prompt = self._build_concretization_prompt(requirement, domain)

        # Call LLM
        response = await self.llm.ainvoke(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        # Parse response
        if isinstance(response, dict):
            result_text = response.get("content", "")
        else:
            # LLMResponse object with .content attribute
            result_text = response.content if hasattr(response, 'content') else str(response)

        # Debug logging
        self.logger.debug(f"LLM response type: {type(response)}")
        self.logger.debug(f"LLM response text (first 500 chars): {result_text[:500]}")

        # Extract JSON from response
        try:
            # Try to parse as JSON
            result_data = json.loads(result_text)
            self.logger.debug("Successfully parsed JSON directly")
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON decode error: {e}")
            # If not valid JSON, try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL)
            if json_match:
                self.logger.debug("Found JSON in markdown code block")
                result_data = json.loads(json_match.group(1))
            else:
                self.logger.error(f"Failed to parse LLM response. Full response: {result_text[:1000]}")
                # Fallback: create minimal structure
                result_data = {
                    "domain": domain or "GENERAL",
                    "project_name": "Generated Project",
                    "description": requirement[:200],
                    "features": [],
                }

        # Convert to ConcretizedRequirement
        golden_data = self._parse_golden_data(result_data, requirement, domain)

        return golden_data

    def _build_concretization_prompt(self, requirement: str, domain: Optional[str]) -> str:
        """Build prompt for requirement concretization."""
        prompt = f"""당신은 요구사항 분석 전문가입니다. 다음 요구사항을 분석하여 구조화된 정보를 추출하세요.

**중요: 모든 텍스트 값을 한국어로 작성하세요. JSON 키(key)는 영어로 유지하되, 값(value)은 반드시 한국어로 작성하세요.**

요구사항:
{requirement}

{f"도메인: {domain}" if domain else ""}

다음 정보를 JSON 형식으로 추출하세요 (모든 텍스트 값은 한국어로):
{{
    "domain": "도메인 이름 (예: E-COMMERCE, HEALTHCARE, FINANCE)",
    "project_name": "간결한 프로젝트 이름",
    "description": "명확한 프로젝트 설명",
    "features": [
        {{
            "id": "F1",
            "name": "기능 이름",
            "description": "상세한 설명",
            "priority": "low|medium|high|critical",
            "acceptance_criteria": ["기준 1", "기준 2"]
        }}
    ],
    "data_models": [
        {{
            "entity_name": "엔티티 이름 (예: User, Product)",
            "attributes": ["속성1", "속성2"],
            "relationships": ["관계 설명"]
        }}
    ],
    "ui_components": [
        {{
            "page_name": "페이지 이름",
            "component_type": "form|table|chart|etc",
            "description": "컴포넌트 설명"
        }}
    ],
    "non_functional_requirements": {{
        "security": "보안 요구사항이 있다면",
        "scalability": "확장성 요구사항이 있다면",
        "performance": "성능 요구사항이 있다면",
        "reliability": "신뢰성 요구사항이 있다면"
    }},
    "workflow_type": "sequential|hierarchical|parallel",
    "deployment_target": "docker|kubernetes|etc",
    "boundaries": {{
        "always_allowed": ["읽기 작업", "기본 CRUD 작업", "로깅"],
        "ask_first": ["파일 작업", "네트워크 호출", "데이터베이스 변경", "외부 API 호출"],
        "never_allowed": ["시스템 명령 실행", "임의 코드 실행", "rm -rf", "파일 시스템 전체 삭제"]
    }},
    "commands": {{
        "install": "pip install -r requirements.txt",
        "test": "pytest tests/",
        "run": "python main.py",
        "lint": "pylint src/",
        "format": "black src/",
        "build": "도커 빌드 명령어가 필요하면",
        "deploy": "배포 명령어가 필요하면"
    }},
    "code_style": {{
        "formatter": "black",
        "line_length": 88,
        "use_type_hints": true,
        "docstring_style": "google",
        "import_order": "isort"
    }},
    "git_workflow": {{
        "branch_naming": "feature/{{issue-number}}-{{description}}",
        "commit_message_format": "<type>(<scope>): <subject>",
        "requires_pr": true,
        "main_branch": "main"
    }}
}}

중요 사항:
- 요구사항에 언급된 모든 기능을 추출하세요
- 데이터 엔티티와 관계를 식별하세요
- 해당되는 경우 UI 컴포넌트를 결정하세요
- 언급된 경우 비기능적 요구사항을 명시하세요
- **보안 경계(boundaries)는 반드시 설정하세요** - 이것은 매우 중요합니다!
  * always_allowed: 항상 허용되는 안전한 작업
  * ask_first: 사용자 승인이 필요한 작업
  * never_allowed: 절대 금지된 위험한 작업
- 프로젝트 명령어(commands)를 명시하세요 (설치, 테스트, 실행, 린트, 포맷)
- 코드 스타일(code_style) 가이드라인을 설정하세요
- Git 워크플로우(git_workflow) 규칙을 정의하세요
- 철저하고 정확하게 작성하세요
- **모든 name, description, acceptance_criteria 등의 값은 한국어로 작성하세요**

오직 유효한 JSON만 반환하고, 추가 텍스트는 포함하지 마세요."""

        return prompt

    def _parse_golden_data(
        self,
        data: Dict[str, Any],
        original_requirement: str,
        domain: Optional[str]
    ) -> ConcretizedRequirement:
        """Parse LLM response into ConcretizedRequirement."""

        # Parse features
        features = []
        for i, f_data in enumerate(data.get("features", [])):
            feature = FeatureSpec(
                id=f_data.get("id", f"F{i+1}"),
                name=f_data.get("name", f"Feature {i+1}"),
                description=f_data.get("description", ""),
                priority=f_data.get("priority", "medium"),
                acceptance_criteria=f_data.get("acceptance_criteria", [])
            )
            features.append(feature)

        # Parse data models
        data_models = []
        for dm_data in data.get("data_models", []):
            data_model = DataModel(
                entity_name=dm_data.get("entity_name", ""),
                attributes=dm_data.get("attributes", []),
                relationships=dm_data.get("relationships", [])
            )
            data_models.append(data_model)

        # Parse UI components
        ui_components = []
        for ui_data in data.get("ui_components", []):
            ui_comp = UIComponent(
                page_name=ui_data.get("page_name", ""),
                component_type=ui_data.get("component_type", ""),
                description=ui_data.get("description", "")
            )
            ui_components.append(ui_comp)

        # Parse NFRs
        nfr_data = data.get("non_functional_requirements", {})
        nfr = NonFunctionalRequirements(
            security=nfr_data.get("security"),
            scalability=nfr_data.get("scalability"),
            performance=nfr_data.get("performance"),
            reliability=nfr_data.get("reliability")
        )

        # Parse Boundaries (CRITICAL for security)
        boundaries_data = data.get("boundaries", {})
        boundaries = BoundariesSpec(
            always_allowed=boundaries_data.get("always_allowed", [
                "읽기 작업",
                "기본 CRUD 작업",
                "로깅"
            ]),
            ask_first=boundaries_data.get("ask_first", [
                "파일 작업",
                "네트워크 호출",
                "데이터베이스 변경",
                "외부 API 호출"
            ]),
            never_allowed=boundaries_data.get("never_allowed", [
                "시스템 명령 실행",
                "임의 코드 실행",
                "rm -rf",
                "파일 시스템 전체 삭제"
            ])
        )

        # Parse Commands
        commands_data = data.get("commands", {})
        commands = CommandsSpec(
            install=commands_data.get("install", "pip install -r requirements.txt"),
            test=commands_data.get("test", "pytest tests/"),
            run=commands_data.get("run", "python main.py"),
            lint=commands_data.get("lint", "pylint src/"),
            format=commands_data.get("format", "black src/"),
            build=commands_data.get("build"),
            deploy=commands_data.get("deploy")
        )

        # Parse Code Style
        code_style_data = data.get("code_style", {})
        code_style = CodeStyleSpec(
            formatter=code_style_data.get("formatter", "black"),
            line_length=code_style_data.get("line_length", 88),
            use_type_hints=code_style_data.get("use_type_hints", True),
            docstring_style=code_style_data.get("docstring_style", "google"),
            import_order=code_style_data.get("import_order", "isort")
        )

        # Parse Git Workflow
        git_workflow_data = data.get("git_workflow", {})
        git_workflow = GitWorkflowSpec(
            branch_naming=git_workflow_data.get("branch_naming", "feature/{issue-number}-{description}"),
            commit_message_format=git_workflow_data.get("commit_message_format", "<type>(<scope>): <subject>"),
            requires_pr=git_workflow_data.get("requires_pr", True),
            main_branch=git_workflow_data.get("main_branch", "main")
        )

        # Create ConcretizedRequirement
        golden_data = ConcretizedRequirement(
            domain=data.get("domain", domain or "GENERAL"),
            project_name=data.get("project_name", "Generated Project"),
            description=data.get("description", original_requirement[:200]),
            features=features,
            data_models=data_models,
            ui_components=ui_components,
            non_functional_requirements=nfr,
            workflow_type=data.get("workflow_type", "sequential"),
            deployment_target=data.get("deployment_target", "docker"),
            boundaries=boundaries,
            commands=commands,
            code_style=code_style,
            git_workflow=git_workflow
        )

        return golden_data


class GoldenDataPipeline:
    """
    Golden Data Pipeline

    End-to-end pipeline for generating Golden Data from requirements.
    Includes validation and refinement steps.
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        use_hierarchical_extraction: bool = True
    ):
        """
        Args:
            llm_plugin: LLM plugin for generation
            use_hierarchical_extraction: Use hierarchical feature extraction (default: True)
        """
        self.concretizer = RequirementConcretizer(llm_plugin)
        self.use_hierarchical_extraction = use_hierarchical_extraction

        # Initialize hierarchical feature extractor if enabled
        if use_hierarchical_extraction:
            from caas_framework.bmad.feature_extraction import HierarchicalFeatureExtractor
            self.feature_extractor = HierarchicalFeatureExtractor(llm_plugin)
        else:
            self.feature_extractor = None

    async def generate(
        self,
        requirement: str,
        domain: Optional[str] = None,
        validate: bool = True
    ) -> ConcretizedRequirement:
        """
        Generate Golden Data from requirement.

        Args:
            requirement: Natural language requirement
            domain: Optional domain hint
            validate: Whether to validate the generated data

        Returns:
            ConcretizedRequirement (Golden Data)
        """
        # Step 1: Concretize
        golden_data = await self.concretizer.concretize(requirement, domain)

        # Step 1.5: Enhanced feature extraction (if enabled)
        if self.use_hierarchical_extraction and self.feature_extractor:
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Using hierarchical feature extraction...")

            # Extract features using hierarchical approach
            enhanced_features = await self.feature_extractor.extract_complete_features(
                requirement=requirement,
                domain=domain or golden_data.domain
            )

            # Replace features with enhanced extraction
            if enhanced_features:
                logger.info(
                    f"Replaced {len(golden_data.features)} features with "
                    f"{len(enhanced_features)} hierarchically extracted features"
                )
                golden_data.features = enhanced_features
            else:
                logger.warning("Hierarchical extraction returned no features, keeping original")

        # Step 2: Validate (optional)
        if validate:
            golden_data = await self._validate_and_refine(golden_data)

        return golden_data

    async def _validate_and_refine(
        self,
        golden_data: ConcretizedRequirement
    ) -> ConcretizedRequirement:
        """
        Validate and refine Golden Data.

        Args:
            golden_data: Initial Golden Data

        Returns:
            Refined Golden Data
        """
        # Basic validation
        if not golden_data.features:
            raise ValueError("No features extracted from requirement")

        # Ensure unique IDs
        feature_ids = set()
        for i, feature in enumerate(golden_data.features):
            if feature.id in feature_ids:
                feature.id = f"F{i+1}"
            feature_ids.add(feature.id)

        return golden_data
