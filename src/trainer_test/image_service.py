from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import cv2

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
_POSSIBLE_IMAGE_DIRS = [
    PROJECT_ROOT / "image-test",
    PROJECT_ROOT / "@image-test",
]
for candidate in _POSSIBLE_IMAGE_DIRS:
    if candidate.exists():
        DEFAULT_IMAGE_DIR = candidate
        break
else:  # pragma: no cover - fallback when folder is missing
    DEFAULT_IMAGE_DIR = _POSSIBLE_IMAGE_DIRS[0]
DEFAULT_NEEDLE_PATH = DEFAULT_IMAGE_DIR / "test-find.png"
DEFAULT_HAYSTACK_PATH = DEFAULT_IMAGE_DIR / "test-screenshot.png"
DEFAULT_OUTPUT_PATH = DEFAULT_IMAGE_DIR / "finded.png"


def _resolve_path(path: str | Path) -> Path:
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = (PROJECT_ROOT / resolved).resolve()
    return resolved


def _load_image(path: Path) -> Any:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Unable to read image at {path}")
    return image


def crop_center_region(
    source: str | Path,
    width: int,
    height: int,
    destination: str | Path | None = None,
) -> Path:
    """Crop the center region from `source` and write it to `destination`."""
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")

    source_path = _resolve_path(source)
    destination_path = _resolve_path(destination or source_path.with_name(f"{source_path.stem}_center.png"))

    image = _load_image(source_path)
    img_height, img_width = image.shape[:2]

    crop_w = min(width, img_width)
    crop_h = min(height, img_height)
    left = max((img_width - crop_w) // 2, 0)
    top = max((img_height - crop_h) // 2, 0)
    region = image[top : top + crop_h, left : left + crop_w]

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destination_path), region)
    return destination_path


def find_image(
    needle: str | Path = DEFAULT_NEEDLE_PATH,
    haystack: str | Path = DEFAULT_HAYSTACK_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    match_threshold: float = 0.78,
) -> dict[str, float | int | str] | None:
    """Locate `needle` within `haystack` via template matching."""
    needle_path = _resolve_path(needle)
    haystack_path = _resolve_path(haystack)
    output_path = _resolve_path(output_path)

    start_time = time.perf_counter()
    haystack_img = _load_image(haystack_path)
    needle_img = _load_image(needle_path)

    haystack_gray = cv2.cvtColor(haystack_img, cv2.COLOR_BGR2GRAY)
    needle_gray = cv2.cvtColor(needle_img, cv2.COLOR_BGR2GRAY)

    result = cv2.matchTemplate(haystack_gray, needle_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    confidence = float(max_val)
    if confidence < match_threshold:
        LOGGER.info(
            "Needle not found (score=%.3f, threshold=%.3f).",
            confidence,
            match_threshold,
        )
        return None

    needle_h, needle_w = needle_gray.shape[:2]
    top_left = max_loc
    bottom_right = (top_left[0] + needle_w, top_left[1] + needle_h)
    center_x = top_left[0] + needle_w // 2
    center_y = top_left[1] + needle_h // 2

    annotated = haystack_img.copy()
    cv2.rectangle(annotated, top_left, bottom_right, (0, 0, 255), 2)
    cv2.circle(annotated, (center_x, center_y), 6, (0, 255, 0), -1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), annotated)

    duration = time.perf_counter() - start_time
    LOGGER.info(
        "Needle center at (%d, %d) with confidence %.3f in %.3fs -> %s",
        center_x,
        center_y,
        confidence,
        duration,
        output_path,
    )

    return {
        "center_x": center_x,
        "center_y": center_y,
        "confidence": confidence,
        "duration": duration,
        "output_path": str(output_path),
        "top_left_x": top_left[0],
        "top_left_y": top_left[1],
        "bottom_right_x": bottom_right[0],
        "bottom_right_y": bottom_right[1],
        "haystack_path": str(haystack_path),
    }


def find_image_in_center_region(
    needle: str | Path,
    screenshot: str | Path,
    region_width: int,
    region_height: int,
    cropped_output: str | Path | None = None,
    marked_output: str | Path | None = None,
    match_threshold: float = 0.78,
) -> dict[str, float | int | str] | None:
    """Crop the center region of `screenshot` and look for `needle` within it."""
    cropped_path = crop_center_region(screenshot, region_width, region_height, cropped_output)
    if marked_output is None:
        cropped = Path(cropped_path)
        marked_output = cropped.with_name(f"{cropped.stem}_marked{cropped.suffix}")
    return find_image(
        needle=needle,
        haystack=cropped_path,
        output_path=marked_output,
        match_threshold=match_threshold,
    )


def annotate_search_area(
    screenshot: str | Path,
    region_width: int,
    region_height: int,
    annotated_path: str | Path,
    match_result: dict[str, float | int | str] | None = None,
) -> Path:
    """Draw the search region (and match if provided) on the original screenshot."""
    screenshot_path = _resolve_path(screenshot)
    annotated_path = _resolve_path(annotated_path)
    image = _load_image(screenshot_path)

    height, width = image.shape[:2]
    crop_w = min(region_width, width)
    crop_h = min(region_height, height)
    left = max((width - crop_w) // 2, 0)
    top = max((height - crop_h) // 2, 0)
    cv2.rectangle(image, (left, top), (left + crop_w, top + crop_h), (255, 255, 0), 2)

    if match_result:
        center_x = int(match_result.get("center_x", 0))
        center_y = int(match_result.get("center_y", 0))
        top_left_x = int(match_result.get("top_left_x", center_x))
        top_left_y = int(match_result.get("top_left_y", center_y))
        bottom_right_x = int(match_result.get("bottom_right_x", center_x))
        bottom_right_y = int(match_result.get("bottom_right_y", center_y))
        cv2.rectangle(
            image,
            (left + top_left_x, top + top_left_y),
            (left + bottom_right_x, top + bottom_right_y),
            (0, 0, 255),
            2,
        )
        cv2.circle(image, (left + center_x, top + center_y), 6, (0, 255, 0), -1)

    annotated_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(annotated_path), image)
    return annotated_path


__all__ = [
    "DEFAULT_HAYSTACK_PATH",
    "DEFAULT_IMAGE_DIR",
    "DEFAULT_NEEDLE_PATH",
    "DEFAULT_OUTPUT_PATH",
    "crop_center_region",
    "find_image",
    "find_image_in_center_region",
    "annotate_search_area",
]

