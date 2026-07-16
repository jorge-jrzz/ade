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


def _asset_index() -> dict[str, str]:
    """Map every asset PNG stem (lowercased) to its path relative to
    ASSETS_DIR, e.g. {"nestjs": "frameworks/nestjs.png", "aws": "infra/aws.png"}."""
    index: dict[str, str] = {}
    for png in sorted(ASSETS_DIR.rglob("*.png")):
        index.setdefault(png.stem.lower(), png.relative_to(ASSETS_DIR).as_posix())
    return index


def find_logo(key: str) -> str:
    """Resolve a short logo alias to a path relative to ASSETS_DIR.

    `find_logo("nestjs")` -> "frameworks/nestjs.png". Accepts an exact stem
    match, or a unique case-insensitive prefix match ("postgres" -> postgresql,
    "nest" -> nestjs). Raises ValueError (listing candidates) when the alias is
    unknown or ambiguous, so the ADE DSL can point at a real asset by name only.
    """
    key_norm = key.lower()
    index = _asset_index()
    if key_norm in index:
        return index[key_norm]

    prefix = sorted(rel for stem, rel in index.items() if stem.startswith(key_norm))
    if len(prefix) == 1:
        return prefix[0]
    if not prefix:
        raise ValueError(
            f"unknown logo {key!r}: no asset matches. Available: {sorted(index)}"
        )
    raise ValueError(f"ambiguous logo {key!r}: matches {prefix}")
