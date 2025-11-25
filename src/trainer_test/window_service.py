from __future__ import annotations

import ctypes
import logging
from dataclasses import dataclass
from typing import Optional

LOGGER = logging.getLogger(__name__)

user32 = ctypes.WinDLL("user32", use_last_error=True)

EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
EnumWindows.argtypes = [EnumWindowsProc, ctypes.c_void_p]
EnumWindows.restype = ctypes.c_bool

IsWindowVisible = user32.IsWindowVisible
IsWindowVisible.argtypes = [ctypes.c_void_p]
IsWindowVisible.restype = ctypes.c_bool

GetWindowText = user32.GetWindowTextW
GetWindowText.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
GetWindowText.restype = ctypes.c_int

GetWindowTextLength = user32.GetWindowTextLengthW
GetWindowTextLength.argtypes = [ctypes.c_void_p]
GetWindowTextLength.restype = ctypes.c_int

GetWindowRect = user32.GetWindowRect
GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_long * 4)]
GetWindowRect.restype = ctypes.c_int

SetForegroundWindow = user32.SetForegroundWindow
SetForegroundWindow.argtypes = [ctypes.c_void_p]
SetForegroundWindow.restype = ctypes.c_bool

GetSystemMetrics = user32.GetSystemMetrics
GetSystemMetrics.argtypes = [ctypes.c_int]
GetSystemMetrics.restype = ctypes.c_int

SM_CXSCREEN = 0
SM_CYSCREEN = 1


@dataclass(frozen=True)
class WindowInfo:
    """Simple container describing a window on the desktop."""

    handle: int
    title: str
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)

    @property
    def center(self) -> tuple[int, int]:
        return self.left + self.width // 2, self.top + self.height // 2

    def as_dict(self) -> dict[str, int | str | tuple[int, int]]:
        return {
            "handle": self.handle,
            "title": self.title,
            "bounds": (self.left, self.top, self.right, self.bottom),
            "width": self.width,
            "height": self.height,
            "center": self.center,
        }


def _get_window_title(hwnd: int) -> str:
    length = GetWindowTextLength(hwnd)
    if length == 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    GetWindowText(hwnd, buffer, length + 1)
    return buffer.value


def _get_window_bounds(hwnd: int) -> tuple[int, int, int, int]:
    rect = (ctypes.c_long * 4)()
    if GetWindowRect(hwnd, rect) == 0:
        return 0, 0, 0, 0
    return rect[0], rect[1], rect[2], rect[3]


def find_window_info(
    partial_title: str,
    *,
    log_missing: bool = True,
    match_mode: str = "substring",
) -> Optional[WindowInfo]:
    """Return the first visible window matching ``partial_title`` (case-insensitive).

    match_mode:
        - "substring": title contains the partial text (default)
        - "prefix": title starts with the partial text
    """

    if not partial_title:
        raise ValueError("partial_title must be a non-empty string")

    if match_mode not in {"substring", "prefix"}:
        raise ValueError("match_mode must be either 'substring' or 'prefix'")

    LOGGER.debug(
        "Searching for window with %s match on '%s'...",
        "prefix" if match_mode == "prefix" else "substring",
        partial_title,
    )
    search_term = partial_title.lower()
    found: list[WindowInfo] = []

    def _callback(hwnd, _lparam):
        if not IsWindowVisible(hwnd):
            return True

        title = _get_window_title(hwnd)
        if not title:
            return True

        haystack = title.lower()
        if (
            match_mode == "substring"
            and search_term in haystack
            or match_mode == "prefix"
            and haystack.startswith(search_term)
        ):
            left, top, right, bottom = _get_window_bounds(hwnd)
            info = WindowInfo(
                handle=int(hwnd),
                title=title,
                left=left,
                top=top,
                right=right,
                bottom=bottom,
            )
            found.append(info)
            LOGGER.info(
                "Window match: '%s' handle=%s bounds=(%d,%d,%d,%d)",
                title,
                hex(info.handle),
                left,
                top,
                right,
                bottom,
            )
            return False  # stop enumeration
        return True  # continue searching

    EnumWindows(EnumWindowsProc(_callback), 0)

    if not found:
        if log_missing:
            LOGGER.warning("No window found containing '%s'.", partial_title)
        return None

    return found[0]


def focus_window(hwnd: int) -> bool:
    """Bring the specified window to the foreground."""
    if not hwnd:
        return False
    return bool(SetForegroundWindow(ctypes.c_void_p(hwnd)))


def get_window_bounds(hwnd: int) -> tuple[int, int, int, int]:
    """Return window rectangle bounds (left, top, right, bottom)."""
    return _get_window_bounds(hwnd)


def get_primary_screen_size() -> tuple[int, int]:
    """Return the primary screen width and height."""
    width = max(0, GetSystemMetrics(SM_CXSCREEN))
    height = max(0, GetSystemMetrics(SM_CYSCREEN))
    return width, height


__all__ = [
    "WindowInfo",
    "find_window_info",
    "focus_window",
    "get_window_bounds",
    "get_primary_screen_size",
]

