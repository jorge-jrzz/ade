"""Semantic analysis for the ADE architecture primitives.

Walks the AST produced by the parser, checks that component references
are valid and that `step` blocks are chronologically consecutive, and
builds the `Model` that `codegen.py` turns into a Manim script.

This layer stays free of Manim (and of the `ade.animations` package):
logo aliases are kept as raw strings here and only resolved to asset
paths later, in codegen.
"""

from dataclasses import dataclass, field


class SemanticError(Exception):
    """Raised when the AST breaks a semantic rule (undeclared name, out-of-order step, ...)."""


# DSL component keyword -> CardKind value (see ade.animations.components.card.CardKind
# and the accent fields of ade.animations.themes.Theme).
KIND_MAP = {
    "service": "service",
    "gateway": "service",
    "database": "database",
    "external": "external",
}
VALID_CARD_KINDS = {"service", "database", "infra", "external"}


@dataclass
class Component:
    kind: str  # DSL keyword: service | gateway | database | external
    name: str
    label: str
    color: str | None = None
    logo: str | None = None       # raw alias/path; resolved in codegen
    sublabel: str | None = None
    at: tuple | None = None       # (x, y) or None -> auto-layout
    size: object = None           # float (width) | (width, height) | None
    card_kind: str = "service"    # CardKind value used by the builders
    infra: str | None = None      # label of the boundary it belongs to, if any


@dataclass
class Boundary:
    label: str
    logo: str | None = None
    at: tuple | None = None
    size: tuple | None = None
    members: list = field(default_factory=list)


@dataclass
class Step:
    number: int
    source: str
    label: str | None
    target: str
    curved: bool = False


@dataclass
class Flow:
    label: str
    steps: list


# --- timeline ops -----------------------------------------------------------

@dataclass
class TLShow:
    names: list


@dataclass
class TLAdd:
    component: Component


@dataclass
class TLMove:
    name: str
    to: tuple


@dataclass
class TLConnect:
    source: str
    label: str | None
    target: str
    curved: bool = False


@dataclass
class TLWait:
    pass


@dataclass
class Timeline:
    label: str
    ops: list


@dataclass
class Model:
    components: dict = field(default_factory=dict)
    boundaries: list = field(default_factory=list)
    flows: list = field(default_factory=list)
    timelines: list = field(default_factory=list)

    def has_architecture(self):
        return bool(self.components or self.timelines)


def _card_kind(dsl_kind, attrs, lineno):
    ck = attrs.get("kind", KIND_MAP.get(dsl_kind, "service"))
    if ck not in VALID_CARD_KINDS:
        raise SemanticError(
            f"line {lineno}: unknown kind {ck!r} (expected one of {sorted(VALID_CARD_KINDS)})"
        )
    return ck


def _make_component(node):
    _, dsl_kind, name, label, attrs, lineno = node
    return Component(
        kind=dsl_kind,
        name=name,
        label=label,
        color=attrs.get("color"),
        logo=attrs.get("logo"),
        sublabel=attrs.get("sublabel"),
        at=attrs.get("at"),
        size=attrs.get("size"),
        card_kind=_card_kind(dsl_kind, attrs, lineno),
    )


def validate(ast):
    """Build and validate a Model from the raw AST. Raises SemanticError on failure."""
    model = Model()

    # 1) top-level component declarations
    for node in ast:
        if node[0] != "component":
            continue
        name = node[2]
        if name in model.components:
            raise SemanticError(f"line {node[5]}: component {name!r} is already declared")
        model.components[name] = _make_component(node)

    # 2) infra boundaries and 3) flows
    for node in ast:
        kind = node[0]
        if kind == "infra":
            _, label, attrs, members, lineno = node
            for name in members:
                if name not in model.components:
                    raise SemanticError(
                        f"line {lineno}: infra {label!r} references undeclared component {name!r}"
                    )
                model.components[name].infra = label
            model.boundaries.append(
                Boundary(label=label, logo=attrs.get("logo"), at=attrs.get("at"),
                         size=attrs.get("size"), members=members)
            )
        elif kind == "flow":
            _, label, raw_steps, lineno = node
            model.flows.append(_build_flow(label, raw_steps, model.components))
        elif kind == "timeline":
            _, label, ops, lineno = node
            model.timelines.append(_build_timeline(label, ops, model.components))

    return model


def _build_flow(label, raw_steps, components):
    expected = 1
    steps = []
    for _, number, source, step_label, target, curved, step_lineno in raw_steps:
        if number != expected:
            raise SemanticError(
                f"line {step_lineno}: expected step {expected}, found step {number}"
            )
        for endpoint in (source, target):
            if endpoint not in components:
                raise SemanticError(
                    f"line {step_lineno}: step {number} references undeclared component {endpoint!r}"
                )
        steps.append(Step(number, source, step_label, target, curved))
        expected += 1
    return Flow(label, steps)


def _build_timeline(label, ops, top_level):
    """Timelines may reference top-level components (via `show`) and introduce
    new ones (via `add`); both become valid targets for move/connect."""
    known = set(top_level)
    result = []
    for op in ops:
        verb = op[0]
        if verb == "show":
            for name in op[1]:
                if name not in known:
                    raise SemanticError(f"timeline {label!r}: show references unknown component {name!r}")
            result.append(TLShow(op[1]))
        elif verb == "add":
            comp = _make_component(op[1])
            if comp.name in known:
                raise SemanticError(f"timeline {label!r}: add re-declares component {comp.name!r}")
            known.add(comp.name)
            result.append(TLAdd(comp))
        elif verb == "move":
            _, name, to = op
            if name not in known:
                raise SemanticError(f"timeline {label!r}: move references unknown component {name!r}")
            result.append(TLMove(name, to))
        elif verb == "connect":
            _, source, conn_label, target, curved = op
            for endpoint in (source, target):
                if endpoint not in known:
                    raise SemanticError(
                        f"timeline {label!r}: connect references unknown component {endpoint!r}"
                    )
            result.append(TLConnect(source, conn_label, target, curved))
        elif verb == "wait":
            result.append(TLWait())
    return Timeline(label, result)
