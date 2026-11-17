"""DSL 中间表示生成器

形式化: IR = Map(Tree)
- 将校验通过的 AST 节点映射为 Agent-IR 五元组对象
- 将 <RoleDef> 节点映射为 R 集合, <GoalDef> 节点映射为 G 集合
- 最终输出标准化的 JSON 格式中间表示, 供后续模块装配使用
"""
import json
from typing import Dict, Any
from .ast_nodes import AgentDef


class IRGenerator:
    """IR = Map(Tree)"""

    def generate(self, tree: AgentDef) -> Dict[str, Any]:
        """将 AST 映射为 Agent-IR 五元组 (R, G, M, T, P)"""
        if tree is None:
            raise ValueError("AST 为空, 无法生成 IR")

        ir = {
            "Role": {
                "role_id": tree.role.name if tree.role else "",
                "description": tree.role.description if tree.role else "",
                "capabilities": list(tree.role.capabilities) if tree.role else [],
            },
            "Goals": [
                {
                    "goal_id": g.name,
                    "type": g.goal_type,
                    "priority": g.priority,
                    "content": g.content,
                    "depends_on": g.depends_on,
                }
                for g in tree.goals
            ],
            "Memory": {
                "type": tree.memory.mem_type if tree.memory else "short",
                "storage": tree.memory.storage if tree.memory else "",
            },
            "Tools": [
                {
                    "tool_id": t.name,
                    "name": t.tool_name,
                    "params": [{"name": p.name, "type": p.type} for p in t.params],
                    "output_type": t.output_type,
                }
                for t in tree.tools
            ],
            "Planner": {
                "strategy": tree.planner.strategy if tree.planner else "CoT",
            },
            "agent_id": tree.agent_id,
        }
        return ir

    def to_json(self, ir: Dict[str, Any]) -> str:
        """输出标准化的 JSON 格式中间表示"""
        return json.dumps(ir, ensure_ascii=False, indent=2)
