"""Generates a runnable Manim script from a validated semantic.Model.

Placement is decided upstream by the pure-Python layout pass (`ade.layout`):
codegen consumes solved geometry and emits builder calls, so it is a dumb
translator with no layout logic of its own. Two shapes are produced:

* static architecture  -> components + boundaries + a flow of connections,
  laid out once and scaled uniformly to fit the frame.
* timeline             -> an imperative sequence (show/add/connect/wait) where
  each graph-changing op re-solves the layout and existing nodes animate to
  their new positions (incremental re-layout).

Logo aliases (e.g. `nestjs`) are resolved to asset paths here via
`assets.find_logo`, keeping the language layer free of Manim.
"""

import re

from ade import layout
from ade.animations.components.assets import find_logo
from ade.animations.themes import LIGHT
from ade.lang.semantic import SemanticError, TLAdd, TLConnect, TLShow, TLWait

GENERATED_IMPORTS = [
    "from manim import DOWN, Dot, RIGHT, LEFT, DL, DR, FadeIn, Group, Scene, Text, Transform, UL, UR, VGroup",
    "from ade.animations.components import BoundaryBuilder, CardBuilder, CardKind, ConnectionBuilder",
    "from ade.animations.themes import LIGHT",
]


def _slugify(label, fallback="Architecture"):
    words = re.findall(r"[A-Za-z0-9]+", label or "")
    if not words:
        return fallback
    return "".join(word.capitalize() for word in words)


def _coord(x, y):
    return f"[{round(x, 3)}, {round(y, 3)}, 0]"


def _port_coord(node, port, offset, scale=1.0):
    x, y = node.x, node.y
    if port == "left":
        x -= node.width / 2
        y += offset
    elif port == "right":
        x += node.width / 2
        y += offset
    elif port == "top":
        x += offset
        y += node.height / 2
    else:
        x += offset
        y -= node.height / 2
    return _coord(x * scale, y * scale)


def _resolve_logo(alias):
    """A raw path (with a slash or .png) is used as-is; anything else is a
    short alias resolved against the asset library."""
    if "/" in alias or alias.endswith(".png"):
        return alias
    try:
        return find_logo(alias)
    except ValueError as error:
        raise SemanticError(str(error)) from error


def _card_expr(comp, size=None):
    """The CardBuilder(...).build() expression for a component. `size` forces
    the solved (width, height) so the render matches the layout estimate."""
    parts = [
        f"CardBuilder().label({comp.label!r})",
        f".kind(CardKind.{comp.card_kind.upper()})",
    ]
    if comp.logo:
        parts.append(f".logo({_resolve_logo(comp.logo)!r})")
    if comp.sublabel:
        parts.append(f".sublabel({comp.sublabel!r})")
    if size is not None:
        parts.append(f".size(width={round(size[0], 3)}, height={round(size[1], 3)})")
    parts.append(".build()")
    return "".join(parts)


def _boundary_expr(box):
    parts = [f"BoundaryBuilder().label({box.label!r})"]
    if box.logo:
        parts.append(f".logo({_resolve_logo(box.logo)!r})")
    parts.append(
        f".size({round(box.width, 3)}, {round(box.height, 3)}).at({_coord(box.x, box.y)}).build()"
    )
    return "".join(parts)


def _connection_expr(
    src_var,
    dst_var,
    label,
    curved,
    label_scale=None,
    route_offset=0.0,
    color=None,
    anchors=None,
    label_position=None,
):
    parts = [f"ConnectionBuilder().between({src_var}, {dst_var})"]
    if anchors is not None:
        source, target, horizontal = anchors
        parts.append(f".anchors({source}, {target}, {horizontal!r})")
    if label_position is not None:
        parts.append(f".label_position({label_position})")
    if color is not None:
        parts.append(f".color({color!r})")
    if label:
        parts.append(f".label({label!r})")
        if label_scale is not None:
            parts.append(f".label_size({round(22 * label_scale, 3)})")
    if curved:
        parts.append(".curved()")
    if route_offset:
        parts.append(f".route_offset({round(route_offset, 3)})")
    parts.append(".build()")
    return "".join(parts)


def generate_manim_script(model):
    """Return (script_source, scene_name, illegible). `illegible` is the
    layout's below-threshold legibility flag, surfaced so the driver can warn."""
    if model.timelines:
        return _generate_timeline(model, model.timelines[0])
    return _generate_static(model)


# --- static architecture ----------------------------------------------------


