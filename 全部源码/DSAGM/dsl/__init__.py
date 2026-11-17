"""DSL 模块入口 - 暴露四阶段解析引擎"""
from .engine import DSLEngine
from .tokens import Token, TokenType
from .ast_nodes import (
    AgentDef, RoleDef, GoalDef, ToolDef, MemDef, PlanDef, Param,
)
from .lexer import Lexer, LexerError
from .parser import Parser, SyntaxException
from .validator import SemanticValidator, SemanticValidationError
from .ir_generator import IRGenerator
from .grammar import (
    V_T, V_N, S_SYMBOL, PRODUCTIONS,
    satisfies_syntax_constraints, satisfies_semantic_constraints,
)

__all__ = [
    "DSLEngine", "Token", "TokenType",
    "AgentDef", "RoleDef", "GoalDef", "ToolDef", "MemDef", "PlanDef", "Param",
    "Lexer", "LexerError", "Parser", "SyntaxException",
    "SemanticValidator", "SemanticValidationError",
    "IRGenerator",
    "V_T", "V_N", "S_SYMBOL", "PRODUCTIONS",
    "satisfies_syntax_constraints", "satisfies_semantic_constraints",
]
