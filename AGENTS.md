# AGENTS.md

ADE (Architectural Design Engine): a DSL for describing and animating software architectures. `.ade` files compile to generated Manim scripts and render to video.

Note: `CLAUDE.md` overlaps with this file but predates the CLI/tooling changes below — where they disagree, trust this file (final video goes to `ade-videos/`, not `build/`; ruff and ty ARE configured).

## Commands

```bash
uv sync                                          # deps (Python 3.13, uv-managed)
uv run pytest                                    # fast unit tests, no Manim (~0.05s)
uv run ruff check .                              # lint
uv run ty check .                                # typecheck — keep at zero diagnostics
uv run ade examples/scene1.ade                   # full pipeline (renders video, slow)
uv run ade file.ade -q h -o renders              # quality low/l|medium/m|high/h; output dir
uv run python -m ade.lang.recognize <file.ade>   # syntax check only, no render
```

Verification order: `pytest` + `ruff` + `ty` are all fast; run all three before considering work done. Rendering (`uv run ade`) is slow and needs Manim system deps — only use it to verify the animations layer, which has no automated tests.

## CLI behavior (src/ade/__init__.py)

- `--quality/-q` presets map to Manim `-q{l,m,h}` via `QUALITY_PRESETS`; default `low`.
- `--output-dir/-o` (default `ade-videos/`) receives ONLY the final MP4; the generated script and all Manim media stay under `build/` (`BUILD_DIR = cwd/build`).
- `run_file()`/`render_architecture()` take optional `quality`/`output_dir` params — keep them optional to not break direct callers.

## Architecture

Pipeline: `.ade` → PLY lexer → parser (plain-tuple AST, shapes in `parser.py` docstring) → `semantic.validate` → `Model` → `layout.solve` (pure Python) → `animations/codegen.py` → script in `build/` → subprocess `uv run manim`.

- `src/ade/lang/` — front-end. `recognize.py` is an academic deliverable with Spanish comments; don't "fix" its language.
- `src/ade/layout.py` — Sugiyama-style auto-layout; the DSL has NO coordinates/sizes.
- `src/ade/animations/` — Manim layer: codegen + fluent builders (`CardBuilder`, etc.) + assets.

**Layering rule (enforced by test):** `ade/lang` and `ade/layout.py` must never import Manim or `ade.animations`. `tests/test_layout.py::test_no_manim_imported` asserts `"manim" not in sys.modules` — so test doubles must not import real animation modules either; `tests/test_cli.py` stubs `ade.animations.codegen` with a `types.ModuleType` inserted into `sys.modules` for this reason.

- Card-size constants in `layout.py` mirror `CardBuilder` sizing by convention (comments bind them); update both together.
- Logos stay raw alias strings in the semantic model; resolved to asset paths only in `codegen.py` via `assets.find_logo` (exact stem or unique case-insensitive prefix).

## Typechecking quirks (ty)

- Manim's own annotations are imperfect: `Camera.background_color` rejects both `str` and `ManimColor` — the existing `# ty: ignore[invalid-assignment]` comments in `animations/examples/` are deliberate; don't remove them.
- Manim point APIs want tuples, not lists: `.move_to((x, y, z))`.
- `[tool.ty.environment] root = ["src"]` in pyproject.

## Conventions

- Ruff per-file ignore: `animations/examples/*` may use `from manim import *`.
- OpenSpec workflow is in use (`openspec/changes/`); planning skills live in `.opencode/skills/` and `.claude/skills/`. Use `openspec` CLI (`status`, `instructions`, `validate <name> --type change --strict` — there is no `--change` flag on `validate`).
- Generated dirs to leave alone: `build/`, `ade-videos/`, `parser.out`/`parsetab.py` (PLY cache).
