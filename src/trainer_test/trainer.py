from __future__ import annotations

import argparse
import logging
import random
from dataclasses import dataclass
import re
import signal
import sys
import threading
import time
from pathlib import Path

import cv2

from .audio_service import play_audio
from .image_service import annotate_search_area, find_image, find_image_in_center_region
from .keyboard_service import press_key, tap
from .mouse_service import jitter, right_click
from .screenshot_service import capture_screenshot
from .notificator_service import send_discord_notification
from .window_service import find_window_info, focus_window

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
START_SOUND_FILE = PROJECT_ROOT / "sounds" / "start.mp3"
REWARD_SOUND_FILE = PROJECT_ROOT / "sounds" / "reward.mp3"

SCREENSHOT_DIR = PROJECT_ROOT / "screenshots"
SCREENSHOT_PATH = SCREENSHOT_DIR / "screenshot.png"
SCREENSHOT_REGION_PATH = SCREENSHOT_DIR / "screenshot_region.png"
SCREENSHOT_REGION_MARKED_PATH = SCREENSHOT_DIR / "screenshot_region_marked.png"

NEEDLE_DIR = PROJECT_ROOT / "image-find"
NEEDLE_PRIMARY = NEEDLE_DIR / "needle.png"
NEEDLE_FALLBACK = NEEDLE_DIR / "jewel_tag.png"

REGION_WIDTH = 800
REGION_HEIGHT = 600

TEST_IMAGE_DIR = PROJECT_ROOT / "image-find-test"
TEST_NEEDLE_PATH = TEST_IMAGE_DIR / "needle.png"
TEST_SCREENSHOT_PATH = TEST_IMAGE_DIR / "screenshot.png"
TEST_REGION_OUTPUT = TEST_IMAGE_DIR / "screenshot_region.png"
TEST_REGION_MARKED = TEST_IMAGE_DIR / "screenshot_region_marked.png"
TEST_DEBUG_OUTPUT = TEST_IMAGE_DIR / "screenshot_debug.png"
TEST_SEARCH_RADIUS = 400
TEST_REGION_WIDTH = TEST_SEARCH_RADIUS * 2
TEST_REGION_HEIGHT = TEST_SEARCH_RADIUS * 2

_POSSIBLE_VISION_DIRS = [
    PROJECT_ROOT / "vision",
    PROJECT_ROOT / "@vision",
]
for candidate in _POSSIBLE_VISION_DIRS:
    if candidate.exists():
        VISION_DIR = candidate
        break
else:  # pragma: no cover - fallback when folder is missing
    VISION_DIR = _POSSIBLE_VISION_DIRS[0]
VISION_LEVEL_SOURCE = VISION_DIR / "screenshot_level.png"
VISION_LEVEL_DEBUG = VISION_DIR / "screenshot_level_debug.png"
VISION_LEVEL_REGION = VISION_DIR / "level_region.png"
LEVEL_BOX_WIDTH = 200
LEVEL_BOX_HEIGHT = 45
LEVEL_OFFSET_X = 555
LEVEL_OFFSET_Y = -370
LEVEL_MAX_VALUE = 400
LEVEL_UPSCALE_FACTOR = 3
LEVEL_CLAHE_CLIP_LIMIT = 2.0
LEVEL_CLAHE_TILE = (8, 8)
LEVEL_TESSERACT_CONFIG = (
    "--psm 7 --oem 3 -c tessedit_char_whitelist=Level:/0123456789"
)
LEVEL_TEXT_PATTERN = re.compile(r"Level:\s*(\d+)\s*/\s*400", re.IGNORECASE)

ZEN_REGION_WIDTH = 120
ZEN_REGION_HEIGHT = 30
ZEN_OFFSET_X = 545
ZEN_OFFSET_Y = 309
ZEN_DEBUG_PATH = VISION_DIR / "screenshot_zen_debug.png"
VISION_ZEN_REGION = VISION_DIR / "zen_region.png"
ZEN_TEXT_PATTERN = re.compile(r"^\s*([0-9][0-9,]*)\s*$")
ZEN_TESSERACT_CONFIG = "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789,"
ZEN_MAX_VALUE = 2_000_000_000

VISION_DIALOG_SCREENSHOT = VISION_DIR / "screenshot_dialog.png"
VISION_DIALOG_NEEDLE = VISION_DIR / "dialog_needle.png"
VISION_DIALOG_REGION = VISION_DIR / "dialog_region.png"
VISION_DIALOG_REGION_MARKED = VISION_DIR / "dialog_region_marked.png"
VISION_DIALOG_DEBUG = VISION_DIR / "screenshot_dialog_debug.png"
DIALOG_REGION_WIDTH = 300
DIALOG_REGION_HEIGHT = 300
DIALOG_OFFSET_X = 0
DIALOG_OFFSET_Y = -100

VISION_INGAME_SCREENSHOT = VISION_DIR / "screenshot_level.png"
VISION_INGAME_NEEDLE = VISION_DIR / "ingame_needle.png"
VISION_INGAME_REGION = VISION_DIR / "ingame_region.png"
VISION_INGAME_REGION_MARKED = VISION_DIR / "ingame_region_marked.png"
VISION_INGAME_DEBUG = VISION_DIR / "screenshot_ingame_debug.png"
INGAME_REGION_WIDTH = 100
INGAME_REGION_HEIGHT = 100
INGAME_OFFSET_X = -470
INGAME_OFFSET_Y = 490

VISION_INVENTORY_SCREENSHOT = VISION_DIR / "screenshot_inventory.png"
VISION_INVENTORY_NEEDLE = VISION_DIR / "inventory_needle.png"
VISION_INVENTORY_REGION = VISION_DIR / "inventory_region.png"
VISION_INVENTORY_REGION_MARKED = VISION_DIR / "inventory_region_marked.png"
VISION_INVENTORY_DEBUG = VISION_DIR / "screenshot_inventory_debug.png"
INVENTORY_REGION_WIDTH = 100
INVENTORY_REGION_HEIGHT = 100
INVENTORY_OFFSET_X = 305
INVENTORY_OFFSET_Y = 515

