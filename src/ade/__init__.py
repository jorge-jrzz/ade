"""ADE (Architectural Design Engine) — command-line entry point.

Full pipeline: .ade file -> lexer (tokens) -> parser (AST)
-> semantic validation -> interpreter (sit/assign) and/or
Manim codegen + render (service/gateway/database/infra/flow).

Usage:
    ade <file.ade> [--quality {low,l,medium,m,high,h}] [--output-dir DIR]
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

BUILD_DIR = Path.cwd() / "build"
DEFAULT_OUTPUT_DIR = Path("ade-videos")
QUALITY_PRESETS = {
    "low": "l",
    "l": "l",
    "medium": "m",
    "m": "m",
    "high": "h",
    "h": "h",
}


def run_file(path, quality="l", output_dir=DEFAULT_OUTPUT_DIR):
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
            render_architecture(model, path, quality, output_dir)
        except SemanticError as error:
            print(f"Semantic error: {error}")
            sys.exit(1)


def render_architecture(model, source_path, quality="l", output_dir=DEFAULT_OUTPUT_DIR):
    from ade.animations.codegen import generate_manim_script

    BUILD_DIR.mkdir(exist_ok=True)
    script_source, scene_name, illegible = generate_manim_script(model)
    if illegible:
        print(
            "Warning: this scene is dense — the layout was scaled below the "
            "legibility threshold and text may be hard to read. Consider "
            "splitting it into smaller scenes."
        )
    script_path = BUILD_DIR / f"{source_path.stem}_scene.py"
    script_path.write_text(script_source, encoding="utf-8")

    # Keep all Manim output (the generated script + media) under build/ so it
    # never clutters the project root. No -p: previewing needs a desktop opener
    # (xdg-open), which isn't available in headless environments.
    subprocess.run(
        [
            "uv",
            "run",
            "manim",
            f"-q{quality}",
            "--media_dir",
            str(BUILD_DIR),
            str(script_path),
            scene_name,
        ],
        check=True,
    )

    # Manim writes to build/videos/<stem>/<quality>/<Scene>.mp4; surface a clean
    # copy in the user-facing output directory without exposing build artifacts.
    rendered = next((BUILD_DIR / "videos").rglob(f"{scene_name}.mp4"), None)
    if rendered is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        final = output_dir / f"{source_path.stem}.mp4"
        shutil.copyfile(rendered, final)
        print(f"Rendered {scene_name} -> {final}")


def parse_args(args=None):
    parser = argparse.ArgumentParser(description="Render an ADE architecture video.")
    parser.add_argument("path", help="Path to the .ade source file")
    parser.add_argument(
        "-q",
        "--quality",
        choices=QUALITY_PRESETS,
        default="low",
        help="Video quality: low/l, medium/m, or high/h (default: low)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for the final MP4 only (default: ade-videos)",
    )
    return parser.parse_args(args)


def main(args=None) -> None:
    options = parse_args(args)
    run_file(options.path, QUALITY_PRESETS[options.quality], options.output_dir)
