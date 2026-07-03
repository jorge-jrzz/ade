"""Generates a runnable Manim script from a validated semantic.Model.

The generated script only calls the helpers in ade_runtime.py with
concrete data (labels, colors, groupings, step order) — it doesn't
re-implement any Manim boilerplate itself.
"""

import re


def _slugify(label, fallback="architecture"):
    words = re.findall(r"[A-Za-z0-9]+", label or "")
    if not words:
        return fallback
    return "".join(word.capitalize() for word in words)


def generate_manim_script(model):
    scene_slug = _slugify(model.flows[0].label if model.flows else None, "Architecture")
    scene_name = f"{scene_slug}Scene"

    lines = [
        "import sys",
        "from pathlib import Path",
        "",
        "sys.path.insert(0, str(Path(__file__).resolve().parent.parent))",
        "",
        "from manim import Scene, VGroup, SurroundingRectangle, Text, FadeIn, WHITE, RIGHT, UP",
        "from ade_runtime import make_node, animate_step",
        "",
        "",
        f"class {scene_name}(Scene):",
        "    def construct(self):",
        "        nodes = {}",
    ]

    for name, comp in model.components.items():
        lines.append(
            f"        nodes[{name!r}] = make_node({comp.label!r}, {comp.color!r})"
        )

    lines.append("")

    # Group components that belong to the same infra block, box them, and
    # arrange everything (standalone nodes + infra boxes) left to right.
    top_level_groups = []
    for infra_label in model.infra_labels:
        members = [n.name for n in model.components.values() if n.infra == infra_label]
        var = f"infra_{_slugify(infra_label, 'infra').lower()}"
        members_list = ", ".join(f"nodes[{m!r}]" for m in members)
        lines.append(f"        {var}_members = VGroup({members_list}).arrange(RIGHT, buff=1.0)")
        lines.append(f"        {var}_box = SurroundingRectangle({var}_members, color=WHITE, buff=0.5)")
        lines.append(
            f"        {var}_label = Text({infra_label!r}, font_size=20).next_to({var}_box, UP, buff=0.15)"
        )
        lines.append(f"        {var} = VGroup({var}_members, {var}_box, {var}_label)")
        top_level_groups.append(var)

    standalone = [n.name for n in model.components.values() if n.infra is None]
    for name in standalone:
        top_level_groups.append(f"nodes[{name!r}]")

    lines.append("")
    lines.append(f"        layout = VGroup({', '.join(top_level_groups)}).arrange(RIGHT, buff=2.0)")
    lines.append("        self.play(FadeIn(layout))")
    lines.append("        self.wait(0.5)")
    lines.append("")

    for flow in model.flows:
        lines.append(f"        # flow: {flow.label}")
        for step in flow.steps:
            lines.append(
                f"        animate_step(self, nodes[{step.source!r}], nodes[{step.target!r}], {step.protocol!r})"
            )
        lines.append("")

    return "\n".join(lines) + "\n", scene_name
