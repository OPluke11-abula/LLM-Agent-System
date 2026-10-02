from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agent_workspace.api import app
from agent_workspace.core.focus_detector import (
    FocusStateReport,
    QueryUserNotificationState,
    WindowsFocusDetector,
)


def test_focus_detector_real_query():
    detector = WindowsFocusDetector()
    report = detector.get_focus_state()

    assert isinstance(report, FocusStateReport)
    assert isinstance(report.in_quiet_mode, bool)
    assert isinstance(report.is_fullscreen, bool)
    assert report.state_code in [m.value for m in QueryUserNotificationState]


def test_focus_detector_mock_busy_game(monkeypatch: pytest.MonkeyPatch):
    detector = WindowsFocusDetector()
    monkeypatch.setattr(
        detector,
        "query_notification_state",
        lambda: QueryUserNotificationState.QUNS_BUSY.value,
    )
    monkeypatch.setattr(
        detector,
        "get_foreground_window_info",
        lambda: (True, "Cyberpunk 2077"),
    )

    report = detector.get_focus_state()
    assert report.in_quiet_mode is True
    assert report.state_code == 2
    assert report.state_name == "QUNS_BUSY"
    assert report.is_fullscreen is True
    assert report.foreground_title == "Cyberpunk 2077"


def test_focus_detector_mock_presentation_mode(monkeypatch: pytest.MonkeyPatch):
    detector = WindowsFocusDetector()
    monkeypatch.setattr(
        detector,
        "query_notification_state",
        lambda: QueryUserNotificationState.QUNS_PRESENTATION_MODE.value,
    )
    monkeypatch.setattr(
        detector,
        "get_foreground_window_info",
        lambda: (False, "PowerPoint Slide Show"),
    )

    report = detector.get_focus_state()
    assert report.in_quiet_mode is True
    assert report.state_code == 4
    assert report.state_name == "QUNS_PRESENTATION_MODE"


def test_focus_detector_mock_normal_desktop(monkeypatch: pytest.MonkeyPatch):
    detector = WindowsFocusDetector()
    monkeypatch.setattr(
        detector,
        "query_notification_state",
        lambda: QueryUserNotificationState.QUNS_ACCEPTS_NOTIFICATIONS.value,
    )
    monkeypatch.setattr(
        detector,
        "get_foreground_window_info",
        lambda: (False, "Visual Studio Code"),
    )

    report = detector.get_focus_state()
    assert report.in_quiet_mode is False
    assert report.state_code == 5
    assert report.state_name == "QUNS_ACCEPTS_NOTIFICATIONS"
    assert report.is_fullscreen is False


def test_focus_detector_non_windows_fallback(monkeypatch: pytest.MonkeyPatch):
    detector = WindowsFocusDetector()
    monkeypatch.setattr(detector, "_is_windows", False)

    report = detector.get_focus_state()
    assert report.in_quiet_mode is False
    assert report.is_fullscreen is False
    assert report.state_name == "QUNS_ACCEPTS_NOTIFICATIONS"


def test_system_focus_state_endpoint():
    client = TestClient(app)
    response = client.get("/v1/system/focus-state")

    assert response.status_code == 200
    body = response.json()
    assert "in_quiet_mode" in body
    assert "state_code" in body
    assert "is_fullscreen" in body
    assert "state_name" in body
