"""DSL 词法分析器

形式化: Lex(T) = K
- 输入 DSL 文本流 T = t1 t2 ... tm
- 通过正则规则匹配生成 Token 序列 K = k1 k2 ... kn
- 每个 Token ki 是二元组 (type, value)
- 过滤空白字符/注释等非语义内容
"""
import re
import json
from typing import List
from .tokens import Token, TokenType, KEYWORDS


class LexerError(Exception):
    pass


class Lexer:
    """词法分析器 Lex: T -> K"""

    TOKEN_SPEC = [
        ('STRING',   r'"(?:\\.|[^"\\])*"'),
        ('FLOAT',    r'\d+\.\d+'),
        ('INT',      r'\d+'),
        ('ID',       r'[a-zA-Z_][a-zA-Z0-9_]*'),
        ('LBRACE',   r'\{'),
        ('RBRACE',   r'\}'),
        ('LBRACKET', r'\['),
        ('RBRACKET', r'\]'),
        ('LPAREN',   r'\('),
        ('RPAREN',   r'\)'),
        ('COLON',    r':'),
        ('COMMA',    r','),
        ('NEWLINE',  r'\n'),
        ('SKIP',     r'[ \t\r]+'),
        ('COMMENT',  r'//[^\n]*'),
    ]

    def __init__(self):
        self.regex = re.compile('|'.join(f'(?P<{name}>{pat})' for name, pat in self.TOKEN_SPEC))

    def lex(self, text: str) -> List[Token]:
        """Lex(T) = K"""
        tokens: List[Token] = []
        line, col = 1, 1

        cursor = 0
        for m in self.regex.finditer(text):
            kind = m.lastgroup
            value = m.group()
            pos = m.start()
            if pos != cursor:
                raise LexerError(f"Unexpected character at offset {cursor}: {text[cursor:pos]!r}")
            cursor = m.end()

            if kind in ('SKIP', 'COMMENT'):
                col += len(value)
                continue
            if kind == 'NEWLINE':
                line += 1
                col = 1
                continue

            if kind == 'STRING':
                tokens.append(Token(TokenType.STRING, json.loads(value), line, col))
            elif kind == 'FLOAT':
                tokens.append(Token(TokenType.FLOAT, float(value), line, col))
            elif kind == 'INT':
                tokens.append(Token(TokenType.INT, int(value), line, col))
            elif kind == 'ID':
                if value in KEYWORDS:
                    tokens.append(Token(TokenType.KEYWORD, value, line, col))
                else:
                    tokens.append(Token(TokenType.ID, value, line, col))
            else:
                tt = {
                    'LBRACE': TokenType.LBRACE, 'RBRACE': TokenType.RBRACE,
                    'LBRACKET': TokenType.LBRACKET, 'RBRACKET': TokenType.RBRACKET,
                    'LPAREN': TokenType.LPAREN, 'RPAREN': TokenType.RPAREN,
                    'COLON': TokenType.COLON, 'COMMA': TokenType.COMMA,
                }[kind]
                tokens.append(Token(tt, value, line, col))

            col += len(value)

        if cursor != len(text):
            raise LexerError(f"Unexpected character at offset {cursor}: {text[cursor:]!r}")
        tokens.append(Token(TokenType.EOF, None, line, col))
        return tokens
