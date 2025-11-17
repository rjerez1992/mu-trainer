from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, Tuple

import mss
import mss.tools

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "screenshots"


def _ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def capture_screenshot(
    output_path: str | Path | None = None,
    region: Tuple[int, int, int, int] | None = None,
) -> Path:
    """Capture a screenshot (full screen or region) and return the saved path."""
    if output_path is None:
        _ensure_output_dir(DEFAULT_OUTPUT_DIR)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = DEFAULT_OUTPUT_DIR / f"screenshot_{timestamp}.png"

    output_path = Path(output_path)
    _ensure_output_dir(output_path.parent)

    with mss.mss() as sct:
        if region:
            left, top, right, bottom = region
            monitor = {
                "left": left,
                "top": top,
                "width": right - left,
                "height": bottom - top,
            }
        else:
            monitor = sct.monitors[0]

        image = sct.grab(monitor)
        mss.tools.to_png(image.rgb, image.size, output=str(output_path))
        LOGGER.debug("Captured screenshot to %s", output_path)

    return output_path


__all__ = ["capture_screenshot", "DEFAULT_OUTPUT_DIR"]

