from manim import DOWN, ORIGIN, RIGHT, DashedVMobject, Group, RoundedRectangle, Text

from ade.animations.components.assets import logo as load_logo
from ade.animations.themes import LIGHT, Theme


class Boundary(Group):
    """A dashed region marking an infrastructure boundary (a cloud, a VPC...).

    `frame` is an invisible solid rectangle kept as a stable geometry
    reference: anchor positions to it, not to the dashed outline.
    """

    def __init__(self, frame, outline, header=None):
        super().__init__(*[m for m in (frame, outline, header) if m is not None])
        self.frame = frame
        self.outline = outline
        self.header = header


class BoundaryBuilder:
    """Fluent builder for Boundaries.

    Example:
        cloud = (
            BoundaryBuilder()
            .label("AWS Cloud Infrastructure")
            .logo("infra/aws.png")
            .size(7.0, 5.6)
            .at([3.2, -0.4, 0])
            .build()
        )
    """

    def __init__(self):
        self._label = None
        self._logo_path = None
        self._logo_height = 0.55
        self._width = 7.0
        self._height = 5.6
        self._position = ORIGIN
        self._theme = LIGHT
        self._num_dashes = 70

    def label(self, text: str) -> "BoundaryBuilder":
        self._label = text
        return self

    def logo(self, path: str, height: float = 0.55) -> "BoundaryBuilder":
        self._logo_path = path
        self._logo_height = height
        return self

    def size(self, width: float, height: float) -> "BoundaryBuilder":
        self._width = width
        self._height = height
        return self

    def at(self, position) -> "BoundaryBuilder":
        self._position = position
        return self

    def theme(self, theme: Theme) -> "BoundaryBuilder":
        self._theme = theme
        return self

    def build(self) -> Boundary:
        frame = RoundedRectangle(
            corner_radius=0.3, width=self._width, height=self._height
        )
        frame.move_to(self._position)
        frame.set_stroke(opacity=0)  # geometry reference only

        visible = frame.copy().set_stroke(self._theme.subtle, width=2.5, opacity=1.0)
        outline = DashedVMobject(
            visible, num_dashes=self._num_dashes, dashed_ratio=0.55
        )

        header_parts = []
        if self._logo_path is not None:
            header_parts.append(load_logo(self._logo_path, self._logo_height))
        if self._label is not None:
            header_parts.append(Text(self._label, font_size=26, color=self._theme.ink))

        header = None
        if header_parts:
            header = Group(*header_parts).arrange(RIGHT, buff=0.3)
            header.next_to(frame.get_top(), DOWN, buff=0.35)

        return Boundary(frame, outline, header)