def _generate_static(model):
    result = layout.solve(model)
    scene_label = (
        model.flows[0].label
        if model.flows
        else (model.boundaries[0].label if model.boundaries else None)
    )
    scene_name = f"{_slugify(scene_label)}Scene"

    lines = ["        cards = {}"]
    for name, comp in model.components.items():
        g = result.nodes[name]
        lines.append(
            f"        cards[{name!r}] = {_card_expr(comp, (g.width, g.height))}.move_to({_coord(g.x, g.y)})"
        )
    for i, box in enumerate(result.boundaries):
        lines.append(f"        boundary_{i} = {_boundary_expr(box)}")

    use_legend = result.legend
    conn_vars = _connection_definitions(model, result, lines, use_legend)
    legend_vars, legend_steps = _legend_definitions(model, lines, use_legend)

    # Group the complete scene before scaling so connections and labels follow
    # the same transform as cards and boundaries.
    members = [f"boundary_{i}" for i in range(len(result.boundaries))]
    members += [f"cards[{n!r}]" for n in model.components]
    members += conn_vars
    members += legend_vars
    if members:
        lines.append(f"        scene_group = Group({', '.join(members)})")
        if result.scale < 0.999:
            lines.append(f"        scene_group.scale({round(result.scale, 4)})")
        if legend_vars:
            corner = getattr(model, "legend_corner", "TR")
            edge = {"TL": "UL", "TR": "UR", "BL": "DL", "BR": "DR"}[corner]
            lines.append(f"        legend.to_corner({edge}, buff=0.3)")

    for i in range(len(result.boundaries)):
        lines.append(f"        self.play(FadeIn(boundary_{i}), run_time=1.2)")

    fade_ins = ", ".join(f"FadeIn(cards[{n!r}], scale=0.85)" for n in model.components)
    if fade_ins:
        lines.append(f"        self.play({fade_ins}, run_time=1.2)")
    lines += _flow_lines(model, conn_vars, legend_steps)
    lines.append("        self.wait(2)")
    return _assemble(scene_name, lines), scene_name, result.illegible


def _connection_definitions(model, result, lines, use_legend=False):
    conn_vars = []
    for flow_index, flow in enumerate(model.flows):
        lines.append("")
        lines.append(f"        # flow: {flow.label}")
        for step_index, step in enumerate(flow.steps):
            var = f"conn_{len(conn_vars)}"
            geometry = result.connections[len(conn_vars)]
            anchors = (
                _port_coord(result.nodes[step.source], geometry.source_port, geometry.source_offset),
                _port_coord(result.nodes[step.target], geometry.target_port, geometry.target_offset),
                geometry.horizontal,
            )
            label_position = _coord(geometry.label_x, geometry.label_y)
            expr = _connection_expr(
                f"cards[{step.source!r}]",
                f"cards[{step.target!r}]",
                None if use_legend else step.label,
                step.curved,
                route_offset=geometry.route_offset,
                color=LIGHT.flow_color(flow_index, step_index),
                anchors=anchors,
                label_position=label_position,
            )
            lines.append(f"        {var} = {expr}")
            conn_vars.append(var)
    return conn_vars


def _legend_definitions(model, lines, enabled=True):
    if not enabled:
        return [], {}
    entries = [
        (index, flow)
        for index, flow in enumerate(model.flows)
        if any(step.label for step in flow.steps)
    ]
    if not entries:
        return [], {}

    parts = []
    step_vars = {}
    for index, flow in entries:
        color = LIGHT.flow_color(index)
        header = f"legend_flow_{index}_header"
        parts.append(
            f"VGroup(Dot(radius=0.08, color={color!r}), Text({flow.label!r}, font_size=24, color={color!r})).arrange(RIGHT, buff=0.12)"
        )
        lines.append(f"        {header} = {parts.pop()}")
        lines.append(f"        {header}.set_opacity(0)")
        step_groups = []
        for step_index, step in enumerate(flow.steps):
            if not step.label:
                continue
            var = f"legend_flow_{index}_step_{step_index}"
            lines.append(
                f"        {var} = Text({step.label!r}, font_size=24, color={LIGHT.flow_color(index, step_index)!r}).set_opacity(0)"
            )
            step_groups.append(var)
            step_vars[(index, step_index)] = (header, var)
        entry = f"legend_entry_{index}"
        members = [header, *step_groups]
        lines.append(f"        {entry} = VGroup({', '.join(members)}).arrange(DOWN, aligned_edge=LEFT, buff=0.08)")
        parts.append(entry)
    lines.append(
        "        legend = VGroup(" + ", ".join(parts) + ").arrange(RIGHT, buff=0.35)"
    )
    return ["legend"], step_vars


def _flow_lines(model, conn_vars, legend_steps):
    lines = []
    if conn_vars:
        connection_index = 0
        for flow_index, flow in enumerate(model.flows):
            flow_has_labels = any(step.label for step in flow.steps)
            header_shown = False
            for step_index, step in enumerate(flow.steps):
                var = conn_vars[connection_index]
                connection_index += 1
                reveals = []
                if flow_has_labels and not header_shown:
                    header, _ = legend_steps.get((flow_index, step_index), (f"legend_flow_{flow_index}_header", ""))
                    reveals.append(f"{header}.animate.set_opacity(1)")
                    header_shown = True
                if step.label and (flow_index, step_index) in legend_steps:
                    _, step_var = legend_steps[(flow_index, step_index)]
                    reveals.append(f"{step_var}.animate.set_opacity(1)")
                anims = ", ".join([f"{var}.grow()", *reveals])
                lines.append(f"        self.play({anims})")
        if not model.flows:
            for var in conn_vars:
                lines.append(f"        self.play({var}.grow())")
        lines.append("")
        lines.append("        # a request travels through the pipeline")
        for var in conn_vars:
            lines.append(f"        self.play({var}.packet_flow(run_time=0.9))")
    return lines


