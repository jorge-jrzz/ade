"""Tests for CLI parsing and render output orchestration without Manim."""

import sys
from types import ModuleType

import pytest

import ade


@pytest.mark.parametrize(
    ("value", "quality"),
    [
        ("low", "l"),
        ("l", "l"),
        ("medium", "m"),
        ("m", "m"),
        ("high", "h"),
        ("h", "h"),
    ],
)
def test_quality_presets_are_normalized(value, quality):
    options = ade.parse_args(["scene.ade", "--quality", value])
    assert ade.QUALITY_PRESETS[options.quality] == quality


def test_cli_defaults_to_low_quality_and_ade_videos():
    options = ade.parse_args(["scene.ade"])
    assert options.quality == "low"
    assert options.output_dir == ade.DEFAULT_OUTPUT_DIR


def test_cli_accepts_short_options():
    options = ade.parse_args(["scene.ade", "-q", "h", "-o", "renders"])
    assert options.quality == "h"
    assert str(options.output_dir) == "renders"


def test_cli_rejects_invalid_quality():
    with pytest.raises(SystemExit):
        ade.parse_args(["scene.ade", "--quality", "ultra"])


def test_main_passes_normalized_options(monkeypatch):
    received = {}

    def fake_run_file(path, quality, output_dir):
        received.update(path=path, quality=quality, output_dir=output_dir)

    monkeypatch.setattr(ade, "run_file", fake_run_file)
    ade.main(["scene.ade", "-q", "medium", "-o", "renders"])

    assert received == {"path": "scene.ade", "quality": "m", "output_dir": ade.Path("renders")}


def test_render_uses_quality_and_copies_only_final_video(tmp_path, monkeypatch):
    build_dir = tmp_path / "build"
    rendered = build_dir / "videos" / "scene_scene" / "480p15" / "Scene.mp4"
    rendered.parent.mkdir(parents=True)
    rendered.write_bytes(b"new video")

    codegen = ModuleType("ade.animations.codegen")
    codegen.__dict__["generate_manim_script"] = lambda model: ("scene source", "Scene", False)
    monkeypatch.setitem(sys.modules, "ade.animations.codegen", codegen)
    monkeypatch.setattr(ade, "BUILD_DIR", build_dir)
    command = []
    monkeypatch.setattr(ade.subprocess, "run", lambda args, check: command.extend(args))

    output_dir = tmp_path / "renders"
    final = output_dir / "scene.mp4"
    output_dir.mkdir()
    final.write_bytes(b"old video")

    ade.render_architecture(object(), tmp_path / "scene.ade", "h", output_dir)

    assert "-qh" in command
    assert "--media_dir" in command
    assert command[command.index("--media_dir") + 1] == str(build_dir)
    assert (build_dir / "scene_scene.py").exists()
    assert final.read_bytes() == b"new video"
    assert list(output_dir.iterdir()) == [final]


def test_static_codegen_scales_connections_with_scene(monkeypatch):
    assets = ModuleType("ade.animations.components.assets")
    assets.__dict__["find_logo"] = lambda alias: alias
    components = ModuleType("ade.animations.components")
    themes = ModuleType("ade.animations.themes")
    from ade.animations.themes import Theme

    themes.__dict__["LIGHT"] = Theme()
    monkeypatch.setitem(sys.modules, "ade.animations.components", components)
    monkeypatch.setitem(sys.modules, "ade.animations.components.assets", assets)
    monkeypatch.setitem(sys.modules, "ade.animations.themes", themes)

    from ade.animations import codegen
    from ade.lang.semantic import Component, Flow, Model, Step

    model = Model(
        components={
            "source": Component("service", "source", "Source"),
            "target": Component("service", "target", "Target"),
        },
        flows=[
            Flow(
                "Flow",
                [
                    Step(
                        1,
                        "source",
                        "A deliberately long request label for scaling",
                        "target",
                    )
                ],
            ),
        ],
    )

    script, _, _ = codegen.generate_manim_script(model)
    connection_index = script.index("conn_0 =")
    group_index = script.index("scene_group =")
    assert connection_index < group_index
    assert "cards['source']" in script[connection_index:group_index]
    assert "cards['target']" in script[connection_index:group_index]
    assert "scene_group = Group(" in script
    assert "conn_0" in script[script.index("scene_group ="):]


