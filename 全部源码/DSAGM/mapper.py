"""DSAGM 语义映射函数 f_map

f_map: AST -> Agent-IR
建立语法节点到语义对象的转换规则, 确保结构信息的无损传递.
"""
from typing import Dict, Any
from .dsl.ast_nodes import AgentDef
from .agent_ir import AgentIR, Role, Goal, Memory, Tool, Planner


def f_map(ast: AgentDef) -> AgentIR:
    """将语法结构转换为语义中间表示模型 Agent-IR"""
    if ast is None:
        raise ValueError("AST 为空, 无法执行 f_map")

    role = Role(
        role_id=ast.role.name if ast.role else "",
        description=ast.role.description if ast.role else "",
        capabilities=list(ast.role.capabilities) if ast.role else [],
    )

    goals = [
        Goal(
            goal_id=g.name, goal_type=g.goal_type, priority=g.priority,
            content=g.content, depends_on=g.depends_on,
        )
        for g in ast.goals
    ]

    memory = Memory(
        mem_type=ast.memory.mem_type if ast.memory else "short",
        storage=ast.memory.storage if ast.memory else "",
    )

    tools = [
        Tool(
            tool_id=t.name, name=t.tool_name,
            params=[{"name": p.name, "type": p.type} for p in t.params],
            output_type=t.output_type,
        )
        for t in ast.tools
    ]

    planner = Planner(strategy=ast.planner.strategy if ast.planner else "CoT")

    return AgentIR(
        Role=role, Goals=goals, Memory=memory,
        Tools=tools, Planner=planner,
        agent_id=ast.agent_id,
    )
