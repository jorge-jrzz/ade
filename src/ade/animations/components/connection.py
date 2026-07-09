import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    TAU,
    UP,
    AnimationGroup,
    Arrow,
    Create,
    CurvedArrow,
    Dot,
    FadeIn,
    FadeOut,
    GrowArrow,
    Line,
    MoveAlongPath,
    Succession,
    Text,
    VGroup,
    linear,
)

from ade.animations.themes import LIGHT, Theme


class Connection(VGroup):
    """An arrow between two components, with an optional label.

    Provides ready-made animations so scenes stay declarative.
    """

    def __init__(self, arrow, label=None):
        super().__init__(*[m for m in (arrow, label) if m is not None])
        self.arrow = arrow
        self.label = label

    def grow(self) -> AnimationGroup:
        """Draw the arrow and fade the label in."""
        intro = GrowArrow(self.arrow) if isinstance(self.arrow, Arrow) else Create(self.arrow)
        anims = [intro]
        if self.label is not None:
            anims.append(FadeIn(self.label, shift=UP * 0.1))
        return AnimationGroup(*anims)

    def packet_flow(self, count: int = 1, run_time: float = 1.2) -> Succession:
        """Small glowing packets traveling along the arrow, one after another,
        simulating requests (HTTPS, gRPC, SQL...)."""
        start = self.arrow.get_start()
        end = self.arrow.get_end()
        direction = (end - start) / np.linalg.norm(end - start)
        path = Line(start, end - direction * 0.3)  # stop short of the tip
        color = self.arrow.get_color()

        trips = []
        for _ in range(count):
            packet = VGroup(
                Dot(radius=0.17, color=color, fill_opacity=0.3),  # halo
                Dot(radius=0.09, color=color),
            ).move_to(path.get_start())
            trips.append(
                Succession(
                    FadeIn(packet, scale=0.5, run_time=0.2),
                    MoveAlongPath(packet, path, run_time=run_time, rate_func=linear),
                    FadeOut(packet, scale=0.5, run_time=0.2),
                )
            )
        return Succession(*trips)


class ConnectionBuilder:
    """Fluent builder for Connections.

    Example:
        flow = (
            ConnectionBuilder()
            .between(gateway, service)
            .label("Process Data")
            .build()
        )
    """

    def __init__(self):
        self._source = None
        self._target = None
        self._label = None
        self._color = None
        self._curve_angle = None
        self._theme = LIGHT
        self._gap = 0.1

    def between(self, source, target) -> "ConnectionBuilder":
        self._source = source
        self._target = target
        return self

    def label(self, text: str) -> "ConnectionBuilder":
        self._label = text
        return self

    def color(self, value: str) -> "ConnectionBuilder":
        self._color = value
        return self

    def curved(self, angle: float = -TAU / 8) -> "ConnectionBuilder":
        """Use a curved arrow; negative angles bend upward."""
        self._curve_angle = angle
        return self

    def theme(self, theme: Theme) -> "ConnectionBuilder":
        self._theme = theme
        return self

    def build(self) -> Connection:
        if self._source is None or self._target is None:
            raise ValueError("a Connection needs endpoints: call .between(source, target)")

        color = self._color or self._theme.flow
        start, end, horizontal = self._anchors()

        if self._curve_angle is not None:
            arrow = CurvedArrow(start, end, angle=self._curve_angle, color=color)
        else:
            arrow = Arrow(
                start,
                end,
                buff=0,
                color=color,
                stroke_width=5,
                max_tip_length_to_length_ratio=0.12,
            )

        label = None
        if self._label is not None:
            label = Text(self._label, font_size=22, color=color)
            label.next_to(arrow, UP if horizontal else RIGHT, buff=0.25)

        return Connection(arrow, label)

    def _anchors(self):
        """Pick the facing edges of source and target along the dominant axis."""
        s, t = self._source, self._target
        delta = t.get_center() - s.get_center()
        if abs(delta[0]) >= abs(delta[1]):  # mostly horizontal
            if delta[0] >= 0:
                return s.get_right() + RIGHT * self._gap, t.get_left() + LEFT * self._gap, True
            return s.get_left() + LEFT * self._gap, t.get_right() + RIGHT * self._gap, True
        if delta[1] <= 0:  # target below source
            return s.get_bottom() + DOWN * self._gap, t.get_top() + UP * self._gap, False
        return s.get_top() + UP * self._gap, t.get_bottom() + DOWN * self._gap, False
