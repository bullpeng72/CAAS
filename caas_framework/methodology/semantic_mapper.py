"""
Semantic Mapper

Phase 3: Use LLM to semantically map code to features
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from caas_framework.methodology.code_analyzer import FileAnalysis
from caas_framework.config.settings import LLMConstants
from caas_framework.models.specifications import FeatureSpec
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils import PromptBuilder, ResponseParser
from caas_framework.utils.logger import get_logger

logger = get_logger()


@dataclass
class FeatureImplementation:
    """Information about how a feature is implemented"""

    feature_id: str
    feature_name: str

    # Implementation details
    implementing_files: List[str] = field(default_factory=list)
    implementing_functions: List[str] = field(default_factory=list)
    implementing_classes: List[str] = field(default_factory=list)

    # Confidence
    confidence_score: float = 0.0  # 0.0 - 1.0

    # Status
    is_fully_implemented: bool = False
    is_partially_implemented: bool = False
    implementation_percentage: float = 0.0

    # Evidence
    evidence: List[str] = field(default_factory=list)  # Why we think it's implemented


@dataclass
class MappingResult:
    """Result of semantic mapping"""

    feature_implementations: List[FeatureImplementation] = field(default_factory=list)
    unimplemented_features: List[str] = field(default_factory=list)
    implementation_rate: float = 0.0


class SemanticMapper:
    """
    Semantic Mapper

    Uses LLM to analyze code and determine which features are implemented.

    Process:
    1. Extract code structure (functions, classes) via CodeAnalyzer
    2. For each feature, ask LLM if it's implemented in the code
    3. Collect evidence and confidence scores
    4. Return mapping with confidence levels
    """

    def __init__(self, llm_plugin: LLMPlugin):
        """
        Initialize semantic mapper

        Args:
            llm_plugin: LLM plugin for semantic analysis
        """
        self.llm = llm_plugin
        self.logger = get_logger()

        # Translation map for common English-Korean feature/agent terms
        self._translation_map = {
            # Feature names
            "keyword input": [
                "키워드 입력",
                "키워드입력",
                "keyword",
                "사용자 인터페이스",
            ],
            "internet search": [
                "인터넷 검색",
                "인터넷검색",
                "웹 검색",
                "search",
                "인터넷 정보 검색",
            ],
            "internet information search": [
                "인터넷 정보 검색",
                "인터넷 검색",
                "정보 검색",
            ],
            "trend report": ["동향 보고서", "트렌드 리포트", "보고서", "report"],
            "trend report generation": [
                "동향 보고서 작성",
                "보고서 생성",
                "리포트 생성",
            ],
            "trend report display": ["보고서 표시", "보고서 보여주기", "결과 표시"],
            "keyword validation": [
                "키워드 검증",
                "키워드 유효성",
                "validation",
                "검증",
            ],
            "report generation": ["보고서 작성", "보고서 생성", "리포트 생성"],
            "data research": ["데이터 조사", "데이터 리서치", "자료 조사"],
            "data investigation": ["데이터 조사", "자료 조사"],
            "error handling": ["오류 처리", "에러 처리", "예외 처리"],
            "security": ["보안", "시큐리티"],
            "user interface": ["사용자 인터페이스", "UI", "인터페이스"],
            # Agent roles (including "관리자" manager variants)
            "user agent": [
                "사용자 대리자",
                "사용자 에이전트",
                "유저 에이전트",
                "사용자 인터페이스 관리자",
            ],
            "validation agent": ["검증 대리자", "검증 에이전트", "키워드 검증 관리자"],
            "research agent": ["조사 대리자", "조사 에이전트", "리서치 에이전트"],
            "report agent": [
                "보고서 작성 대리자",
                "보고서 에이전트",
                "보고서 작성 관리자",
            ],
            "search agent": [
                "검색 에이전트",
                "검색 관리자",
                "인터넷 정보 검색 및 보고서 작성 관리자",
            ],
        }

    def _get_translation_variants(self, text: str) -> List[str]:
        """
        Get all translation variants for a given text.
        Enhanced to handle compound terms and common suffixes.

        Args:
            text: Text to get variants for

        Returns:
            List of translation variants including original text
        """
        text_lower = text.lower().strip()
        variants = [text, text_lower]

        # Normalize by removing common suffixes (Korean)
        korean_suffixes = ["관리자", "대리자", "에이전트"]
        text_normalized = text
        for suffix in korean_suffixes:
            if suffix in text:
                text_normalized = text.replace(suffix, "").strip()
                variants.append(text_normalized)

        # Check translation map
        for english, korean_variants in self._translation_map.items():
            # Check if english term is in text
            if english in text_lower:
                variants.extend(korean_variants)

            # Check if any korean variant is in text
            for korean in korean_variants:
                if korean in text or korean in text_normalized:
                    variants.append(english)
                    # Add all other korean variants too
                    variants.extend(korean_variants)

        # Add word-level tokens for better matching
        # Extract Korean and English words
        import re

        korean_words = re.findall(r"[가-힣]+", text)
        english_words = re.findall(r"[a-zA-Z]+", text_lower)

        variants.extend(korean_words)
        variants.extend(english_words)

        return list(set(v for v in variants if v))

    async def map_features_to_code(
        self, features: List[FeatureSpec], code_analyses: Dict[str, FileAnalysis]
    ) -> MappingResult:
        """
        Map features to code using semantic analysis

        Args:
            features: List of features to check
            code_analyses: Analyzed code base

        Returns:
            MappingResult with implementation details
        """
        self.logger.info(f"Starting semantic mapping for {len(features)} features")

        # Check if this is CrewAI code - use specialized mapper
        is_crewai = any(a.is_crewai_code for a in code_analyses.values())
        if is_crewai:
            self.logger.info("Detected CrewAI code, using CrewAI-specific mapper")
            return self._map_features_to_crewai(features, code_analyses)

        feature_implementations = []
        unimplemented = []

        for feature in features:
            self.logger.debug(f"Analyzing feature: {feature.name} ({feature.id})")

            implementation = await self._analyze_feature_implementation(
                feature, code_analyses
            )

            if (
                implementation.is_fully_implemented
                or implementation.is_partially_implemented
            ):
                feature_implementations.append(implementation)
            else:
                unimplemented.append(feature.id)

        # Calculate implementation rate
        total = len(features)
        implemented = len(feature_implementations)
        implementation_rate = (implemented / total * 100) if total > 0 else 0

        result = MappingResult(
            feature_implementations=feature_implementations,
            unimplemented_features=unimplemented,
            implementation_rate=implementation_rate,
        )

        self.logger.info(
            f"Mapping complete: {implemented}/{total} features implemented "
            f"({implementation_rate:.1f}%)"
        )

        return result

    def _map_features_to_crewai(
        self, features: List[FeatureSpec], code_analyses: Dict[str, FileAnalysis]
    ) -> MappingResult:
        """
        Map features to CrewAI agents and tasks (specialized, no LLM needed)

        In CrewAI systems:
        - Agent definitions implement capabilities
        - Task definitions implement executions
        - Agent + Task = Feature Implementation

        Args:
            features: List of features to check
            code_analyses: Analyzed CrewAI code

        Returns:
            MappingResult with CrewAI-specific mappings
        """
        from difflib import SequenceMatcher

        feature_implementations = []
        unimplemented = []

        # Collect all agents and tasks
        all_agents = []
        all_tasks = []
        for file_path, analysis in code_analyses.items():
            for agent in analysis.agent_definitions:
                all_agents.append((file_path, agent))
            for task in analysis.task_definitions:
                all_tasks.append((file_path, task))

        self.logger.info(
            f"Found {len(all_agents)} agents and {len(all_tasks)} tasks in CrewAI code"
        )

        def levenshtein_distance(s1: str, s2: str) -> int:
            """Calculate Levenshtein distance between two strings"""
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)

            previous_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row

            return previous_row[-1]

        def fuzzy_similarity(text1: str, text2: str) -> float:
            """
            Calculate fuzzy similarity using both SequenceMatcher and Levenshtein distance.
            Enhanced with translation-aware matching for bilingual support.
            Returns combined score (0.0 - 1.0)
            """
            text1 = text1.lower().strip()
            text2 = text2.lower().strip()

            # Direct comparison
            seq_ratio = SequenceMatcher(None, text1, text2).ratio()
            max_len = max(len(text1), len(text2))
            if max_len == 0:
                lev_similarity = 1.0
            else:
                lev_distance = levenshtein_distance(text1, text2)
                lev_similarity = 1.0 - (lev_distance / max_len)

            direct_score = seq_ratio * 0.6 + lev_similarity * 0.4

            # Check translation variants for better matching
            variants1 = self._get_translation_variants(text1)
            variants2 = self._get_translation_variants(text2)

            best_variant_score = 0.0
            for v1 in variants1:
                for v2 in variants2:
                    v1_lower = v1.lower().strip()
                    v2_lower = v2.lower().strip()

                    # Check for exact substring match first
                    if v1_lower in v2_lower or v2_lower in v1_lower:
                        variant_score = 0.9  # High score for substring match
                    else:
                        # Fuzzy match on variants
                        var_seq_ratio = SequenceMatcher(
                            None, v1_lower, v2_lower
                        ).ratio()
                        var_max_len = max(len(v1_lower), len(v2_lower))
                        if var_max_len == 0:
                            var_lev_sim = 1.0
                        else:
                            var_lev_dist = levenshtein_distance(v1_lower, v2_lower)
                            var_lev_sim = 1.0 - (var_lev_dist / var_max_len)
                        variant_score = var_seq_ratio * 0.6 + var_lev_sim * 0.4

                    best_variant_score = max(best_variant_score, variant_score)

            # Use best score between direct and variant matching
            final_score = max(direct_score, best_variant_score)

            return final_score

        for feature in features:
            # Match feature to agents and tasks
            best_agent_match = None
            best_agent_score = 0.0
            best_agent_file = None

            best_task_match = None
            best_task_score = 0.0
            best_task_file = None

            # Find best matching agent (using fuzzy matching)
            for file_path, agent in all_agents:
                score = 0.0
                if agent.role:
                    role_score = fuzzy_similarity(feature.name, agent.role)
                    score = max(score, role_score)
                if agent.goal:
                    goal_score = fuzzy_similarity(feature.description, agent.goal)
                    score = max(score, goal_score)

                if score > best_agent_score:
                    best_agent_score = score
                    best_agent_match = agent
                    best_agent_file = file_path

            # Find best matching task (using fuzzy matching)
            for file_path, task in all_tasks:
                score = fuzzy_similarity(feature.description, task.description)
                if task.expected_output:
                    output_score = fuzzy_similarity(
                        feature.description, task.expected_output
                    )
                    score = max(score, output_score)

                if score > best_task_score:
                    best_task_score = score
                    best_task_match = task
                    best_task_file = file_path

            # Determine implementation status with weighted scoring
            # Agent weight: 60%, Task weight: 40%
            combined_score = best_agent_score * 0.6 + best_task_score * 0.4

            # Adjusted thresholds (lowered from 40% to 35%)
            threshold_full = 0.35  # 35% similarity = implemented
            threshold_partial = 0.20  # 20% similarity = partially implemented

            if combined_score >= threshold_full:
                # Fully implemented
                evidence = []
                implementing_files = set()

                evidence.append(
                    f"Combined score: {combined_score:.2f} (Agent: {best_agent_score:.2f} [60%], Task: {best_task_score:.2f} [40%])"
                )

                if best_agent_match:
                    evidence.append(
                        f"✓ Agent '{best_agent_match.role}' matches feature (fuzzy similarity: {best_agent_score:.2f})"
                    )
                    if best_agent_match.goal:
                        evidence.append(f"  Goal: {best_agent_match.goal}")
                    implementing_files.add(best_agent_file)

                if best_task_match:
                    evidence.append(
                        f"✓ Task '{best_task_match.description[:50]}...' matches feature (fuzzy similarity: {best_task_score:.2f})"
                    )
                    implementing_files.add(best_task_file)

                implementation = FeatureImplementation(
                    feature_id=feature.id,
                    feature_name=feature.name,
                    is_fully_implemented=True,
                    is_partially_implemented=False,
                    confidence_score=combined_score,
                    implementation_percentage=100,
                    implementing_files=list(implementing_files),
                    implementing_functions=[],
                    implementing_classes=[],
                    evidence=evidence,
                )
                feature_implementations.append(implementation)

            elif combined_score >= threshold_partial:
                # Partially implemented
                evidence = []
                implementing_files = set()

                evidence.append(
                    f"Partial score: {combined_score:.2f} (Agent: {best_agent_score:.2f} [60%], Task: {best_task_score:.2f} [40%])"
                )

                if best_agent_score >= threshold_partial:
                    evidence.append(
                        f"⚠️  Agent '{best_agent_match.role}' partially matches (fuzzy similarity: {best_agent_score:.2f})"
                    )
                    implementing_files.add(best_agent_file)

                if best_task_score >= threshold_partial:
                    evidence.append(
                        f"⚠️  Task partially matches (fuzzy similarity: {best_task_score:.2f})"
                    )
                    implementing_files.add(best_task_file)

                implementation = FeatureImplementation(
                    feature_id=feature.id,
                    feature_name=feature.name,
                    is_fully_implemented=False,
                    is_partially_implemented=True,
                    confidence_score=combined_score,
                    implementation_percentage=int(combined_score * 100),
                    implementing_files=list(implementing_files),
                    implementing_functions=[],
                    implementing_classes=[],
                    evidence=evidence,
                )
                feature_implementations.append(implementation)

            else:
                # Not implemented
                unimplemented.append(feature.id)

        # Calculate implementation rate
        total = len(features)
        implemented = len(feature_implementations)
        implementation_rate = (implemented / total * 100) if total > 0 else 0

        result = MappingResult(
            feature_implementations=feature_implementations,
            unimplemented_features=unimplemented,
            implementation_rate=implementation_rate,
        )

        self.logger.info(
            f"CrewAI mapping complete: {implemented}/{total} features implemented "
            f"({implementation_rate:.1f}%)"
        )

        return result

    async def _analyze_feature_implementation(
        self, feature: FeatureSpec, code_analyses: Dict[str, FileAnalysis]
    ) -> FeatureImplementation:
        """
        Analyze if a single feature is implemented

        Args:
            feature: Feature to analyze
            code_analyses: Code analysis results

        Returns:
            FeatureImplementation with details
        """
        # Build code summary for LLM
        code_summary = self._build_code_summary(code_analyses)

        # Check if this is CrewAI code
        is_crewai = any(a.is_crewai_code for a in code_analyses.values())

        # Ask LLM if feature is implemented
        task_description = f"""You are a code analyst. Analyze whether the following feature is implemented in the provided code.

