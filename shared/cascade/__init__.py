"""Cascade regeneration — auto-regenerate parent/section/executive narratives.

When a leaf narrative is edited or approved, the cascade system
automatically regenerates all affected ancestor narratives in
topological order: parents → sections → executive summary.
"""

from shared.cascade.manager import CascadeManager
from shared.cascade.regenerator import CascadeRegenerator, CascadeResult

__all__ = [
    "CascadeManager",
    "CascadeRegenerator",
    "CascadeResult",
]
