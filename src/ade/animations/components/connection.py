from manim import (
    DOWN,
    LEFT,
    RIGHT,
    TAU,
    UP,
    AnimationGroup,
    ArcBetweenPoints,
    Arrow,
    Create,
    CurvedArrow,
    Dot,
    FadeIn,
    FadeOut,
    GrowArrow,
    Line,
    MoveAlongPath,
    Mobject,
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

    def __init__(self, arrow, label=None, spine=None):
        if spine is None:
            spine = Line(arrow.get_start(), arrow.get_end())
        # Keep the packet path in the group so scene transforms apply to it,
        # while hiding it because the arrow is the visible representation.
        spine.set_opacity(0)
        super().__init__(*[m for m in (arrow, label, spine) if m is not None])
        self.arrow = arrow
        self.label = label
        # Geometric path the packet follows; it shares transforms with the arrow.
        self.spine = spine

    def grow(self) -> AnimationGroup:
        """Draw the arrow and fade the label in."""
        intro = (
            GrowArrow(self.arrow)
            if isinstance(self.arrow, Arrow)
            else Create(self.arrow)
        )
        anims = [intro]
        if self.label is not None:
            anims.append(FadeIn(self.label, shift=UP * 0.1))
        return AnimationGroup(*anims)

    def packet_flow(self, count: int = 1, run_time: float = 1.2) -> Succession:
        """Small glowing packets traveling along the arrow, one after another,
        simulating requests (HTTPS, gRPC, SQL...)."""
        # Trim the spine's tip end proportionally so the packet stops short of
        # the arrow tip on any path shape (straight or curved), preserving the
        # ~0.3 unit gap the straight case used before.
        length = max(self.spine.get_arc_length(), 1e-6)
        trim = min(max(0.3 / length, 0.02), 0.5)
        path = self.spine.copy()
        path.pointwise_become_partial(self.spine, 0, 1 - trim)
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
        self._source: Mobject | None = None
        self._target: Mobject | None = None
        self._label = None
        self._label_font_size = 22
        self._color = None
        self._curve_angle = None
        self._theme = LIGHT
        self._gap = 0.1

    def between(self, source: Mobject, target: Mobject) -> "ConnectionBuilder":
        self._source = source
        self._target = target
        return self

    def label(self, text: str) -> "ConnectionBuilder":
        self._label = text
        return self

    def label_size(self, value: float) -> "ConnectionBuilder":
        self._label_font_size = value
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
            raise ValueError(
                "a Connection needs endpoints: call .between(source, target)"
            )

        color = self._color or self._theme.flow
        start, end, horizontal = self._anchors()

        if self._curve_angle is not None:
            arrow = CurvedArrow(start, end, angle=self._curve_angle, color=color)
            spine = ArcBetweenPoints(start, end, angle=self._curve_angle)
        else:
            arrow = Arrow(
                start,
                end,
                buff=0,
                color=color,
                stroke_width=5,
                max_tip_length_to_length_ratio=0.12,
            )
            spine = Line(start, end)

        label = None
        if self._label is not None:
            label = Text(self._label, font_size=self._label_font_size, color=color)
            label.next_to(arrow, UP if horizontal else RIGHT, buff=0.25)

        return Connection(arrow, label, spine=spine)

    def _anchors(self):
        """Pick the facing edges of source and target along the dominant axis."""
        s, t = self._source, self._target
        assert s is not None and t is not None
        delta = t.get_center() - s.get_center()
        if abs(delta[0]) >= abs(delta[1]):  # mostly horizontal
            if delta[0] >= 0:
                return (
                    s.get_right() + RIGHT * self._gap,
                    t.get_left() + LEFT * self._gap,
                    True,
                )
            return (
                s.get_left() + LEFT * self._gap,
                t.get_right() + RIGHT * self._gap,
                True,
            )
        if delta[1] <= 0:  # target below source
            return (
                s.get_bottom() + DOWN * self._gap,
                t.get_top() + UP * self._gap,
                False,
            )
        return s.get_top() + UP * self._gap, t.get_bottom() + DOWN * self._gap, False
