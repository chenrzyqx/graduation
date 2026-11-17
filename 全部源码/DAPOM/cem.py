"""DAPOM 约束抽取引擎 CEM

四级流水线:
1. 词法分析:   将 DSL 文本切分为 Token
2. 语法分析:   根据 BNF 构建 AST
3. 语义访问器: 深度优先遍历 AST, 为每类约束节点设计独立访问器
4. 约束归一化与校验: (1) 优先级归一化 [0,1] 且 Σ=1;
                    (2) 能力约束无自相矛盾;
                    (3) 工具调用次数非负;
                    (4) 输出格式符合预定义枚举
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, List, Tuple
import numpy as np

from DSAGM.dsl.engine import DSLEngine
from DSAGM.dsl.ast_nodes import AgentDef


class CEMConstraintError(Exception):
    pass


class ConstraintExtractionEngine:
    """ε: P -> C  (从 DSL 中提取语义约束)

    从 DSL 语法树中提取 5 类约束:
    - C_goal:     目标优先级约束
    - C_role:     角色能力边界约束
    - C_tool:     工具调用限制
    - C_memory:   记忆使用限制
    - C_output:   输出格式与风格约束
    """

    def __init__(self, constraint_dim: int = 128):
        if constraint_dim < 20:
            raise ValueError('constraint_dim must reserve at least 20 semantic fields')
        self.engine = DSLEngine()
        self.constraint_dim = constraint_dim

    def extract(self, dsl_text: str, runtime_constraints=None) -> Tuple[Dict[str, Any], "ConstraintVector"]:
        """ε(P) = C

        四级流水线: DSL 文本 -> Token -> AST -> 语义访问 -> 约束对象 -> 向量化
        """
        # 阶段 1-2: 词法分析 + 语法分析
        _ir_dict, ast = self.engine.parse(dsl_text)

        # 阶段 3: 语义访问器 (深度优先遍历 AST)
        constraints = self._visit_ast(ast)
        configured = runtime_constraints or {}
        unknown_tools = set(configured.get('tool_limits', {})) - {t['tool_id'] for t in constraints['C_tool']}
        if unknown_tools:
            raise CEMConstraintError(f'Limits reference undeclared tools: {unknown_tools}')
        for tool in constraints['C_tool']:
            if tool['tool_id'] in configured.get('tool_limits', {}):
                tool['max_calls'] = configured['tool_limits'][tool['tool_id']]
                tool['limit_source'] = 'runtime_constraints.tool_limits'
        constraints['C_output'] = dict(configured.get('output', {}))
        constraints['C_budget'] = dict(configured.get('budget', {}))
        constraints['sources'] = {'C_goal': 'DSL.goal', 'C_role': 'DSL.role',
                                  'C_tool': 'DSL.tool + explicit runtime tool_limits',
                                  'C_output': 'runtime_constraints.output',
                                  'C_budget': 'runtime_constraints.budget'}

        # 阶段 4: 约束归一化与校验
        self._normalize_and_validate(constraints)

        # 约束向量化
        constraint_vec = self._vectorize(constraints)
        return constraints, constraint_vec

    def _visit_ast(self, ast: AgentDef) -> Dict[str, Any]:
        """深度优先遍历 AST, 抽取每类约束"""
        constraints = {
            "C_goal": [],
            "C_role": {},
            "C_tool": [],
            "C_memory": {},
            "C_output": {},
        }

        # 角色能力边界约束 (C_role)
        if ast.role:
            constraints["C_role"] = {
                "role_id": ast.role.name,
                "description": ast.role.description,
                "capabilities": list(ast.role.capabilities),
                "forbidden_actions": [],
            }

        # 目标优先级约束 (C_goal)
        for g in ast.goals:
            constraints["C_goal"].append({
                "goal_id": g.name,
                "type": g.goal_type,
                "priority": g.priority,
                "content": g.content,
                "depends_on": g.depends_on,
            })

        # 工具调用限制 (C_tool)
        for t in ast.tools:
            constraints["C_tool"].append({
                "tool_id": t.name,
                "name": t.tool_name,
                "params": [{"name": p.name, "type": p.type} for p in t.params],
                "output_type": t.output_type,
            })

        # 记忆使用限制 (C_memory)
        if ast.memory:
            constraints["C_memory"] = {
                "type": ast.memory.mem_type,
                "storage": ast.memory.storage,
            }

        # 输出格式与风格约束 (C_output)
        return constraints

    def _normalize_and_validate(self, constraints: Dict[str, Any]):
        """约束归一化与校验

        (1) 目标优先级归一化到 [0,1] 且总和为 1
        (2) 能力约束无自相矛盾
        (3) 工具调用次数非负
        (4) 输出格式符合预定义枚举
        """
        # (1) 目标优先级归一化
        goals = constraints["C_goal"]
        if goals:
            total = sum(g["priority"] for g in goals)
            if total > 0:
                for g in goals:
                    g["priority"] = g["priority"] / total
            total_after = sum(g["priority"] for g in goals)
            if abs(total_after - 1.0) > 1e-6:
                raise CEMConstraintError(
                    f"目标优先级未归一化: Σ = {total_after:.6f}"
                )

        # (2) 能力约束无自相矛盾
        caps = set(constraints["C_role"].get("capabilities", []))
        forbidden = set(constraints["C_role"].get("forbidden_actions", []))
        if caps & forbidden:
            raise CEMConstraintError(
                f"能力约束自相矛盾: {caps & forbidden} 同时出现在 capabilities 和 forbidden"
            )

        # (3) 工具调用次数非负
        for t in constraints["C_tool"]:
            if "max_calls" in t and (not isinstance(t['max_calls'], int) or t["max_calls"] < 0):
                raise CEMConstraintError(
                    f"工具 {t['tool_id']} 调用次数 {t['max_calls']} 为负"
                )

        # (4) 输出格式符合预定义枚举
        valid_formats = {"json", "text", "xml", "markdown"}
        if constraints["C_output"].get("format") is not None and constraints["C_output"]["format"] not in valid_formats:
            raise CEMConstraintError(
                f"输出格式 {constraints['C_output'].get('format')} 不在枚举内"
            )

    def _vectorize(self, constraints: Dict[str, Any]) -> "ConstraintVector":
        """约束向量化 c ∈ R^k

        将结构化约束集合嵌入至向量空间, 适配优化模型的计算需求.
        """
        vec = np.zeros(self.constraint_dim, dtype=np.float32)

        for i, g in enumerate(constraints["C_goal"][:5]):
            vec[i] = g["priority"]

        caps = constraints["C_role"].get("capabilities", [])
        vec[5] = min(len(caps) / 5.0, 1.0)
        vec[6] = 1.0 if constraints["C_role"].get("description") else 0.0

        for i, t in enumerate(constraints["C_tool"][:5]):
            vec[10 + i] = float(t.get("max_calls", 0))

        mem = constraints["C_memory"]
        vec[15] = 1.0 if mem.get("type") == "long" else 0.0
        vec[16] = 1.0 if mem.get("storage") else 0.0
        vec[17] = min(mem.get("max_retrieval", 0) / 10.0, 1.0)

        out = constraints["C_output"]
        vec[18] = 1.0 if out.get("format") == "json" else 0.0
        vec[19] = 1.0 if out.get("strategy") else 0.0

        # Reserved dimensions remain zero; no fabricated semantic features.
        return ConstraintVector(vec, constraints)


class ConstraintVector:
    """约束向量表示 c ∈ R^k"""

    def __init__(self, vec: np.ndarray, raw: Dict[str, Any]):
        self.vec = vec
        self.raw = raw
        self.dim = len(vec)

    def __repr__(self):
        return f"ConstraintVector(dim={self.dim}, |c|={np.linalg.norm(self.vec):.4f})"
