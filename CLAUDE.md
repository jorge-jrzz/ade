# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ADE (Architectural Design Engine): a DSL for describing and animating software architectures, rendered with Manim. `.ade` source files are compiled to generated Manim scripts and rendered to video.

## Commands

```bash
uv sync                                          # install dependencies (Python 3.13, managed by uv)
uv run ade examples/scene1.ade                   # run the full pipeline on a .ade file
uv run python -m ade.lang.lexer                  # lexer standalone
uv run python -m ade.lang.recognize <file.ade>   # syntax recognizer only (no AST/codegen)
uv run pytest                                    # unit tests (layout pass; Manim-free, fast)
```

Running a `.ade` file with architecture blocks writes a generated Manim script to `build/<name>_scene.py`, renders it at low quality (`manim -ql`) with all media under `build/`, and copies the final video to `build/<name>.mp4`. Rendering requires Manim's system dependencies and takes a while — the fast way to check language-layer changes is `recognize` or importing/parsing directly, without rendering.

The layout pass has a `pytest` suite (`tests/test_layout.py`); the Manim rendering layer has no automated tests — verify it by rendering examples. No linter is configured.

## Architecture

Pipeline (driven by `src/ade/__init__.py::run_file`):

```
.ade file → lexer (PLY) → parser (tuple AST) → semantic.validate → Model
    ├── classic statements (sit/assign) → lang/interpreter.py (direct evaluation)
    └── architecture (service/infra/flow/timeline) → layout.solve → animations/codegen.py
        → generated Manim script in build/ → subprocess `uv run manim -ql`
```

Placement is fully automatic: the DSL carries **no coordinates or sizes**. `src/ade/layout.py`
is a pure-Python (Manim-free) layered/Sugiyama-style pass that runs between `semantic.validate`
and codegen — it assigns every component a position and every boundary a box from the flow
edges and infra membership, auto-sizes cards from their content, honors a top-level
`direction: LR|TD` hint, and scales the drawing to fit the 16:9 frame (warning if it must shrink
below legibility). Timelines re-solve incrementally per `add`/`connect` so existing nodes slide
into place. It is unit-tested in `tests/test_layout.py` (fast, no rendering).

Two packages under `src/ade/`:

- **`ade/lang`** — language front-end: `lexer.py` and `parser.py` (PLY-based; the AST is plain tuples, node shapes documented in `parser.py`'s docstring), `semantic.py` (validation + the `Model` dataclasses: `Component`, `Boundary`, `Flow`, `Timeline`...), `interpreter.py` (evaluates only the classic `sit`/arithmetic statements). `recognize.py` is a standalone recognizer that prints matched grammar rules instead of building an AST (an academic deliverable; its comments are in Spanish).
- **`ade/animations`** — Manim layer: `codegen.py` turns a validated `Model` into a scene script string; `components/` holds the builders the generated code calls (`CardBuilder`, `BoundaryBuilder`, `ConnectionBuilder`) plus `assets.py`; `themes.py` defines the `LIGHT` theme; `examples/` are hand-written demo scenes that generated output should match visually.

**Layering rule:** `ade/lang` and `ade/layout.py` must stay free of Manim and of the `ade.animations` package (so the layout pass stays fast and unit-testable without rendering). Card-size estimates in `layout.py` are abstract constants bound by comment to `CardBuilder`'s sizing, not Manim text metrics. Logo values are kept as raw alias strings in the semantic model and only resolved to asset paths in `codegen.py` via `assets.find_logo`.

Logo assets live in `ade/animations/assets/` as PNGs (rasterized from SVGs with cairosvg, since Manim's SVGMobject doesn't support gradients). `find_logo` resolves a short alias (`nestjs`, `aws`, ...) by exact stem or unique case-insensitive prefix, and raises with the candidate list on unknown/ambiguous aliases.

The DSL syntax (component/infra/flow/timeline blocks and their attributes) is documented with examples in the README's language cheatsheet; the `examples/*.ade` files each exercise a different feature.
