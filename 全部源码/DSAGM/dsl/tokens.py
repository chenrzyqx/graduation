"""DSL Token 类型定义"""


from enum import Enum
from dataclasses import dataclass
from typing import Any


class TokenType(Enum):
    KEYWORD = "KEYWORD"
    ID = "ID"
    STRING = "STRING"
    FLOAT = "FLOAT"
    INT = "INT"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    COLON = "COLON"
    COMMA = "COMMA"
    TYPE_ANNOT = "TYPE_ANNOT"
    EOF = "EOF"


KEYWORDS = {
    "agent", "role", "goal", "tool", "memory", "planner",
    "description", "capabilities", "type", "priority", "content",
    "name", "params", "input", "output", "storage", "strategy",
    "short", "long", "depends_on",
    "CoT", "ReAct", "ToT",
    "classification", "generation", "reasoning",
    "string", "int", "float", "bool",
}


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int = 0
    col: int = 0

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:C{self.col})"