# --- timeline (incremental re-layout) ---------------------------------------


def _generate_timeline(model, timeline):
    scene_name = f"{_slugify(timeline.label)}Scene"

    # One scale factor for the whole timeline, taken from the final snapshot so
    # nothing resizes mid-animation.
    final_visible, final_edges = {}, []
    for op in timeline.ops:
        if isinstance(op, TLShow):
            for name in op.names:
                final_visible[name] = model.components[name]
        elif isinstance(op, TLAdd):
            final_visible[op.component.name] = op.component
        elif isinstance(op, TLConnect):
            final_edges.append((op.source, op.target))
    final = layout.solve_graph(final_visible, final_edges, [], model.direction)
    scale = final.scale

    def sc(v):
        return round(v * scale, 4)

    lines = ["        cards = {}"]
    visible = {}  # name -> Component (compile-time replay)
    edges = []
    conns = []  # (var, src, tgt, label, curved)
    conn_count = 0

    def snapshot(newly):
        """Solve the current graph, create new cards, move existing ones, and
        re-anchor live connections."""
        result = layout.solve_graph(visible, edges, [], model.direction)
        newly = set(newly)
        for name in newly:
            g = result.nodes[name]
            lines.append(
                f"        cards[{name!r}] = "
                f"{_card_expr(visible[name], (sc(g.width), sc(g.height)))}.move_to({_coord(sc(g.x), sc(g.y))})"
            )

        anims = []
        moved = False
        for name in visible:
            g = result.nodes[name]
            if name in newly:
                anims.append(f"FadeIn(cards[{name!r}], scale=0.85)")
            else:
                anims.append(
                    f"cards[{name!r}].animate.move_to({_coord(sc(g.x), sc(g.y))})"
                )
                moved = True
        if anims:
            lines.append(f"        self.play({', '.join(anims)})")

        # Existing arrows now point at stale positions; rebuild each from the
        # moved cards and Transform the live connection into it.
        if moved and conns:
            reanchor = []
            for k, (var, src, tgt, label, curved) in enumerate(conns):
                target = f"{var}_re{k}"
                geometry = result.connections[k]
                anchors = (
                    _port_coord(result.nodes[src], geometry.source_port, geometry.source_offset, scale),
                    _port_coord(result.nodes[tgt], geometry.target_port, geometry.target_offset, scale),
                    geometry.horizontal,
                )
                label_position = _coord(geometry.label_x * scale, geometry.label_y * scale)
                lines.append(
                    f"        {target} = {_connection_expr(f'cards[{src!r}]', f'cards[{tgt!r}]', label, curved, route_offset=geometry.route_offset, anchors=anchors, label_position=label_position)}"
                )
                reanchor.append(f"Transform({var}, {target})")
            lines.append(f"        self.play({', '.join(reanchor)}, run_time=0.5)")
        return result

    for op in timeline.ops:
        if isinstance(op, TLShow):
            newly = [n for n in op.names if n not in visible]
            for name in op.names:
                visible[name] = model.components[name]
            snapshot(newly)
        elif isinstance(op, TLAdd):
            visible[op.component.name] = op.component
            snapshot([op.component.name])
        elif isinstance(op, TLConnect):
            edges.append((op.source, op.target))
            result = snapshot([])  # positions may shift to make room for the new edge
            var = f"conn_{conn_count}"
            conn_count += 1
            expr = _connection_expr(
                f"cards[{op.source!r}]",
                f"cards[{op.target!r}]",
                op.label,
                op.curved,
                label_scale=scale,
                route_offset=result.connections[-1].route_offset,
                color=LIGHT.flow_color(0, conn_count),
                anchors=(
                    _port_coord(
                        result.nodes[op.source],
                        result.connections[-1].source_port,
                        result.connections[-1].source_offset,
                        scale,
                    ),
                    _port_coord(
                        result.nodes[op.target],
                        result.connections[-1].target_port,
                        result.connections[-1].target_offset,
                        scale,
                    ),
                    result.connections[-1].horizontal,
                ),
                label_position=_coord(
                    result.connections[-1].label_x * scale,
                    result.connections[-1].label_y * scale,
                ),
            )
            lines.append(f"        {var} = {expr}")
            lines.append(f"        self.play({var}.grow())")
            conns.append((var, op.source, op.target, op.label, op.curved))
        elif isinstance(op, TLWait):
            lines.append("        self.wait(0.8)")

    lines.append("        self.wait(2)")
    return _assemble(scene_name, lines), scene_name, final.illegible


# --- shared -----------------------------------------------------------------


def _assemble(scene_name, body_lines):
    header = list(GENERATED_IMPORTS) + [
        "",
        "",
        f"class {scene_name}(Scene):",
        "    def construct(self):",
        "        self.camera.background_color = LIGHT.background",
    ]
    return "\n".join(header + body_lines) + "\n"
