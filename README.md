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
// Components: service | gateway | database | external
service  api "API Gateway" {
    logo: nestjs          // short asset alias, resolved automatically
    sublabel: "v2"
    at: (-4.8, -1.3)      // explicit position (omit -> auto-layout)
    size: 2.8             // width, or size: (w, h)
    kind: infra           // optional CardKind override (color)
}
service  x "X" color: blue        // legacy inline color (still valid)

// Infra boundary: dashed region; members are bare ids
infra "AWS Cloud" { logo: aws  at: (3.15, -0.4)  size: (7.2, 5.6)  api  db }

// Flow: --[label]--> carries a connection label; `curved` optional
flow "Login" {
    step 1: client --[HTTPS]--> api
    step 2: api --[Read/Write]--> db curved
}

// Timeline: imperative animation (show / add / move / connect / wait)
timeline "Scaling" {
    show web1, db
    connect web1 --[Read/Write]--> db curved
    move web1 to (-4.6, -0.8)
    add service web2 "Web Server 2" { at: (-1.4, -0.8) }
    connect web2 --> db
    wait
}
```
Logos are referenced by alias (`nestjs`, `python`, `aws`, `postgresql`, ...) and resolved from
`ade/animations/assets`; an unknown alias fails with the list of available ones.

## Lexer / parser only
```
uv run python -m ade.lang.lexer
uv run python -m ade.lang.recognize examples/login_flow.ade
```
