"""
Code Injectors

Inject error handling, logging, and other cross-cutting concerns into generated code.
"""

import ast
from typing import List, Optional


class ErrorHandlingInjector:
    """
    Enhanced Error Handling Injector

    Wraps functions with try-except blocks, retry logic, and proper error handling.

    Features:
    - Automatic try-except wrapping
    - Retry logic with exponential backoff
    - Fallback mechanisms
    - Circuit breaker pattern
    """

    def __init__(self, enable_retry: bool = True, max_retries: int = 3):
        """
        Initialize injector.

        Args:
            enable_retry: Enable retry logic for functions
            max_retries: Maximum retry attempts
        """
        self.enable_retry = enable_retry
        self.max_retries = max_retries

    def inject(self, code: str, error_types: Optional[List[str]] = None) -> str:
        """
        Inject error handling into Python code.

        Args:
            code: Python code
            error_types: Specific error types to catch (default: Exception)

        Returns:
            str: Code with error handling
        """
        try:
            tree = ast.parse(code)
            transformer = ErrorHandlingTransformer(error_types or ["Exception"])
            modified_tree = transformer.visit(tree)
            ast.fix_missing_locations(modified_tree)
            return ast.unparse(modified_tree)
        except SyntaxError:
            # If code has syntax errors, return as-is
            return code

    def wrap_function(
        self, func_code: str, error_handler: str = "logger.error", reraise: bool = False
    ) -> str:
        """
        Wrap a function with try-except.

        Args:
            func_code: Function code
            error_handler: Error handling statement
            reraise: Whether to reraise exception

        Returns:
            str: Wrapped function code
        """
        lines = func_code.split("\n")
        if not lines:
            return func_code

        # Find function definition
        func_def_idx = next((i for i, line in enumerate(lines) if "def " in line), None)
        if func_def_idx is None:
            return func_code

        # Find function body start
        body_start = func_def_idx + 1
        while body_start < len(lines) and (
            not lines[body_start].strip()
            or lines[body_start].strip().startswith('"""')
            or lines[body_start].strip().startswith("'''")
        ):
            body_start += 1

        if body_start >= len(lines):
            return func_code

        # Get indentation
        indent = len(lines[body_start]) - len(lines[body_start].lstrip())
        indent_str = " " * indent

        # Wrap body with try-except
        wrapped_lines = lines[:body_start]
        wrapped_lines.append(f"{indent_str}try:")

        # Add function body with extra indentation
        for line in lines[body_start:]:
            if line.strip():
                wrapped_lines.append(f"    {line}")
            else:
                wrapped_lines.append(line)

        # Add except block
        wrapped_lines.extend(
            [
                f"{indent_str}except Exception as e:",
                f'{indent_str}    {error_handler}(f"Error: {{str(e)}}")',
            ]
        )

        if reraise:
            wrapped_lines.append(f"{indent_str}    raise")

        return "\n".join(wrapped_lines)

    def inject_retry_logic(
        self,
        code: str,
        functions_to_retry: Optional[List[str]] = None,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
    ) -> str:
        """
        Inject retry logic with exponential backoff.

        Args:
            code: Python code
            functions_to_retry: List of function names to add retry logic (None = all)
            max_retries: Maximum retry attempts
            backoff_factor: Exponential backoff multiplier

        Returns:
            str: Code with retry logic
        """
        # Add retry decorator
        retry_decorator = f'''
import time
import logging
from functools import wraps

def retry_with_backoff(max_retries={max_retries}, backoff_factor={backoff_factor}):
    """
    Retry decorator with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logging.error(f"{{func.__name__}} failed after {{max_retries}} attempts: {{str(e)}}")
                        raise

                    wait_time = backoff_factor ** retries
                    logging.warning(f"{{func.__name__}} failed (attempt {{retries}}/{{max_retries}}), retrying in {{wait_time}}s...")
                    time.sleep(wait_time)

            return None
        return wrapper
    return decorator

'''
        # Add decorator to code
        if retry_decorator not in code:
            # Find first import or function definition
            lines = code.split("\n")
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("def ") or line.startswith("class "):
                    insert_idx = i
                    break
                elif "import" in line:
                    insert_idx = i + 1

            lines.insert(insert_idx, retry_decorator)
            code = "\n".join(lines)

        # Apply decorator to specified functions or all async functions
        try:
            tree = ast.parse(code)
            transformer = RetryDecoratorTransformer(functions_to_retry)
            modified_tree = transformer.visit(tree)
            ast.fix_missing_locations(modified_tree)
            return ast.unparse(modified_tree)
        except SyntaxError:
            return code

    def generate_error_handling_utils(self) -> str:
        """
        Generate utility functions for error handling.

        Returns:
            str: Utility functions code
        """
        return '''
"""Error Handling Utilities"""

import logging
import traceback
from typing import Optional, Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handler"""

    @staticmethod
    def handle_error(error: Exception, context: Optional[dict] = None) -> None:
        """
        Handle error with logging and context.

        Args:
            error: Exception to handle
            context: Additional context information
        """
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc()
        }

        if context:
            error_info["context"] = context

        logger.error(f"Error occurred: {error_info}")

    @staticmethod
    def safe_execute(func: Callable, *args, default=None, **kwargs) -> Any:
        """
        Execute function safely with fallback.

        Args:
            func: Function to execute
            *args: Positional arguments
            default: Default value on error
            **kwargs: Keyword arguments

        Returns:
            Function result or default value
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ErrorHandler.handle_error(e, {
                "function": func.__name__,
                "args": args,
                "kwargs": kwargs
            })
            return default


def circuit_breaker(failure_threshold: int = 5, timeout: int = 60):
    """
    Circuit breaker decorator to prevent cascade failures.

    Args:
        failure_threshold: Number of failures before opening circuit
        timeout: Seconds to wait before attempting retry
    """
    def decorator(func: Callable):
        failures = 0
        last_failure_time = 0

        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal failures, last_failure_time

            # Check if circuit is open
            import time
            current_time = time.time()
            if failures >= failure_threshold:
                if current_time - last_failure_time < timeout:
                    raise Exception(f"Circuit breaker open for {func.__name__}")
                else:
                    # Reset circuit
                    failures = 0

            try:
                result = func(*args, **kwargs)
                failures = 0  # Reset on success
                return result
            except Exception as e:
                failures += 1
                last_failure_time = current_time
                logger.error(f"Circuit breaker: {func.__name__} failed ({failures}/{failure_threshold})")
                raise

        return wrapper
    return decorator
'''


