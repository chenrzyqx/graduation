"""Agent-IR 五元组形式化建模

Agent-IR = (R, G, M, T, P)
- R: 角色集合
- G: 目标集合
- M: 记忆模型
- T: 工具集合
- P: 规划策略集合
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import numpy as np


@dataclass
class Role:
    """Role = (role_id, description, capabilities)

    role_id:    角色唯一标识符, 用于在语义模型中进行索引
    description:角色的自然语言描述信息, 用于在提示生成阶段定义智能体身份与表达风格
    capabilities: 能力约束集合, 用于限定该角色在执行过程中的行为范围
    """
    role_id: str = ""
    description: str = ""
    capabilities: List[str] = field(default_factory=list)


@dataclass
class Goal:
    """Goal = (goal_type, constraint, priority)

    goal_type:  目标类型 (推理类/检索类/生成类)
    constraint: 目标执行时必须满足的约束条件 (输出格式限制或逻辑规则)
    priority:   目标优先级权重, 满足归一化约束 Σw_i = 1
    """
    goal_id: str = ""
    goal_type: str = ""
    priority: float = 0.0
    content: str = ""
    depends_on: Optional[str] = None

    @property
    def constraint(self) -> str:
        return self.content


@dataclass
class Memory:
    """Memory = (M_short, M_long)

    M_short: 短期记忆, 维护当前对话上下文
    M_long:  长期记忆, 存储历史经验与外部知识 (向量集合)
    """
    mem_type: str = "short"
    storage: str = ""
    short_term: List[str] = field(default_factory=list)
    long_term: List[Dict[str, Any]] = field(default_factory=list)

    def retrieve(self, query_emb: np.ndarray, k: int = 1) -> List[Dict[str, Any]]:
        """记忆检索: argmax_{e_i ∈ M_long} cos(q, e_i.embedding)"""
        if not self.long_term:
            return []
        sims = []
        for item in self.long_term:
            emb = np.asarray(item.get("embedding", []))
            if emb.size == 0 or query_emb.size == 0:
                continue
            denom = np.linalg.norm(query_emb) * np.linalg.norm(emb) + 1e-9
            sims.append((np.dot(query_emb, emb) / denom, item))
        sims.sort(key=lambda x: -x[0])
        return [s[1] for s in sims[:k]]


@dataclass
class Tool:
    """Tool = (name, input_type, output_type, api)"""
    tool_id: str = ""
    name: str = ""
    params: List[Dict[str, str]] = field(default_factory=list)
    output_type: str = ""
    api: Optional[callable] = None

    def decide(self, state_vec: np.ndarray) -> float:
        raise NotImplementedError('Tool utility must come from the configured planner and observed state')


@dataclass
class Planner:
    """Planner = (candidates, strategy)

    strategy: 候选规划策略
    state:    当前语义状态向量
    U:        策略效用函数值
    """
    candidates: List[str] = field(default_factory=lambda: ["CoT", "ReAct", "ToT"])
    strategy: str = "CoT"

    def select(self, state_vec: np.ndarray) -> str:
        """策略选择: P* = argmax_p U(s, p)"""
        return self.strategy

    def transition(self, s_t: np.ndarray, a: Any) -> np.ndarray:
        """状态转移: s_{t+1} = T(s_t, a)"""
        return s_t


@dataclass
class AgentIR:
    """Agent-IR = (R, G, M, T, P) 五元组

    智能体语义的最小完备表达单元, 任何复杂智能体系统均可在此抽象结构上进行扩展.
    """
    Role: Role = field(default_factory=Role)
    Goals: List[Goal] = field(default_factory=list)
    Memory: Memory = field(default_factory=Memory)
    Tools: List[Tool] = field(default_factory=list)
    Planner: Planner = field(default_factory=Planner)
    agent_id: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "Role": {"role_id": self.Role.role_id,
                     "description": self.Role.description,
                     "capabilities": self.Role.capabilities},
            "Goals": [{"goal_id": g.goal_id, "type": g.goal_type,
                       "priority": g.priority, "content": g.content,
                       "depends_on": g.depends_on} for g in self.Goals],
            "Memory": {"type": self.Memory.mem_type,
                       "storage": self.Memory.storage},
            "Tools": [{"tool_id": t.tool_id, "name": t.name,
                       "params": t.params, "output_type": t.output_type}
                      for t in self.Tools],
            "Planner": {"strategy": self.Planner.strategy},
        }

    def structure_integrity(self, threshold=None) -> bool:
        """Check configured/assembled instances, not neural-vector norms or case count."""
        if not self.Role.role_id or not self.Goals or not self.Memory.storage:
            return False
        if self.Planner.strategy not in {'CoT', 'ReAct', 'ToT'} or not self.Tools:
            return False
        names = [g.goal_id for g in self.Goals]
        if len(names) != len(set(names)) or abs(sum(g.priority for g in self.Goals) - 1) > 1e-6:
            return False
        if any(not 0 <= g.priority <= 1 or (g.depends_on and g.depends_on not in names) for g in self.Goals):
            return False
        allowed = {'string', 'int', 'float', 'bool'}
        return all(callable(t.api) and t.output_type in allowed
                   and all(p.get('type') in allowed for p in t.params) for t in self.Tools)
