# Design: fix-curved-packet-flow

## Context

`ConnectionBuilder.build()` creates either an `Arrow` or a `CurvedArrow(start, end, angle=self._curve_angle)` and hands it to `Connection`. The curve angle is not retained. `Connection.packet_flow()` then reconstructs a path from `arrow.get_start()`/`get_end()` as a straight `Line`, trimming the tip end by `direction * 0.3` — correct only for straight arrows.

## Goals / Non-Goals

**Goals:**
- Packets follow the connection's real geometry (arc or line).
- Tip trim works uniformly for both shapes.

**Non-Goals:**
- Any change to arrow rendering, labels, anchors, themes, DSL, or codegen.
- Edge routing (belongs to the separate `auto-layout` change).

## Decisions

- **Spine over introspection**: the builder constructs an explicit spine path — `ArcBetweenPoints(start, end, angle=_curve_angle)` when curved, `Line(start, end)` otherwise — and passes it to `Connection` alongside the arrow. `packet_flow` animates along the spine. Rationale: rebuilding from stored parameters is simpler and more robust than extracting the arc from `CurvedArrow`'s point data (whose submobject/tip structure is a Manim implementation detail that has shifted between versions).
- **Proportional trim**: instead of shortening the endpoint by an absolute straight-line offset, trim the spine by proportion (e.g. `pointwise_become_partial(spine, 0, ~0.93)`, or an equivalent partial copy) so the packet stops just short of the tip on any path shape. The proportion can be derived from `0.3 / arc_length` clamped to a sane range, preserving today's visual gap on straight arrows.
- `Connection`'s constructor keeps its public shape (`arrow`, `label`) with the spine as an additional argument defaulting to a straight line derived from the arrow — hand-written scenes constructing `Connection` directly (if any) keep working.

## Risks / Trade-offs

- **[Arc mismatch]** If the spine's angle/endpoints drift from what `CurvedArrow` renders, the packet floats off the stroke. → Mitigation: build both from the same `start`, `end`, and `angle` values in the same method; visual check on `scene1`.
- **[Manim API variance]** `pointwise_become_partial` semantics on arcs. → Mitigation: trivial to eyeball in the rendered output; fall back to `ArcBetweenPoints` with a reduced angle span if needed.

## Migration Plan

Single-file change, lands independently of `auto-layout` in either order.