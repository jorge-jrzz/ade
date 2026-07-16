"""Generates a runnable Manim script from a validated semantic.Model.

The generated script drives the reusable builders in
`ade.animations.components` (CardBuilder / BoundaryBuilder /
ConnectionBuilder) and the `LIGHT` theme, so a scene rendered from a
`.ade` file looks like the hand-written demos in
`ade.animations.examples`. Two shapes are produced:

* static architecture  -> components + boundaries + a flow of connections
* timeline             -> an imperative sequence (show/add/move/connect/wait)

Logo aliases (e.g. `nestjs`) are resolved to asset paths here via
`assets.find_logo`, keeping the language layer free of Manim.
"""

import re

from ade.animations.components.assets import find_logo
from ade.lang.semantic import SemanticError, TLAdd, TLConnect, TLMove, TLShow, TLWait

GENERATED_IMPORTS = [
    "from manim import Scene, FadeIn, Group, SurroundingRectangle, Text, UP, RIGHT",
    "from ade.animations.components import BoundaryBuilder, CardBuilder, CardKind, ConnectionBuilder",
    "from ade.animations.themes import LIGHT",
]


def _slugify(label, fallback="Architecture"):
    words = re.findall(r"[A-Za-z0-9]+", label or "")
    if not words:
        return fallback
    return "".join(word.capitalize() for word in words)


def _pos(at):
    x, y = at if at is not None else (0, 0)
    return f"[{x}, {y}, 0]"


def _resolve_logo(alias):
    """A raw path (with a slash or .png) is used as-is; anything else is a
    short alias resolved against the asset library."""
    if "/" in alias or alias.endswith(".png"):
        return alias
    try:
        return find_logo(alias)
    except ValueError as error:
        raise SemanticError(str(error)) from error


def _card_expr(comp):
    """The CardBuilder(...).build() expression for a component (no placement)."""
    parts = [f"CardBuilder().label({comp.label!r})", f".kind(CardKind.{comp.card_kind.upper()})"]
    if comp.logo:
        parts.append(f".logo({_resolve_logo(comp.logo)!r})")
    if comp.sublabel:
        parts.append(f".sublabel({comp.sublabel!r})")
    if comp.size is not None:
        if isinstance(comp.size, tuple):
            parts.append(f".size(width={comp.size[0]}, height={comp.size[1]})")
        else:
            parts.append(f".size(width={comp.size})")
    parts.append(".build()")
    return "".join(parts)


def _boundary_expr(boundary):
    w, h = boundary.size
    parts = [f"BoundaryBuilder().label({boundary.label!r})"]
    if boundary.logo:
        parts.append(f".logo({_resolve_logo(boundary.logo)!r})")
    parts.append(f".size({w}, {h}).at({_pos(boundary.at)}).build()")
    return "".join(parts)


def _connection_expr(src_var, dst_var, label, curved):
    parts = [f"ConnectionBuilder().between({src_var}, {dst_var})"]
    if label:
        parts.append(f".label({label!r})")
    if curved:
        parts.append(".curved()")
    parts.append(".build()")
    return "".join(parts)


def generate_manim_script(model):
    if model.timelines:
        return _generate_timeline(model, model.timelines[0])
    return _generate_static(model)


# --- static architecture ----------------------------------------------------

def _generate_static(model):
    scene_label = model.flows[0].label if model.flows else (
        model.boundaries[0].label if model.boundaries else None
    )
    scene_name = f"{_slugify(scene_label)}Scene"

    explicit = any(c.at is not None for c in model.components.values()) or any(
        b.at is not None for b in model.boundaries
    )

    body = _static_explicit(model) if explicit else _static_auto(model)
    body += _flow_lines(model)
    body.append("        self.wait(2)")

    return _assemble(scene_name, body), scene_name


