"""Syntax analyzer (yacc) for the ADE language.

From the lexer tokens it builds an AST (abstract syntax tree) made of
tuples. Classic nodes:
    ('sit', expr), ('assign', name, expr), ('binop', op, left, right),
    ('number', n), ('string', s), ('var', name)

Architecture nodes:
    ('direction', value, lineno)          value : LR | TD (validated in semantic)
    ('component', kind, name, label, attrs, lineno)
        kind  : service | gateway | database | external
        attrs : dict with any of color/kind/logo/sublabel
    ('infra', label, attrs, [members...], lineno)
        attrs : dict with any of logo
    ('flow', label, [steps...], lineno)
        step = ('step', number, source, label_or_None, target, curved, lineno)
    ('timeline', label, [ops...], lineno)
        op = ('show', [ids]) | ('add', component_node)
           | ('connect', src, label_or_None, target, curved) | ('wait',)

Placement is fully automatic (see ade.layout): the language carries no
coordinates or sizes — only the optional top-level `direction:` hint.

Grammar (informal):

    program        : statement*
    statement      : SIT ( expression )
                   | ID EQUALS expression
                   | DIRECTION COLON ID
                   | component_kind ID STRING [ COLOR COLON ID | { attr* } ]
                   | INFRA STRING { infra_item* }
                   | FLOW STRING { step* }
                   | TIMELINE STRING { tl_stmt* }
    component_kind : SERVICE | GATEWAY | DATABASE | EXTERNAL
    attr           : (COLOR|KIND) COLON ID | LOGO COLON logo_ref
                   | SUBLABEL COLON STRING
    infra_item     : ID | LOGO COLON logo_ref
    step           : STEP NUMBER COLON ID arrow ID [CURVED]
    tl_stmt        : SHOW id_csv | ADD component_kind ID STRING [{ attr* }]
                   | CONNECT ID arrow ID [CURVED] | WAIT
    arrow          : ARROW | ARROW_PROTO
    expression     : expression (+|-|*|/) expression | ( expression )
                   | NUMBER | STRING | ID
"""

import ply.yacc as yacc

from ade.lang.lexer import tokens, build_lexer  # noqa: F401 (yacc needs `tokens`)

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


# --- components -------------------------------------------------------------

def p_component_kind(p):
    """component_kind : SERVICE
                      | GATEWAY
                      | DATABASE
                      | EXTERNAL"""
    p[0] = p.slice[1].type.lower()


def p_statement_component_plain(p):
    """statement : component_kind ID STRING"""
    p[0] = ("component", p[1], p[2], p[3], {}, p.lineno(2))


def p_statement_component_color(p):
    """statement : component_kind ID STRING COLOR COLON ID"""
    p[0] = ("component", p[1], p[2], p[3], {"color": p[6]}, p.lineno(2))


def p_statement_component_block(p):
    """statement : component_kind ID STRING LBRACE attr_list RBRACE"""
    p[0] = ("component", p[1], p[2], p[3], p[5], p.lineno(2))


# --- attribute blocks -------------------------------------------------------

def p_attr_list_multi(p):
    """attr_list : attr_list attr"""
    key, value = p[2]
    p[0] = {**p[1], key: value}


def p_attr_list_empty(p):
    """attr_list : empty"""
    p[0] = {}


def p_attr_color(p):
    """attr : COLOR COLON ID"""
    p[0] = ("color", p[3])


def p_attr_kind(p):
    """attr : KIND COLON kind_value"""
    p[0] = ("kind", p[3])


def p_kind_value(p):
    """kind_value : SERVICE
                  | GATEWAY
                  | DATABASE
                  | EXTERNAL
                  | INFRA"""
    p[0] = p.slice[1].type.lower()


def p_attr_logo(p):
    """attr : LOGO COLON logo_ref"""
    p[0] = ("logo", p[3])


def p_attr_sublabel(p):
    """attr : SUBLABEL COLON STRING"""
    p[0] = ("sublabel", p[3])


def p_logo_ref(p):
    """logo_ref : ID
                | STRING"""
    p[0] = p[1]


# --- infra (boundary) -------------------------------------------------------

def p_statement_infra(p):
    """statement : INFRA STRING LBRACE infra_item_list RBRACE"""
    attrs, members = p[4]
    p[0] = ("infra", p[2], attrs, members, p.lineno(1))


