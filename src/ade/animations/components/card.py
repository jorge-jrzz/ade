from enum import Enum

from manim import DOWN, Group, RoundedRectangle, Text

from ade.animations.components.assets import logo as load_logo
from ade.animations.themes import LIGHT, Theme


class CardKind(Enum):
    """Semantic kind of a card; drives the accent color from the Theme."""

    SERVICE = "service"
    DATABASE = "database"
    INFRA = "infra"
    EXTERNAL = "external"


class Card(Group):
    """A diagram card: rounded box with an optional logo, a label and an
    optional sublabel. Exposes its parts so scenes can anchor to them.

    It is a Group (not VGroup) because logos are ImageMobjects (raster).
    """

    def __init__(self, box, content, logo_image=None, label=None, sublabel=None):
        super().__init__(box, content)
        self.box = box
        self.logo = logo_image
        self.label = label
        self.sublabel = sublabel


class CardBuilder:
    """Fluent builder for Cards.

    Example:
        db = (
            CardBuilder()
            .label("PostgreSQL")
            .logo("databases/postgresql.png")
            .kind(CardKind.DATABASE)
            .sublabel("Primary")
            .build()
        )
    """

    # Auto-sizing bounds. These mirror the abstract estimates in
    # `ade.layout` (MIN_CARD_W / MAX_CARD_W / MIN_CARD_H / CARD_PADDING) so a
    # card renders at the size the layout pass reserved for it. Keep them in
    # sync if either side changes.
    MIN_HEIGHT = 1.1
    MIN_WIDTH = 2.6
    MAX_WIDTH = 3.6
    PADDING = 0.6

    def __init__(self):
        self._label = None
        self._sublabel = None
        self._logo_path = None
        self._logo_height = 1.1
        self._kind = CardKind.SERVICE
        self._theme = LIGHT
        self._width = None
        self._height = None

    def label(self, text: str) -> "CardBuilder":
        self._label = text
        return self

    def sublabel(self, text: str) -> "CardBuilder":
        self._sublabel = text
        return self

    def logo(self, path: str, height: float = 1.1) -> "CardBuilder":
        self._logo_path = path
        self._logo_height = height
        return self

    def kind(self, kind: CardKind) -> "CardBuilder":
        self._kind = kind
        return self

    def theme(self, theme: Theme) -> "CardBuilder":
        self._theme = theme
        return self

    def size(self, width: float = None, height: float = None) -> "CardBuilder":
        """Force the box size; by default it adapts to the content."""
        self._width = width
        self._height = height
        return self

    def build(self) -> Card:
        if not self._label:
            raise ValueError("a Card needs a label: call .label(...)")

        theme = self._theme
        accent = getattr(theme, self._kind.value)

        label = Text(self._label, font_size=24, color=theme.ink)
        parts = [label]

        logo_image = None
        if self._logo_path is not None:
            logo_image = load_logo(self._logo_path, self._logo_height)
            parts.insert(0, logo_image)

        sublabel = None
        if self._sublabel is not None:
            sublabel = Text(self._sublabel, font_size=18, color=theme.subtle)
            parts.append(sublabel)

        content = Group(*parts).arrange(DOWN, buff=0.25)

        width = self._width or min(
            self.MAX_WIDTH, max(self.MIN_WIDTH, content.width + self.PADDING)
        )
        height = self._height or max(self.MIN_HEIGHT, content.height + self.PADDING)
        if content.width > width - 0.4:
            content.scale_to_fit_width(width - 0.4)

        box = RoundedRectangle(corner_radius=0.2, width=width, height=height)
        box.set_fill(theme.card_fill, opacity=1.0)
        box.set_stroke(accent, width=2.5)
        content.move_to(box.get_center())

        return Card(box, content, logo_image=logo_image, label=label, sublabel=sublabel)
