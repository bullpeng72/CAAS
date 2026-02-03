"""
AST-Based Code Generator

Python AST 모듈을 사용하여 CrewAI 코드를 생성합니다.
문자열 조합 대신 AST 노드를 직접 생성하여 문법 오류를 원천 차단합니다.

장점:
- ✅ 문법 오류 불가능 (AST가 보장)
- ✅ 타입 안전성 (AST 노드는 타입 체크 가능)
- ✅ 자동 포맷팅 (black 통합)
- ✅ 리팩토링 용이 (AST 변환)
"""

import ast
from ast import (
    Assign,
    Attribute,
    Call,
    Compare,
    Constant,
    Eq,
    Expr,
    FunctionDef,
    If,
    Import,
    ImportFrom,
    Load,
    Module,
    Name,
    Return,
    Store,
    Subscript,
    alias,
    arg,
    arguments,
    keyword,
)
from ast import Dict as AstDict
from ast import List as AstList
from typing import Any, Dict, List, Optional, Union


class ASTCodeGenerator:
    """
    AST 기반 코드 생성기

    Python AST를 사용하여 CrewAI 프로젝트 코드를 생성합니다.
    """

    def __init__(self, use_black: bool = True):
        """
        Args:
            use_black: black 포맷터 사용 여부 (기본: True)
        """
        self.use_black = use_black

    def generate_agent_code(self, agent: Dict[str, Any], tools: Optional[List[str]] = None) -> str:
        """
        Agent 객체 생성 코드를 AST로 생성

        Args:
            agent: Agent 정보 (id, role, goal, backstory 등)
            tools: 도구 목록

        Returns:
            str: Agent 생성 코드
        """
        # Agent() 호출 생성
        keywords_list = [
            keyword(arg="role", value=Constant(value=agent.get("role", "Agent"))),
            keyword(arg="goal", value=Constant(value=agent.get("goal", "Execute tasks"))),
            keyword(arg="backstory", value=Constant(value=agent.get("backstory", "Expert agent"))),
            keyword(arg="verbose", value=Constant(value=True)),
            keyword(
                arg="allow_delegation", value=Constant(value=agent.get("allow_delegation", False))
            ),
        ]

        # Tools 추가 (있는 경우)
        if tools:
            tools_list = AstList(elts=[Constant(value=tool) for tool in tools], ctx=Load())
            keywords_list.append(keyword(arg="tools", value=tools_list))

        agent_call = Call(func=Name(id="Agent", ctx=Load()), args=[], keywords=keywords_list)

        # Assignment: agent_id = Agent(...)
        agent_id = agent.get("id", "agent")
        assignment = Assign(targets=[Name(id=agent_id, ctx=Store())], value=agent_call)

        # Fix missing locations
        ast.fix_missing_locations(assignment)

        # AST를 Python 코드로 변환
        code = ast.unparse(assignment)
        return code

    def generate_task_code(self, task: Dict[str, Any], agent_var: str = "agents") -> str:
        """
        Task 객체 생성 코드를 AST로 생성

        Args:
            task: Task 정보 (description, expected_output, agent 등)
            agent_var: Agent를 참조하는 변수명 (기본: 'agents')

        Returns:
            str: Task 생성 코드
        """
        # Agent 참조 생성 (agents['agent_id'])
        agent_id = task.get("agent", "agent")
        agent_ref = Subscript(
            value=Name(id=agent_var, ctx=Load()), slice=Constant(value=agent_id), ctx=Load()
        )

        # Task() 호출 생성
        task_call = Call(
            func=Name(id="Task", ctx=Load()),
            args=[],
            keywords=[
                keyword(
                    arg="description", value=Constant(value=task.get("description", "Execute task"))
                ),
                keyword(
                    arg="expected_output",
                    value=Constant(value=task.get("expected_output", "Task completed")),
                ),
                keyword(arg="agent", value=agent_ref),
                keyword(arg="human_input", value=Constant(value=task.get("human_input", False))),
            ],
        )

        return ast.unparse(task_call)

    def generate_crew_code(
        self,
        agents_var: str = "agents",
        tasks_var: str = "tasks",
        process: str = "sequential",
        verbose: bool = True,
    ) -> str:
        """
        Crew 객체 생성 코드를 AST로 생성

        Args:
            agents_var: Agents 변수명
            tasks_var: Tasks 변수명
            process: Process 타입 ('sequential' 또는 'hierarchical')
            verbose: Verbose 모드

        Returns:
            str: Crew 생성 코드
        """
        # list(agents.values())
        agents_list = Call(
            func=Name(id="list", ctx=Load()),
            args=[
                (
                    Call(
                        func=Name(id="values", ctx=Load()),
                        args=[Name(id=agents_var, ctx=Load())],
                        keywords=[],
                    )
                    if isinstance(agents_var, str) and "." not in agents_var
                    else Call(
                        func=Attribute(
                            value=Name(id=agents_var, ctx=Load()), attr="values", ctx=Load()
                        ),
                        args=[],
                        keywords=[],
                    )
                )
            ],
            keywords=[],
        )

        # Process.sequential or Process.hierarchical
        process_attr = Attribute(value=Name(id="Process", ctx=Load()), attr=process, ctx=Load())

        # Crew() 호출
        crew_call = Call(
            func=Name(id="Crew", ctx=Load()),
            args=[],
            keywords=[
                keyword(arg="agents", value=agents_list),
                keyword(arg="tasks", value=Name(id=tasks_var, ctx=Load())),
                keyword(arg="process", value=process_attr),
                keyword(arg="verbose", value=Constant(value=verbose)),
            ],
        )

        # Assignment: crew = Crew(...)
        assignment = Assign(targets=[Name(id="crew", ctx=Store())], value=crew_call)

        return ast.unparse(assignment)

    def generate_imports(self, modules: List[Union[str, Dict[str, List[str]]]]) -> List[str]:
        """
        Import statements를 AST로 생성

        Args:
            modules: Import할 모듈 목록
                - 문자열: "import module"
                - Dict: {"module": ["name1", "name2"]} -> "from module import name1, name2"

        Returns:
            List[str]: Import 구문 목록
        """
        import_statements = []

        for module in modules:
            if isinstance(module, str):
                # Simple import: import module
                import_node = Import(names=[alias(name=module, asname=None)])
                import_statements.append(ast.unparse(import_node))

            elif isinstance(module, dict):
                # From import: from module import name1, name2
                for mod_name, names in module.items():
                    import_node = ImportFrom(
                        module=mod_name,
                        names=[alias(name=name, asname=None) for name in names],
                        level=0,
                    )
                    import_statements.append(ast.unparse(import_node))

        return import_statements

    def generate_create_agents_function(
        self, agents: List[Dict[str, Any]], tools_map: Optional[Dict[str, List[str]]] = None
    ) -> str:
        """
        create_agents() 함수를 AST로 생성

        Args:
            agents: Agent 목록
            tools_map: Agent ID별 도구 목록

        Returns:
            str: create_agents() 함수 코드
        """
        tools_map = tools_map or {}

        # 함수 본문 생성
        body = []

        # agents = {} 초기화
        agents_init = Assign(
            targets=[Name(id="agents", ctx=Store())], value=AstDict(keys=[], values=[])
        )
        body.append(agents_init)

        # 각 Agent 생성 및 할당
        for agent in agents:
            agent_id = agent.get("id", "agent")
            agent_tools = tools_map.get(agent_id, [])

            # Agent 생성 코드
            keywords_list = [
                keyword(arg="role", value=Constant(value=agent.get("role", "Agent"))),
                keyword(arg="goal", value=Constant(value=agent.get("goal", "Execute tasks"))),
                keyword(
                    arg="backstory", value=Constant(value=agent.get("backstory", "Expert agent"))
                ),
                keyword(arg="verbose", value=Constant(value=True)),
                keyword(
                    arg="allow_delegation",
                    value=Constant(value=agent.get("allow_delegation", False)),
                ),
            ]

            # Tools 추가
            if agent_tools:
                tools_list = AstList(
                    elts=[Name(id=tool, ctx=Load()) for tool in agent_tools], ctx=Load()
                )
                keywords_list.append(keyword(arg="tools", value=tools_list))

            agent_call = Call(func=Name(id="Agent", ctx=Load()), args=[], keywords=keywords_list)

            # agents['agent_id'] = Agent(...)
            agent_assign = Assign(
                targets=[
                    Subscript(
                        value=Name(id="agents", ctx=Load()),
                        slice=Constant(value=agent_id),
                        ctx=Store(),
                    )
                ],
                value=agent_call,
            )
            body.append(agent_assign)

        # return agents
        return_stmt = Return(value=Name(id="agents", ctx=Load()))
        body.append(return_stmt)

        # 함수 정의
        func_def = FunctionDef(
            name="create_agents",
            args=arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=body,
            decorator_list=[],
            returns=None,
        )

        # Fix missing locations
        ast.fix_missing_locations(func_def)

        return ast.unparse(func_def)

    def generate_create_tasks_function(self, tasks: List[Dict[str, Any]]) -> str:
        """
        create_tasks(agents) 함수를 AST로 생성

        Args:
            tasks: Task 목록

        Returns:
            str: create_tasks() 함수 코드
        """
        # 함수 본문 생성
        body = []

        # tasks = [] 초기화
        tasks_init = Assign(
            targets=[Name(id="tasks", ctx=Store())], value=AstList(elts=[], ctx=Load())
        )
        body.append(tasks_init)

        # 각 Task 생성 및 추가
        for task in tasks:
            agent_id = task.get("agent", "agent")

            # Agent 참조
            agent_ref = Subscript(
                value=Name(id="agents", ctx=Load()), slice=Constant(value=agent_id), ctx=Load()
            )

            # Task 생성
            task_call = Call(
                func=Name(id="Task", ctx=Load()),
                args=[],
                keywords=[
                    keyword(
                        arg="description",
                        value=Constant(value=task.get("description", "Execute task")),
                    ),
                    keyword(
                        arg="expected_output",
                        value=Constant(value=task.get("expected_output", "Task completed")),
                    ),
                    keyword(arg="agent", value=agent_ref),
                    keyword(
                        arg="human_input", value=Constant(value=task.get("human_input", False))
                    ),
                ],
            )

            # tasks.append(Task(...))
            append_call = Expr(
                value=Call(
                    func=Attribute(value=Name(id="tasks", ctx=Load()), attr="append", ctx=Load()),
                    args=[task_call],
                    keywords=[],
                )
            )
            body.append(append_call)

        # return tasks
        return_stmt = Return(value=Name(id="tasks", ctx=Load()))
        body.append(return_stmt)

        # 함수 정의
        func_def = FunctionDef(
            name="create_tasks",
            args=arguments(
                posonlyargs=[],
                args=[arg(arg="agents", annotation=None)],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=body,
            decorator_list=[],
            returns=None,
        )

        # Fix missing locations
        ast.fix_missing_locations(func_def)

        return ast.unparse(func_def)

    def generate_main_function(
        self, process: str = "sequential", has_user_inputs: bool = False
    ) -> str:
        """
        main() 함수를 AST로 생성

        Args:
            process: Process 타입
            has_user_inputs: 사용자 입력 수집 여부

        Returns:
            str: main() 함수 코드
        """
        body = []

        # agents = create_agents()
        agents_call = Assign(
            targets=[Name(id="agents", ctx=Store())],
            value=Call(func=Name(id="create_agents", ctx=Load()), args=[], keywords=[]),
        )
        body.append(agents_call)

        # tasks = create_tasks(agents)
        tasks_call = Assign(
            targets=[Name(id="tasks", ctx=Store())],
            value=Call(
                func=Name(id="create_tasks", ctx=Load()),
                args=[Name(id="agents", ctx=Load())],
                keywords=[],
            ),
        )
        body.append(tasks_call)

        # crew = Crew(...)
        process_attr = Attribute(value=Name(id="Process", ctx=Load()), attr=process, ctx=Load())

        crew_call = Assign(
            targets=[Name(id="crew", ctx=Store())],
            value=Call(
                func=Name(id="Crew", ctx=Load()),
                args=[],
                keywords=[
                    keyword(
                        arg="agents",
                        value=Call(
                            func=Name(id="list", ctx=Load()),
                            args=[
                                Call(
                                    func=Attribute(
                                        value=Name(id="agents", ctx=Load()),
                                        attr="values",
                                        ctx=Load(),
                                    ),
                                    args=[],
                                    keywords=[],
                                )
                            ],
                            keywords=[],
                        ),
                    ),
                    keyword(arg="tasks", value=Name(id="tasks", ctx=Load())),
                    keyword(arg="process", value=process_attr),
                    keyword(arg="verbose", value=Constant(value=True)),
                ],
            ),
        )
        body.append(crew_call)

        # result = crew.kickoff() or crew.kickoff(inputs=user_inputs)
        kickoff_args = []
        kickoff_keywords = []

        if has_user_inputs:
            kickoff_keywords.append(keyword(arg="inputs", value=Name(id="user_inputs", ctx=Load())))

        result_call = Assign(
            targets=[Name(id="result", ctx=Store())],
            value=Call(
                func=Attribute(value=Name(id="crew", ctx=Load()), attr="kickoff", ctx=Load()),
                args=kickoff_args,
                keywords=kickoff_keywords,
            ),
        )
        body.append(result_call)

        # return result
        return_stmt = Return(value=Name(id="result", ctx=Load()))
        body.append(return_stmt)

        # 함수 정의
        func_def = FunctionDef(
            name="main",
            args=arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=body,
            decorator_list=[],
            returns=None,
        )

        # Fix missing locations
        ast.fix_missing_locations(func_def)

        return ast.unparse(func_def)

    def generate_full_module(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        process: str = "sequential",
        tools_map: Optional[Dict[str, List[str]]] = None,
        docstring: Optional[str] = None,
    ) -> str:
        """
        전체 Python 모듈을 AST로 생성

        Args:
            agents: Agent 목록
            tasks: Task 목록
            process: Process 타입
            tools_map: Agent ID별 도구 목록
            docstring: 모듈 docstring

        Returns:
            str: 완전한 Python 모듈 코드
        """
        module_body = []

        # Docstring
        if docstring:
            module_body.append(Expr(value=Constant(value=docstring)))

        # Imports
        import_nodes = [
            ImportFrom(
                module="crewai",
                names=[
                    alias(name="Agent", asname=None),
                    alias(name="Task", asname=None),
                    alias(name="Crew", asname=None),
                    alias(name="Process", asname=None),
                ],
                level=0,
            )
        ]
        module_body.extend(import_nodes)

        # create_agents() 함수
        agents_func_code = self.generate_create_agents_function(agents, tools_map)
        agents_func_ast = ast.parse(agents_func_code).body[0]
        module_body.append(agents_func_ast)

        # create_tasks() 함수
        tasks_func_code = self.generate_create_tasks_function(tasks)
        tasks_func_ast = ast.parse(tasks_func_code).body[0]
        module_body.append(tasks_func_ast)

        # main() 함수
        main_func_code = self.generate_main_function(process)
        main_func_ast = ast.parse(main_func_code).body[0]
        module_body.append(main_func_ast)

        # if __name__ == "__main__": main()
        main_guard = If(
            test=Compare(
                left=Name(id="__name__", ctx=Load()),
                ops=[Eq()],
                comparators=[Constant(value="__main__")],
            ),
            body=[Expr(value=Call(func=Name(id="main", ctx=Load()), args=[], keywords=[]))],
            orelse=[],
        )
        module_body.append(main_guard)

        # 모듈 생성
        module = Module(body=module_body, type_ignores=[])

        # Fix missing locations
        ast.fix_missing_locations(module)

        # AST를 코드로 변환
        code = ast.unparse(module)

        # Black으로 포맷팅
        if self.use_black:
            code = self.format_with_black(code)

        return code

    def format_with_black(self, code: str) -> str:
        """
        Black으로 코드 포맷팅

        Args:
            code: Python 코드

        Returns:
            str: 포맷팅된 코드
        """
        try:
            import black

            mode = black.Mode(
                target_versions={black.TargetVersion.PY311},
                line_length=100,
            )
            return black.format_str(code, mode=mode)
        except ImportError:
            # Black이 설치되지 않은 경우 원본 반환
            return code
        except Exception:
            # 포맷팅 실패 시 원본 반환
            return code

    def validate_syntax(self, code: str) -> bool:
        """
        생성된 코드의 문법 검증

        Args:
            code: Python 코드

        Returns:
            bool: 문법이 유효하면 True
        """
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
