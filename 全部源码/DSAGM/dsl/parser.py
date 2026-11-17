"""DSL 语法分析器

形式化: Parse(K) = Tree
- 基于 LL(*) 算法的语法分析器
- 验证 Token 序列是否符合 BNF 语法结构
- 若存在语法错误则抛出 SyntaxException
- AST 节点与 DSL 语法结构一一对应, 形成树状结构 Tree = (N, E)
"""
from typing import List, Optional
from .tokens import Token, TokenType
from .ast_nodes import AgentDef, RoleDef, GoalDef, ToolDef, MemDef, PlanDef, Param


class SyntaxException(Exception):
    """若存在语法错误则抛出"""
    pass


class Parser:
    """LL(*) 递归下降语法分析器: Parse(K) -> Tree"""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, ttype: TokenType, value=None) -> Token:
        tok = self._peek()
        if tok.type != ttype or (value is not None and tok.value != value):
            raise SyntaxException(
                f"Syntax error at L{tok.line}:C{tok.col}: expected {ttype.name}"
                f"{'/'+value if value else ''}, got {tok.type.name}/{tok.value!r}"
            )
        return self._advance()

    def _match(self, ttype: TokenType, value=None) -> Optional[Token]:
        tok = self._peek()
        if tok.type == ttype and (value is None or tok.value == value):
            return self._advance()
        return None

    def parse(self) -> AgentDef:
        """S -> 'agent' ID '{' RoleDef GoalDef* ToolDef* MemDef PlanDef '}'"""
        self._expect(TokenType.KEYWORD, "agent")
        agent_id = self._expect(TokenType.ID).value
        self._expect(TokenType.LBRACE)

        role = self._parse_role()
        goals = self._parse_goals()
        tools = self._parse_tools()
        memory = self._parse_memory()
        planner = self._parse_planner()

        self._expect(TokenType.RBRACE)
        self._expect(TokenType.EOF)

        return AgentDef(
            agent_id=agent_id,
            role=role,
            goals=goals,
            tools=tools,
            memory=memory,
            planner=planner,
            line=1,
        )

    def _parse_role(self) -> RoleDef:
        """RoleDef -> 'role' ID '{' 'description' STRING 'capabilities' '[' IDList ']' '}'"""
        self._expect(TokenType.KEYWORD, "role")
        role_id = self._expect(TokenType.ID).value
        self._expect(TokenType.LBRACE)

        self._expect(TokenType.KEYWORD, "description")
        desc = self._expect(TokenType.STRING).value

        self._expect(TokenType.KEYWORD, "capabilities")
        self._expect(TokenType.LBRACKET)
        caps = self._parse_id_list()
        self._expect(TokenType.RBRACKET)
        self._expect(TokenType.RBRACE)

        return RoleDef(name=role_id, description=desc, capabilities=caps)

    def _parse_id_list(self) -> List[str]:
        """IDList -> ID | ID ',' IDList"""
        ids = [self._expect(TokenType.ID).value]
        while self._match(TokenType.COMMA):
            ids.append(self._expect(TokenType.ID).value)
        return ids

    def _parse_goals(self) -> List[GoalDef]:
        """GoalDef 可重复"""
        goals = []
        while self._peek().type == TokenType.KEYWORD and self._peek().value == "goal":
            self._advance()
            goal_id = self._expect(TokenType.ID).value
            self._expect(TokenType.LBRACE)

            self._expect(TokenType.KEYWORD, "type")
            gtype = self._parse_type()

            self._expect(TokenType.KEYWORD, "priority")
            priority = self._expect(TokenType.FLOAT).value

            content = ""
            if self._match(TokenType.KEYWORD, "content"):
                content = self._expect(TokenType.STRING).value

            depends_on = None
            if self._match(TokenType.KEYWORD, "depends_on"):
                depends_on = self._expect(TokenType.ID).value

            self._expect(TokenType.RBRACE)
            goals.append(GoalDef(
                name=goal_id, goal_type=gtype,
                priority=priority, content=content,
                depends_on=depends_on,
            ))
        return goals

    def _parse_tools(self) -> List[ToolDef]:
        """ToolDef 可重复"""
        tools = []
        while self._peek().type == TokenType.KEYWORD and self._peek().value == "tool":
            self._advance()
            tool_id = self._expect(TokenType.ID).value
            self._expect(TokenType.LBRACE)

            self._expect(TokenType.KEYWORD, "name")
            tname = self._expect(TokenType.STRING).value

            params = []
            if self._match(TokenType.KEYWORD, "params"):
                params = self._parse_param_list()
            elif self._match(TokenType.KEYWORD, "input"):
                params = self._parse_param_list()

            self._expect(TokenType.KEYWORD, "output")
            otype = self._parse_type()

            self._expect(TokenType.RBRACE)
            tools.append(ToolDef(
                name=tool_id, tool_name=tname,
                params=params, output_type=otype,
            ))
        return tools

    def _parse_param_list(self) -> List[Param]:
        """ParamList -> Param | Param ',' ParamList"""
        params = [self._parse_param()]
        while self._match(TokenType.COMMA):
            params.append(self._parse_param())
        return params

    def _parse_param(self) -> Param:
        """Param -> ID ':' TYPE"""
        pname = self._expect(TokenType.ID).value
        self._expect(TokenType.COLON)
        ptype = self._parse_type()
        return Param(name=pname, type=ptype)

    def _parse_memory(self) -> MemDef:
        """MemDef -> 'memory' '{' 'type' ('short'|'long') 'storage' STRING '}'"""
        self._expect(TokenType.KEYWORD, "memory")
        self._expect(TokenType.LBRACE)

        self._expect(TokenType.KEYWORD, "type")
        mtok = self._peek()
        if mtok.type == TokenType.KEYWORD and mtok.value in ("short", "long"):
            mem_type = self._advance().value
        else:
            raise SyntaxException(
                f"Syntax error at L{mtok.line}:C{mtok.col}: expected 'short'|'long'"
            )

        self._expect(TokenType.KEYWORD, "storage")
        storage = self._expect(TokenType.STRING).value
        self._expect(TokenType.RBRACE)

        return MemDef(mem_type=mem_type, storage=storage)

    def _parse_planner(self) -> PlanDef:
        """PlanDef -> 'planner' '{' 'strategy' ('CoT'|'ReAct'|'ToT') '}'"""
        self._expect(TokenType.KEYWORD, "planner")
        self._expect(TokenType.LBRACE)

        self._expect(TokenType.KEYWORD, "strategy")
        stok = self._peek()
        if stok.type == TokenType.KEYWORD and stok.value in ("CoT", "ReAct", "ToT"):
            strategy = self._advance().value
        else:
            raise SyntaxException(
                f"Syntax error at L{stok.line}:C{stok.col}: expected 'CoT'|'ReAct'|'ToT'"
            )

        self._expect(TokenType.RBRACE)
        return PlanDef(strategy=strategy)

    def _parse_type(self) -> str:
        """TYPE ∈ {'classification','generation','reasoning','string','int','float','bool'}"""
        tok = self._peek()
        if tok.type == TokenType.KEYWORD and tok.value in (
            "classification", "generation", "reasoning",
            "string", "int", "float", "bool",
        ):
            return self._advance().value
        raise SyntaxException(
            f"Syntax error at L{tok.line}:C{tok.col}: invalid TYPE {tok.value!r}"
        )