VISION_CHARACTER_SCREENSHOT = VISION_DIR / "screenshot_level.png"
VISION_CHARACTER_NEEDLE = VISION_DIR / "character_needle.png"
VISION_CHARACTER_REGION = VISION_DIR / "character_region.png"
VISION_CHARACTER_REGION_MARKED = VISION_DIR / "character_region_marked.png"
VISION_CHARACTER_DEBUG = VISION_DIR / "screenshot_character_debug.png"
CHARACTER_REGION_WIDTH = 100
CHARACTER_REGION_HEIGHT = 100
CHARACTER_OFFSET_X = 210
CHARACTER_OFFSET_Y = 515

VISION_RUN_DIR = PROJECT_ROOT / "vision_run"
RUN_BASE_SCREENSHOT = VISION_RUN_DIR / "screenshot_base.png"
RUN_LEVEL_SCREENSHOT = VISION_RUN_DIR / "screenshot_level.png"
RUN_INVENTORY_SCREENSHOT = VISION_RUN_DIR / "screenshot_inventory.png"
RUN_LEVEL_REGION = VISION_RUN_DIR / "level_region.png"
RUN_LEVEL_DEBUG = VISION_RUN_DIR / "level_debug.png"
RUN_ZEN_REGION = VISION_RUN_DIR / "zen_region.png"
RUN_ZEN_DEBUG = VISION_RUN_DIR / "zen_debug.png"
RUN_ERROR_ATTACHMENT = VISION_RUN_DIR / "error_attachment.png"

NOTIFICATION_IMAGE_OUTPUT = VISION_DIR / "notification_issue.png"
NOTIFICATION_IMAGE_WIDTH = 1920
NOTIFICATION_IMAGE_HEIGHT = 1080
NOTIFICATION_IMAGE_OFFSET_X = 0
NOTIFICATION_IMAGE_OFFSET_Y = 12

DISCORD_WEBHOOK_URL = (
    "ENTER_YOUR_DISCORD_WEBHOOK_URL_HERE"
)
DISCORD_UID = "ENTER_YOUR_DISCORD_UID_HERE"
CHARACTER_NAME = "ENTER_YOUR_CHARACTER_NAME_HERE"
TEST_LEVEL_PLACEHOLDER = "000"
STAR_EMOJI = "⭐"
WARNING_ICON = "⚠️"
COIN_EMOJI = "🪙"
ROCKET_EMOJI = "🚀"

STARTING_MAX_ATTEMPTS = 5
STARTING_RETRY_DELAY_SECONDS = 5
HEALTHCHECK_INTERVAL_SECONDS = 180
MENU_MAX_RETRIES = 10
MENU_CLOSE_MAX_RETRIES = 10
LEVEL_MAX_ATTEMPTS = 3
ZEN_MAX_ATTEMPTS = 3
ZEN_THRESHOLD_INFO = 1_900_000_000

LOG_LEVEL = "INFO"
FOCUS_WINDOW_SUBSTRING = "99B"
FOCUS_EACH_CYCLE = True
START_DELAY_SECONDS = 3.0
RIGHT_CLICK_COUNT = 24
RIGHT_CLICK_INTERVAL = 0.25
KEY_SEQUENCE_DELAY = 0.75
CYCLE_DELAY_SECONDS = 0.1
MOUSE_JITTER_RADIUS = 100
MOUSE_JITTER_STEPS = 2

REWARD_KEY = "space"
REWARD_KEY_REPEAT = 4
REWARD_KEY_INTERVAL = 0.5


@dataclass(frozen=True)
class VisionSearchConfig:
    label: str
    needle: Path
    region_width: int
    region_height: int
    offset_x: int
    offset_y: int


@dataclass
class OcrResult:
    text: str
    value: int | None
    region_path: Path
    debug_path: Path


INGAME_SEARCH_CONFIG = VisionSearchConfig(
    label="ingame",
    needle=VISION_INGAME_NEEDLE,
    region_width=INGAME_REGION_WIDTH,
    region_height=INGAME_REGION_HEIGHT,
    offset_x=INGAME_OFFSET_X,
    offset_y=INGAME_OFFSET_Y,
)

DIALOG_SEARCH_CONFIG = VisionSearchConfig(
    label="dialog",
    needle=VISION_DIALOG_NEEDLE,
    region_width=DIALOG_REGION_WIDTH,
    region_height=DIALOG_REGION_HEIGHT,
    offset_x=DIALOG_OFFSET_X,
    offset_y=DIALOG_OFFSET_Y,
)

INVENTORY_SEARCH_CONFIG = VisionSearchConfig(
    label="inventory",
    needle=VISION_INVENTORY_NEEDLE,
    region_width=INVENTORY_REGION_WIDTH,
    region_height=INVENTORY_REGION_HEIGHT,
    offset_x=INVENTORY_OFFSET_X,
    offset_y=INVENTORY_OFFSET_Y,
)

