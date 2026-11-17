"""DSL 语义校验器

采用访问者模式 (Visitor Pattern) 遍历 AST 节点, 执行语义级校验:
- 优先级归一化校验: Σw_i = 1, |W - 1.0| > ε 则报错
- 工具参数类型匹配: 检查 ToolDef 中参数类型是否在支持类型集合内
- 依赖环检测: 构建有向图 G_dep = (V_goal, E_dep), DFS 检测是否存在环
"""
from typing import List, Set, Dict
from .ast_nodes import AgentDef, GoalDef, ToolDef
from .parser import SyntaxException

EPSILON = 1e-6

SUPPORTED_TYPES = {"classification", "generation", "reasoning",
                   "string", "int", "float", "bool"}


class SemanticValidationError(Exception):
    pass


class SemanticValidator:
    """Valid(Tree) = True iff Φ_sem(Tree) holds"""

    def validate(self, tree: AgentDef) -> bool:
        if tree is None:
            return False
        for collection in (tree.goals, tree.tools):
            names = [node.name for node in collection]
            if len(names) != len(set(names)):
                raise SemanticValidationError("Duplicate component identifier")
        for goal in tree.goals:
            if not 0 <= goal.priority <= 1:
                raise SemanticValidationError("Goal priority must be in [0, 1]")
        self._check_priority_normalization(tree)
        self._check_tool_param_types(tree)
        self._check_goal_dependency_cycle(tree)
        return True

    def _check_priority_normalization(self, tree: AgentDef):
        """优先级归一化校验 Σw_i = 1"""
        if not tree.goals:
            raise SemanticValidationError("目标集合为空: 至少需要一个 GoalDef")
        total = sum(g.priority for g in tree.goals)
        if abs(total - 1.0) > EPSILON:
            raise SemanticValidationError(
                f"目标优先级未归一化: Σw_i = {total:.6f}, 期望 1.0 (容差 {EPSILON})"
            )

    def _check_tool_param_types(self, tree: AgentDef):
        """工具参数类型匹配"""
        for tool in tree.tools:
            for p in tool.params:
                if p.type not in SUPPORTED_TYPES:
                    raise SemanticValidationError(
                        f"工具 {tool.tool_name} 参数 {p.name} 类型 {p.type!r} 不在支持集合内"
                    )
            if tool.output_type not in SUPPORTED_TYPES:
                raise SemanticValidationError(
                    f"工具 {tool.tool_name} 输出类型 {tool.output_type!r} 不在支持集合内"
                )

    def _check_goal_dependency_cycle(self, tree: AgentDef):
        """依赖环检测

        构建有向图 G_dep = (V_goal, E_dep), 通过深度优先搜索 (DFS) 检测是否存在环.
        若存在环, 则说明目标定义存在逻辑死锁.
        """
        V_goal: Dict[str, GoalDef] = {g.name: g for g in tree.goals}
        E_dep: Dict[str, str] = {}
        for g in tree.goals:
            if g.depends_on:
                if g.depends_on not in V_goal:
                    raise SemanticValidationError(
                        f"目标 {g.name} depends_on 不存在目标 {g.depends_on!r}"
                    )
                E_dep[g.name] = g.depends_on

        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {v: WHITE for v in V_goal}

        def dfs(u: str):
            color[u] = GRAY
            v = E_dep.get(u)
            if v is not None:
                if color[v] == GRAY:
                    raise SemanticValidationError(
                        f"目标依赖存在环 (逻辑死锁): {u} -> {v}"
                    )
                if color[v] == WHITE:
                    dfs(v)
            color[u] = BLACK

        for v in list(V_goal.keys()):
            if color[v] == WHITE:
                dfs(v)
