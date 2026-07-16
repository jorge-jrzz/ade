# Proposal: auto-layout

## Why

ADE's main inspiration is Mermaid, but today every non-trivial `.ade` scene forces the author to hand-place coordinates (`at:`) and sizes (`size:`) — see `examples/scene4.ade`, which is mostly magic numbers. The existing auto-layout (`_static_auto` in `codegen.py`) is a legacy single-row `arrange(RIGHT)` that ignores flows, and a single `at:` anywhere flips the whole scene to fully-explicit mode. The author should describe the architecture; the engine should decide where things go on the fixed 16:9 video canvas.

## What Changes

- **BREAKING**: Remove `at:` and `size:` attributes (components and infra blocks) and the timeline `move` op from the language entirely — lexer tokens, parser grammar rules, semantic model fields (`Component.at/size`, `Boundary.at/size`, `TLMove`), and all codegen paths that consume them (`_static_explicit` and the explicit/auto switch die completely). Hard removal: no deprecation warnings, no parsed-but-ignored syntax, no zombie code. `recognize.py` (the standalone academic recognizer) stays in sync with the reduced grammar.
- Add a layout engine as a **Model → Model pass** between `semantic.validate` and codegen: hand-rolled Sugiyama-style layered layout in pure Python (no graphviz/dagre dependency; target graphs are 5–10 nodes). It assigns positions to every component and computes every boundary box. Manim-free and unit-testable without rendering.
- Cards are **auto-sized from content** (label/sublabel/logo) using abstract size estimates, so `size:` is unnecessary and the layout pass needs no Manim text metrics.
- New top-level `direction:` statement — `LR` (default) or `TD`, like Mermaid's `graph LR/TD`.
- **Canvas fitting**: layout is computed at ideal spacing, then scaled down uniformly to fit the ~14.2 × 8 unit Manim frame if it overflows; a compiler warning is emitted when the required scale makes text illegible (below ~0.7×), suggesting the scene be split.
- **Timelines become purely topological** (`show` / `add` / `connect` / `wait`) with incremental re-layout: each `add`/`connect` re-solves the layout and existing nodes animate to their new positions. The manual `move` choreography (e.g. `examples/scene2.ade` moving nodes to make room) is subsumed by automatic re-layout transitions.
- All `examples/*.ade` rewritten to the coordinate-free syntax; README language cheatsheet updated.

## Capabilities

### New Capabilities

- `layout-engine`: automatic layered (Sugiyama-style) placement of components and boundaries from flow edges and infra membership, direction control (LR/TD), content-based card sizing, canvas fitting with legibility warning, and incremental re-layout for timelines.

### Modified Capabilities

<!-- No existing specs in openspec/specs/ yet; the language-surface removals are captured as requirements inside layout-engine's spec deltas where relevant. -->

- (none — `openspec/specs/` is empty; this change introduces the first spec'd capability)

## Impact

- **Language front-end** (`src/ade/lang/`): `lexer.py`, `parser.py`, `semantic.py`, `recognize.py` — grammar and model shrink (remove `at`/`size`/`move`), plus the new `direction` statement.
- **New module**: layout pass (pure Python, Manim-free; lives outside `ade/lang` per the layering rule, e.g. `src/ade/layout.py` or `src/ade/layout/`).
- **Codegen** (`src/ade/animations/codegen.py`): `_static_explicit`, `_static_auto`, and the explicit/auto switch replaced by a single path that renders the solved layout; timeline generation gains re-layout transitions.
- **Card builders** (`src/ade/animations/components/card.py`): content-based auto-sizing.
- **Examples & docs**: every `examples/*.ade` file, README cheatsheet.
- **Pipeline driver** (`src/ade/__init__.py::run_file`): inserts the layout pass.
- **Testing**: introduces the project's first unit tests (layout pass is pure Python and fast); end-to-end verification by rendering the rewritten examples.
- Independent of the separate `fix-curved-packet-flow` change; neither depends on the other.
