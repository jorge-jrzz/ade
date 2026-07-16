# ADE (Architectural Design Engine)

DSL for describing and animating software architectures with Manim.

## Setup
```
uv sync
```

## Run
```
uv run ade examples/hello.ade        # classic: sit(...) + arithmetic
uv run ade examples/login_flow.ade   # architecture (auto-layout)
uv run ade examples/scene1.ade       # web server -> database
uv run ade examples/scene3.ade       # logos + AWS boundary
uv run ade examples/scene4.ade       # full request pipeline
uv run ade examples/scene2.ade       # timeline (scaling animation)
```
Each `.ade` with architecture generates a Manim script under `build/` and renders it.

## Package layout
- `ade/lang` — lexer, parser, semantic analysis, interpreter (the language front-end).
- `ade/animations` — Manim layer: `codegen` (turns a validated model into a scene), the
  `components` builders (`CardBuilder`, `BoundaryBuilder`, `ConnectionBuilder`), themes and assets.

## Language cheatsheet
```
// Layout direction (optional, at most once): LR (default) | TD
direction: LR

// Components: service | gateway | database | external
// Placement and size are fully automatic — no coordinates in the DSL.
service  api "API Gateway" {
    logo: nestjs          // short asset alias, resolved automatically
    sublabel: "v2"
    kind: infra           // optional CardKind override (color)
}
service  x "X" color: blue        // legacy inline color (still valid)

// Infra boundary: dashed region; members are bare ids (box is auto-sized)
infra "AWS Cloud" { logo: aws  api  db }

// Flow: --[label]--> carries a connection label; `curved` optional.
// Flow steps are the edges that drive the automatic layered layout.
flow "Login" {
    step 1: client --[HTTPS]--> api
    step 2: api --[Read/Write]--> db curved
}

// Timeline: imperative animation (show / add / connect / wait).
// Each add/connect re-solves the layout; existing nodes slide to make room.
timeline "Scaling" {
    show web1, db
    connect web1 --[Read/Write]--> db curved
    add service web2 "Web Server 2"
    connect web2 --> db
    wait
}
```
Placement is decided by the layout engine (`ade/layout.py`): components are laid out in
flow order along the `direction` axis, boundaries wrap their members, and the whole scene is
scaled to fit the 16:9 frame (a warning prints if it must shrink below legibility).

Logos are referenced by alias (`nestjs`, `python`, `aws`, `postgresql`, ...) and resolved from
`ade/animations/assets`; an unknown alias fails with the list of available ones.

## Lexer / parser only
```
uv run python -m ade.lang.lexer
uv run python -m ade.lang.recognize examples/login_flow.ade
```
