# Tasks: fix-curved-packet-flow

## 1. Implementation

- [x] 1.1 In `ConnectionBuilder.build()`, construct an explicit spine path (`ArcBetweenPoints(start, end, angle=_curve_angle)` when curved, `Line(start, end)` otherwise) and pass it to `Connection` (spine argument defaults to a straight line derived from the arrow, keeping direct constructors working)
- [x] 1.2 Rewrite `Connection.packet_flow` to animate along the spine with proportional tip trimming (derive proportion from ~0.3/path length, clamped), removing the straight-`Line` reconstruction

## 2. Verification

- [x] 2.1 Render `examples/scene1.ade` and confirm the packet follows the curved web→db arc and fades out short of the tip
- [x] 2.2 Render `examples/scene4.ade` (straight arrows) and confirm packet behavior is visually unchanged