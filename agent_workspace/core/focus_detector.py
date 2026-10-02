from __future__ import annotations

import ctypes
import logging
import sys
from enum import IntEnum
from typing import Optional, Tuple

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class QueryUserNotificationState(IntEnum):
    UNKNOWN = -1
    QUNS_NOT_PRESENT = 1  # Screen saver, lock screen, non-active console session
    QUNS_BUSY = 2  # Fullscreen DirectX/OpenGL app or game
    QUNS_RUNNING_D_NOT_D = 3  # Quiet hours or focus assist enabled
    QUNS_PRESENTATION_MODE = 4  # Presentation mode (PowerPoint fullscreen, etc.)
    QUNS_ACCEPTS_NOTIFICATIONS = 5  # Normal interactive desktop
    QUNS_QUIET_TIME = 6  # First hour after clean boot or quiet time
    QUNS_APP = 7  # Windows Store app in full-screen mode


class FocusStateReport(BaseModel):
    in_quiet_mode: bool = False
    state_code: int = 5
    state_name: str = "QUNS_ACCEPTS_NOTIFICATIONS"
    is_fullscreen: bool = False
    foreground_title: str = ""
    platform: str = "win32"


class WindowsFocusDetector:
    """Non-invasive focus and quiet mode detector for desktop environments.

    Uses Windows SHQueryUserNotificationState and GetForegroundWindow rect checks
    with zero third-party dependencies. Gracefully falls back on non-Windows platforms.
    """

    def __init__(self) -> None:
        self._is_windows = sys.platform == "win32"

    def query_notification_state(self) -> int:
        if not self._is_windows:
            return QueryUserNotificationState.QUNS_ACCEPTS_NOTIFICATIONS.value
        try:
            state = ctypes.c_int()
            hr = ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state))
            if hr == 0:  # S_OK
                return state.value
        except Exception as e:
            logger.debug(f"SHQueryUserNotificationState call failed: {e}")
        return QueryUserNotificationState.UNKNOWN.value

    def get_foreground_window_info(self) -> Tuple[bool, str]:
        if not self._is_windows:
            return False, ""
        try:
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return False, ""

            # Window Title
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value or ""

            # Rect Comparison to Primary Screen
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            screen_w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
            screen_h = user32.GetSystemMetrics(1)  # SM_CYSCREEN

            # Check if window covers screen and has no standard caption
            is_fullscreen = (
                rect.left <= 0
                and rect.top <= 0
                and rect.right >= screen_w
                and rect.bottom >= screen_h
            )
            return is_fullscreen, title
        except Exception as e:
            logger.debug(f"Foreground window check failed: {e}")
            return False, ""

    def get_focus_state(self) -> FocusStateReport:
        if not self._is_windows:
            return FocusStateReport(
                in_quiet_mode=False,
                state_code=QueryUserNotificationState.QUNS_ACCEPTS_NOTIFICATIONS.value,
                state_name=QueryUserNotificationState.QUNS_ACCEPTS_NOTIFICATIONS.name,
                is_fullscreen=False,
                foreground_title="",
                platform=sys.platform,
            )

        state_code = self.query_notification_state()
        state_name = "UNKNOWN"
        for member in QueryUserNotificationState:
            if member.value == state_code:
                state_name = member.name
                break

        is_fullscreen, title = self.get_foreground_window_info()

        # In Quiet Mode if Windows reports busy/presentation/do-not-disturb, or if foreground app is full screen
        in_quiet = state_code in (
            QueryUserNotificationState.QUNS_BUSY.value,
            QueryUserNotificationState.QUNS_RUNNING_D_NOT_D.value,
            QueryUserNotificationState.QUNS_PRESENTATION_MODE.value,
            QueryUserNotificationState.QUNS_QUIET_TIME.value,
        ) or is_fullscreen

        return FocusStateReport(
            in_quiet_mode=in_quiet,
            state_code=state_code,
            state_name=state_name,
            is_fullscreen=is_fullscreen,
            foreground_title=title,
            platform="win32",
        )


_global_detector: Optional[WindowsFocusDetector] = None


def get_focus_detector() -> WindowsFocusDetector:
    global _global_detector
    if _global_detector is None:
        _global_detector = WindowsFocusDetector()
    return _global_detector