def test_static_codegen_emits_connection_route_offset(monkeypatch):
    assets = ModuleType("ade.animations.components.assets")
    assets.__dict__["find_logo"] = lambda alias: alias
    components = ModuleType("ade.animations.components")
    themes = ModuleType("ade.animations.themes")
    from ade.animations.themes import Theme

    themes.__dict__["LIGHT"] = Theme()
    monkeypatch.setitem(sys.modules, "ade.animations.components", components)
    monkeypatch.setitem(sys.modules, "ade.animations.components.assets", assets)
    monkeypatch.setitem(sys.modules, "ade.animations.themes", themes)

    from ade.animations import codegen
    from ade.lang.semantic import Component, Flow, Model, Step

    model = Model(
        components={
            "source": Component("service", "source", "Source"),
            "target": Component("service", "target", "Target"),
        },
        flows=[
            Flow(
                "Flow",
                [
                    Step(1, "source", "First", "target"),
                    Step(2, "target", "Second", "source"),
                ],
            ),
        ],
    )

    script, _, _ = codegen.generate_manim_script(model)
    assert ".route_offset(-0.35)" in script
    assert ".route_offset(0.35)" in script


def test_static_codegen_emits_explicit_connection_anchors(monkeypatch):
    assets = ModuleType("ade.animations.components.assets")
    assets.__dict__["find_logo"] = lambda alias: alias
    components = ModuleType("ade.animations.components")
    themes = ModuleType("ade.animations.themes")
    from ade.animations.themes import Theme

    themes.__dict__["LIGHT"] = Theme()
    monkeypatch.setitem(sys.modules, "ade.animations.components", components)
    monkeypatch.setitem(sys.modules, "ade.animations.components.assets", assets)
    monkeypatch.setitem(sys.modules, "ade.animations.themes", themes)

    from ade.animations import codegen
    from ade.lang.semantic import Component, Flow, Model, Step

    model = Model(
        components={
            "source": Component("service", "source", "Source"),
            "target": Component("service", "target", "Target"),
        },
        flows=[Flow("Flow", [Step(1, "source", "Request", "target")])],
    )

    script, _, _ = codegen.generate_manim_script(model)
    assert ".anchors([1.3, 0.0, 0], [1.3, 0.0, 0], True)" not in script
    assert ".anchors(" in script


def test_static_codegen_emits_layout_label_positions(monkeypatch):
    assets = ModuleType("ade.animations.components.assets")
    assets.__dict__["find_logo"] = lambda alias: alias
    components = ModuleType("ade.animations.components")
    themes = ModuleType("ade.animations.themes")
    from ade.animations.themes import Theme

    themes.__dict__["LIGHT"] = Theme()
    monkeypatch.setitem(sys.modules, "ade.animations.components", components)
    monkeypatch.setitem(sys.modules, "ade.animations.components.assets", assets)
    monkeypatch.setitem(sys.modules, "ade.animations.themes", themes)

    from ade.animations import codegen
    from ade.lang.semantic import Component, Flow, Model, Step

    model = Model(
        components={
            "source": Component("service", "source", "Source"),
            "a": Component("service", "a", "A"),
            "b": Component("service", "b", "B"),
            "c": Component("service", "c", "C"),
        },
        flows=[
            Flow(
                "Fanout",
                [
                    Step(1, "source", "A", "a"),
                    Step(2, "source", "B", "b"),
                    Step(3, "source", "C", "c"),
                ],
            )
        ],
    )

    script, _, _ = codegen.generate_manim_script(model)
    positions = [line.split(".label_position(", 1)[1].split(")", 1)[0] for line in script.splitlines() if ".label_position(" in line]
    assert len(positions) == 3
    assert len(set(positions)) == 3


def test_static_codegen_colors_flows_and_adds_legend(monkeypatch):
    assets = ModuleType("ade.animations.components.assets")
    assets.__dict__["find_logo"] = lambda alias: alias
    components = ModuleType("ade.animations.components")
    themes = ModuleType("ade.animations.themes")
    from ade.animations.themes import Theme

    themes.__dict__["LIGHT"] = Theme()
    monkeypatch.setitem(sys.modules, "ade.animations.components", components)
    monkeypatch.setitem(sys.modules, "ade.animations.components.assets", assets)
    monkeypatch.setitem(sys.modules, "ade.animations.themes", themes)

    from ade.animations import codegen
    from ade.lang.semantic import Component, Flow, Model, Step

    model = Model(
        components={
            "source": Component("service", "source", "Source"),
            "target": Component("service", "target", "Target"),
        },
        flows=[
            Flow("Requests", [Step(1, "source", "Request", "target")]),
            Flow("Responses", [Step(1, "target", "Response", "source")]),
        ],
    )

    script, _, _ = codegen.generate_manim_script(model)
    assert ".color('#2563EB')" in script
    assert ".color('#EA580C')" in script
    assert "legend = VGroup(" in script
    assert "legend" in script[script.index("scene_group ="):]
    assert "Text('Request', font_size=24, color='#2563EB')" in script
    assert "from manim import DOWN, Dot, RIGHT," in script


def test_flow_palette_is_deterministic_and_varies_steps():
    from ade.animations.themes import Theme

    theme = Theme()
    assert theme.flow_color(0, 0) == theme.flow_color(0, 0)
    assert theme.flow_color(0, 0) != theme.flow_color(1, 0)
    assert theme.flow_color(0, 0) != theme.flow_color(0, 1)
