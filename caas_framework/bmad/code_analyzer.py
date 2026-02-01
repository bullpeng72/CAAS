"""
Code Analyzer

Phase 3: Analyze generated code to extract implemented features
"""

import ast
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import logging


logger = logging.getLogger(__name__)


@dataclass
class FunctionInfo:
    """Information about a function/method"""
    name: str
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    line_number: int = 0
    is_async: bool = False
    calls: List[str] = field(default_factory=list)  # Functions it calls


@dataclass
class ClassInfo:
    """Information about a class"""
    name: str
    docstring: Optional[str] = None
    base_classes: List[str] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class AgentDefinition:
    """CrewAI Agent definition"""
    name: str
    role: Optional[str] = None
    goal: Optional[str] = None
    backstory: Optional[str] = None
    line_number: int = 0


@dataclass
class TaskDefinition:
    """CrewAI Task definition"""
    description: str
    agent_name: Optional[str] = None
    expected_output: Optional[str] = None
    line_number: int = 0


@dataclass
class FileAnalysis:
    """Analysis result for a single file"""
    file_path: str
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    global_variables: List[str] = field(default_factory=list)
    line_count: int = 0

    # High-level categorization
    is_crewai_code: bool = False
    has_agents: bool = False
    has_tasks: bool = False
    has_crew: bool = False

    # CrewAI-specific extractions
    agent_definitions: List[AgentDefinition] = field(default_factory=list)
    task_definitions: List[TaskDefinition] = field(default_factory=list)


