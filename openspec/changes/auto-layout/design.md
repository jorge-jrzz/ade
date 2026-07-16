# Design: auto-layout

## Context

ADE compiles `.ade` files through `lexer → parser (tuple AST) → semantic.validate → Model`, then either interprets classic statements or generates a Manim script (`animations/codegen.py`). Placement today is manual: `at:` / `size:` attributes on components and infra blocks, and `move X to (x, y)` ops in timelines. Codegen has two static paths — `_static_explicit` (used if *any* `at:` appears) and a legacy `_static_auto` (single `arrange(RIGHT)` row that ignores flows).

Two hard constraints shape this design:

- **Layering rule**: `ade/lang` must stay free of Manim and of `ade.animations`.
- **Fixed canvas**: output is a 16:9 video; the Manim frame is ~14.22 × 8.0 scene units (not an infinite canvas like Mermaid's).

## Goals / Non-Goals

**Goals:**

- Coordinate-free DSL: authors declare components, boundaries, flows, timelines — never positions or sizes.
- Deterministic, layered (Sugiyama-style) layout driven by flow edges and infra membership.
- `direction: LR` (default) / `direction: TD` top-level statement.
- Hard removal of `at:`, `size:`, and timeline `move` — grammar, AST, model, codegen, recognizer. No zombie code.
- Layout pass is pure Python, Manim-free, unit-testable without rendering (first tests in the repo).
- Timelines re-layout incrementally: `add`/`connect` re-solves positions and animates existing nodes to their new spots.

**Non-Goals:**

- Multi-scene composition / camera movement ("unir escenas") — future work.
- Edge routing around obstacles, crossing minimization beyond simple heuristics (graphs are 5–10 nodes).
- Pinning/mixed manual+auto positioning (deliberately dropped with `at:`).
- Themes/styling changes; the `fix-curved-packet-flow` bug (separate change).

## Decisions

### D1: Layout is a Model → Model pass between semantic and codegen

```
.ade → lexer → parser → semantic.validate → Model
                                  → layout.solve(Model, direction) → LayoutResult
                                  → codegen(Model, LayoutResult) → Manim script
```

`layout.solve` computes a position for every component and a box (center + size) for every boundary, returned in a `LayoutResult` (or written to layout-only fields) rather than reusing the deleted `at`/`size` model fields — keeping "author input" and "computed geometry" distinct. Codegen becomes a single rendering path that always receives solved geometry.

**Why not layout inside codegen / at Manim runtime?** Pure-Python pass is testable in milliseconds without rendering (the current dev loop's biggest pain), and keeps codegen a dumb translator. **Alternative rejected:** graphviz/`dot` or dagre bindings — real dependency cost (system binary / JS runtime) for graphs of ≤10 nodes that a ~150-line Sugiyama handles.

**Where it lives:** new top-level module `src/ade/layout.py` (or package if it grows). It imports from `ade.lang.semantic` (the Model) but never from `ade.animations` or Manim — same side of the layering fence as `ade/lang`, so the rule extends to: *`ade/lang` and `ade/layout` stay Manim-free*.

### D2: Hand-rolled Sugiyama, simplified for tiny graphs

1. **Graph extraction**: nodes = components; directed edges = flow steps (and timeline `connect` ops). Duplicate edges collapse; self-loops ignored for ranking.
2. **Ranking (layers)**: longest-path layering from sources (nodes with no incoming edges get rank 0). Cycles (e.g. `login_flow.ade`'s `db --> auth --> frontend` back-edges) are handled by ignoring edges that would revisit a node during a DFS — back-edges don't create new ranks.
3. **Cluster constraint**: all members of an `infra` must occupy contiguous ranks/slots; the boundary box is the members' bounding box plus padding, with the label/logo band on top. If members' ranks are non-adjacent, intermediate empty rank slots are allowed inside the box.
4. **In-rank ordering**: barycenter heuristic (average position of neighbors in the previous rank) — one pass is enough at this scale. `external` components bias to the start of their rank.
5. **Coordinates**: ranks spaced along the main axis (LR: x; TD: y) with fixed ideal gaps (e.g. 2.0 units between ranks, 1.0 between siblings), nodes centered within their rank, whole drawing centered on origin.

**Alternative rejected:** force-directed layout — non-deterministic, worse for pipeline-shaped diagrams, and Mermaid's own look comes from layering.

### D3: Content-based card sizing via abstract metrics

The layout pass estimates each card's width/height from label length, sublabel presence, and logo presence, using tuned constants (e.g. `width ≈ max(MIN_W, chars × CHAR_W + padding)`), mirrored by `CardBuilder`'s auto-sizing so estimate and render agree closely. Exact Manim text metrics are *not* used — that would drag Manim into the layout layer for ~5% better estimates. `CardBuilder.size(...)` stays as a programmatic API (hand-written example scenes use it); only the DSL surface loses `size:`.

### D4: Canvas fitting — layout at ideal spacing, then uniform scale-down

After solving, compare the drawing's bounding box to the usable frame (14.22 × 8.0 minus a safety margin). If it overflows, codegen wraps the scene in a uniform scale factor `s = min(1, usable_w / w, usable_h / h)` applied to the whole layout (positions and card sizes scale together). If `s < 0.7`, `run_file` prints a warning: the scene is likely illegible and should be split. **Alternative rejected:** compressing gaps before scaling — more moving parts for marginal gain at this node count; revisit if real scenes hit the warning often.

### D5: Incremental re-layout for timelines

The generated timeline scene is compiled as a sequence of *layout snapshots*: codegen replays the timeline ops, and at each graph-changing op (`add`, `connect`) re-runs `layout.solve` on the graph-so-far (visible nodes + edges declared so far). Between snapshots:

- nodes present in both → `card.animate.move_to(new_pos)` (played together)
- new node → `FadeIn` at its position in the new snapshot
- existing connections re-anchor: connections are redrawn/updated after moves so arrows track their endpoints

All snapshots are computed at compile time (the full timeline is known), so this is still a pure codegen concern — no runtime layout. The *final* snapshot is used for canvas fitting (scale factor fixed across the whole timeline, so nothing jumps in size mid-animation).

**Why incremental over one global final layout?** The re-accommodation ("nodes slide to make room") is the content of a scaling story like `scene2.ade`; a global layout would leave awkward reserved gaps at the start. Cost: connection re-anchoring after moves needs care (see Risks).

### D6: Hard removal surface

| Layer | Removed |
|---|---|
| `lexer.py` | `AT`, `SIZE`, `MOVE`, `TO` tokens (keep any still used elsewhere — verify before deleting) |
| `parser.py` | `at:`/`size:` attribute rules, `move` timeline op rule; AST docstring updated |
| `semantic.py` | `Component.at/size`, `Boundary.at/size`, `TLMove`; validation of those attrs |
| `codegen.py` | `_static_explicit`, `_static_auto`, the explicit/auto switch, `_pos` on author coords, `TLMove` branch |
| `recognize.py` | matching grammar rules (kept in sync; it is a parallel grammar, Spanish comments preserved) |
| `examples/*.ade` | rewritten coordinate-free |
| README | cheatsheet updated: attrs removed, `direction:` added |

New surface: `DIRECTION` handling — top-level `direction: LR` / `direction: TD` statement, at most one per file (semantic error on duplicates), default `LR` when absent, stored on `Model`.

## Risks / Trade-offs

- **[Estimate drift]** Abstract card metrics disagree with rendered Manim sizes → cards overlap or gaps look uneven. → Mitigation: generous default gaps; keep the estimate constants next to `CardBuilder`'s sizing logic with a comment binding them; end-to-end render of all examples as the acceptance check.
- **[Connection re-anchoring in timelines]** After a re-layout move, existing arrows point at stale positions. → Mitigation: generated code rebuilds or updates connections in the same play as the moves; covered by an explicit spec scenario.
- **[Cycles in flows]** `login_flow.ade` has response edges (db→auth→frontend). Naïve longest-path loops forever. → Mitigation: DFS-based back-edge detection is part of the ranking algorithm from day one, with a unit test using `login_flow`'s exact graph.
- **[Aesthetic regression vs hand-tuned scenes]** Hand-placed `scene4.ade` was tuned to look good; the solver's first output may look worse. → Mitigation: treat the current rendered examples as the visual bar; tune gap constants against them before merging.
- **[Breaking change with no escape hatch]** Removing `at:` means no manual override exists if the solver misbehaves. Accepted deliberately (Mermaid-style simplicity); the escape hatch is fixing the solver.

## Migration Plan

Single-repo, no external users. Land as one change: grammar removal + layout pass + codegen rewrite + examples rewrite must ship together (the old examples don't parse under the new grammar). Verification order: layout unit tests → `recognize` over all rewritten examples → full renders of all examples.

## Open Questions

- Whether `TLShow` of a not-yet-connected node places it by kind heuristic only (rank 0 guess) until its first `connect` refines it — current answer: yes, solve with whatever edges exist at that point; acceptable jitter at this scale.
