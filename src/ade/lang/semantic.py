"""Semantic analysis for the ADE architecture primitives.

Walks the AST produced by the parser, checks that component references
are valid and that `step` blocks are chronologically consecutive, and
builds the `Model` that `codegen.py` turns into a Manim script.
"""

from dataclasses import dataclass, field


class SemanticError(Exception):
    """Raised when the AST breaks a semantic rule (undeclared name, out-of-order step, ...)."""


@dataclass
class Component:
    kind: str  # service | gateway | database
    name: str
    label: str
    color: str
    infra: str | None = None  # label of the infra block it belongs to, if any


@dataclass
class Step:
    number: int
    source: str
    protocol: str | None
    target: str


@dataclass
class Flow:
    label: str
    steps: list[Step]


@dataclass
class Model:
    components: dict[str, Component] = field(default_factory=dict)
    infra_labels: list[str] = field(default_factory=list)
    flows: list[Flow] = field(default_factory=list)

    def has_architecture(self):
        return bool(self.components)


def validate(ast):
    """Build and validate a Model from the raw AST. Raises SemanticError on failure."""
    model = Model()

    for node in ast:
        kind = node[0]
        if kind != "component":
            continue
        _, comp_kind, name, label, color, lineno = node
        if name in model.components:
            raise SemanticError(
                f"line {lineno}: component {name!r} is already declared"
            )
        model.components[name] = Component(comp_kind, name, label, color)

    for node in ast:
        kind = node[0]
        if kind == "infra":
            _, label, names, lineno = node
            model.infra_labels.append(label)
            for name in names:
                if name not in model.components:
                    raise SemanticError(
                        f"line {lineno}: infra {label!r} references undeclared component {name!r}"
                    )
                model.components[name].infra = label
        elif kind == "flow":
            _, label, raw_steps, lineno = node
            expected = 1
            steps = []
            for step_node in raw_steps:
                _, number, source, protocol, target, step_lineno = step_node
                if number != expected:
                    raise SemanticError(
                        f"line {step_lineno}: expected step {expected}, found step {number}"
                    )
                for endpoint in (source, target):
                    if endpoint not in model.components:
                        raise SemanticError(
                            f"line {step_lineno}: step {number} references undeclared component {endpoint!r}"
                        )
                steps.append(Step(number, source, protocol, target))
                expected += 1
            model.flows.append(Flow(label, steps))

    return model
