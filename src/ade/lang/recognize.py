"""Standalone syntax recognizer for ADE (entrega parcial del analizador sintactico).

Reconoce las mismas oraciones que parser.py (sit, asignaciones,
declaracion de componentes, bloque infra, bloque flow/step) pero en
lugar de construir un AST para traducir, cada regla imprime un mensaje
cuando reconoce una oracion valida de la gramatica. No ejecuta
(interpreter.py), no valida semanticamente (semantic.py) y no genera
codigo Manim (codegen.py) -- esas fases son responsabilidad de ade.py.

Uso:
    uv run python -m ade.lang.recognize examples/login_flow.ade
"""

import sys
from pathlib import Path

import ply.yacc as yacc

from ade.lang.lexer import tokens, build_lexer  # noqa: F401 (yacc necesita `tokens`)

precedence = (
    ("left", "PLUS", "MINUS"),
    ("left", "TIMES", "DIVIDE"),
)


def p_program(p):
    """program : program statement
               | statement"""


def p_statement_sit(p):
    """statement : SIT LPAREN expression RPAREN"""
    print("Oracion reconocida: sit(...)")


def p_statement_assign(p):
    """statement : ID EQUALS expression"""
    print(f"Oracion reconocida: asignacion de variable {p[1]!r}")


def p_statement_component(p):
    """statement : SERVICE ID STRING COLOR COLON ID
                  | GATEWAY ID STRING COLOR COLON ID
                  | DATABASE ID STRING COLOR COLON ID"""
    kind = p.slice[1].type.lower()
    print(
        f'Oracion reconocida: declaracion de {kind} {p[2]!r} ("{p[3]}") color={p[6]}'
    )


def p_statement_infra(p):
    """statement : INFRA STRING LBRACE id_list RBRACE"""
    print(f'Oracion reconocida: bloque infra "{p[2]}" con miembros {p[4]}')


def p_id_list_multi(p):
    """id_list : id_list ID"""
    p[0] = p[1] + [p[2]]


def p_id_list_single(p):
    """id_list : ID"""
    p[0] = [p[1]]


def p_statement_flow(p):
    """statement : FLOW STRING LBRACE step_list RBRACE"""
    print(f'Oracion reconocida: bloque flow "{p[2]}" con {len(p[4])} step(s)')


def p_step_list_multi(p):
    """step_list : step_list step"""
    p[0] = p[1] + [p[2]]


def p_step_list_single(p):
    """step_list : step"""
    p[0] = [p[1]]


def p_step_plain(p):
    """step : STEP NUMBER COLON ID ARROW ID"""
    print(f"Oracion reconocida: step {p[2]}: {p[4]} --> {p[6]}")
    p[0] = p[2]


def p_step_protocol(p):
    """step : STEP NUMBER COLON ID ARROW_PROTO ID"""
    print(f"Oracion reconocida: step {p[2]}: {p[4]} --[{p[5]}]--> {p[6]}")
    p[0] = p[2]


def p_expression_binop(p):
    """expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression"""


def p_expression_group(p):
    """expression : LPAREN expression RPAREN"""


def p_expression_number(p):
    """expression : NUMBER"""


def p_expression_string(p):
    """expression : STRING"""


def p_expression_var(p):
    """expression : ID"""


def p_error(p):
    if p:
        print(f"Error sintactico en {p.value!r} (linea {p.lineno}): oracion no reconocida")
    else:
        print("Error sintactico: fin de archivo inesperado")


def build_parser():
    # write_tables/debug off: no genera artefactos en el paquete ni choca con parser.py
    return yacc.yacc(write_tables=False, debug=False)


def recognize_file(path):
    path = Path(path)
    source = path.read_text(encoding="utf-8")

    build_lexer()
    parser = build_parser()
    parser.parse(source)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m ade.lang.recognize <archivo.ade>")
        sys.exit(1)
    recognize_file(sys.argv[1])
