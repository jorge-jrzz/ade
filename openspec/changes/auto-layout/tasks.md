# Tasks: auto-layout

## 1. Layout engine (pure Python, testable first)

- [x] 1.1 Create `src/ade/layout.py`: graph extraction from `Model` (components as nodes; flow steps and timeline connects as directed edges; infra membership as clusters)
- [x] 1.2 Implement longest-path ranking with DFS back-edge handling (cycles must terminate; test against `login_flow`'s graph shape)
- [x] 1.3 Implement cluster-contiguity constraint and in-rank barycenter ordering (`external` kinds bias to rank start)
- [x] 1.4 Implement abstract card-size estimation from label/sublabel/logo (constants documented as bound to `CardBuilder` sizing)
- [x] 1.5 Implement coordinate assignment (LR and TD), boundary boxes as padded member bounding boxes with label band, drawing centered on origin
- [x] 1.6 Implement canvas fitting: uniform scale factor vs usable frame (~14.22 × 8.0 minus margin), expose the factor and a below-0.7 legibility flag in `LayoutResult`
- [x] 1.7 Set up pytest and unit-test the pass: pipeline ranking, cycle termination, determinism, cluster contiguity, LR vs TD axes, sizing monotonicity, scale factor/warning flag (no Manim imports anywhere in these tests)

## 2. Language surface removal + direction

- [x] 2.1 Remove `at:`/`size:` attribute rules and the timeline `move` op from `parser.py` (grammar + AST docstring); drop now-unused tokens from `lexer.py` (verify each token has no remaining rule before deleting)
- [x] 2.2 Add top-level `direction: LR|TD` statement to lexer/parser; store on the AST
- [x] 2.3 Update `semantic.py`: delete `Component.at/size`, `Boundary.at/size`, `TLMove` and their validation; add `Model.direction` with default `LR` and a semantic error on duplicate `direction:` statements
- [x] 2.4 Update `recognize.py` to the reduced grammar plus `direction` (keep Spanish comments/style; it must recognize exactly what `parser.py` parses)

## 3. Codegen rewrite

- [x] 3.1 Wire the layout pass into `run_file` (`semantic.validate → layout.solve → codegen`); print the legibility warning when the flag is set
- [x] 3.2 Replace `_static_explicit`/`_static_auto` and the explicit/auto switch with a single static path that renders solved positions, boundary boxes, and the uniform scale factor
- [x] 3.3 Add content-based auto-sizing to `CardBuilder` mirroring the layout estimates (keep `.size()` as programmatic API for hand-written examples)
- [x] 3.4 Rewrite timeline generation: compile layout snapshots at each `add`/`connect`, emit simultaneous `move_to` animations for surviving nodes, `FadeIn` for new ones, and connection re-anchoring after moves; apply the final snapshot's scale from the first frame; remove the `TLMove` branch

## 4. Examples, docs, verification

- [x] 4.1 Rewrite all `examples/*.ade` coordinate-free (scene2 loses its `move`s; scene4 loses all `at:`/`size:`)
- [x] 4.2 Update README language cheatsheet: remove `at:`/`size:`/`move`, document `direction:`
- [x] 4.3 Run `recognize` over every rewritten example (fast grammar check), then render all examples end-to-end and compare visual quality against the current hand-tuned outputs; tune gap/padding constants if needed
- [x] 4.4 Sweep for zombie code: no references to `at`, `size` (DSL sense), `TLMove`, `_static_explicit`, `_static_auto` remain; update CLAUDE.md pipeline description (layout pass, no coordinates)
