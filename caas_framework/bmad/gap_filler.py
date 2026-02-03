"""
Gap Filler

Phase 3: Automatically generate code for unimplemented features
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from caas_framework.bmad.code_analyzer import FileAnalysis
from caas_framework.bmad.completeness_validator import CompletenessReport
from caas_framework.bmad.semantic_mapper import SemanticMapper
from caas_framework.config.settings import LLMConstants
from caas_framework.models.specifications import FeatureSpec
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils import PromptBuilder, ResponseParser
from caas_framework.utils.logger import get_logger

logger = get_logger()


@dataclass
class GeneratedCode:
    """Generated code for a feature"""

    feature_id: str
    feature_name: str
    target_file: str
    code_snippet: str
    insertion_point: str  # "append", "insert_at_line_N", "replace_function_X"
    explanation: str


@dataclass
class GapFillingResult:
    """Result of gap filling process"""

    generated_codes: List[GeneratedCode] = field(default_factory=list)
    updated_files: Dict[str, str] = field(default_factory=list)  # file_path → new content
    features_filled: List[str] = field(default_factory=list)  # feature IDs
    errors: List[str] = field(default_factory=list)
    success: bool = True


class GapFiller:
    """
    Gap Filler

    Automatically generates code for unimplemented features.

    Process:
    1. Identify unimplemented features from completeness report
    2. For each feature:
       a. Determine best file to add implementation
       b. Generate code snippet using LLM
       c. Determine insertion point
    3. Merge generated code into existing files
    4. Return updated file contents
    """

    def __init__(self, llm_plugin: LLMPlugin):
        """
        Initialize gap filler

        Args:
            llm_plugin: LLM plugin for code generation
        """
        self.llm = llm_plugin
        self.semantic_mapper = SemanticMapper(llm_plugin)
        self.logger = get_logger()

    async def fill_gaps(
        self,
        completeness_report: CompletenessReport,
        existing_code: Dict[str, str],
        code_analyses: Dict[str, FileAnalysis],
        max_features: int = 5,
    ) -> GapFillingResult:
        """
        Fill implementation gaps

        Args:
            completeness_report: Completeness validation report
            existing_code: Dictionary of file_path → content
            code_analyses: Analyzed code structure
            max_features: Maximum number of features to implement (to avoid overwhelming)

        Returns:
            GapFillingResult with generated code
        """
        self.logger.info(
            f"Starting gap filling for {len(completeness_report.unimplemented_features)} features"
        )

        result = GapFillingResult()

        # Prioritize features to implement
        features_to_implement = self._prioritize_features(
            completeness_report.unimplemented_features, max_features
        )

        self.logger.info(
            f"Selected {len(features_to_implement)} high-priority features to implement"
        )

        # Generate code for each feature
        for feature in features_to_implement:
            try:
                self.logger.info(f"Generating code for: {feature.name} ({feature.id})")

                generated = await self._generate_feature_code(feature, existing_code, code_analyses)

                result.generated_codes.append(generated)
                result.features_filled.append(feature.id)

            except Exception as e:
                self.logger.error(f"Failed to generate code for {feature.id}: {e}")
                result.errors.append(f"{feature.id}: {str(e)}")

        # Merge generated code into files
        if result.generated_codes:
            self.logger.info(f"Merging {len(result.generated_codes)} code snippets into files")
            result.updated_files = self._merge_code_into_files(
                existing_code, result.generated_codes
            )

        result.success = len(result.errors) == 0

        self.logger.info(
            f"Gap filling complete: {len(result.features_filled)} features implemented, "
            f"{len(result.errors)} errors"
        )

        return result

    def _prioritize_features(
        self, features: List[FeatureSpec], max_features: int
    ) -> List[FeatureSpec]:
        """
        Prioritize features to implement

        Args:
            features: Unimplemented features
            max_features: Maximum to select

        Returns:
            Prioritized list of features
        """
        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        sorted_features = sorted(features, key=lambda f: priority_order.get(f.priority.lower(), 3))

        return sorted_features[:max_features]

    async def _generate_feature_code(
        self,
        feature: FeatureSpec,
        existing_code: Dict[str, str],
        code_analyses: Dict[str, FileAnalysis],
    ) -> GeneratedCode:
        """
        Generate code for a single feature

        Args:
            feature: Feature to implement
            existing_code: Existing code files
            code_analyses: Code structure analysis

        Returns:
            GeneratedCode with implementation
        """
        # Step 1: Find best file to add code
        target_file, confidence = await self.semantic_mapper.find_best_implementation_location(
            feature, code_analyses
        )

        self.logger.debug(f"Selected {target_file} for {feature.id} (confidence: {confidence:.2f})")

        # Step 2: Build context from existing code
        context = self._build_code_context(target_file, existing_code, code_analyses)

        # Step 3: Generate code using LLM
        code_snippet, explanation = await self._generate_code_snippet(feature, target_file, context)

        # Step 4: Determine insertion point
        insertion_point = "append"  # Simple strategy: append to end

        return GeneratedCode(
            feature_id=feature.id,
            feature_name=feature.name,
            target_file=target_file,
            code_snippet=code_snippet,
            insertion_point=insertion_point,
            explanation=explanation,
        )

    def _build_code_context(
        self,
        target_file: str,
        existing_code: Dict[str, str],
        code_analyses: Dict[str, FileAnalysis],
    ) -> str:
        """Build code context for LLM"""
        context_lines = []

        # Include target file if it exists
        if target_file in existing_code:
            context_lines.append(f"### Existing code in {target_file}:")
            context_lines.append("```python")
            context_lines.append(existing_code[target_file])
            context_lines.append("```")

        # Include analysis
        if target_file in code_analyses:
            analysis = code_analyses[target_file]
            context_lines.append("\n### Code structure:")
            context_lines.append(f"- {len(analysis.functions)} functions")
            context_lines.append(f"- {len(analysis.classes)} classes")
            if analysis.imports:
                context_lines.append(f"- Imports: {', '.join(analysis.imports[:5])}")

        return "\n".join(context_lines)

    async def _generate_code_snippet(
        self, feature: FeatureSpec, target_file: str, context: str
    ) -> Tuple[str, str]:
        """
        Generate code snippet for feature

        Args:
            feature: Feature to implement
            target_file: Target file
            context: Code context

        Returns:
            Tuple of (code_snippet, explanation)
        """
        prompt = (
            PromptBuilder(f"generate code for feature '{feature.name}'")
            .add_task(
                f"""You are an expert Python developer. Generate code to implement the following feature.

