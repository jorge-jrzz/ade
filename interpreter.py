"""Interpreter for the ADE language.

Walks the AST produced by the parser and evaluates it. Program state
lives in `variables`, a name -> value dictionary.
"""


class Interpreter:
    def __init__(self):
        self.variables = {}

    def run(self, program):
        """Execute the list of statements in the AST."""
        if program is None:  # the parser already reported a syntax error
            return
        for statement in program:
            self._statement(statement)

    def _statement(self, node):
        kind = node[0]
        if kind == "sit":
            print(self._expression(node[1]))
        elif kind == "assign":
            self.variables[node[1]] = self._expression(node[2])
        else:
            raise RuntimeError(f"Unknown statement: {kind}")

    def _expression(self, node):
        kind = node[0]
        if kind == "number" or kind == "string":
            return node[1]
        if kind == "var":
            if node[1] not in self.variables:
                raise NameError(f"Undefined variable: {node[1]!r}")
            return self.variables[node[1]]
        if kind == "binop":
            op = node[1]
            left, right = self._expression(node[2]), self._expression(node[3])
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                return left / right
        raise RuntimeError(f"Unknown expression: {kind}")
