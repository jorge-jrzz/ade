from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Color palette shared by every visual component.

    Today this is a plain value object. If alternate looks are needed later
    (dark mode, per-cloud-provider styling), new Theme instances — or a
    factory that produces them — can be added without touching the scenes.
    """

    background: str = "#FBFBFA"  # near-white canvas
    ink: str = "#1F2937"  # main text
    subtle: str = "#8C9BAB"  # secondary text, dashed boundaries
    card_fill: str = "#FFFFFF"
    card_stroke: str = "#D0D5DB"  # neutral borders
    flow: str = "#F97316"  # arrows / data in motion
    flow_palette: tuple[tuple[str, str, str], ...] = (
        ("#2563EB", "#1D4ED8", "#60A5FA"),
        ("#EA580C", "#C2410C", "#FB923C"),
        ("#059669", "#047857", "#34D399"),
        ("#7C3AED", "#6D28D9", "#A78BFA"),
    )

    # Accent per component kind; field names must match CardKind values.
    service: str = "#2E6FDB"  # blue
    database: str = "#059669"  # green
    infra: str = "#6B7280"  # gray
    external: str = "#F97316"  # orange

    def flow_color(self, flow_index: int, step_index: int = 0) -> str:
        """Return a stable family/step color for a rendered flow edge."""
        family = self.flow_palette[flow_index % len(self.flow_palette)]
        return family[step_index % len(family)]


LIGHT = Theme()
