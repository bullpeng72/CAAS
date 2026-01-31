"""
Frontend Logic Generator

Domain-specific frontend 로직을 생성합니다.
TODO 플레이스홀더 대신 실제 동작하는 코드를 생성합니다.
"""

import ast
from typing import List, Dict, Any, Optional
from app.models.domain_types import DomainType, ExecutionPattern
from app.utils.logger import get_logger

logger = get_logger("codegen.frontend_logic")


class FrontendLogicGenerator:
    """Frontend domain-specific 로직 생성기"""

    def __init__(self):
        self.logger = logger

    def generate_button_handler(
        self,
        domain_type: Optional[DomainType],
        button_label: str,
        component_id: str,
        available_variables: List[str] = None,
        execution_pattern: Optional[ExecutionPattern] = None
    ) -> List[ast.stmt]:
        """
        버튼 클릭 이벤트 핸들러 생성

        Args:
            domain_type: Domain type (TASK_MANAGEMENT, DATA_ANALYSIS, etc.)
            button_label: 버튼 레이블 (예: "Add Task", "Delete Task")
            component_id: 컴포넌트 ID
            available_variables: 사용 가능한 변수 목록 (예: ["task_name", "priority"])
            execution_pattern: 실행 패턴

        Returns:
            AST statement 리스트 (실제 동작하는 코드)
        """
        available_variables = available_variables or []

        # Domain type이 없으면 generic handler 반환
        if not domain_type:
            return self._generate_generic_handler(button_label, available_variables)

        # Domain type별 handler 생성
        if domain_type == DomainType.TASK_MANAGEMENT:
            return self._generate_task_management_handler(
                button_label, component_id, available_variables
            )
        elif domain_type == DomainType.DATA_ANALYSIS:
            return self._generate_data_analysis_handler(
                button_label, component_id, available_variables
            )
        elif domain_type == DomainType.CONVERSATIONAL_AI:
            return self._generate_conversational_handler(
                button_label, component_id, available_variables
            )
        elif domain_type == DomainType.REPORT_GENERATION:
            return self._generate_report_handler(
                button_label, component_id, available_variables
            )
        else:
            # 기타 domain은 generic handler 사용
            return self._generate_generic_handler(button_label, available_variables)

    def _generate_generic_handler(
        self, button_label: str, available_variables: List[str]
    ) -> List[ast.stmt]:
        """Generic button handler (TODO 플레이스홀더)"""
        return [
            ast.Expr(value=ast.Constant(value=f"TODO: {button_label} 버튼 클릭 시 동작 구현")),
            ast.Pass()
        ]

    def _generate_task_management_handler(
        self, button_label: str, component_id: str, available_variables: List[str]
    ) -> List[ast.stmt]:
        """Task Management domain button handler"""

        button_lower = button_label.lower()

        # Add Task 버튼
        if "add" in button_lower or "create" in button_lower or "새" in button_lower or "추가" in button_lower:
            # task 관련 변수가 있는지 확인 (task_name, task_description, task_input 등)
            has_task_name = any("task" in var.lower() for var in available_variables)
            has_priority = any("priority" in var for var in available_variables)

            statements = []

            # Input validation
            if has_task_name:
                # if task_name:
                # Find first variable containing "task"
                task_name_var = next((v for v in available_variables if "task" in v.lower()), "task_name")

                statements.append(
                    ast.If(
                        test=ast.Name(id=task_name_var, ctx=ast.Load()),
                        body=[
                            # Initialize session state if needed
                            # if "tasks" not in st.session_state:
                            #     st.session_state.tasks = []
                            ast.If(
                                test=ast.UnaryOp(
                                    op=ast.Not(),
                                    operand=ast.Compare(
                                        left=ast.Constant(value="tasks"),
                                        ops=[ast.In()],
                                        comparators=[
                                            ast.Attribute(
                                                value=ast.Name(id="st", ctx=ast.Load()),
                                                attr="session_state",
                                                ctx=ast.Load()
                                            )
                                        ]
                                    )
                                ),
                                body=[
                                    ast.Assign(
                                        targets=[
                                            ast.Subscript(
                                                value=ast.Attribute(
                                                    value=ast.Name(id="st", ctx=ast.Load()),
                                                    attr="session_state",
                                                    ctx=ast.Load()
                                                ),
                                                slice=ast.Constant(value="tasks"),
                                                ctx=ast.Store()
                                            )
                                        ],
                                        value=ast.List(elts=[], ctx=ast.Load())
                                    )
                                ],
                                orelse=[]
                            ),
                            # Add task to session_state
                            # st.session_state.tasks.append({"name": task_name, "priority": priority, "status": "pending"})
                            ast.Expr(
                                value=ast.Call(
                                    func=ast.Attribute(
                                        value=ast.Attribute(
                                            value=ast.Attribute(
                                                value=ast.Name(id="st", ctx=ast.Load()),
                                                attr="session_state",
                                                ctx=ast.Load()
                                            ),
                                            attr="tasks",
                                            ctx=ast.Load()
                                        ),
                                        attr="append",
                                        ctx=ast.Load()
                                    ),
                                    args=[
                                        ast.Dict(
                                            keys=[
                                                ast.Constant(value="name"),
                                                ast.Constant(value="priority"),
                                                ast.Constant(value="status")
                                            ],
                                            values=[
                                                ast.Name(id=task_name_var, ctx=ast.Load()),
                                                ast.Name(id="priority", ctx=ast.Load()) if has_priority else ast.Constant(value="medium"),
                                                ast.Constant(value="pending")
                                            ]
                                        )
                                    ],
                                    keywords=[]
                                )
                            ),
                            # st.success(f"Task '{task_name}' added!")
                            ast.Expr(
                                value=ast.Call(
                                    func=ast.Attribute(
                                        value=ast.Name(id="st", ctx=ast.Load()),
                                        attr="success",
                                        ctx=ast.Load()
                                    ),
                                    args=[
                                        ast.JoinedStr(
                                            values=[
                                                ast.Constant(value="Task '"),
                                                ast.FormattedValue(
                                                    value=ast.Name(id=task_name_var, ctx=ast.Load()),
                                                    conversion=-1,
                                                    format_spec=None
                                                ),
                                                ast.Constant(value="' added!")
                                            ]
                                        )
                                    ],
                                    keywords=[]
                                )
                            ),
                            # st.rerun()
                            ast.Expr(
                                value=ast.Call(
                                    func=ast.Attribute(
                                        value=ast.Name(id="st", ctx=ast.Load()),
                                        attr="rerun",
                                        ctx=ast.Load()
                                    ),
                                    args=[],
                                    keywords=[]
                                )
                            )
                        ],
                        orelse=[
                            # else: st.warning("Please enter a task name")
                            ast.Expr(
                                value=ast.Call(
                                    func=ast.Attribute(
                                        value=ast.Name(id="st", ctx=ast.Load()),
                                        attr="warning",
                                        ctx=ast.Load()
                                    ),
                                    args=[ast.Constant(value="Please enter a task name")],
                                    keywords=[]
                                )
                            )
                        ]
                    )
                )
            else:
                # task_name 변수가 없으면 generic handler
                statements.append(
                    ast.Expr(value=ast.Constant(value=f"TODO: {button_label} - task_name variable not found"))
                )
                statements.append(ast.Pass())

            return statements

        # Delete Task 버튼
        elif "delete" in button_lower or "remove" in button_lower or "삭제" in button_lower:
            return [
                # if "tasks" in st.session_state and st.session_state.tasks:
                #     st.session_state.tasks.pop(task_index)
                #     st.success("Task deleted!")
                #     st.rerun()
                ast.If(
                    test=ast.BoolOp(
                        op=ast.And(),
                        values=[
                            ast.Compare(
                                left=ast.Constant(value="tasks"),
                                ops=[ast.In()],
                                comparators=[
                                    ast.Attribute(
                                        value=ast.Name(id="st", ctx=ast.Load()),
                                        attr="session_state",
                                        ctx=ast.Load()
                                    )
                                ]
                            ),
                            ast.Attribute(
                                value=ast.Attribute(
                                    value=ast.Name(id="st", ctx=ast.Load()),
                                    attr="session_state",
                                    ctx=ast.Load()
                                ),
                                attr="tasks",
                                ctx=ast.Load()
                            )
                        ]
                    ),
                    body=[
                        ast.Expr(
                            value=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id="st", ctx=ast.Load()),
                                    attr="info",
                                    ctx=ast.Load()
                                ),
                                args=[ast.Constant(value="Delete functionality: Select task from table and use delete action")],
                                keywords=[]
                            )
                        )
                    ],
                    orelse=[]
                )
            ]

        # Complete/Mark as Done 버튼
        elif "complete" in button_lower or "done" in button_lower or "완료" in button_lower:
            return [
                ast.Expr(value=ast.Constant(value="# Mark task as complete")),
                ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="st", ctx=ast.Load()),
                            attr="info",
                            ctx=ast.Load()
                        ),
                        args=[ast.Constant(value="Complete functionality: Select task from table")],
                        keywords=[]
                    )
                )
            ]

        # Filter 버튼
        elif "filter" in button_lower or "search" in button_lower:
            return [
                ast.Expr(value=ast.Constant(value="# Filter tasks")),
                ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="st", ctx=ast.Load()),
                            attr="info",
                            ctx=ast.Load()
                        ),
                        args=[ast.Constant(value="Filter functionality: Use filter controls above")],
                        keywords=[]
                    )
                )
            ]

        else:
            # 알 수 없는 버튼은 generic handler
            return self._generate_generic_handler(button_label, available_variables)

    def _generate_data_analysis_handler(
        self, button_label: str, component_id: str, available_variables: List[str]
    ) -> List[ast.stmt]:
        """Data Analysis domain button handler"""

        button_lower = button_label.lower()

        if "analyze" in button_lower or "분석" in button_lower:
            return [
                ast.Expr(value=ast.Constant(value="# Analyze data")),
                ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="st", ctx=ast.Load()),
                            attr="info",
                            ctx=ast.Load()
                        ),
                        args=[ast.Constant(value="Analysis functionality: Upload data file first")],
                        keywords=[]
                    )
                )
            ]
        else:
            return self._generate_generic_handler(button_label, available_variables)

    def _generate_conversational_handler(
        self, button_label: str, component_id: str, available_variables: List[str]
    ) -> List[ast.stmt]:
        """Conversational AI domain button handler"""

        return [
            ast.Expr(value=ast.Constant(value="# Send message")),
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="st", ctx=ast.Load()),
                        attr="info",
                        ctx=ast.Load()
                    ),
                    args=[ast.Constant(value="Chat functionality: Use agent execution below")],
                    keywords=[]
                )
            )
        ]

    def _generate_report_handler(
        self, button_label: str, component_id: str, available_variables: List[str]
    ) -> List[ast.stmt]:
        """Report Generation domain button handler"""

        return [
            ast.Expr(value=ast.Constant(value="# Generate report")),
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="st", ctx=ast.Load()),
                        attr="info",
                        ctx=ast.Load()
                    ),
                    args=[ast.Constant(value="Report generation: Configure parameters above")],
                    keywords=[]
                )
            )
        ]

    def generate_table_display(
        self,
        domain_type: Optional[DomainType],
        table_label: str,
        component_id: str
    ) -> List[ast.stmt]:
        """
        테이블 표시 코드 생성

        Args:
            domain_type: Domain type
            table_label: 테이블 레이블
            component_id: 컴포넌트 ID

        Returns:
            AST statement 리스트
        """
        if domain_type == DomainType.TASK_MANAGEMENT:
            return self._generate_task_table()
        else:
            # Generic table
            return [
                ast.Expr(value=ast.Constant(value="# TODO: 테이블 데이터를 준비하고 표시")),
                ast.Expr(value=ast.Constant(value=f"# st.dataframe({component_id}_data)"))
            ]

    def _generate_task_table(self) -> List[ast.stmt]:
        """Task management 테이블 생성"""
        return [
            # if "tasks" in st.session_state and st.session_state.tasks:
            #     st.dataframe(st.session_state.tasks)
            # else:
            #     st.info("No tasks yet")
            ast.If(
                test=ast.BoolOp(
                    op=ast.And(),
                    values=[
                        ast.Compare(
                            left=ast.Constant(value="tasks"),
                            ops=[ast.In()],
                            comparators=[
                                ast.Attribute(
                                    value=ast.Name(id="st", ctx=ast.Load()),
                                    attr="session_state",
                                    ctx=ast.Load()
                                )
                            ]
                        ),
                        ast.Attribute(
                            value=ast.Attribute(
                                value=ast.Name(id="st", ctx=ast.Load()),
                                attr="session_state",
                                ctx=ast.Load()
                            ),
                            attr="tasks",
                            ctx=ast.Load()
                        )
                    ]
                ),
                body=[
                    ast.Expr(
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id="st", ctx=ast.Load()),
                                attr="dataframe",
                                ctx=ast.Load()
                            ),
                            args=[
                                ast.Attribute(
                                    value=ast.Attribute(
                                        value=ast.Name(id="st", ctx=ast.Load()),
                                        attr="session_state",
                                        ctx=ast.Load()
                                    ),
                                    attr="tasks",
                                    ctx=ast.Load()
                                )
                            ],
                            keywords=[]
                        )
                    )
                ],
                orelse=[
                    ast.Expr(
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id="st", ctx=ast.Load()),
                                attr="info",
                                ctx=ast.Load()
                            ),
                            args=[ast.Constant(value="No tasks yet. Add your first task above!")],
                            keywords=[]
                        )
                    )
                ]
            )
        ]