CHARACTER_SEARCH_CONFIG = VisionSearchConfig(
    label="character",
    needle=VISION_CHARACTER_NEEDLE,
    region_width=CHARACTER_REGION_WIDTH,
    region_height=CHARACTER_REGION_HEIGHT,
    offset_x=CHARACTER_OFFSET_X,
    offset_y=CHARACTER_OFFSET_Y,
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trainer orchestrator.")
    parser.add_argument(
        "--test-image-find",
        action="store_true",
        help="Run image-find diagnostic on image-find-test and exit.",
    )
    parser.add_argument(
        "--test-get-level",
        action="store_true",
        help="Annotate the vision screenshot and run OCR on the target region.",
    )
    parser.add_argument(
        "--test-notification",
        action="store_true",
        help="Send a sample Discord notification via the configured webhook.",
    )
    parser.add_argument(
        "--test-notification-img",
        action="store_true",
        help="Send a Discord notification with an attached screenshot crop.",
    )
    parser.add_argument(
        "--test-dialog",
        action="store_true",
        help="Search for dialog needle in the dialog screenshot region.",
    )
    parser.add_argument(
        "--test-ingame",
        action="store_true",
        help="Search for ingame needle in the level screenshot region.",
    )
    parser.add_argument(
        "--test-inventory",
        action="store_true",
        help="Search for inventory needle in the inventory screenshot region.",
    )
    parser.add_argument(
        "--test-character",
        action="store_true",
        help="Search for character needle in the level screenshot region.",
    )
    parser.add_argument(
        "--test-zen",
        action="store_true",
        help="OCR the zen amount from the inventory screenshot.",
    )
    return parser.parse_args(argv)


def _setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _focus_target(log_missing: bool = True) -> None:
    if not FOCUS_WINDOW_SUBSTRING:
        return

    info = find_window_info(FOCUS_WINDOW_SUBSTRING)
    if not info:
        if log_missing:
            LOGGER.warning("Window containing '%s' not found.", FOCUS_WINDOW_SUBSTRING)
        return

    if focus_window(info.handle):
        LOGGER.debug("Focused window '%s' (%s)", info.title, hex(info.handle))
    else:
        LOGGER.warning("Failed to focus window '%s' (%s)", info.title, hex(info.handle))


def _perform_right_clicks(stop_event: threading.Event) -> bool:
    LOGGER.info("Performing %d right-clicks (%.2fs apart)...", RIGHT_CLICK_COUNT, RIGHT_CLICK_INTERVAL)
    for index in range(RIGHT_CLICK_COUNT):
        if stop_event.is_set():
            return True

        try:
            right_click()
        except Exception:
            LOGGER.exception("Right-click failed.")
            return True

        if index < RIGHT_CLICK_COUNT - 1:
            if stop_event.wait(RIGHT_CLICK_INTERVAL):
                return True
    return False


def _send_key_sequence(stop_event: threading.Event) -> bool:
    LOGGER.info("Sending key sequence Q -> W")

    try:
        tap("Q")
    except Exception:
        LOGGER.exception("Failed to press 'Q'.")
        return True

    if stop_event.wait(KEY_SEQUENCE_DELAY):
        return True

    try:
        tap("W")
    except Exception:
        LOGGER.exception("Failed to press 'W'.")
        return True
    return False


def _select_needle_image() -> Path | None:
    for candidate in (NEEDLE_PRIMARY, NEEDLE_FALLBACK):
        if candidate.exists():
            return candidate
    LOGGER.warning("No needle image found under %s", NEEDLE_DIR)
    return None


def _handle_reward_sequence(stop_event: threading.Event) -> bool:
    if stop_event.is_set():
        return False

    try:
        screenshot_path = capture_screenshot(SCREENSHOT_PATH)
    except Exception:
        LOGGER.exception("Failed to capture screenshot for reward check.")
        return False

    needle_path = _select_needle_image()
    if not needle_path:
        return False

    start = time.perf_counter()
    try:
        result = find_image_in_center_region(
            needle=needle_path,
            screenshot=screenshot_path,
            region_width=REGION_WIDTH,
            region_height=REGION_HEIGHT,
            cropped_output=SCREENSHOT_REGION_PATH,
            marked_output=SCREENSHOT_REGION_MARKED_PATH,
        )
    except Exception:
        LOGGER.exception("Image search failed.")
        return False
    duration = time.perf_counter() - start

    LOGGER.info(
        "Reward search finished in %.3fs -> %s",
        duration,
        "FOUND" if result else "not found",
    )

    if not result:
        return False

    play_audio(REWARD_SOUND_FILE)
    try:
        press_key(REWARD_KEY, repeat=REWARD_KEY_REPEAT, interval=REWARD_KEY_INTERVAL)
    except Exception:
        LOGGER.exception("Failed to send reward key presses.")
    return True


def _run_image_find_test() -> int:
    LOGGER.info("Running image-find test mode.")

    if not TEST_NEEDLE_PATH.exists():
        LOGGER.error("Needle image not found: %s", TEST_NEEDLE_PATH)
        return 1
    if not TEST_SCREENSHOT_PATH.exists():
        LOGGER.error("Screenshot not found: %s", TEST_SCREENSHOT_PATH)
        return 1

    result = find_image_in_center_region(
        needle=TEST_NEEDLE_PATH,
        screenshot=TEST_SCREENSHOT_PATH,
        region_width=TEST_REGION_WIDTH,
        region_height=TEST_REGION_HEIGHT,
        cropped_output=TEST_REGION_OUTPUT,
        marked_output=TEST_REGION_MARKED,
    )

    annotate_search_area(
        screenshot=TEST_SCREENSHOT_PATH,
        region_width=TEST_REGION_WIDTH,
        region_height=TEST_REGION_HEIGHT,
        annotated_path=TEST_DEBUG_OUTPUT,
        match_result=result,
    )

    if result:
        message = (
            f"Needle FOUND at (center={result['center_x']}, {result['center_y']}) "
            f"confidence={result['confidence']:.3f} "
            f"in {result['duration']:.3f}s"
        )
        print(message)
        LOGGER.info(message)
        LOGGER.info("Annotated screenshot saved to %s", TEST_DEBUG_OUTPUT)
        return 0

    print("Needle NOT found in the specified region.")
    LOGGER.info("Needle not found; see %s for search area.", TEST_DEBUG_OUTPUT)
    return 2


def _compute_region_bounds(total_size: int, region_size: int, desired_center: int) -> tuple[int, int]:
    """Return (start, end) bounds clamped to the image size."""
    if total_size <= 0:
        return 0, 0
    half_size = region_size // 2
    max_start = max(total_size - region_size, 0)
    start = desired_center - half_size
    start = max(0, min(start, max_start))
    end = min(start + region_size, total_size)
    return start, end


def _calculate_centered_region(
    image_width: int,
    image_height: int,
    region_width: int,
    region_height: int,
    offset_x: int,
    offset_y: int,
) -> tuple[int, int, int, int]:
    desired_center_x = image_width // 2 + offset_x
    desired_center_y = image_height // 2 + offset_y
    left, right = _compute_region_bounds(image_width, region_width, desired_center_x)
    top, bottom = _compute_region_bounds(image_height, region_height, desired_center_y)
    return left, top, right, bottom


def _capture_screenshot_to(target_path: Path) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    return capture_screenshot(target_path)


def _run_centered_search_runtime(
    screenshot_path: Path,
    config: VisionSearchConfig,
) -> tuple[bool, Path | None, Path | None]:
    if not screenshot_path.exists():
        LOGGER.error("Screenshot not found for %s search: %s", config.label, screenshot_path)
        return False, None, None
    if not config.needle.exists():
        LOGGER.error("Needle not found for %s search: %s", config.label, config.needle)
        return False, None, None

    image = cv2.imread(str(screenshot_path))
    if image is None:
        LOGGER.error("Failed to read screenshot for %s search: %s", config.label, screenshot_path)
        return False, None, None

    height, width = image.shape[:2]
    left, top, right, bottom = _calculate_centered_region(
        width,
        height,
        config.region_width,
        config.region_height,
        config.offset_x,
        config.offset_y,
    )

    if left == right or top == bottom:
        LOGGER.error(
            "%s search region evaluated to empty bounds (left=%d, right=%d, top=%d, bottom=%d).",
            config.label,
            left,
            right,
            top,
            bottom,
        )
        return False, None, None

    region = image[top:bottom, left:right]
    if region.size == 0:
        LOGGER.error("%s search region contains no pixels.", config.label)
        return False, None, None

    VISION_RUN_DIR.mkdir(parents=True, exist_ok=True)
    region_path = VISION_RUN_DIR / f"{config.label}_region.png"
    region_marked_path = VISION_RUN_DIR / f"{config.label}_region_marked.png"
    debug_path = VISION_RUN_DIR / f"{config.label}_debug.png"

    cv2.imwrite(str(region_path), region)
    result = find_image(
        needle=config.needle,
        haystack=region_path,
        output_path=region_marked_path,
    )

    debug_image = image.copy()
    cv2.rectangle(
        debug_image,
        (left, top),
        (max(right - 1, left), max(bottom - 1, top)),
        (255, 255, 0),
        2,
    )

    if result:
        top_left_x = left + int(result.get("top_left_x", 0))
        top_left_y = top + int(result.get("top_left_y", 0))
        bottom_right_x = left + int(result.get("bottom_right_x", 0))
        bottom_right_y = top + int(result.get("bottom_right_y", 0))
        center_x = left + int(result.get("center_x", 0))
        center_y = top + int(result.get("center_y", 0))

        cv2.rectangle(
            debug_image,
            (top_left_x, top_left_y),
            (bottom_right_x, bottom_right_y),
            (0, 0, 255),
            2,
        )
        cv2.circle(debug_image, (center_x, center_y), 5, (0, 255, 0), -1)

    cv2.imwrite(str(debug_path), debug_image)
    return result is not None, region_path, debug_path


def _detect_with_config(screenshot_path: Path, config: VisionSearchConfig) -> tuple[bool, Path | None, Path | None]:
    return _run_centered_search_runtime(screenshot_path, config)


def _detect_ingame(screenshot_path: Path) -> tuple[bool, Path | None, Path | None]:
    return _detect_with_config(screenshot_path, INGAME_SEARCH_CONFIG)


def _detect_dialog(screenshot_path: Path) -> tuple[bool, Path | None, Path | None]:
    return _detect_with_config(screenshot_path, DIALOG_SEARCH_CONFIG)


def _detect_inventory(screenshot_path: Path) -> tuple[bool, Path | None, Path | None]:
    return _detect_with_config(screenshot_path, INVENTORY_SEARCH_CONFIG)


def _detect_character_menu(screenshot_path: Path) -> tuple[bool, Path | None, Path | None]:
    return _detect_with_config(screenshot_path, CHARACTER_SEARCH_CONFIG)


def _tap_with_delay(key: str, delay: float = 2) -> None:
    actual_delay = max(0.0, delay + random.uniform(-0.5, 0.5))
    LOGGER.info("Sending key '%s' with %.3fs post-delay.", key, actual_delay)
    tap(key)
    time.sleep(actual_delay)


def _send_info_notification(message: str, emoji: str | None = None) -> bool:
    suffix = emoji or STAR_EMOJI
    content = f"<@{DISCORD_UID}> {CHARACTER_NAME}. {message} {suffix}"
    success = send_discord_notification(DISCORD_WEBHOOK_URL, content)
    if success:
        LOGGER.info("Discord info message sent: %s", message)
    else:
        LOGGER.error("Failed to send Discord info message: %s", message)
    return success


def _send_error_notification(message: str, screenshot_path: Path | None = None) -> bool:
    attachment = _prepare_error_attachment(screenshot_path)
    content = f"<@{DISCORD_UID}> Error for {CHARACTER_NAME}. {message} {WARNING_ICON}"
    success = send_discord_notification(
        DISCORD_WEBHOOK_URL,
        content,
        file_path=attachment,
    )
    if success:
        LOGGER.info("Discord error message sent: %s", message)
    else:
        LOGGER.error("Failed to send Discord error message: %s", message)
    return success


def _prepare_center_crop(
    screenshot_path: Path,
    width: int,
    height: int,
    output_path: Path,
    offset_x: int = 0,
    offset_y: int = 0,
) -> Path | None:
    if not screenshot_path.exists():
        LOGGER.error("Screenshot not found for cropping: %s", screenshot_path)
        return None

    image = cv2.imread(str(screenshot_path))
    if image is None:
        LOGGER.error("Failed to read screenshot for cropping: %s", screenshot_path)
        return None

    img_height, img_width = image.shape[:2]
    left, top, right, bottom = _calculate_centered_region(
        img_width,
        img_height,
        width,
        height,
        offset_x,
        offset_y,
    )

    region = image[top:bottom, left:right]
    if region.size == 0:
        LOGGER.error("Center crop produced an empty region for %s", screenshot_path)
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), region)
    return output_path