def _static_explicit(model):
    lines = ["        cards = {}"]

    # boundaries with an explicit box are drawn first (behind the cards)
    boxed_later = []
    for i, boundary in enumerate(model.boundaries):
        if boundary.at is not None and isinstance(boundary.size, tuple):
            lines.append(f"        boundary_{i} = {_boundary_expr(boundary)}")
            lines.append(f"        self.play(FadeIn(boundary_{i}), run_time=1.5)")
        else:
            boxed_later.append((i, boundary))

    for name, comp in model.components.items():
        lines.append(f"        cards[{name!r}] = {_card_expr(comp)}.move_to({_pos(comp.at)})")

    fade_ins = ", ".join(f"FadeIn(cards[{n!r}], scale=0.85)" for n in model.components)
    if fade_ins:
        lines.append(f"        self.play({fade_ins}, run_time=1.2)")

    for i, boundary in boxed_later:
        members = ", ".join(f"cards[{m!r}]" for m in boundary.members)
        lines.append(f"        boundary_{i} = SurroundingRectangle(Group({members}), color=LIGHT.subtle, buff=0.5)")
        lines.append(f"        self.play(FadeIn(boundary_{i}))")

    return lines


def _static_auto(model):
    """Legacy auto-layout: box each infra group, arrange everything left→right."""
    lines = ["        cards = {}"]
    for name, comp in model.components.items():
        lines.append(f"        cards[{name!r}] = {_card_expr(comp)}")

    top_groups = []
    for boundary in model.boundaries:
        var = f"grp_{_slugify(boundary.label, 'infra').lower()}"
        members = ", ".join(f"cards[{m!r}]" for m in boundary.members)
        lines.append(f"        {var}_members = Group({members}).arrange(RIGHT, buff=1.0)")
        lines.append(f"        {var}_box = SurroundingRectangle({var}_members, color=LIGHT.subtle, buff=0.5)")
        lines.append(f"        {var}_label = Text({boundary.label!r}, font_size=20, color=LIGHT.ink).next_to({var}_box, UP, buff=0.15)")
        lines.append(f"        {var} = Group({var}_members, {var}_box, {var}_label)")
        top_groups.append(var)

    for name, comp in model.components.items():
        if comp.infra is None:
            top_groups.append(f"cards[{name!r}]")

    lines.append(f"        layout = Group({', '.join(top_groups)}).arrange(RIGHT, buff=2.0)")
    lines.append("        self.play(FadeIn(layout))")
    lines.append("        self.wait(0.5)")
    return lines


def _flow_lines(model):
    lines = []
    conn_vars = []
    for flow in model.flows:
        lines.append("")
        lines.append(f"        # flow: {flow.label}")
        for step in flow.steps:
            var = f"conn_{len(conn_vars)}"
            expr = _connection_expr(f"cards[{step.source!r}]", f"cards[{step.target!r}]", step.label, step.curved)
            lines.append(f"        {var} = {expr}")
            lines.append(f"        self.play({var}.grow())")
            conn_vars.append(var)

    if conn_vars:
        lines.append("")
        lines.append("        # a request travels through the pipeline")
        for var in conn_vars:
            lines.append(f"        self.play({var}.packet_flow(run_time=0.9))")
    return lines


# --- timeline ---------------------------------------------------------------

def _generate_timeline(model, timeline):
    scene_name = f"{_slugify(timeline.label)}Scene"
    lines = ["        cards = {}"]
    conn_count = 0

    for op in timeline.ops:
        if isinstance(op, TLShow):
            for name in op.names:
                comp = model.components[name]
                lines.append(f"        cards[{name!r}] = {_card_expr(comp)}.move_to({_pos(comp.at)})")
            fades = ", ".join(f"FadeIn(cards[{n!r}], scale=0.85)" for n in op.names)
            lines.append(f"        self.play({fades})")
        elif isinstance(op, TLAdd):
            comp = op.component
            lines.append(f"        cards[{comp.name!r}] = {_card_expr(comp)}.move_to({_pos(comp.at)})")
            lines.append(f"        self.play(FadeIn(cards[{comp.name!r}], scale=0.85))")
        elif isinstance(op, TLMove):
            lines.append(f"        self.play(cards[{op.name!r}].animate.move_to({_pos(op.to)}))")
        elif isinstance(op, TLConnect):
            var = f"conn_{conn_count}"
            conn_count += 1
            expr = _connection_expr(f"cards[{op.source!r}]", f"cards[{op.target!r}]", op.label, op.curved)
            lines.append(f"        {var} = {expr}")
            lines.append(f"        self.play({var}.grow())")
        elif isinstance(op, TLWait):
            lines.append("        self.wait(0.8)")

    lines.append("        self.wait(2)")
    return _assemble(scene_name, lines), scene_name


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
