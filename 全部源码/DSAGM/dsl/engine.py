"""DSL 解析引擎

基于 ANTLR4 工具链, 引擎执行流程分为四个阶段:
1. 词法分析 Lexical Analysis:      Lex(T) = K
2. 语法分析 Syntax Analysis:       Parse(K) = Tree
3. 语义访问与校验 Semantic Validation: Valid(Tree)
4. 中间表示生成 IR Generation:     IR = Map(Tree)
"""
from typing import Tuple, Dict, Any
from .lexer import Lexer
from .parser import Parser
from .validator import SemanticValidator
from .ir_generator import IRGenerator
from .ast_nodes import AgentDef
from .tokens import Token


class DSLEngine:
    """ANTLR4 风格四阶段解析引擎

    完整对应:
        Lex(T)     = K
        Parse(K)   = Tree
        Valid(Tree)= True/False
        IR         = Map(Tree)
    """

    def __init__(self):
        self.lexer = Lexer()
        self.parser_cls = Parser
        self.validator = SemanticValidator()
        self.ir_generator = IRGenerator()

    def parse(self, dsl_text: str, *, validate: bool = True) -> Tuple[Dict[str, Any], AgentDef]:
        """完整四阶段流水线: DSL 文本 -> Token -> AST -> 校验 -> Agent-IR"""
        # 阶段 1: Lex(T) = K
        tokens = self.lexer.lex(dsl_text)

        # 阶段 2: Parse(K) = Tree
        parser = self.parser_cls(tokens)
        ast: AgentDef = parser.parse()

        # 阶段 3: Valid(Tree)
        if validate and not self.validator.validate(ast):
            raise ValueError("语义校验失败: Φ_sem 不成立")

        # 阶段 4: IR = Map(Tree)
        ir = self.ir_generator.generate(ast)
        return ir, ast
