from __future__ import annotations

import threading
import time
from typing import Iterable

import interception

_init_lock = threading.Lock()
_initialized = False


def _ensure_ready() -> None:
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if not _initialized:
            interception.auto_capture_devices()
            _initialized = True


def press_key(key: str, repeat: int = 1, interval: float = 0.1) -> None:
    """Press a key one or more times."""
    _ensure_ready()
    interception.press(key, presses=repeat, interval=interval)


def tap(key: str) -> None:
    """Alias for a single quick key press."""
    press_key(key)


def hold(keys: Iterable[str], duration: float) -> None:
    """Hold the specified keys simultaneously for `duration` seconds."""
    if duration <= 0:
        raise ValueError("duration must be positive")

    _ensure_ready()
    ctx = interception.hold_key(*keys)
    ctx.__enter__()
    try:
        time.sleep(duration)
    finally:
        ctx.__exit__(None, None, None)


def key_down_once(key: str) -> None:
    _ensure_ready()
    interception.key_down(key)


def key_up_once(key: str) -> None:
    _ensure_ready()
    interception.key_up(key)


__all__ = ["press_key", "tap", "hold", "key_down_once", "key_up_once"]

