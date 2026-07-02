"""Lexical analyzer (lex) for the ADE language.

This defines the language alphabet: which character sequences form a
valid token. PLY builds the lexer from the `tokens` tuple, the `t_*`
rules and the functions whose docstring is a regex.
"""

import ply.lex as lex

# Reserved words: identifier -> token type
reserved = {
    "sit": "SIT",  # prints to console: sit("Hello, World!")
}

# Full list of tokens the parser can receive
tokens = (
    "NUMBER",
    "STRING",
    "ID",
    "PLUS",
    "MINUS",
    "TIMES",
    "DIVIDE",
    "EQUALS",
    "LPAREN",
    "RPAREN",
) + tuple(reserved.values())

# Simple tokens: a single pattern, no extra logic
t_PLUS = r"\+"
t_MINUS = r"-"
t_TIMES = r"\*"
t_DIVIDE = r"/"
t_EQUALS = r"="
t_LPAREN = r"\("
t_RPAREN = r"\)"

# Characters the lexer ignores entirely (spaces and tabs)
t_ignore = " \t"


def t_STRING(t):
    r'"[^"\n]*"'
    t.value = t.value[1:-1]  # strip the quotes
    return t


def t_NUMBER(t):
    r"\d+(\.\d+)?"
    t.value = float(t.value) if "." in t.value else int(t.value)
    return t


def t_ID(t):
    r"[a-zA-Z_][a-zA-Z_0-9]*"
    # If the identifier is a reserved word, switch its type
    t.type = reserved.get(t.value, "ID")
    return t


def t_COMMENT(t):
    r"\#[^\n]*"
    pass  # comments produce no token


def t_newline(t):
    r"\n+"
    t.lexer.lineno += len(t.value)


def t_error(t):
    print(f"Illegal character {t.value[0]!r} at line {t.lexer.lineno}")
    t.lexer.skip(1)


def build_lexer():
    return lex.lex()


if __name__ == "__main__":
    # Quick check: tokenize one line and print each token
    lexer = build_lexer()
    lexer.input('sit("Hello, World!")  # my first program')
    for token in lexer:
        print(token)
