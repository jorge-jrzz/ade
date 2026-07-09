from pathlib import Path

from manim import ImageMobject

ASSETS_DIR = Path(__file__).parent.parent / "assets"


def logo(path: str, height: float = 1.0) -> ImageMobject:
    """Load a logo PNG from the assets folder at the given height.

    PNGs are rasterized from the source SVGs with cairosvg (1024px),
    because SVGMobject does not support gradients. To regenerate them
    after adding new SVGs, see the README.
    """
    return ImageMobject(str(ASSETS_DIR / path)).scale_to_fit_height(height)