def _prepare_error_attachment(screenshot_path: Path | None) -> Path | None:
    if not screenshot_path:
        return None
    return _prepare_center_crop(
        screenshot_path,
        NOTIFICATION_IMAGE_WIDTH,
        NOTIFICATION_IMAGE_HEIGHT,
        RUN_ERROR_ATTACHMENT,
    )


def _run_centered_image_search(
    *,
    screenshot_path: Path,
    needle_path: Path,
    region_width: int,
    region_height: int,
    offset_x: int,
    offset_y: int,
    region_output: Path,
    region_marked_output: Path,
    debug_output: Path,
    search_label: str,
) -> int:
    LOGGER.info("Running %s search test mode.", search_label)

    if not screenshot_path.exists():
        LOGGER.error("%s screenshot not found: %s", search_label.title(), screenshot_path)
        return 1
    if not needle_path.exists():
        LOGGER.error("%s needle not found: %s", search_label.title(), needle_path)
        return 1

    screenshot = cv2.imread(str(screenshot_path))
    if screenshot is None:
        LOGGER.error("Failed to read %s screenshot: %s", search_label, screenshot_path)
        return 1

    height, width = screenshot.shape[:2]
    left, top, right, bottom = _calculate_centered_region(
        width,
        height,
        region_width,
        region_height,
        offset_x,
        offset_y,
    )

    if left == right or top == bottom:
        LOGGER.error(
            "%s search region is empty (left=%d, right=%d, top=%d, bottom=%d).",
            search_label.title(),
            left,
            right,
            top,
            bottom,
        )
        return 1

    region = screenshot[top:bottom, left:right]
    if region.size == 0:
        LOGGER.error("%s search region contains no pixels.", search_label.title())
        return 1

    region_output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(region_output), region)

    region_marked_output.parent.mkdir(parents=True, exist_ok=True)
    result = find_image(
        needle=needle_path,
        haystack=region_output,
        output_path=region_marked_output,
    )

    debug = screenshot.copy()
    cv2.rectangle(
        debug,
        (left, top),
        (max(right - 1, left), max(bottom - 1, top)),
        (255, 255, 0),
        2,
    )

    if result:
        top_left_x = left + int(result.get("top_left_x", 0))
        top_left_y = top + int(result.get("top_left_y", 0))
        bottom_right_x = left + int(result.get("bottom_right_x", 0))
        bottom_right_y = top + int(result.get("bottom_right_y", 0))
        center_x = left + int(result.get("center_x", 0))
        center_y = top + int(result.get("center_y", 0))

        confidence = result.get("confidence")
        if isinstance(confidence, (int, float)):
            confidence_display = f"{confidence:.3f}"
        else:
            confidence_display = confidence or "n/a"

        cv2.rectangle(
            debug,
            (top_left_x, top_left_y),
            (bottom_right_x, bottom_right_y),
            (0, 0, 255),
            2,
        )
        cv2.circle(debug, (center_x, center_y), 5, (0, 255, 0), -1)
        found_message = (
            f"{search_label.title()} needle FOUND at (center={center_x}, {center_y}) "
            f"confidence={confidence_display}"
        )
        print(found_message)
        LOGGER.info(found_message)
        exit_code = 0
    else:
        not_found_message = f"{search_label.title()} needle NOT found in the specified region."
        print(not_found_message)
        LOGGER.info(not_found_message)
        exit_code = 2

    debug_output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(debug_output), debug)
    LOGGER.info("%s search debug screenshot saved to %s", search_label.title(), debug_output)

    return exit_code


