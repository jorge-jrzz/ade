"""Syntax analyzer (yacc) for the ADE language.

From the lexer tokens it builds an AST (abstract syntax tree) made of
tuples: ('sit', expr), ('assign', name, expr), ('binop', op, left, right),
('number', n), ('string', s), ('var', name).

Current grammar:

    program     : statement*
    statement   : SIT ( expression )
                | ID EQUALS expression
    expression  : expression (+|-|*|/) expression
                | ( expression )
                | NUMBER | STRING | ID
"""

import ply.yacc as yacc

from lexer import tokens, build_lexer  # noqa: F401 (yacc needs `tokens`)

# Operator precedence: resolves the ambiguity of 1 + 2 * 3
precedence = (
    ("left", "PLUS", "MINUS"),
    ("left", "TIMES", "DIVIDE"),
)


def p_program(p):
    """program : program statement
               | statement"""
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]


def p_statement_sit(p):
    """statement : SIT LPAREN expression RPAREN"""
    p[0] = ("sit", p[3])


def p_statement_assign(p):
    """statement : ID EQUALS expression"""
    p[0] = ("assign", p[1], p[3])


def p_expression_binop(p):
    """expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression"""
    p[0] = ("binop", p[2], p[1], p[3])


def p_expression_group(p):
    """expression : LPAREN expression RPAREN"""
    p[0] = p[2]


def p_expression_number(p):
    """expression : NUMBER"""
    p[0] = ("number", p[1])


def p_expression_string(p):
    """expression : STRING"""
    p[0] = ("string", p[1])


def p_expression_var(p):
    """expression : ID"""
    p[0] = ("var", p[1])


def p_error(p):
    if p:
        print(f"Syntax error at {p.value!r} (line {p.lineno})")
    else:
        print("Syntax error: unexpected end of file")


def build_parser():
    return yacc.yacc()


if __name__ == "__main__":
    # Quick check: print the AST of a small program
    build_lexer()
    parser = build_parser()
    ast = parser.parse('sit("Hello, World!")\nx = 2 + 3 * 4\nsit(x)')
    for node in ast:
        print(node)