Feature to check:
- ID: {feature.id}
- Name: {feature.name}
- Description: {feature.description}
- Acceptance Criteria: {feature.acceptance_criteria}

Analyze the code carefully and determine:
1. Is this feature fully implemented?
2. Is it partially implemented?
3. Which files/functions/classes implement it?
4. What is your confidence level (0.0 - 1.0)?
5. What evidence supports your conclusion?"""

        if is_crewai:
            task_description += """

**IMPORTANT for CrewAI Multi-Agent Systems:**
- In CrewAI, features are implemented through Agent and Task definitions
- An Agent with a matching role/goal implements the feature's capability
- A Task with matching description implements the feature's execution
- Look for Agent() calls with role/goal matching the feature
- Look for Task() calls with description matching the feature
- The combination of Agent + Task = Feature Implementation
- Don't expect traditional API endpoints or CRUD functions
- Example: Feature "Task Creation" → Agent(role="Task Manager") + Task(description="Create task") = IMPLEMENTED"""

        task_description += """

Be thorough but realistic. Don't claim implementation unless you see actual code."""

        guidelines = [
            "Only mark as fully_implemented if ALL acceptance criteria are met",
            "Mark as partially_implemented if some criteria are met",
            "Provide specific evidence from the code",
            "Be conservative with confidence scores",
            "List exact file names, function names, and class names",
        ]

        if is_crewai:
            guidelines.extend(
                [
                    "In CrewAI systems, Agent definitions ARE implementations",
                    "In CrewAI systems, Task definitions ARE implementations",
                    "Match feature descriptions to Agent goals and Task descriptions",
                    "An Agent + Task pair implementing a feature = fully_implemented",
                ]
            )

        guidelines.append("Return only valid JSON")

        prompt = (
            PromptBuilder(f"analyze if feature '{feature.name}' is implemented in code")
            .add_task(task_description)
            .add_context("Code Structure", code_summary)
            .add_output_format(
                {
                    "is_fully_implemented": True,
                    "is_partially_implemented": False,
                    "confidence_score": 0.85,
                    "implementation_percentage": 100,
                    "implementing_files": ["tasks.py"],
                    "implementing_functions": ["add_task", "create_task"],
                    "implementing_classes": ["TaskManager"],
                    "evidence": [
                        "Found add_task function in tasks.py that creates new tasks",
                        "TaskManager class has create_task method matching description",
                    ],
                },
                "Return analysis in JSON format:",
            )
            .add_guidelines(guidelines)
            .build()
        )

        response = await self.llm.ainvoke(
            messages=[{"role": "user", "content": prompt}],
            response_format=LLMConstants.RESPONSE_FORMAT_JSON,
            temperature=LLMConstants.TEMPERATURE_PRECISE,
        )

        result = ResponseParser.parse_structured_response(
            response,
            expected_fields=[
                "is_fully_implemented",
                "is_partially_implemented",
                "confidence_score",
                "implementation_percentage",
            ],
            fallback_factory=lambda: {
                "is_fully_implemented": False,
                "is_partially_implemented": False,
                "confidence_score": 0.0,
                "implementation_percentage": 0,
            },
        )

        # Create FeatureImplementation
        implementation = FeatureImplementation(
            feature_id=feature.id,
            feature_name=feature.name,
            is_fully_implemented=result.get("is_fully_implemented", False),
            is_partially_implemented=result.get("is_partially_implemented", False),
            confidence_score=float(result.get("confidence_score", 0.0)),
            implementation_percentage=float(result.get("implementation_percentage", 0)),
            implementing_files=result.get("implementing_files", []),
            implementing_functions=result.get("implementing_functions", []),
            implementing_classes=result.get("implementing_classes", []),
            evidence=result.get("evidence", []),
        )

        return implementation

    def _build_code_summary(self, code_analyses: Dict[str, FileAnalysis]) -> str:
        """
        Build concise summary of code for LLM

        Args:
            code_analyses: Code analysis results

        Returns:
            String summary of code structure
        """
        lines = []

        # Check if this is CrewAI code
        is_crewai = any(a.is_crewai_code for a in code_analyses.values())
        if is_crewai:
            lines.append("**This is a CrewAI Multi-Agent System**")
            lines.append(
                "Note: In CrewAI systems, features are implemented through Agent and Task definitions."
            )

        for file_path, analysis in code_analyses.items():
            lines.append(f"\n### File: {file_path}")
            lines.append(f"Lines: {analysis.line_count}")

            # Imports
            if analysis.imports:
                lines.append(f"Imports: {', '.join(analysis.imports[:5])}")
                if len(analysis.imports) > 5:
                    lines.append(f"  ... and {len(analysis.imports) - 5} more")

            # CrewAI Agents (IMPORTANT for feature mapping)
            if analysis.agent_definitions:
                lines.append(
                    f"\n**CrewAI Agents ({len(analysis.agent_definitions)}):**"
                )
                for agent in analysis.agent_definitions:
                    lines.append(f"  - Agent: {agent.role or agent.name}")
                    if agent.goal:
                        lines.append(f"    Goal: {agent.goal}")
                    if agent.backstory:
                        lines.append(f"    Backstory: {agent.backstory[:100]}...")

            # CrewAI Tasks (IMPORTANT for feature mapping)
            if analysis.task_definitions:
                lines.append(f"\n**CrewAI Tasks ({len(analysis.task_definitions)}):**")
                for task in analysis.task_definitions[:15]:
                    lines.append(f"  - Task: {task.description[:100]}...")
                    if task.expected_output:
                        lines.append(f"    Expected: {task.expected_output[:80]}...")
                    if task.agent_name:
                        lines.append(f"    Agent: {task.agent_name}")
                if len(analysis.task_definitions) > 15:
                    lines.append(
                        f"  ... and {len(analysis.task_definitions) - 15} more tasks"
                    )

            # Functions
            if analysis.functions:
                lines.append(f"\nFunctions ({len(analysis.functions)}):")
                for func in analysis.functions[:10]:  # Limit to avoid token overflow
                    params = ", ".join(func.parameters)
                    lines.append(f"  - {func.name}({params})")
                    if func.docstring:
                        first_line = func.docstring.split("\n")[0]
                        lines.append(f'    "{first_line}"')
                if len(analysis.functions) > 10:
                    lines.append(f"  ... and {len(analysis.functions) - 10} more")

            # Classes
            if analysis.classes:
                lines.append(f"\nClasses ({len(analysis.classes)}):")
                for cls in analysis.classes[:5]:  # Limit to avoid token overflow
                    lines.append(f"  - class {cls.name}")
                    if cls.docstring:
                        first_line = cls.docstring.split("\n")[0]
                        lines.append(f'    "{first_line}"')
                    if cls.methods:
                        lines.append(
                            f"    Methods: {', '.join(m.name for m in cls.methods[:5])}"
                        )
                        if len(cls.methods) > 5:
                            lines.append(f"    ... and {len(cls.methods) - 5} more")
                if len(analysis.classes) > 5:
                    lines.append(f"  ... and {len(analysis.classes) - 5} more")

        return "\n".join(lines)

    async def find_best_implementation_location(
        self, feature: FeatureSpec, code_analyses: Dict[str, FileAnalysis]
    ) -> Tuple[str, float]:
        """
        Find the best file to implement a feature

        Args:
            feature: Feature to implement
            code_analyses: Existing code structure

        Returns:
            Tuple of (file_path, confidence_score)
        """
        code_summary = self._build_code_summary(code_analyses)

        prompt = (
            PromptBuilder(f"find best location to implement feature '{feature.name}'")
            .add_task(
                f"""You are a code architect. Determine the best file to implement the following feature.

Feature:
- Name: {feature.name}
- Description: {feature.description}

Consider:
- Which existing file is most related?
- Would it be better in a new file?
- What would be the file name?

Recommend the most logical location."""
            )
            .add_context("Existing Code Structure", code_summary)
            .add_output_format(
                {
                    "recommended_file": "tasks.py",
                    "confidence": 0.9,
                    "reasoning": "Feature is related to task management, tasks.py already handles task operations",
                },
                "Return recommendation in JSON format:",
            )
            .build()
        )

        response = await self.llm.ainvoke(
            messages=[{"role": "user", "content": prompt}],
            response_format=LLMConstants.RESPONSE_FORMAT_JSON,
            temperature=LLMConstants.TEMPERATURE_BALANCED,
        )

        result = ResponseParser.parse_structured_response(
            response,
            expected_fields=["recommended_file", "confidence"],
            fallback_factory=lambda: {"recommended_file": "main.py", "confidence": 0.5},
        )

        return result["recommended_file"], float(result.get("confidence", 0.5))