class RetryDecoratorTransformer(ast.NodeTransformer):
    """AST transformer to add retry decorators"""

    def __init__(self, functions_to_retry: Optional[List[str]] = None):
        """
        Args:
            functions_to_retry: List of function names to add retry (None = all)
        """
        self.functions_to_retry = functions_to_retry

    def visit_FunctionDef(self, node):
        """Add retry decorator to functions"""
        # Check if function should have retry
        if self.functions_to_retry and node.name not in self.functions_to_retry:
            return node

        # Skip if already has retry decorator
        if any(
            "retry" in dec.id if isinstance(dec, ast.Name) else False for dec in node.decorator_list
        ):
            return node

        # Add retry decorator
        retry_dec = ast.Name(id="retry_with_backoff", ctx=ast.Load())
        node.decorator_list.insert(0, ast.Call(func=retry_dec, args=[], keywords=[]))

        return node


class ErrorHandlingTransformer(ast.NodeTransformer):
    """AST transformer to inject error handling"""

    def __init__(self, error_types: List[str]):
        self.error_types = error_types

    def visit_FunctionDef(self, node):
        """Visit function definitions and wrap with try-except"""
        # Skip if already has try-except
        if any(isinstance(stmt, ast.Try) for stmt in node.body):
            return node

        # Skip special methods
        if node.name.startswith("__") and node.name.endswith("__"):
            return node

        # Create try-except wrapper
        try_node = ast.Try(
            body=node.body,
            handlers=[
                ast.ExceptHandler(
                    type=ast.Name(id="Exception", ctx=ast.Load()),
                    name="e",
                    body=[
                        ast.Expr(
                            value=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id="logger", ctx=ast.Load()),
                                    attr="error",
                                    ctx=ast.Load(),
                                ),
                                args=[
                                    ast.JoinedStr(
                                        values=[
                                            ast.Constant(value=f"Error in {node.name}: "),
                                            ast.FormattedValue(
                                                value=ast.Call(
                                                    func=ast.Name(id="str", ctx=ast.Load()),
                                                    args=[ast.Name(id="e", ctx=ast.Load())],
                                                    keywords=[],
                                                ),
                                                conversion=-1,
                                                format_spec=None,
                                            ),
                                        ]
                                    )
                                ],
                                keywords=[],
                            )
                        ),
                        ast.Raise(),
                    ],
                )
            ],
            orelse=[],
            finalbody=[],
        )

        node.body = [try_node]
        return node


