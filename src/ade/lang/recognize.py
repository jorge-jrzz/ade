"""Reconocedor sintactico independiente de ADE (entrega del analizador sintactico).

Reconoce las mismas oraciones que parser.py -- declaracion de direccion,
componentes (con o sin bloque de atributos), bloque infra, bloque flow/step y
bloque timeline -- pero en lugar de construir un AST para traducir, cada regla
imprime un mensaje cuando reconoce una oracion valida de la gramatica. No
ejecuta (interpreter.py), no valida semanticamente (semantic.py) y no genera
codigo Manim (codegen.py) -- esas fases son responsabilidad de ade.

La colocacion es automatica (ade.layout): la gramatica ya no acepta coordenadas
(`at:`), tamanos (`size:`) ni el `move` del timeline.

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


# --- estatutos clasicos -----------------------------------------------------


def p_statement_sit(p):
    """statement : SIT LPAREN expression RPAREN"""
    print("Oracion reconocida: sit(...)")


def p_statement_assign(p):
    """statement : ID EQUALS expression"""
    print(f"Oracion reconocida: asignacion de variable {p[1]!r}")


# --- direccion de layout ----------------------------------------------------


def p_statement_direction(p):
    """statement : DIRECTION COLON ID"""
    print(f"Oracion reconocida: direccion de layout {p[3]}")


# --- componentes ------------------------------------------------------------


def p_component_kind(p):
    """component_kind : SERVICE
    | GATEWAY
    | DATABASE
    | EXTERNAL"""
    p[0] = p.slice[1].type.lower()


def p_statement_component_plain(p):
    """statement : component_kind ID STRING"""
    print(f'Oracion reconocida: declaracion de {p[1]} {p[2]!r} ("{p[3]}")')


def p_statement_component_color(p):
    """statement : component_kind ID STRING COLOR COLON ID"""
    print(f"Oracion reconocida: declaracion de {p[1]} {p[2]!r} color={p[6]}")


def p_statement_component_block(p):
    """statement : component_kind ID STRING LBRACE attr_list RBRACE"""
    print(f"Oracion reconocida: declaracion de {p[1]} {p[2]!r} con bloque de atributos")


# --- bloque de atributos ----------------------------------------------------


def p_attr_list_multi(p):
    """attr_list : attr_list attr"""


def p_attr_list_empty(p):
    """attr_list : empty"""


def p_attr_color(p):
    """attr : COLOR COLON ID"""


def p_attr_kind(p):
    """attr : KIND COLON kind_value"""


def p_kind_value(p):
    """kind_value : SERVICE
    | GATEWAY
    | DATABASE
    | EXTERNAL
    | INFRA"""


def p_attr_logo(p):
    """attr : LOGO COLON logo_ref"""


def p_attr_sublabel(p):
    """attr : SUBLABEL COLON STRING"""


def p_logo_ref(p):
    """logo_ref : ID
    | STRING"""


# --- bloque infra -----------------------------------------------------------


def p_statement_infra(p):
    """statement : INFRA STRING LBRACE infra_item_list RBRACE"""
    print(f'Oracion reconocida: bloque infra "{p[2]}"')


def p_infra_item_list_multi(p):
    """infra_item_list : infra_item_list infra_item"""


def p_infra_item_list_empty(p):
    """infra_item_list : empty"""


def p_infra_item_member(p):
    """infra_item : ID"""


def p_infra_item_logo(p):
    """infra_item : LOGO COLON logo_ref"""


# --- bloque flow / steps ----------------------------------------------------


def p_statement_flow(p):
    """statement : FLOW STRING LBRACE step_list RBRACE"""
    print(f'Oracion reconocida: bloque flow "{p[2]}" con {len(p[4])} step(s)')


def p_step_list_multi(p):
    """step_list : step_list step"""
    p[0] = p[1] + [p[2]]


def p_step_list_single(p):
    """step_list : step"""
    p[0] = [p[1]]


def p_step(p):
    """step : STEP NUMBER COLON ID arrow ID step_opt"""
    print(f"Oracion reconocida: step {p[2]}: {p[4]} --> {p[6]}")
    p[0] = p[2]


def p_arrow_plain(p):
    """arrow : ARROW"""


def p_arrow_proto(p):
    """arrow : ARROW_PROTO"""


def p_step_opt_curved(p):
    """step_opt : CURVED"""


def p_step_opt_empty(p):
    """step_opt : empty"""


# --- bloque timeline --------------------------------------------------------


def p_statement_timeline(p):
    """statement : TIMELINE STRING LBRACE tl_list RBRACE"""
    print(f'Oracion reconocida: bloque timeline "{p[2]}"')


def p_tl_list_multi(p):
    """tl_list : tl_list tl_stmt"""


def p_tl_list_empty(p):
    """tl_list : empty"""


def p_tl_show(p):
    """tl_stmt : SHOW id_csv"""


def p_tl_add_plain(p):
    """tl_stmt : ADD component_kind ID STRING"""


def p_tl_add_block(p):
    """tl_stmt : ADD component_kind ID STRING LBRACE attr_list RBRACE"""


def p_tl_connect(p):
    """tl_stmt : CONNECT ID arrow ID step_opt"""


def p_tl_wait(p):
    """tl_stmt : WAIT"""


def p_id_csv_multi(p):
    """id_csv : id_csv COMMA ID"""


def p_id_csv_single(p):
    """id_csv : ID"""


# --- expresiones ------------------------------------------------------------


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


def p_empty(p):
    """empty :"""


def p_error(p):
    if p:
        print(
            f"Error sintactico en {p.value!r} (linea {p.lineno}): oracion no reconocida"
        )
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