def _preprocess_level_region(region):
    """Apply grayscale, contrast enhancement, scaling, and thresholding."""
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    upscaled = cv2.resize(
        gray,
        None,
        fx=LEVEL_UPSCALE_FACTOR,
        fy=LEVEL_UPSCALE_FACTOR,
        interpolation=cv2.INTER_CUBIC,
    )
    clahe = cv2.createCLAHE(
        clipLimit=LEVEL_CLAHE_CLIP_LIMIT, tileGridSize=LEVEL_CLAHE_TILE
    )
    enhanced = clahe.apply(upscaled)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def _preprocess_currency_region(region):
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    upscaled = cv2.resize(
        gray,
        None,
        fx=2.0,
        fy=2.0,
        interpolation=cv2.INTER_CUBIC,
    )
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(upscaled)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def _perform_level_ocr_from_screenshot(
    screenshot_path: Path,
    debug_path: Path,
    region_output: Path,
) -> OcrResult | None:
    if not screenshot_path.exists():
        LOGGER.error("Level screenshot not found: %s", screenshot_path)
        return None

    image = cv2.imread(str(screenshot_path))
    if image is None:
        LOGGER.error("Failed to read level screenshot: %s", screenshot_path)
        return None

    height, width = image.shape[:2]
    left, top, right, bottom = _calculate_centered_region(
        width,
        height,
        LEVEL_BOX_WIDTH,
        LEVEL_BOX_HEIGHT,
        LEVEL_OFFSET_X,
        LEVEL_OFFSET_Y,
    )

    if left == right or top == bottom:
        LOGGER.error(
            "Level OCR region is empty (left=%d, right=%d, top=%d, bottom=%d).",
            left,
            right,
            top,
            bottom,
        )
        return None

    debug_image = image.copy()
    cv2.rectangle(
        debug_image,
        (left, top),
        (max(right - 1, left), max(bottom - 1, top)),
        (0, 0, 255),
        2,
    )
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(debug_path), debug_image)
    LOGGER.info("Level debug screenshot saved to %s", debug_path)

    region = image[top:bottom, left:right]
    if region.size == 0:
        LOGGER.error("Level OCR region contains no pixels.")
        return None

    region_output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(region_output), region)

    preprocessed = _preprocess_level_region(region)

    try:
        import pytesseract  # type: ignore[import]
        from PIL import Image  # type: ignore[import]
    except ImportError:
        LOGGER.error("pytesseract (and Pillow) are required for OCR; reinstall dependencies.")
        return None

    pil_image = Image.fromarray(preprocessed)
    try:
        text = pytesseract.image_to_string(pil_image, config=LEVEL_TESSERACT_CONFIG)
    except pytesseract.TesseractNotFoundError:
        LOGGER.error(
            "Tesseract OCR engine is not installed or not on PATH; install it to continue."
        )
        return None

    cleaned_text = text.strip()
    if cleaned_text:
        LOGGER.info("Level OCR detected text: %s", cleaned_text)
    else:
        LOGGER.info("Level OCR detected no text.")

    level_value = _extract_level_value(cleaned_text)
    return OcrResult(
        text=cleaned_text,
        value=level_value,
        region_path=region_output,
        debug_path=debug_path,
    )


