"""Entry point for the ADE language.

Usage:
    uv run python plyy/ade.py plyy/hello.ade

Full pipeline: .ade file -> lexer (tokens) -> parser (AST)
-> semantic validation -> interpreter (sit/assign) and/or
Manim codegen + render (service/gateway/database/infra/flow).
"""

import subprocess
import sys
from pathlib import Path

from lexer import build_lexer
from parser import build_parser
from interpreter import Interpreter
from semantic import SemanticError, validate
from codegen import generate_manim_script

BUILD_DIR = Path(__file__).parent / "build"


def run_file(path):
    path = Path(path)
    if path.suffix != ".ade":
        print(f"Warning: expected a .ade file, got {path.suffix!r}")
    source = path.read_text(encoding="utf-8")

    build_lexer()
    parser = build_parser()
    ast = parser.parse(source)
    if ast is None:  # the parser already reported a syntax error
        sys.exit(1)

    try:
        model = validate(ast)
    except SemanticError as error:
        print(f"Semantic error: {error}")
        sys.exit(1)

    classic_statements = [node for node in ast if node[0] in ("sit", "assign")]
    Interpreter().run(classic_statements)

    if model.has_architecture():
        render_architecture(model, path)


def render_architecture(model, source_path):
    BUILD_DIR.mkdir(exist_ok=True)
    script_source, scene_name = generate_manim_script(model)
    script_path = BUILD_DIR / f"{source_path.stem}_scene.py"
    script_path.write_text(script_source, encoding="utf-8")

    subprocess.run(
        [sys.executable, "-m", "manim", "-pql", str(script_path), scene_name],
        cwd=Path(__file__).parent,
        check=True,
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python ade.py <file.ade>")
        sys.exit(1)
    run_file(sys.argv[1])
