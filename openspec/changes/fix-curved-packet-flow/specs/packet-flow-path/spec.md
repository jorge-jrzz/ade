# packet-flow-path

## ADDED Requirements

### Requirement: Packets follow the connection geometry
`Connection.packet_flow` SHALL animate packets along the connection's actual geometric path: the same arc drawn by a curved connection (same endpoints and curve angle), or the straight line of a straight connection. The packet MUST remain visually on the arrow's stroke for the whole trip.

#### Scenario: curved connection
- **WHEN** a scene plays `packet_flow` on a connection built with `.curved()`
- **THEN** the packet travels along the drawn arc, not the straight chord between the endpoints

#### Scenario: straight connection
- **WHEN** a scene plays `packet_flow` on a straight connection
- **THEN** the packet travels along the straight arrow exactly as before this change

### Requirement: Packets stop short of the arrow tip
The packet's path SHALL end slightly before the arrow tip on both straight and curved connections, using proportional trimming of the path rather than a straight-line endpoint offset, preserving the current visual gap on straight arrows.

#### Scenario: no tip overlap on a curve
- **WHEN** a packet reaches the end of its trip on a curved connection
- **THEN** it fades out near, but not on top of, the arrow tip