def _perform_zen_ocr_from_screenshot(
    screenshot_path: Path,
    debug_path: Path,
    region_output: Path,
) -> OcrResult | None:
    if not screenshot_path.exists():
        LOGGER.error("Zen screenshot not found: %s", screenshot_path)
        return None

    image = cv2.imread(str(screenshot_path))
    if image is None:
        LOGGER.error("Failed to read zen screenshot: %s", screenshot_path)
        return None

    height, width = image.shape[:2]
    left, top, right, bottom = _calculate_centered_region(
        width,
        height,
        ZEN_REGION_WIDTH,
        ZEN_REGION_HEIGHT,
        ZEN_OFFSET_X,
        ZEN_OFFSET_Y,
    )

    if left == right or top == bottom:
        LOGGER.error(
            "Zen OCR region is empty (left=%d, right=%d, top=%d, bottom=%d).",
            left,
            right,
            top,
            bottom,
        )
        return None

    debug_image = image.copy()
    cv2.rectangle(
        debug_image,
        (left, top),
        (max(right - 1, left), max(bottom - 1, top)),
        (0, 0, 255),
        2,
    )
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(debug_path), debug_image)
    LOGGER.info("Zen debug screenshot saved to %s", debug_path)

    region = image[top:bottom, left:right]
    if region.size == 0:
        LOGGER.error("Zen OCR region contains no pixels.")
        return None

    region_output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(region_output), region)

    preprocessed = _preprocess_currency_region(region)

    try:
        import pytesseract  # type: ignore[import]
        from PIL import Image  # type: ignore[import]
    except ImportError:
        LOGGER.error("pytesseract (and Pillow) are required for OCR; reinstall dependencies.")
        return None

    pil_image = Image.fromarray(preprocessed)
    try:
        text = pytesseract.image_to_string(pil_image, config=ZEN_TESSERACT_CONFIG)
    except pytesseract.TesseractNotFoundError:
        LOGGER.error(
            "Tesseract OCR engine is not installed or not on PATH; install it to continue."
        )
        return None

    cleaned_text = text.strip()
    if cleaned_text:
        LOGGER.info("Zen OCR detected text: %s", cleaned_text)
    else:
        LOGGER.info("Zen OCR detected no text.")

    zen_value = _parse_zen_value(cleaned_text)
    return OcrResult(
        text=cleaned_text,
        value=zen_value,
        region_path=region_output,
        debug_path=debug_path,
    )


def _extract_level_value(text: str) -> int | None:
    match = LEVEL_TEXT_PATTERN.search(text)
    if not match:
        return None
    try:
        level_value = int(match.group(1))
    except ValueError:
        return None
    if level_value < 0 or level_value > LEVEL_MAX_VALUE:
        return None
    return level_value


def _parse_zen_value(text: str) -> int | None:
    match = ZEN_TEXT_PATTERN.match(text)
    if not match:
        return None
    digits = match.group(1).replace(",", "")
    try:
        value = int(digits)
    except ValueError:
        return None
    if value < 0 or value > ZEN_MAX_VALUE:
        return None
    return value


def _build_notification_message(character_name: str) -> str:
    mention = f"<@{DISCORD_UID}>"
    return f"{mention} {character_name} has reached level {TEST_LEVEL_PLACEHOLDER} {STAR_EMOJI}"


def _build_notification_issue_message(character_name: str) -> str:
    mention = f"<@{DISCORD_UID}>"
    return (
        f"{mention} Routine for character {character_name} has encountered an issue {WARNING_ICON}."
    )


def _run_test_notification(character_name: str) -> int:
    message = _build_notification_message(character_name)
    LOGGER.info("Sending test notification for character '%s'.", character_name)
    success = send_discord_notification(DISCORD_WEBHOOK_URL, message)
    if success:
        print("Discord notification sent successfully.")
        LOGGER.info("Discord notification delivered.")
        return 0

    print("Failed to send Discord notification; see logs for details.")
    LOGGER.error("Discord notification failed to send.")
    return 1


def _run_test_notification_img(character_name: str) -> int:
    crop_path = _prepare_notification_image()
    if not crop_path:
        print("Failed to prepare notification image; see logs for details.")
        return 1

    message = _build_notification_issue_message(character_name)
    LOGGER.info("Sending notification with image for character '%s'.", character_name)
    success = send_discord_notification(
        DISCORD_WEBHOOK_URL,
        message,
        file_path=crop_path,
    )

    if success:
        print("Discord notification with image sent successfully.")
        LOGGER.info("Discord notification with image delivered.")
        return 0

    print("Failed to send Discord notification with image; see logs for details.")
    LOGGER.error("Discord notification with image failed to send.")
    return 1


def _prepare_notification_image() -> Path | None:
    return _prepare_center_crop(
        VISION_LEVEL_SOURCE,
        NOTIFICATION_IMAGE_WIDTH,
        NOTIFICATION_IMAGE_HEIGHT,
        NOTIFICATION_IMAGE_OUTPUT,
        NOTIFICATION_IMAGE_OFFSET_X,
        NOTIFICATION_IMAGE_OFFSET_Y,
    )


