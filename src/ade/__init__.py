"""ADE (Architectural Design Engine) — command-line entry point.

Full pipeline: .ade file -> lexer (tokens) -> parser (AST)
-> semantic validation -> interpreter (sit/assign) and/or
Manim codegen + render (service/gateway/database/infra/flow).

Usage:
    ade <file.ade>
"""

import shutil
import subprocess
import sys
from pathlib import Path

BUILD_DIR = Path.cwd() / "build"


def run_file(path):
    # Imported lazily so `import ade` stays light (submodules import this package).
    from ade.lang.lexer import build_lexer
    from ade.lang.parser import build_parser
    from ade.lang.interpreter import Interpreter
    from ade.lang.semantic import SemanticError, validate

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
        try:
            render_architecture(model, path)
        except SemanticError as error:
            print(f"Semantic error: {error}")
            sys.exit(1)


def render_architecture(model, source_path):
    from ade.animations.codegen import generate_manim_script

    BUILD_DIR.mkdir(exist_ok=True)
    script_source, scene_name = generate_manim_script(model)
    script_path = BUILD_DIR / f"{source_path.stem}_scene.py"
    script_path.write_text(script_source, encoding="utf-8")

    # Keep all Manim output (the generated script + media) under build/ so it
    # never clutters the project root. No -p: previewing needs a desktop opener
    # (xdg-open), which isn't available in headless environments.
    subprocess.run(
        ["uv", "run", "manim", "-ql", "--media_dir", str(BUILD_DIR),
         str(script_path), scene_name],
        check=True,
    )

    # Manim writes to build/videos/<stem>/<quality>/<Scene>.mp4; surface a clean
    # copy at build/<name>.mp4 and tell the user where it landed.
    rendered = next((BUILD_DIR / "videos").rglob(f"{scene_name}.mp4"), None)
    if rendered is not None:
        final = BUILD_DIR / f"{source_path.stem}.mp4"
        shutil.copyfile(rendered, final)
        print(f"Rendered {scene_name} -> {final}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: ade <file.ade>")
        sys.exit(1)
    run_file(sys.argv[1])
