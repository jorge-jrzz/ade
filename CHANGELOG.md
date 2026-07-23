# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-23

First release of ADE (Architectural Design Engine): a DSL for describing and
animating software architectures, rendered to video with Manim.

### Added

#### Language (`.ade` DSL)

- Component declarations: `service`, `gateway`, `database`, `external`, with
  optional `logo`, `sublabel`, `kind`, and legacy inline `color`.
- `infra` boundaries: dashed auto-sized regions wrapping member components.
- `flow` blocks: numbered steps (`--[label]-->`, optional `curved`) that drive
  the layout and the connection animations.
- `timeline` blocks: imperative animation (`show` / `add` / `connect` / `wait`)
  with incremental re-layout — existing nodes slide to make room.
- Top-level `direction: LR | TD` layout hint.
- Classic statements: `sit(...)` output and arithmetic assignments, evaluated
  by a direct interpreter.
- PLY-based lexer and parser producing a plain-tuple AST, semantic validation
  into a `Model`, and a standalone syntax recognizer
  (`python -m ade.lang.recognize`).

#### Automatic layout

- Pure-Python Sugiyama-style layered layout (`ade.layout`): the DSL carries no
  coordinates or sizes. Components are placed from flow order, cards are
  auto-sized from content, boundaries wrap their members, and the scene is
  scaled to fit the 16:9 frame with a legibility warning when it must shrink.

#### Rendering (Manim layer)

- Code generation from a validated `Model` to a Manim scene script.
- Fluent component builders: `CardBuilder`, `BoundaryBuilder`,
  `ConnectionBuilder` (curved arrows, labels, packet-flow animations).
- `LIGHT` theme and bundled PNG logo assets resolved by short alias
  (`nestjs`, `python`, `aws`, `postgresql`, ...).

#### CLI

- `ade <file.ade>` runs the full pipeline: parse, validate, interpret, layout,
  codegen, and render.
- `--quality` / `-q` presets: `low`/`l` (default, 854x480 15FPS), `medium`/`m`
  (1280x720 30FPS), `high`/`h` (1920x1080 60FPS).
- `--output-dir` / `-o`: destination for the final MP4 only (default
  `ade-videos/`); created on demand, overwrites same-named videos. Internal
  Manim artifacts stay under `build/`.

#### Tooling

- Fast Manim-free test suite (`pytest`) covering the layout pass and the CLI.
- `ruff` linting and `ty` typechecking, both at zero diagnostics.
- `uv`-managed project (Python 3.13) with `mise` tasks for setup and examples.

[0.1.0]: https://github.com/jorge-jrzz/ade/releases/tag/v0.1.0
