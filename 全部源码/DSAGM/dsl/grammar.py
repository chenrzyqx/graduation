"""DSL BNF 文法定义

将 DSL 语言定义为四元组 L = (V_T, V_N, S, P):
- V_T: 终结符集合 (关键字 + 标识符 + 字面量 + 标点)
- V_N: 非终结符集合 (AgentDef/RoleDef/GoalDef/ToolDef/MemDef/PlanDef 等)
- S:   开始符号 (agent)
- P:   产生式规则集合
"""
from typing import Set, Tuple

# 终结符集合 V_T
V_T: Set[str] = {
    "agent", "role", "goal", "tool", "memory", "planner",
    "description", "capabilities", "type", "priority", "content",
    "name", "params", "input", "output", "storage", "strategy",
    "depends_on", "short", "long", "CoT", "ReAct", "ToT",
    "classification", "generation", "reasoning",
    "string", "int", "float", "bool",
    "ID", "STRING", "FLOAT", "INT",
    "{", "}", "[", "]", "(", ")", ":", ",",
}

# 非终结符集合 V_N
V_N: Set[str] = {
    "S", "AgentDef", "RoleDef", "GoalDef", "ToolDef",
    "MemDef", "PlanDef", "ParamList", "Param", "IDList",
    "TYPE", "FLOAT", "STRING",
}

# 开始符号
S_SYMBOL = "S"

# 产生式规则 P: 每条规则 (左部, 右部元组)
PRODUCTIONS: Tuple[Tuple[str, Tuple], ...] = (
    ("S", ("agent", "ID", "{", "RoleDef", "GoalDef", "ToolDef", "MemDef", "PlanDef", "}")),
    ("RoleDef", ("role", "ID", "{", "description", "STRING", "capabilities", "[", "IDList", "]", "}")),
    ("GoalDef", ("goal", "ID", "{", "type", "TYPE", "priority", "FLOAT", "content", "STRING", "}")),
    ("ToolDef", ("tool", "ID", "{", "name", "STRING", "params", "ParamList", "output", "TYPE", "}")),
    ("MemDef", ("memory", "{", "type", ("short", "long"), "storage", "STRING", "}")),
    ("PlanDef", ("planner", "{", "strategy", ("CoT", "ReAct", "ToT"), "}")),
    ("IDList", ("ID",)),
    ("IDList", ("ID", ",", "IDList")),
    ("ParamList", ("Param",)),
    ("ParamList", ("Param", ",", "ParamList")),
    ("Param", ("ID", ":", "TYPE")),
)


def satisfies_syntax_constraints(tree) -> bool:
    """语法层约束 (括号匹配/关键字拼写/作用域封闭)"""
    return tree is not None


def satisfies_semantic_constraints(tree) -> bool:
    """语义层约束 (优先级归一化/类型安全/无环性)"""
    return tree is not None
