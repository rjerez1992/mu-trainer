from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
import time
from pathlib import Path

from .audio_service import play_audio
from .image_service import annotate_search_area, find_image_in_center_region
from .keyboard_service import press_key, tap
from .mouse_service import jitter, right_click
from .screenshot_service import capture_screenshot
from .window_service import find_window_info, focus_window

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
START_SOUND_FILE = PROJECT_ROOT / "sounds" / "start.mp3"
REWARD_SOUND_FILE = PROJECT_ROOT / "sounds" / "reward.mp3"

SCREENSHOT_DIR = PROJECT_ROOT / "screenshots"
SCREENSHOT_PATH = SCREENSHOT_DIR / "screenshot.png"
SCREENSHOT_REGION_PATH = SCREENSHOT_DIR / "screenshot_region.png"
SCREENSHOT_REGION_MARKED_PATH = SCREENSHOT_DIR / "screenshot_region_marked.png"

NEEDLE_DIR = PROJECT_ROOT / "@image-find"
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

LOG_LEVEL = "INFO"
FOCUS_WINDOW_SUBSTRING = "99B"
FOCUS_EACH_CYCLE = True
START_DELAY_SECONDS = 3.0
RIGHT_CLICK_COUNT = 9
RIGHT_CLICK_INTERVAL = 0.8
KEY_SEQUENCE_DELAY = 0.9
CYCLE_DELAY_SECONDS = 2.0
MOUSE_JITTER_RADIUS = 100
MOUSE_JITTER_STEPS = 2

REWARD_KEY = "space"
REWARD_KEY_REPEAT = 4
REWARD_KEY_INTERVAL = 0.5


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trainer orchestrator.")
    parser.add_argument(
        "--test-image-find",
        action="store_true",
        help="Run image-find diagnostic on image-find-test and exit.",
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


def _run_action_loop(stop_event: threading.Event) -> None:
    LOGGER.info("Starting in %.1fs...", START_DELAY_SECONDS)
    if stop_event.wait(START_DELAY_SECONDS):
        return

    play_audio(START_SOUND_FILE)
    #_focus_target()

    while not stop_event.is_set():
        #if FOCUS_EACH_CYCLE:
        #    _focus_target(log_missing=False)

        #if MOUSE_JITTER_STEPS > 0 and MOUSE_JITTER_RADIUS > 0:
        #    jitter(radius=MOUSE_JITTER_RADIUS, steps=MOUSE_JITTER_STEPS)

        if _perform_right_clicks(stop_event):
            break
        if _send_key_sequence(stop_event):
            break

        reward_triggered = _handle_reward_sequence(stop_event)
        if stop_event.is_set():
            break
        if reward_triggered:
            LOGGER.info("Reward detected; skipping delay before next cycle.")
            continue

        LOGGER.info("Waiting %.1fs before next cycle...", CYCLE_DELAY_SECONDS)
        if stop_event.wait(CYCLE_DELAY_SECONDS):
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

    if getattr(args, "test_image_find", False):
        return _run_image_find_test()

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

