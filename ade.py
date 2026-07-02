"""Entry point for the ADE language.

Usage:
    uv run python plyy/ade.py plyy/hello.ade

Full pipeline: .ade file -> lexer (tokens) -> parser (AST)
-> interpreter (execution).
"""

import sys
from pathlib import Path

from lexer import build_lexer
from parser import build_parser
from interpreter import Interpreter


def run_file(path):
    path = Path(path)
    if path.suffix != ".ade":
        print(f"Warning: expected a .ade file, got {path.suffix!r}")
    source = path.read_text(encoding="utf-8")

    build_lexer()
    parser = build_parser()
    ast = parser.parse(source)

    Interpreter().run(ast)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python ade.py <file.ade>")
        sys.exit(1)
    run_file(sys.argv[1])
