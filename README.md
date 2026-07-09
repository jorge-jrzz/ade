# ADE (Architectural Design Engine)

DSL for describing and animating software architectures with Manim.

## Setup
```
uv sync
```

## Run
```
uv run ade.py hello.ade
uv run ade.py login_flow.ade
```

## Lexer / parser only
```
uv run python lexer.py
uv run recognize.py login_flow.ade
```