class LoggingInjector:
    """
    Enhanced Logging Injector

    Injects structured logging (JSON format) into generated code.

    Features:
    - JSON-formatted logs
    - Contextual information
    - Request ID tracking
    - Performance metrics
    """

    def __init__(self, use_json_format: bool = True):
        """
        Initialize injector.

        Args:
            use_json_format: Use JSON format for structured logging
        """
        self.use_json_format = use_json_format

    def inject(self, code: str, logger_name: str = "app", log_level: str = "info") -> str:
        """
        Inject structured logging into Python code.

        Args:
            code: Python code
            logger_name: Logger name
            log_level: Log level (debug, info, warning, error)

        Returns:
            str: Code with structured logging
        """
        # Add logging import if not present
        if "import logging" not in code and "from logging import" not in code:
            if self.use_json_format:
                logging_import = f"""import logging
import json
import time
from datetime import datetime
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    \"\"\"Custom JSON formatter for structured logging\"\"\"

    def format(self, record):
        log_data = {{
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }}

        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

logger = logging.getLogger("{logger_name}")
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

"""
            else:
                logging_import = f"""import logging

logger = logging.getLogger("{logger_name}")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

"""
            code = logging_import + code

        try:
            tree = ast.parse(code)
            transformer = LoggingTransformer(log_level)
            modified_tree = transformer.visit(tree)
            ast.fix_missing_locations(modified_tree)
            return ast.unparse(modified_tree)
        except SyntaxError:
            return code

    def add_function_logging(self, func_code: str, logger_name: str = "logger") -> str:
        """
        Add logging to function entry/exit.

        Args:
            func_code: Function code
            logger_name: Logger variable name

        Returns:
            str: Function with logging
        """
        lines = func_code.split("\n")
        if not lines:
            return func_code

        # Find function definition
        func_def_idx = next((i for i, line in enumerate(lines) if "def " in line), None)
        if func_def_idx is None:
            return func_code

        # Extract function name
        func_def = lines[func_def_idx]
        func_name = func_def.split("def ")[1].split("(")[0].strip()

        # Find function body start
        body_start = func_def_idx + 1
        while body_start < len(lines) and (
            not lines[body_start].strip()
            or lines[body_start].strip().startswith('"""')
            or lines[body_start].strip().startswith("'''")
        ):
            body_start += 1

        if body_start >= len(lines):
            return func_code

        # Get indentation
        indent = len(lines[body_start]) - len(lines[body_start].lstrip())
        indent_str = " " * indent

        # Add entry log
        logged_lines = lines[:body_start]
        logged_lines.append(f'{indent_str}{logger_name}.info(f"Entering {func_name}")')

        # Add rest of function body
        logged_lines.extend(lines[body_start:])

        # Add exit log before return statements
        final_lines = []
        for line in logged_lines:
            if "return " in line:
                line_indent = len(line) - len(line.lstrip())
                final_lines.append(
                    " " * line_indent + f'{logger_name}.info(f"Exiting {func_name}")'
                )
            final_lines.append(line)

        return "\n".join(final_lines)

    def generate_structured_logging_utils(self) -> str:
        """
        Generate utility functions for structured logging.

        Returns:
            str: Utility functions code
        """
        return '''
"""Structured Logging Utilities"""

import logging
import json
import time
from typing import Any, Dict, Optional
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)


class StructuredLogger:
    """Structured logging helper"""

    @staticmethod
    def log_with_context(
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Log message with structured context.

        Args:
            level: Log level (debug, info, warning, error)
            message: Log message
            context: Additional context dictionary
            **kwargs: Extra fields
        """
        log_data = {
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }

        if context:
            log_data["context"] = context

        log_data.update(kwargs)

        log_func = getattr(logger, level.lower())
        log_func(json.dumps(log_data))

    @staticmethod
    def log_performance(func):
        """Decorator to log function performance"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                StructuredLogger.log_with_context(
                    "info",
                    f"{func.__name__} completed",
                    context={
                        "function": func.__name__,
                        "duration_seconds": duration,
                        "status": "success"
                    }
                )

                return result
            except Exception as e:
                duration = time.time() - start_time

                StructuredLogger.log_with_context(
                    "error",
                    f"{func.__name__} failed",
                    context={
                        "function": func.__name__,
                        "duration_seconds": duration,
                        "status": "error",
                        "error": str(e)
                    }
                )
                raise

        return wrapper


def log_request(request_id: Optional[str] = None):
    """
    Decorator to log HTTP requests.

    Args:
        request_id: Optional request ID for tracking
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import uuid
            req_id = request_id or str(uuid.uuid4())

            StructuredLogger.log_with_context(
                "info",
                f"Request started: {func.__name__}",
                context={
                    "request_id": req_id,
                    "function": func.__name__
                }
            )

            try:
                result = func(*args, **kwargs)

                StructuredLogger.log_with_context(
                    "info",
                    f"Request completed: {func.__name__}",
                    context={
                        "request_id": req_id,
                        "function": func.__name__,
                        "status": "success"
                    }
                )

                return result
            except Exception as e:
                StructuredLogger.log_with_context(
                    "error",
                    f"Request failed: {func.__name__}",
                    context={
                        "request_id": req_id,
                        "function": func.__name__,
                        "status": "error",
                        "error": str(e)
                    }
                )
                raise

        return wrapper
    return decorator
'''


class LoggingTransformer(ast.NodeTransformer):
    """AST transformer to inject logging"""

    def __init__(self, log_level: str):
        self.log_level = log_level

    def visit_FunctionDef(self, node):
        """Visit function definitions and add logging"""
        # Skip special methods
        if node.name.startswith("__") and node.name.endswith("__"):
            return node

        # Skip logging-related methods to prevent infinite recursion
        # (e.g., JSONFormatter.format, LoggingHandler methods, etc.)
        if node.name in ("format", "emit", "handleError", "filter"):
            return node

        # Add entry log
        entry_log = ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="logger", ctx=ast.Load()), attr=self.log_level, ctx=ast.Load()
                ),
                args=[ast.Constant(value=f"Entering {node.name}")],
                keywords=[],
            )
        )

        # Insert at beginning of function
        node.body.insert(0, entry_log)

        return node
