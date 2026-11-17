"""DSL AST 节点定义

AST 节点与 DSL 语法结构一一对应, 形成树状结构 Tree = (N, E)
根节点为 AgentDef, 子节点分别为 RoleDef/GoalDef/ToolDef/MemDef/PlanDef
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ASTNode:
    """AST 节点基类"""
    name: str = ""
    line: int = 0


@dataclass
class RoleDef(ASTNode):
    """角色定义节点: Role = (role_id, description, capabilities)"""
    description: str = ""
    capabilities: List[str] = field(default_factory=list)


@dataclass
class GoalDef(ASTNode):
    """目标定义节点: Goal = (goal_type, constraint, priority)"""
    goal_type: str = ""
    priority: float = 0.0
    content: str = ""
    depends_on: Optional[str] = None


@dataclass
class Param:
    """工具参数: ID ':' TYPE"""
    name: str
    type: str


@dataclass
class ToolDef(ASTNode):
    """工具定义节点: Tool = (name, input_type, output_type, api)"""
    tool_name: str = ""
    params: List[Param] = field(default_factory=list)
    output_type: str = ""


@dataclass
class MemDef(ASTNode):
    """记忆定义节点: Memory = (M_short, M_long)"""
    mem_type: str = "short"
    storage: str = ""


@dataclass
class PlanDef(ASTNode):
    """规划策略节点: Planner = (candidates, strategy)"""
    strategy: str = "CoT"


@dataclass
class AgentDef(ASTNode):
    """智能体根节点: AgentDef -> 'agent' ID '{' RoleDef GoalDef* ToolDef* MemDef PlanDef '}'"""
    agent_id: str = ""
    role: Optional[RoleDef] = None
    goals: List[GoalDef] = field(default_factory=list)
    tools: List[ToolDef] = field(default_factory=list)
    memory: Optional[MemDef] = None
    planner: Optional[PlanDef] = None
