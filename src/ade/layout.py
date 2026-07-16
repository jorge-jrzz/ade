"""Automatic layered (Sugiyama-style) layout for ADE architectures.

This is a Model -> geometry pass that sits between `semantic.validate` and
`codegen`: it decides where every component goes and how big every boundary
box is, so the DSL never needs manual `at:`/`size:` coordinates.

It is **pure Python and Manim-free** (same side of the layering fence as
`ade/lang`): card sizes are *estimated* from label/logo/sublabel content using
constants tuned to mirror `CardBuilder`'s own sizing, so the pass stays fast
and unit-testable without rendering. See `CARD SIZING` below — those constants
are bound to `ade.animations.components.card.CardBuilder.build`.

Pipeline:

    Model --(solve)--> LayoutResult(nodes, boundaries, scale, illegible)

`codegen` consumes the solved geometry and, for timelines, calls `solve_graph`
once per snapshot to animate incremental re-layout.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field

# --- CARD SIZING (bound to CardBuilder.build) -------------------------------
# Abstract text metrics, calibrated against Manim's Text widths so the layout
# estimate agrees with what CardBuilder renders. Kept here (not imported) to
# keep this module Manim-free; if CardBuilder's fonts/padding change, retune.
CHAR_W = 0.19  # ~width per label char at font_size 24
SUBLABEL_CHAR_W = 0.15  # ~width per sublabel char at font_size 18
LABEL_H = 0.26  # label line height (font_size 24)
SUBLABEL_H = 0.24  # sublabel line height (font_size 18)
LOGO_H = 1.1  # CardBuilder default logo height
LOGO_W = 1.1  # logos are ~square once rasterized
CONTENT_GAP = 0.25  # CardBuilder content arrange(DOWN, buff=0.25)
CARD_PADDING = 0.6  # CardBuilder.PADDING
MIN_CARD_W = 2.6  # floor so short cards still read
MAX_CARD_W = 3.6  # cap; CardBuilder scales long labels to fit inside
MIN_CARD_H = 1.1  # CardBuilder.MIN_HEIGHT

# --- SPACING ----------------------------------------------------------------
RANK_GAP = 1.7  # gap along the main axis between adjacent layers
SIBLING_GAP = 0.8  # gap along the cross axis between nodes in one layer
BOUNDARY_PAD = 0.5  # padding between an infra box and its members
BOUNDARY_LABEL_BAND = 0.7  # extra top room for the boundary label/logo

# --- CANVAS -----------------------------------------------------------------
FRAME_W = 14.22  # Manim 16:9 frame width (scene units)
FRAME_H = 8.0
FRAME_MARGIN = 0.6  # keep content off the very edge
USABLE_W = FRAME_W - FRAME_MARGIN
USABLE_H = FRAME_H - FRAME_MARGIN
LEGIBILITY_THRESHOLD = 0.7  # below this scale, text is likely illegible


@dataclass
class NodeGeom:
    x: float
    y: float
    width: float
    height: float


@dataclass
class BoundaryGeom:
    label: str
    logo: str | None
    x: float
    y: float
    width: float
    height: float


@dataclass
class LayoutResult:
    nodes: dict = field(default_factory=dict)  # name -> NodeGeom
    boundaries: list = field(default_factory=list)  # list[BoundaryGeom]
    scale: float = 1.0
    illegible: bool = False
    direction: str = "LR"


# --- card size estimation (task 1.4) ----------------------------------------


def estimate_card_size(comp):
    """Estimate a card's (width, height) from its content, mirroring
    `CardBuilder.build`. Kept abstract (no Manim) — see CARD SIZING above."""
    heights = []
    widths = []
    if comp.logo:
        heights.append(LOGO_H)
        widths.append(LOGO_W)
    heights.append(LABEL_H)
    widths.append(len(comp.label) * CHAR_W)
    if comp.sublabel:
        heights.append(SUBLABEL_H)
        widths.append(len(comp.sublabel) * SUBLABEL_CHAR_W)

    content_w = max(widths)
    content_h = sum(heights) + CONTENT_GAP * (len(heights) - 1)

    width = min(MAX_CARD_W, max(MIN_CARD_W, content_w + CARD_PADDING))
    height = max(MIN_CARD_H, content_h + CARD_PADDING)
    return width, height


# --- ranking (task 1.2) -----------------------------------------------------


def _rank_nodes(names, edges):
    """Longest-path layering. Cycles are broken by dropping DFS back-edges
    (edges whose target is still on the recursion stack), so ranking always
    terminates and every node gets exactly one rank."""
    index = {n: i for i, n in enumerate(names)}
    succ = {n: [] for n in names}
    seen = set()
    for s, t in edges:
        if s == t or s not in succ or t not in succ or (s, t) in seen:
            continue
        succ[s].append(t)
        seen.add((s, t))

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in names}
    forward = {n: [] for n in names}

    def dfs(u):
        color[u] = GRAY
        for v in succ[u]:
            if color[v] == GRAY:
                continue  # back-edge: would revisit a node on the stack
            forward[u].append(v)
            if color[v] == WHITE:
                dfs(v)
        color[u] = BLACK

    for n in sorted(names, key=lambda n: index[n]):
        if color[n] == WHITE:
            dfs(n)

    # longest-path ranks over the acyclic forward edges (Kahn topological order)
    indeg = {n: 0 for n in names}
    for u in names:
        for v in forward[u]:
            indeg[v] += 1
    rank = {n: 0 for n in names}
    queue = deque(n for n in names if indeg[n] == 0)
    while queue:
        u = queue.popleft()
        for v in forward[u]:
            rank[v] = max(rank[v], rank[u] + 1)
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)

    preds = defaultdict(list)
    for u in names:
        for v in forward[u]:
            preds[v].append(u)
    return rank, preds


# --- in-rank ordering (task 1.3) --------------------------------------------


def _order_ranks(names, rank, preds, components):
    """Barycenter ordering within each rank; `external` cards bias to the rank
    start, and members of the same infra are kept adjacent (contiguity)."""
    decl = {n: i for i, n in enumerate(names)}
    by_rank = defaultdict(list)
    for n in sorted(names, key=lambda n: decl[n]):
        by_rank[rank[n]].append(n)

    def is_external(n):
        return components[n].card_kind == "external"

    pos = {}  # node -> slot index in its rank
    for r in sorted(by_rank):
        group = by_rank[r]
        if r == min(by_rank):
            keyed = sorted(group, key=lambda n: (0 if is_external(n) else 1, decl[n]))
        else:

            def bary(n):
                ps = preds.get(n, [])
                if not ps:
                    return decl[n]
                return sum(pos[p] for p in ps if p in pos) / len(ps)

            keyed = sorted(
                group,
                key=lambda n: (0 if is_external(n) else 1, bary(n), decl[n]),
            )
        keyed = _group_clusters(keyed, components)
        by_rank[r] = keyed
        for i, n in enumerate(keyed):
            pos[n] = i
    return by_rank


def _group_clusters(seq, components):
    """Stable-group nodes so members of the same infra are adjacent."""
    first = {}
    for i, n in enumerate(seq):
        label = components[n].infra
        if label is not None and label not in first:
            first[label] = i
    base = {n: i for i, n in enumerate(seq)}

    def key(n):
        label = components[n].infra
        return (first[label] if label is not None else base[n], base[n])

    return sorted(seq, key=key)


# --- coordinate assignment (task 1.5) ---------------------------------------


def _assign_coords(by_rank, sizes, direction):
    """Place ranks along the main axis (LR: x, TD: y) and stack siblings along
    the cross axis, then center the whole drawing on the origin."""
    lr = direction == "LR"

    def main_size(n):
        return sizes[n][0] if lr else sizes[n][1]

    def cross_size(n):
        return sizes[n][1] if lr else sizes[n][0]

    # main-axis center per rank, spaced by half-extents + RANK_GAP
    main_center = {}
    prev_center = 0.0
    prev_half = 0.0
    for i, r in enumerate(sorted(by_rank)):
        half = max(main_size(n) for n in by_rank[r]) / 2
        if i == 0:
            center = 0.0
        else:
            center = prev_center + prev_half + RANK_GAP + half
        main_center[r] = center
        prev_center, prev_half = center, half

    nodes = {}
    for r in sorted(by_rank):
        seq = by_rank[r]
        total = sum(cross_size(n) for n in seq) + SIBLING_GAP * (len(seq) - 1)
        cursor = total / 2
        for n in seq:
            cs = cross_size(n)
            cross = cursor - cs / 2
            cursor -= cs + SIBLING_GAP
            w, h = sizes[n]
            if lr:
                nodes[n] = NodeGeom(main_center[r], cross, w, h)
            else:
                nodes[n] = NodeGeom(cross, -main_center[r], w, h)
    return nodes


def _boundary_boxes(boundaries, nodes):
    """A padded bounding box of each infra's (visible) members, with a top band
    reserved for the label/logo."""
    boxes = []
    for boundary in boundaries:
        members = [m for m in boundary.members if m in nodes]
        if not members:
            continue
        xs0 = min(nodes[m].x - nodes[m].width / 2 for m in members)
        xs1 = max(nodes[m].x + nodes[m].width / 2 for m in members)
        ys0 = min(nodes[m].y - nodes[m].height / 2 for m in members)
        ys1 = max(nodes[m].y + nodes[m].height / 2 for m in members)
        width = (xs1 - xs0) + 2 * BOUNDARY_PAD
        height = (ys1 - ys0) + 2 * BOUNDARY_PAD + BOUNDARY_LABEL_BAND
        cx = (xs0 + xs1) / 2
        cy = (ys0 + ys1) / 2 + BOUNDARY_LABEL_BAND / 2
        boxes.append(BoundaryGeom(boundary.label, boundary.logo, cx, cy, width, height))
    return boxes


def _recenter(nodes, boxes):
    """Shift everything so the full bounding box is centered on the origin."""
    xs, ys = [], []
    for g in nodes.values():
        xs += [g.x - g.width / 2, g.x + g.width / 2]
        ys += [g.y - g.height / 2, g.y + g.height / 2]
    for b in boxes:
        xs += [b.x - b.width / 2, b.x + b.width / 2]
        ys += [b.y - b.height / 2, b.y + b.height / 2]
    if not xs:
        return 0.0, 0.0
    dx = (min(xs) + max(xs)) / 2
    dy = (min(ys) + max(ys)) / 2
    for g in nodes.values():
        g.x -= dx
        g.y -= dy
    for b in boxes:
        b.x -= dx
        b.y -= dy
    return max(xs) - min(xs), max(ys) - min(ys)


def _fit_scale(width, height):
    """Uniform scale to fit the usable frame (never scales up)."""
    if width <= 0 or height <= 0:
        return 1.0
    return min(1.0, USABLE_W / width, USABLE_H / height)


# --- public API -------------------------------------------------------------


def solve_graph(components, edges, boundaries, direction="LR"):
    """Solve a layout for an explicit graph (used directly for timeline
    snapshots). `components` is an ordered name->Component mapping."""
    names = list(components)
    if not names:
        return LayoutResult(direction=direction)

    sizes = {n: estimate_card_size(components[n]) for n in names}
    rank, preds = _rank_nodes(names, edges)
    by_rank = _order_ranks(names, rank, preds, components)
    nodes = _assign_coords(by_rank, sizes, direction)
    boxes = _boundary_boxes(boundaries, nodes)
    width, height = _recenter(nodes, boxes)
    scale = _fit_scale(width, height)
    return LayoutResult(
        nodes=nodes,
        boundaries=boxes,
        scale=scale,
        illegible=scale < LEGIBILITY_THRESHOLD,
        direction=direction,
    )


def solve(model, direction=None):
    """Solve the static layout for a whole Model. Flow steps define the
    directed edges used for layering."""
    direction = direction or getattr(model, "direction", None) or "LR"
    edges = []
    for flow in model.flows:
        for step in flow.steps:
            edges.append((step.source, step.target))
    return solve_graph(model.components, edges, model.boundaries, direction)
