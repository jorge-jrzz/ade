"""Reusable building blocks for architecture diagrams.

Each component is created through a fluent builder, so optional parts
(logos, sublabels, headers) can be combined freely and new options can
be added later without breaking existing scenes.
"""

from ade.animations.components.assets import ASSETS_DIR, logo
from ade.animations.components.boundary import Boundary, BoundaryBuilder
from ade.animations.components.card import Card, CardBuilder, CardKind
from ade.animations.components.connection import Connection, ConnectionBuilder

__all__ = [
    "ASSETS_DIR",
    "logo",
    "Boundary",
    "BoundaryBuilder",
    "Card",
    "CardBuilder",
    "CardKind",
    "Connection",
    "ConnectionBuilder",
]
