# Trainer Test

This repo bundles a handful of focused automation services driven by a single loop in `trainer.py`. Everything is built for advanced users who want full control without extra opinionated layers.

### Libraries & Responsibilities

- `interception-python` (pyinterception) – hardware-grade mouse/keyboard input (`mouse_service`, `keyboard_service`)
- `ctypes` Win32 bindings – window discovery/focus (`window_service`)
- `mss` – instant screenshots (`screenshot_service`)
- `opencv-python` – template matching, region cropping, debug overlays (`image_service`)
- `playsound` – lightweight audio cues (`audio_service`)

Each service does one job:

- `mouse_service`: `move_to/move_by/click/right_click/jitter/position`
- `keyboard_service`: `press_key/tap/hold` (auto-captures devices once)
- `window_service`: `find_window_info`, `focus_window`, `get_window_bounds`
- `screenshot_service`: `capture_screenshot` (full screen or explicit region)
- `image_service`: `crop_center_region`, `find_image`, `find_image_in_center_region`, `annotate_search_area`
- `audio_service`: `play_audio`

The current action loop behaves as follows:

1. Wait 3 seconds after launch.
2. Play `sounds/start.mp3`.
X
X
5. Right-click 9 times, 0.75 s apart.
6. Tap `Q`, wait 0.5 s, tap `W`.
7. Sleep 6 seconds and repeat until stopped.

To change behaviour you edit the constants or the loop body inside `trainer.py`. There are no enable/disable switches anymore—the script simply executes whatever you program in that loop.

## Usage

```bash
poetry install
poetry run python -m trainer_test.trainer
```

Tips:

- Install the Interception driver beforehand (pyinterception only provides the bindings).
- Update `FOCUS_WINDOW_SUBSTRING` so the trainer can focus the proper MU window each cycle.
- Replace `sounds/start.mp3` if you want a different start cue.
- Stop the trainer with `Ctrl+C`.

### Required Assets / Config

- `sounds/start.mp3` and `sounds/reward.mp3`
- `@image-find/needle.png` (fallback `jewel_tag.png`) for runtime reward detection
- `image-find-test/needle.png` and `image-find-test/screenshot.png` for `--test-image-find`
- `screenshots/` (auto-created) stores the latest screenshot, region crop, and marked versions
- Edit the constants at the top of `trainer.py` (delays, window name, search region sizes) to match your client.