def _run_test_get_level() -> int:
    LOGGER.info("Running level OCR test mode.")

    result = _perform_level_ocr_from_screenshot(
        VISION_LEVEL_SOURCE,
        VISION_LEVEL_DEBUG,
        VISION_LEVEL_REGION,
    )
    if result is None:
        return 1

    if result.text:
        print(f"Detected text: {result.text}")
        LOGGER.info("OCR detected text: %s", result.text)
    else:
        print("No text detected in the selected region.")
        LOGGER.info("OCR did not detect any text in the selected region.")

    if result.value is not None:
        print(f"Detected level: {result.value}")
        LOGGER.info("Parsed level value: %d", result.value)
    else:
        print("Unable to parse the level value from OCR output.")
        LOGGER.info("Failed to parse level value from OCR output: %r", result.text)
    return 0


def _run_test_dialog() -> int:
    return _run_centered_image_search(
        screenshot_path=VISION_DIALOG_SCREENSHOT,
        needle_path=VISION_DIALOG_NEEDLE,
        region_width=DIALOG_REGION_WIDTH,
        region_height=DIALOG_REGION_HEIGHT,
        offset_x=DIALOG_OFFSET_X,
        offset_y=DIALOG_OFFSET_Y,
        region_output=VISION_DIALOG_REGION,
        region_marked_output=VISION_DIALOG_REGION_MARKED,
        debug_output=VISION_DIALOG_DEBUG,
        search_label="dialog",
    )


def _run_test_ingame() -> int:
    return _run_centered_image_search(
        screenshot_path=VISION_INGAME_SCREENSHOT,
        needle_path=VISION_INGAME_NEEDLE,
        region_width=INGAME_REGION_WIDTH,
        region_height=INGAME_REGION_HEIGHT,
        offset_x=INGAME_OFFSET_X,
        offset_y=INGAME_OFFSET_Y,
        region_output=VISION_INGAME_REGION,
        region_marked_output=VISION_INGAME_REGION_MARKED,
        debug_output=VISION_INGAME_DEBUG,
        search_label="ingame",
    )


def _run_test_inventory() -> int:
    return _run_centered_image_search(
        screenshot_path=VISION_INVENTORY_SCREENSHOT,
        needle_path=VISION_INVENTORY_NEEDLE,
        region_width=INVENTORY_REGION_WIDTH,
        region_height=INVENTORY_REGION_HEIGHT,
        offset_x=INVENTORY_OFFSET_X,
        offset_y=INVENTORY_OFFSET_Y,
        region_output=VISION_INVENTORY_REGION,
        region_marked_output=VISION_INVENTORY_REGION_MARKED,
        debug_output=VISION_INVENTORY_DEBUG,
        search_label="inventory",
    )


def _run_test_character() -> int:
    return _run_centered_image_search(
        screenshot_path=VISION_CHARACTER_SCREENSHOT,
        needle_path=VISION_CHARACTER_NEEDLE,
        region_width=CHARACTER_REGION_WIDTH,
        region_height=CHARACTER_REGION_HEIGHT,
        offset_x=CHARACTER_OFFSET_X,
        offset_y=CHARACTER_OFFSET_Y,
        region_output=VISION_CHARACTER_REGION,
        region_marked_output=VISION_CHARACTER_REGION_MARKED,
        debug_output=VISION_CHARACTER_DEBUG,
        search_label="character",
    )


def _run_test_zen() -> int:
    LOGGER.info("Running zen OCR test mode.")

    result = _perform_zen_ocr_from_screenshot(
        VISION_INVENTORY_SCREENSHOT,
        ZEN_DEBUG_PATH,
        VISION_ZEN_REGION,
    )
    if result is None:
        return 1

    if result.text:
        print(f"Detected zen text: {result.text}")
        LOGGER.info("Zen OCR detected text: %s", result.text)
    else:
        print("No zen text detected in the selected region.")
        LOGGER.info("Zen OCR did not detect any text in the selected region.")

    if result.value is not None:
        print(f"Detected zen amount: {result.value:,}")
        LOGGER.info("Parsed zen amount: %d", result.value)
    else:
        print("Unable to parse zen amount from OCR output.")
        LOGGER.info("Failed to parse zen amount from OCR output: %r", result.text)
    return 0


def _enter_running_state(stop_event: threading.Event) -> bool:
    LOGGER.info("Entering STARTING state.")
    for attempt in range(STARTING_MAX_ATTEMPTS):
        if stop_event.is_set():
            return False

        LOGGER.info("Checking in-game status (attempt %d/%d)...", attempt + 1, STARTING_MAX_ATTEMPTS)
        _capture_screenshot_to(RUN_BASE_SCREENSHOT)
        ingame_found, _, _ = _detect_ingame(RUN_BASE_SCREENSHOT)
        if ingame_found:
            LOGGER.info("%s Trainer started", ROCKET_EMOJI)
            play_audio(START_SOUND_FILE)
            return True

        if attempt < STARTING_MAX_ATTEMPTS - 1:
            LOGGER.info(
                "Not in game yet; retrying in %ds.",
                STARTING_RETRY_DELAY_SECONDS,
            )
            if stop_event.wait(STARTING_RETRY_DELAY_SECONDS):
                return False

    LOGGER.error("Unable to start trainer %s", WARNING_ICON)
    return False


def _perform_healthcheck_cycle() -> bool:
    screenshot_path = _capture_screenshot_to(RUN_BASE_SCREENSHOT)
    ingame_found, _, _ = _detect_ingame(screenshot_path)
    if not ingame_found:
        _send_error_notification(
            "Character seems not to be in game",
            screenshot_path,
        )
        return False

    dialog_found, _, _ = _detect_dialog(screenshot_path)
    if dialog_found:
        _send_error_notification(
            "Dialog window opened",
            screenshot_path,
        )
        return False

    return True


