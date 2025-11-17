from __future__ import annotations

import random
import threading
import time
from typing import Iterable, Tuple

import interception

_init_lock = threading.Lock()
_initialized = False


def _ensure_ready() -> None:
    """Initialise interception once so subsequent calls are instant."""
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if not _initialized:
            interception.auto_capture_devices()
            _initialized = True


def move_to(x: int, y: int) -> None:
    """Move the mouse to absolute screen coordinates."""
    _ensure_ready()
    interception.move_to(x, y)


def move_by(dx: int, dy: int) -> None:
    """Move the mouse relative to its current position."""
    _ensure_ready()
    interception.move_relative(dx, dy)


def click(
    button: str = "left",
    x: int | tuple[int, int] | None = None,
    y: int | None = None,
    clicks: int = 1,
    interval: float = 0.1,
    delay: float = 0.3,
) -> None:
    """Click at the current (or provided) position using the specified button."""
    _ensure_ready()
    interception.click(
        x,
        y,
        button=button,
        clicks=clicks,
        interval=interval,
        delay=delay,
    )


def right_click(delay: float = 0.3) -> None:
    """Convenience helper for a right mouse click."""
    click("right", delay=delay)


def position() -> Tuple[int, int]:
    """Return the current mouse position."""
    _ensure_ready()
    pos = interception.mouse_position()
    if isinstance(pos, Iterable):
        pos = tuple(pos)
    return pos  # type: ignore[return-value]


def jitter(radius: int = 80, steps: int = 2, delay: float = 0.02) -> None:
    """Randomly move the mouse around its current position."""
    if radius <= 0 or steps <= 0:
        return

    current_x, current_y = position()
    for _ in range(steps):
        offset_x = random.randint(-radius, radius)
        offset_y = random.randint(-radius, radius)
        move_to(current_x + offset_x, current_y + offset_y)
        if delay > 0:
            time.sleep(delay)


__all__ = ["move_to", "move_by", "click", "right_click", "position", "jitter"]

