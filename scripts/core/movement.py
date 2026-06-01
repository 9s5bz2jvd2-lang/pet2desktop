"""
Movement helpers – screen geometry, boundary clamping, walk parameters.
"""

from __future__ import annotations

import random
from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication


def get_screen_geometry() -> QRect:
    """Return the *available* geometry of the primary screen."""
    screen = QGuiApplication.primaryScreen()
    if screen is not None:
        return screen.availableGeometry()
    # Sensible fallback
    return QRect(0, 0, 1920, 1080)


def clamp_to_screen(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    """Clamp (*x*, *y*) so a window of (*width*×*height*) stays on-screen."""
    bounds = get_screen_geometry()
    cx = max(bounds.left(), min(x, bounds.right() - width))
    cy = max(bounds.top(), min(y, bounds.bottom() - height))
    return cx, cy


def random_walk_distance() -> int:
    """Return a walk distance in [50, 300] px."""
    return random.randint(50, 300)


def random_walk_direction() -> str:
    """Return ``"left"`` or ``"right"`` at random."""
    return random.choice(["left", "right"])


def random_idle_duration_ms() -> int:
    """Return an idle duration in [3000, 10000] ms."""
    return random.randint(3000, 10000)


def attention_position(pet_width: int, pet_height: int) -> tuple[int, int]:
    """Return a position near the centre-bottom of the screen.

    Used when the pet wants to "get attention" for a health reminder.
    Adds a small random offset so it doesn't land on the exact same
    spot every time.
    """
    bounds = get_screen_geometry()
    margin = 40
    cx = bounds.left() + (bounds.width() - pet_width) // 2
    cy = bounds.bottom() - pet_height - margin
    # ±80 px horizontal jitter
    cx += random.randint(-80, 80)
    cx, cy = clamp_to_screen(cx, cy, pet_width, pet_height)
    return cx, cy


# Walk animation parameters
WALK_SPEED_PX_PER_SEC = 100
WALK_TICK_MS = 30
WALK_STEP_PX = max(1, int(WALK_SPEED_PX_PER_SEC * WALK_TICK_MS / 1000))
