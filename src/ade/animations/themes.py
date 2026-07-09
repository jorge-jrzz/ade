from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Color palette shared by every visual component.

    Today this is a plain value object. If alternate looks are needed later
    (dark mode, per-cloud-provider styling), new Theme instances — or a
    factory that produces them — can be added without touching the scenes.
    """

    background: str = "#FBFBFA"   # near-white canvas
    ink: str = "#1F2937"          # main text
    subtle: str = "#8C9BAB"       # secondary text, dashed boundaries
    card_fill: str = "#FFFFFF"
    card_stroke: str = "#D0D5DB"  # neutral borders
    flow: str = "#F97316"         # arrows / data in motion

    # Accent per component kind; field names must match CardKind values.
    service: str = "#2E6FDB"      # blue
    database: str = "#059669"     # green
    infra: str = "#6B7280"        # gray
    external: str = "#F97316"     # orange


LIGHT = Theme()
