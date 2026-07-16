# Proposal: fix-curved-packet-flow

## Why

Animated packets (`Connection.packet_flow` in `src/ade/animations/components/connection.py`) always travel in a straight line between the arrow's endpoints, because the path is built as `Line(start, end - direction * 0.3)`. On curved connections (`ConnectionBuilder.curved()`, which draws a `CurvedArrow`) the packet visibly cuts across the arc instead of following it — every generated scene with a `curved` flow step shows the bug (e.g. `examples/scene1.ade`).

## What Changes

- `Connection` gains knowledge of its geometric spine, shared by the arrow and `packet_flow`: an arc with the builder's `_curve_angle` when curved (currently lost after `build()`), the existing straight line otherwise.
- The "stop short of the tip" trim becomes proportion-based path trimming (works on arcs and lines alike) instead of subtracting a straight-line offset from the endpoint.
- No language, model, or codegen changes; hand-written demo scenes in `ade/animations/examples` benefit automatically.

## Capabilities

### New Capabilities

- `packet-flow-path`: packets animated along a connection follow the connection's actual geometry (straight or curved), stopping short of the arrow tip.

### Modified Capabilities

- (none — `openspec/specs/` has no existing capability covering connections)

## Impact

- `src/ade/animations/components/connection.py` only (`Connection`, `ConnectionBuilder`).
- Verification: no test suite; verify by rendering `examples/scene1.ade` (curved web→db connection) and a straight-arrow example (e.g. `examples/scene4.ade`) and observing packet paths.
- Independent of the `auto-layout` change; neither depends on the other.
