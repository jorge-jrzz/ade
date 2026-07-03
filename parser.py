"""Syntax analyzer (yacc) for the ADE language.

From the lexer tokens it builds an AST (abstract syntax tree) made of
tuples: ('sit', expr), ('assign', name, expr), ('binop', op, left, right),
('number', n), ('string', s), ('var', name), plus the architecture nodes:
('component', kind, name, label, color, lineno),
('infra', label, [names...], lineno),
('flow', label, [steps...], lineno) where
step = ('step', number, source, protocol_or_None, target, lineno).

Current grammar:

    program         : statement*
    statement       : SIT ( expression )
                    | ID EQUALS expression
                    | component_decl
                    | infra_block
                    | flow_block
    component_decl  : (SERVICE|GATEWAY|DATABASE) ID STRING COLOR COLON ID
    infra_block     : INFRA STRING { id_list }
    id_list         : id_list ID | ID
    flow_block      : FLOW STRING { step_list }
    step_list       : step_list step | step
    step            : STEP NUMBER COLON ID (ARROW|ARROW_PROTO) ID
    expression      : expression (+|-|*|/) expression
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


def p_statement_component(p):
    """statement : SERVICE ID STRING COLOR COLON ID
                  | GATEWAY ID STRING COLOR COLON ID
                  | DATABASE ID STRING COLOR COLON ID"""
    kind = p.slice[1].type.lower()
    p[0] = ("component", kind, p[2], p[3], p[6], p.lineno(1))


def p_statement_infra(p):
    """statement : INFRA STRING LBRACE id_list RBRACE"""
    p[0] = ("infra", p[2], p[4], p.lineno(1))


def p_id_list_multi(p):
    """id_list : id_list ID"""
    p[0] = p[1] + [p[2]]


def p_id_list_single(p):
    """id_list : ID"""
    p[0] = [p[1]]


def p_statement_flow(p):
    """statement : FLOW STRING LBRACE step_list RBRACE"""
    p[0] = ("flow", p[2], p[4], p.lineno(1))


def p_step_list_multi(p):
    """step_list : step_list step"""
    p[0] = p[1] + [p[2]]


def p_step_list_single(p):
    """step_list : step"""
    p[0] = [p[1]]


def p_step_plain(p):
    """step : STEP NUMBER COLON ID ARROW ID"""
    p[0] = ("step", p[2], p[4], None, p[6], p.lineno(1))


def p_step_protocol(p):
    """step : STEP NUMBER COLON ID ARROW_PROTO ID"""
    p[0] = ("step", p[2], p[4], p[5], p[6], p.lineno(1))


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
