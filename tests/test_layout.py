"""Unit tests for the pure-Python layout pass (`ade.layout`).

These import only `ade.layout` and `ade.lang.semantic` — no Manim, so they run
in milliseconds without rendering. If any import here pulls in Manim, that is a
layering-rule violation, not a test bug.
"""

import sys

from ade import layout
from ade.lang.semantic import Boundary, Component, Flow, Model, Step


def _comp(name, label, kind="service", logo=None, sublabel=None, infra=None):
    c = Component(kind=kind, name=name, label=label, card_kind=kind,
                  logo=logo, sublabel=sublabel)
    c.infra = infra
    return c


def _model(components, edges=(), boundaries=(), direction="LR"):
    m = Model()
    for c in components:
        m.components[c.name] = c
    m.boundaries = list(boundaries)
    steps = [Step(i + 1, s, None, t) for i, (s, t) in enumerate(edges)]
    m.flows = [Flow("f", steps)] if steps else []
    m.direction = direction
    return m


def _pipeline_model():
    comps = [
        _comp("client", "Web Client", "external"),
        _comp("api", "API Gateway"),
        _comp("proc", "Processing Service", logo="python"),
        _comp("db", "PostgreSQL", "database"),
    ]
    edges = [("client", "api"), ("api", "proc"), ("proc", "db")]
    return _model(comps, edges)


# --- layering ---------------------------------------------------------------

def test_pipeline_lays_out_in_flow_order():
    result = layout.solve(_pipeline_model())
    xs = {n: g.x for n, g in result.nodes.items()}
    assert xs["client"] < xs["api"] < xs["proc"] < xs["db"]


def test_pipeline_no_overlap():
    result = layout.solve(_pipeline_model())
    geoms = list(result.nodes.values())
    for i in range(len(geoms)):
        for j in range(i + 1, len(geoms)):
            a, b = geoms[i], geoms[j]
            sep_x = abs(a.x - b.x) >= (a.width + b.width) / 2 - 1e-6
            sep_y = abs(a.y - b.y) >= (a.height + b.height) / 2 - 1e-6
            assert sep_x or sep_y, f"cards overlap: {a} {b}"


def test_cyclic_flow_terminates():
    # login_flow's shape: response edges db->auth and auth->frontend form cycles.
    comps = [
        _comp("frontend", "React App"),
        _comp("api", "API Gateway"),
        _comp("auth", "Auth Service"),
        _comp("db", "Users DB", "database"),
    ]
    edges = [("frontend", "api"), ("api", "auth"), ("auth", "db"),
             ("db", "auth"), ("auth", "frontend")]
    result = layout.solve(_model(comps, edges))
    assert set(result.nodes) == {"frontend", "api", "auth", "db"}
    xs = {n: g.x for n, g in result.nodes.items()}
    # forward edges rank frontend<api<auth<db; back-edges add no layers
    assert xs["frontend"] < xs["api"] < xs["auth"] < xs["db"]


def test_deterministic():
    a = layout.solve(_pipeline_model())
    b = layout.solve(_pipeline_model())
    assert {n: (g.x, g.y, g.width, g.height) for n, g in a.nodes.items()} == \
           {n: (g.x, g.y, g.width, g.height) for n, g in b.nodes.items()}


# --- clusters ---------------------------------------------------------------

def test_cluster_members_enclosed_others_outside():
    comps = [
        _comp("client", "Web Client", "external"),
        _comp("api", "API Gateway"),
        _comp("proc", "Processing Service", infra="AWS"),
        _comp("db", "PostgreSQL", "database", infra="AWS"),
    ]
    edges = [("client", "api"), ("api", "proc"), ("proc", "db")]
    boundaries = [Boundary(label="AWS", members=["proc", "db"])]
    result = layout.solve(_model(comps, edges, boundaries))
    assert len(result.boundaries) == 1
    box = result.boundaries[0]
    left, right = box.x - box.width / 2, box.x + box.width / 2
    bottom, top = box.y - box.height / 2, box.y + box.height / 2

    def inside(n):
        g = result.nodes[n]
        return left <= g.x - g.width / 2 and g.x + g.width / 2 <= right and \
            bottom <= g.y - g.height / 2 and g.y + g.height / 2 <= top

    assert inside("proc") and inside("db")
    assert not inside("client") and not inside("api")


# --- direction --------------------------------------------------------------

def test_lr_advances_horizontally():
    result = layout.solve(_pipeline_model(), direction="LR")
    ys = [g.y for g in result.nodes.values()]
    assert max(ys) - min(ys) < 1e-6            # single horizontal row
    xs = [g.x for g in result.nodes.values()]
    assert max(xs) - min(xs) > 1.0             # spread along x


def test_td_advances_vertically():
    result = layout.solve(_pipeline_model(), direction="TD")
    xs = [g.x for g in result.nodes.values()]
    assert max(xs) - min(xs) < 1e-6            # single vertical column
    ys = {n: g.y for n, g in result.nodes.items()}
    assert ys["client"] > ys["api"] > ys["proc"] > ys["db"]  # top -> bottom


# --- sizing -----------------------------------------------------------------

def test_long_labels_get_wider_cards():
    short = _comp("db", "DB")
    long = _comp("svc", "Processing Service")
    assert layout.estimate_card_size(long)[0] > layout.estimate_card_size(short)[0]


def test_logo_and_sublabel_grow_height():
    plain = _comp("a", "Service")
    rich = _comp("b", "Service", logo="python", sublabel="Primary")
    assert layout.estimate_card_size(rich)[1] > layout.estimate_card_size(plain)[1]


# --- canvas fitting ---------------------------------------------------------

def test_small_scene_not_scaled():
    comps = [_comp("a", "A"), _comp("b", "B")]
    result = layout.solve(_model(comps, [("a", "b")]))
    assert result.scale == 1.0
    assert not result.illegible


def test_oversized_scene_scaled_and_flagged():
    # A long chain overflows the frame and must scale below the threshold.
    comps = [_comp(f"n{i}", f"Node {i}") for i in range(12)]
    edges = [(f"n{i}", f"n{i + 1}") for i in range(11)]
    result = layout.solve(_model(comps, edges))
    assert result.scale < 1.0
    assert result.illegible  # far below 0.7
    # every node still fits inside the usable frame after scaling
    for g in result.nodes.values():
        assert abs(g.x) * result.scale <= layout.USABLE_W / 2 + 1e-6


def test_no_manim_imported():
    assert "manim" not in sys.modules