def _perform_level_cycle(previous_level: int | None) -> tuple[bool, int | None]:
    menu_open = False
    region_path: Path | None = None
    for attempt in range(MENU_MAX_RETRIES):
        _tap_with_delay("C")
        _capture_screenshot_to(RUN_LEVEL_SCREENSHOT)
        menu_open, region_path, _ = _detect_character_menu(RUN_LEVEL_SCREENSHOT)
        if menu_open:
            break
    if not menu_open:
        _send_error_notification("Unable to open character menu for level check", RUN_LEVEL_SCREENSHOT)
        return False, previous_level

    detected_level: int | None = None
    for attempt in range(LEVEL_MAX_ATTEMPTS):
        _capture_screenshot_to(RUN_LEVEL_SCREENSHOT)
        ocr_result = _perform_level_ocr_from_screenshot(
            RUN_LEVEL_SCREENSHOT,
            RUN_LEVEL_DEBUG,
            RUN_LEVEL_REGION,
        )
        if ocr_result and ocr_result.value is not None:
            detected_level = ocr_result.value
            break

    if detected_level is None:
        _send_error_notification("Unable to find and parse character level", RUN_LEVEL_SCREENSHOT)
        return False, previous_level

    if previous_level is not None:
        if previous_level < 380 <= detected_level:
            _send_info_notification(f"Character reached level {detected_level}")
        elif previous_level < 280 <= detected_level:
            _send_info_notification(f"Character reached level {detected_level}")
        elif previous_level < 150 <= detected_level:
            _send_info_notification(f"Character reached level {detected_level}")

    closed = False
    for attempt in range(MENU_CLOSE_MAX_RETRIES):
        _tap_with_delay("C")
        _capture_screenshot_to(RUN_LEVEL_SCREENSHOT)
        menu_open, _, _ = _detect_character_menu(RUN_LEVEL_SCREENSHOT)
        if not menu_open:
            closed = True
            break
    if not closed:
        _send_error_notification("Unable to close character menu after level check", RUN_LEVEL_SCREENSHOT)
        return False, detected_level

    return True, detected_level


def _perform_zen_cycle() -> bool:
    inventory_open = False
    region_path: Path | None = None
    for attempt in range(MENU_MAX_RETRIES):
        _tap_with_delay("I")
        _capture_screenshot_to(RUN_INVENTORY_SCREENSHOT)
        inventory_open, region_path, _ = _detect_inventory(RUN_INVENTORY_SCREENSHOT)
        if inventory_open:
            break
    if not inventory_open:
        _send_error_notification("Unable to open inventory for zen check", RUN_INVENTORY_SCREENSHOT)
        return False

    detected_zen: int | None = None
    for attempt in range(ZEN_MAX_ATTEMPTS):
        _capture_screenshot_to(RUN_INVENTORY_SCREENSHOT)
        ocr_result = _perform_zen_ocr_from_screenshot(
            RUN_INVENTORY_SCREENSHOT,
            RUN_ZEN_DEBUG,
            RUN_ZEN_REGION,
        )
        if ocr_result and ocr_result.value is not None:
            detected_zen = ocr_result.value
            break

    if detected_zen is None:
        _send_error_notification("Unable to find and parse zen amount", RUN_INVENTORY_SCREENSHOT)
        return False

    if detected_zen > ZEN_THRESHOLD_INFO:
        _send_info_notification("Character zen is reaching maximum value", emoji=COIN_EMOJI)

    closed = False
    for attempt in range(MENU_CLOSE_MAX_RETRIES):
        _tap_with_delay("I")
        _capture_screenshot_to(RUN_INVENTORY_SCREENSHOT)
        inventory_open, _, _ = _detect_inventory(RUN_INVENTORY_SCREENSHOT)
        if not inventory_open:
            closed = True
            break
    if not closed:
        _send_error_notification("Unable to close inventory after zen check", RUN_INVENTORY_SCREENSHOT)
        return False

    return True


def _perform_running_cycle(previous_level: int | None) -> tuple[bool, int | None]:
    if not _perform_healthcheck_cycle():
        return False, previous_level

    level_success, updated_level = _perform_level_cycle(previous_level)
    if not level_success:
        return False, previous_level

    if not _perform_zen_cycle():
        return False, previous_level

    return True, (updated_level if updated_level is not None else previous_level)


def _run_action_loop(stop_event: threading.Event) -> None:
    if stop_event.is_set():
        return

    if not _enter_running_state(stop_event):
        return

    previous_level: int | None = None

    while not stop_event.is_set():
        cycle_start = time.monotonic()
        continue_running, previous_level = _perform_running_cycle(previous_level)
        if not continue_running:
            break

        elapsed = time.monotonic() - cycle_start
        wait_time = max(HEALTHCHECK_INTERVAL_SECONDS - elapsed, 0)
        LOGGER.info("Waiting %.1fs before next health check...", wait_time)
        if stop_event.wait(wait_time):
            break


def _register_signal_handlers(stop_event: threading.Event) -> None:
    def handler(signum, _frame):
        LOGGER.info("Received signal %s; shutting down.", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handler)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _setup_logging()
    character_name = CHARACTER_NAME

    if getattr(args, "test_notification", False):
        return _run_test_notification(character_name)

    if getattr(args, "test_notification_img", False):
        return _run_test_notification_img(character_name)

    if getattr(args, "test_get_level", False):
        return _run_test_get_level()

    if getattr(args, "test_dialog", False):
        return _run_test_dialog()

    if getattr(args, "test_ingame", False):
        return _run_test_ingame()

    if getattr(args, "test_inventory", False):
        return _run_test_inventory()

    if getattr(args, "test_character", False):
        return _run_test_character()

    if getattr(args, "test_image_find", False):
        return _run_image_find_test()

    if getattr(args, "test_zen", False):
        return _run_test_zen()

    stop_event = threading.Event()
    _register_signal_handlers(stop_event)

    try:
        _run_action_loop(stop_event)
    except KeyboardInterrupt:
        LOGGER.info("Keyboard interrupt received; exiting.")
    except Exception as exc:
        LOGGER.exception("Trainer encountered an error: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