def p_infra_item_list_multi(p):
    """infra_item_list : infra_item_list infra_item"""
    attrs, members = p[1]
    key, value = p[2]
    if key == "member":
        p[0] = (attrs, members + [value])
    else:
        p[0] = ({**attrs, key: value}, members)


def p_infra_item_list_empty(p):
    """infra_item_list : empty"""
    p[0] = ({}, [])


def p_infra_item_member(p):
    """infra_item : ID"""
    p[0] = ("member", p[1])


def p_infra_item_logo(p):
    """infra_item : LOGO COLON logo_ref"""
    p[0] = ("logo", p[3])


# --- flow / steps -----------------------------------------------------------

def p_statement_flow(p):
    """statement : FLOW STRING LBRACE step_list RBRACE"""
    p[0] = ("flow", p[2], p[4], p.lineno(1))


def p_step_list_multi(p):
    """step_list : step_list step"""
    p[0] = p[1] + [p[2]]


def p_step_list_single(p):
    """step_list : step"""
    p[0] = [p[1]]


def p_step(p):
    """step : STEP NUMBER COLON ID arrow ID step_opt"""
    p[0] = ("step", p[2], p[4], p[5], p[6], p[7], p.lineno(1))


def p_arrow_plain(p):
    """arrow : ARROW"""
    p[0] = None


def p_arrow_proto(p):
    """arrow : ARROW_PROTO"""
    p[0] = p[1]  # the label carried by --[label]-->


def p_step_opt_curved(p):
    """step_opt : CURVED"""
    p[0] = True


def p_step_opt_empty(p):
    """step_opt : empty"""
    p[0] = False


# --- timeline (imperative animation) ---------------------------------------

def p_statement_timeline(p):
    """statement : TIMELINE STRING LBRACE tl_list RBRACE"""
    p[0] = ("timeline", p[2], p[4], p.lineno(1))


def p_tl_list_multi(p):
    """tl_list : tl_list tl_stmt"""
    p[0] = p[1] + [p[2]]


def p_tl_list_empty(p):
    """tl_list : empty"""
    p[0] = []


def p_tl_show(p):
    """tl_stmt : SHOW id_csv"""
    p[0] = ("show", p[2])


def p_tl_add_plain(p):
    """tl_stmt : ADD component_kind ID STRING"""
    p[0] = ("add", ("component", p[2], p[3], p[4], {}, p.lineno(3)))


def p_tl_add_block(p):
    """tl_stmt : ADD component_kind ID STRING LBRACE attr_list RBRACE"""
    p[0] = ("add", ("component", p[2], p[3], p[4], p[6], p.lineno(3)))


def p_tl_connect(p):
    """tl_stmt : CONNECT ID arrow ID step_opt"""
    p[0] = ("connect", p[2], p[3], p[4], p[5])


def p_tl_wait(p):
    """tl_stmt : WAIT"""
    p[0] = ("wait",)


def p_id_csv_multi(p):
    """id_csv : id_csv COMMA ID"""
    p[0] = p[1] + [p[3]]


def p_id_csv_single(p):
    """id_csv : ID"""
    p[0] = [p[1]]


# --- layout direction -------------------------------------------------------

def p_statement_direction(p):
    """statement : DIRECTION COLON ID"""
    p[0] = ("direction", p[3], p.lineno(1))


# --- classic statements / expressions --------------------------------------

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


def p_empty(p):
    """empty :"""
    p[0] = None


def p_error(p):
    if p:
        print(f"Syntax error at {p.value!r} (line {p.lineno})")
    else:
        print("Syntax error: unexpected end of file")


def build_parser():
    # write_tables/debug off so PLY doesn't drop parsetab.py / parser.out into the package.
    return yacc.yacc(write_tables=False, debug=False)


if __name__ == "__main__":
    # Quick check: print the AST of a small program that exercises the new syntax
    build_lexer()
    parser = build_parser()
    sample = '''
    direction: LR
    external client "Web Client"
    gateway api "API Gateway" { logo: nestjs }
    database db "PostgreSQL" { logo: postgres  sublabel: "Primary" }
    infra "AWS Cloud" { logo: aws  api  db }
    flow "Login" {
        step 1: client --[HTTPS]--> api
        step 2: api --[SQL]--> db curved
    }
    timeline "Scaling" {
        show client, api
        add service web2 "Web Server 2"
        connect api --> web2
        wait
    }
    '''
    for node in parser.parse(sample):
        print(node)
