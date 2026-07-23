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