class CodeAnalyzer:
    """
    Code Analyzer

    Analyzes Python code using AST to extract:
    - Functions and their signatures
    - Classes and their methods
    - Import statements
    - Function calls

    This information is used to understand what the code actually implements.
    """

    def __init__(self):
        """Initialize code analyzer"""
        self.logger = logging.getLogger(__name__)

    def analyze_file(self, file_path: str, content: str) -> FileAnalysis:
        """
        Analyze a single Python file

        Args:
            file_path: Path to the file
            content: File content as string

        Returns:
            FileAnalysis with extracted information
        """
        analysis = FileAnalysis(file_path=file_path)

        try:
            # Parse AST
            tree = ast.parse(content, filename=file_path)

            # Count lines
            analysis.line_count = len(content.splitlines())

            # Extract information
            self._extract_imports(tree, analysis)
            self._extract_functions(tree, analysis)
            self._extract_classes(tree, analysis)
            self._extract_global_variables(tree, analysis)

            # Categorize
            self._categorize_file(analysis)

            # Extract CrewAI-specific structures
            if analysis.is_crewai_code:
                self._extract_crewai_structures(tree, content, analysis)

        except SyntaxError as e:
            self.logger.error(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Error analyzing {file_path}: {e}")

        return analysis

    def analyze_code_base(self, files: Dict[str, str]) -> Dict[str, FileAnalysis]:
        """
        Analyze entire codebase

        Args:
            files: Dictionary of file_path → content

        Returns:
            Dictionary of file_path → FileAnalysis
        """
        analyses = {}

        for file_path, content in files.items():
            # Only analyze Python files
            if file_path.endswith('.py'):
                analysis = self.analyze_file(file_path, content)
                analyses[file_path] = analysis

        return analyses

    def _extract_imports(self, tree: ast.AST, analysis: FileAnalysis) -> None:
        """Extract import statements"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    analysis.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    analysis.imports.append(f"{module}.{alias.name}")

    def _extract_functions(self, tree: ast.AST, analysis: FileAnalysis) -> None:
        """Extract top-level functions"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Skip methods (they're handled in classes)
                if self._is_method(node, tree):
                    continue

                func_info = self._parse_function(node)
                analysis.functions.append(func_info)

    def _extract_classes(self, tree: ast.AST, analysis: FileAnalysis) -> None:
        """Extract class definitions"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._parse_class(node)
                analysis.classes.append(class_info)

    def _extract_global_variables(self, tree: ast.AST, analysis: FileAnalysis) -> None:
        """Extract global variable assignments"""
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        analysis.global_variables.append(target.id)

    def _parse_function(self, node: ast.FunctionDef) -> FunctionInfo:
        """Parse function/method node"""
        func_info = FunctionInfo(
            name=node.name,
            docstring=ast.get_docstring(node),
            line_number=node.lineno,
            is_async=isinstance(node, ast.AsyncFunctionDef)
        )

        # Extract parameters
        for arg in node.args.args:
            func_info.parameters.append(arg.arg)

        # Extract decorators
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                func_info.decorators.append(decorator.id)
            elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                func_info.decorators.append(decorator.func.id)

        # Extract return type annotation
        if node.returns:
            func_info.return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else None

        # Extract function calls
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    func_info.calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    func_info.calls.append(child.func.attr)

        return func_info

    def _parse_class(self, node: ast.ClassDef) -> ClassInfo:
        """Parse class node"""
        class_info = ClassInfo(
            name=node.name,
            docstring=ast.get_docstring(node),
            line_number=node.lineno
        )

        # Extract base classes
        for base in node.bases:
            if isinstance(base, ast.Name):
                class_info.base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                class_info.base_classes.append(base.attr)

        # Extract methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self._parse_function(item)
                class_info.methods.append(method_info)
            elif isinstance(item, ast.Assign):
                # Extract class attributes
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_info.attributes.append(target.id)

        return class_info

    def _is_method(self, node: ast.FunctionDef, tree: ast.AST) -> bool:
        """Check if function is a method (inside a class)"""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                if node in parent.body:
                    return True
        return False

    def _categorize_file(self, analysis: FileAnalysis) -> None:
        """Categorize file based on its content"""
        # Check for CrewAI imports
        crewai_imports = [
            'crewai', 'crewai.agent', 'crewai.task', 'crewai.crew',
            'crewai.Agent', 'crewai.Task', 'crewai.Crew'
        ]

        for imp in analysis.imports:
            if any(ci in imp for ci in crewai_imports):
                analysis.is_crewai_code = True
                break

        # Check for Agent/Task/Crew usage
        all_names = (
            [f.name for f in analysis.functions] +
            [c.name for c in analysis.classes] +
            analysis.global_variables
        )

        for name in all_names:
            name_lower = name.lower()
            if 'agent' in name_lower:
                analysis.has_agents = True
            if 'task' in name_lower:
                analysis.has_tasks = True
            if 'crew' in name_lower:
                analysis.has_crew = True

    def get_summary(self, analyses: Dict[str, FileAnalysis]) -> Dict[str, Any]:
        """
        Generate summary statistics

        Args:
            analyses: Dictionary of file analyses

        Returns:
            Summary statistics
        """
        total_functions = sum(len(a.functions) for a in analyses.values())
        total_classes = sum(len(a.classes) for a in analyses.values())
        total_methods = sum(
            len(c.methods) for a in analyses.values() for c in a.classes
        )
        total_lines = sum(a.line_count for a in analyses.values())

        crewai_files = sum(1 for a in analyses.values() if a.is_crewai_code)
        total_agents = sum(len(a.agent_definitions) for a in analyses.values())
        total_tasks = sum(len(a.task_definitions) for a in analyses.values())

        return {
            'total_files': len(analyses),
            'total_lines': total_lines,
            'total_functions': total_functions,
            'total_classes': total_classes,
            'total_methods': total_methods,
            'crewai_files': crewai_files,
            'files_with_agents': sum(1 for a in analyses.values() if a.has_agents),
            'files_with_tasks': sum(1 for a in analyses.values() if a.has_tasks),
            'files_with_crew': sum(1 for a in analyses.values() if a.has_crew),
            'total_agent_definitions': total_agents,
            'total_task_definitions': total_tasks,
        }

    def _extract_crewai_structures(
        self, tree: ast.AST, content: str, analysis: FileAnalysis
    ) -> None:
        """
        Extract CrewAI-specific structures (Agents and Tasks)

        Args:
            tree: AST tree
            content: File content
            analysis: File analysis to update
        """
        # Find all Agent() and Task() calls
        for node in ast.walk(tree):
            # Look for Agent(...) calls
            if isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                # Extract Agent definitions
                if func_name == 'Agent':
                    agent_def = self._parse_agent_call(node)
                    if agent_def:
                        analysis.agent_definitions.append(agent_def)

                # Extract Task definitions
                elif func_name == 'Task':
                    task_def = self._parse_task_call(node)
                    if task_def:
                        analysis.task_definitions.append(task_def)

    def _parse_agent_call(self, node: ast.Call) -> Optional[AgentDefinition]:
        """Parse Agent() call to extract definition"""
        agent_def = AgentDefinition(
            name="",
            line_number=node.lineno
        )

        # Extract from positional arguments (generated code format)
        # Agent(name, role, goal, tools, ...)
        if len(node.args) >= 2:
            # args[0]: name
            if isinstance(node.args[0], ast.Constant):
                agent_def.name = node.args[0].value
            # args[1]: role
            if isinstance(node.args[1], ast.Constant):
                agent_def.role = node.args[1].value
            # args[2]: goal (if present)
            if len(node.args) >= 3 and isinstance(node.args[2], ast.Constant):
                agent_def.goal = node.args[2].value

        # Extract keyword arguments (alternative format)
        for keyword in node.keywords:
            if keyword.arg == 'role' and isinstance(keyword.value, ast.Constant):
                agent_def.role = keyword.value.value
                if not agent_def.name:
                    agent_def.name = keyword.value.value
            elif keyword.arg == 'goal' and isinstance(keyword.value, ast.Constant):
                agent_def.goal = keyword.value.value
            elif keyword.arg == 'backstory' and isinstance(keyword.value, ast.Constant):
                agent_def.backstory = keyword.value.value

        return agent_def if agent_def.role else None

    def _parse_task_call(self, node: ast.Call) -> Optional[TaskDefinition]:
        """Parse Task() call to extract definition"""
        task_def = TaskDefinition(
            description="",
            line_number=node.lineno
        )

        # Extract from positional arguments (generated code format)
        # Task(name, description, expected_output, agent, context, ...)
        if len(node.args) >= 2:
            # args[0]: name (skip, not needed for TaskDefinition)
            # args[1]: description
            if isinstance(node.args[1], ast.Constant):
                task_def.description = node.args[1].value
            # args[2]: expected_output (if present)
            if len(node.args) >= 3 and isinstance(node.args[2], ast.Constant):
                task_def.expected_output = node.args[2].value
            # args[3]: agent (if present)
            if len(node.args) >= 4:
                if isinstance(node.args[3], ast.Constant):
                    # agent name as string
                    task_def.agent_name = node.args[3].value
                elif isinstance(node.args[3], ast.Name):
                    # agent variable reference
                    task_def.agent_name = node.args[3].id

        # Extract keyword arguments (alternative format)
        for keyword in node.keywords:
            if keyword.arg == 'description' and isinstance(keyword.value, ast.Constant):
                task_def.description = keyword.value.value
            elif keyword.arg == 'expected_output' and isinstance(keyword.value, ast.Constant):
                task_def.expected_output = keyword.value.value
            elif keyword.arg == 'agent':
                # Try to extract agent name
                if isinstance(keyword.value, ast.Subscript):
                    # agents["name"]
                    if isinstance(keyword.value.slice, ast.Constant):
                        task_def.agent_name = keyword.value.slice.value
                elif isinstance(keyword.value, ast.Name):
                    task_def.agent_name = keyword.value.id
                elif isinstance(keyword.value, ast.Constant):
                    task_def.agent_name = keyword.value.value

        return task_def if task_def.description else None

    def extract_feature_hints(self, analysis: FileAnalysis) -> List[str]:
        """
        Extract feature hints from code

        Looks at function/method names and docstrings to infer what features
        might be implemented.

        Args:
            analysis: File analysis result

        Returns:
            List of feature hint strings
        """
        hints = []

        # Extract from function names
        for func in analysis.functions:
            hints.append(func.name)
            if func.docstring:
                # Extract first line of docstring
                first_line = func.docstring.split('\n')[0].strip()
                hints.append(first_line)

        # Extract from class names and methods
        for cls in analysis.classes:
            hints.append(cls.name)
            if cls.docstring:
                first_line = cls.docstring.split('\n')[0].strip()
                hints.append(first_line)

            for method in cls.methods:
                hints.append(f"{cls.name}.{method.name}")
                if method.docstring:
                    first_line = method.docstring.split('\n')[0].strip()
                    hints.append(first_line)

        # Extract from CrewAI structures
        for agent in analysis.agent_definitions:
            if agent.role:
                hints.append(agent.role)
            if agent.goal:
                hints.append(agent.goal)

        for task in analysis.task_definitions:
            if task.description:
                hints.append(task.description)

        return hints
