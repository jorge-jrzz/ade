# layout-engine

## ADDED Requirements

### Requirement: Coordinate-free language surface
The ADE language SHALL NOT accept manual placement syntax: the `at:` and `size:` attributes (on components and infra blocks) and the timeline `move` op MUST be removed from the grammar entirely — lexer, parser, semantic model, codegen, and the standalone recognizer (`recognize.py`). Files using the removed syntax MUST fail with a syntax error, not a warning.

#### Scenario: at attribute is rejected
- **WHEN** a `.ade` file declares `service web "Web" { at: (-4.4, 0) }`
- **THEN** parsing fails with a syntax error and no scene is generated

#### Scenario: size attribute is rejected
- **WHEN** a `.ade` file declares `service web "Web" { size: 2.8 }` or an infra block with `size: (7.2, 5.6)`
- **THEN** parsing fails with a syntax error

#### Scenario: timeline move is rejected
- **WHEN** a timeline contains `move web1 to (-4.6, -0.8)`
- **THEN** parsing fails with a syntax error

#### Scenario: no zombie code remains
- **WHEN** the change is complete
- **THEN** `Component.at`, `Component.size`, `Boundary.at`, `Boundary.size`, `TLMove`, `_static_explicit`, and the explicit/auto codegen switch no longer exist in the codebase

### Requirement: Automatic layered layout
The system SHALL compute positions for all components via a deterministic layered (Sugiyama-style) layout in a pure-Python pass between semantic validation and codegen. Flow steps (and timeline `connect` ops) SHALL define the directed edges used for layering; nodes with no incoming edges start the first layer. The layout pass MUST NOT import Manim or `ade.animations`.

#### Scenario: pipeline lays out in flow order
- **WHEN** a scene declares components `client → api → proc → db` connected by flow steps
- **THEN** each component is placed one layer after its predecessor along the main axis, with no overlaps

#### Scenario: cyclic flows terminate
- **WHEN** a flow contains response edges forming a cycle (e.g. `frontend → api → auth → db → auth → frontend` as in `login_flow.ade`)
- **THEN** layout completes (back-edges do not create layers) and every component still receives exactly one position

#### Scenario: deterministic output
- **WHEN** the same `.ade` file is compiled twice
- **THEN** the computed positions are identical

### Requirement: Infra boundaries are placed automatically
The layout SHALL keep all members of an `infra` block spatially contiguous and SHALL compute the boundary box as the members' bounding box plus padding, with room for the boundary's label and optional logo. Boundary geometry is computed, never author-specified.

#### Scenario: boundary encloses its members
- **WHEN** an infra block declares members `proc` and `db`
- **THEN** the rendered dashed boundary fully contains both cards with visible padding and its label does not overlap any card

#### Scenario: non-members stay outside
- **WHEN** a component is not listed in the infra block
- **THEN** its card is placed outside the boundary box

### Requirement: Direction control
The language SHALL support a top-level `direction:` statement with values `LR` and `TD`. When absent, direction defaults to `LR`. More than one `direction:` statement in a file SHALL be a semantic error.

#### Scenario: default is left-to-right
- **WHEN** a file has no `direction:` statement
- **THEN** layers advance along the horizontal axis, left to right

#### Scenario: top-down layout
- **WHEN** a file declares `direction: TD`
- **THEN** layers advance along the vertical axis, top to bottom

#### Scenario: duplicate direction rejected
- **WHEN** a file declares `direction:` twice
- **THEN** compilation fails with a semantic error naming the duplicate

### Requirement: Content-based card sizing
Card dimensions SHALL be derived from card content (label length, sublabel presence, logo presence) using abstract size estimates shared between the layout pass and `CardBuilder`, with no Manim dependency in the layout pass. The DSL exposes no size control.

#### Scenario: long labels get wider cards
- **WHEN** two services are declared, one labeled `"DB"` and one labeled `"Processing Service"`
- **THEN** the second card is wider than the first and neither label overflows its card

### Requirement: Canvas fitting with legibility warning
The layout SHALL be computed at ideal spacing and then, if its bounding box exceeds the usable 16:9 Manim frame (~14.22 × 8.0 units minus a margin), the whole scene SHALL be scaled down uniformly to fit. When the applied scale factor falls below the legibility threshold (0.7), the compiler SHALL print a warning suggesting the scene be split.

#### Scenario: small scene renders at natural size
- **WHEN** a scene's ideal layout fits within the usable frame
- **THEN** no scaling is applied

#### Scenario: oversized scene is scaled and warned
- **WHEN** a scene's ideal layout requires a scale factor below 0.7 to fit
- **THEN** the scene still renders fully inside the frame and a legibility warning is printed to the console

### Requirement: Incremental timeline re-layout
Timelines SHALL consist only of `show`, `add`, `connect`, and `wait` ops. At each graph-changing op (`add`, `connect`), the system SHALL re-solve the layout for the graph visible so far and animate existing nodes from their previous positions to their new ones; new nodes fade in at their solved position. Existing connections SHALL track their endpoints across these moves. All snapshots are computed at compile time, and one scale factor (from the final snapshot) applies to the entire timeline.

#### Scenario: adding a node makes room
- **WHEN** a timeline shows `web1` and `db` connected, then executes `add service web2` and `connect web2 --> db`
- **THEN** `web1` and `db` animate to new positions that accommodate `web2`, and `web2` fades in at its position without overlapping either

#### Scenario: connections follow moved nodes
- **WHEN** a re-layout moves nodes that already have connections between them
- **THEN** after the move, every arrow starts and ends at the current facing edges of its endpoint cards

#### Scenario: stable scale across the timeline
- **WHEN** a timeline grows from 2 to 4 nodes
- **THEN** card sizes do not change mid-animation; the scale chosen for the final snapshot is used from the first frame