Feature to implement:
- Name: {feature.name}
- Description: {feature.description}
- Acceptance Criteria: {feature.acceptance_criteria}

Target file: {target_file}

Requirements:
1. Generate clean, production-ready Python code
2. Follow Python best practices
3. Include docstrings
4. Handle errors appropriately
5. Match the style of existing code
6. Make it compatible with CrewAI framework if this is a CrewAI project

Generate ONLY the new code to add (function, class, or code block).
Do NOT include the entire file - just the new code snippet."""
            )
            .add_context("Existing Code Context", context)
            .add_output_format(
                {
                    "code_snippet": 'def new_function():\n    """Docstring"""\n    # Implementation\n    pass',
                    "explanation": "This function implements X by doing Y",
                },
                "Return the code snippet in JSON format:",
            )
            .add_guidelines(
                [
                    "Generate complete, working code",
                    "Include type hints if appropriate",
                    "Add error handling",
                    "Write clear docstrings",
                    "Match existing code style",
                    "Keep it simple and focused",
                    "Return only valid JSON",
                ]
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
            expected_fields=["code_snippet", "explanation"],
            fallback_factory=lambda: {
                "code_snippet": f"# TODO: Implement {feature.name}\npass",
                "explanation": f"Placeholder for {feature.name}",
            },
        )

        code_snippet = result.get("code_snippet", "# TODO: Implement feature\npass")
        explanation = result.get("explanation", "Generated code for feature")

        return code_snippet, explanation

    def _merge_code_into_files(
        self, existing_code: Dict[str, str], generated_codes: List[GeneratedCode]
    ) -> Dict[str, str]:
        """
        Merge generated code into existing files

        Args:
            existing_code: Existing file contents
            generated_codes: List of generated code snippets

        Returns:
            Updated file contents
        """
        updated_files = existing_code.copy()

        # Group by file
        codes_by_file: Dict[str, List[GeneratedCode]] = {}
        for gen_code in generated_codes:
            if gen_code.target_file not in codes_by_file:
                codes_by_file[gen_code.target_file] = []
            codes_by_file[gen_code.target_file].append(gen_code)

        # Merge into each file
        for file_path, codes in codes_by_file.items():
            if file_path in updated_files:
                # Append to existing file
                current_content = updated_files[file_path]
                new_content = self._append_code_to_file(current_content, codes)
                updated_files[file_path] = new_content
            else:
                # Create new file
                new_content = self._create_new_file(file_path, codes)
                updated_files[file_path] = new_content

        return updated_files

    def _append_code_to_file(self, current_content: str, codes: List[GeneratedCode]) -> str:
        """Append generated code to existing file"""
        lines = [current_content]

        lines.append("\n\n# === Auto-generated code for missing features ===\n")

        for gen_code in codes:
            lines.append(f"\n# Feature: {gen_code.feature_name} ({gen_code.feature_id})")
            lines.append(f"# {gen_code.explanation}")
            lines.append(gen_code.code_snippet)
            lines.append("")

        return "\n".join(lines)

    def _create_new_file(self, file_path: str, codes: List[GeneratedCode]) -> str:
        """Create new file with generated code"""
        lines = [
            '"""',
            f"Auto-generated file: {file_path}",
            "Generated by CAAS Framework - Gap Filler",
            '"""',
            "",
            "from crewai import Agent, Task, Crew",
            "",
        ]

        for gen_code in codes:
            lines.append(f"\n# Feature: {gen_code.feature_name} ({gen_code.feature_id})")
            lines.append(f"# {gen_code.explanation}")
            lines.append(gen_code.code_snippet)
            lines.append("")

        return "\n".join(lines)
