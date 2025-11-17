from __future__ import annotations

import logging
from pathlib import Path

from playsound import playsound

LOGGER = logging.getLogger(__name__)


def play_audio(file_path: str | Path) -> None:
    """Play an audio file using playsound."""
    path = Path(file_path)
    if not path.exists():
        LOGGER.warning("Audio file not found: %s", path)
        return

    LOGGER.debug("Playing audio: %s", path)
    playsound(str(path))


__all__ = ["play_audio"]

