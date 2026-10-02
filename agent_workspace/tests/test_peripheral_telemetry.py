from __future__ import annotations

import json
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from agent_workspace.api import app
from agent_workspace.core.peripheral_telemetry import (
    PeripheralDevice,
    PeripheralTelemetryProvider,
    PeripheralTelemetryReport,
)


def test_peripheral_telemetry_missing_file(tmp_path: Path):
    non_existent = tmp_path / "non_existent_status.json"
    provider = PeripheralTelemetryProvider(status_file=non_existent)
    report = provider.get_telemetry()

    assert isinstance(report, PeripheralTelemetryReport)
    assert report.available is False
    assert report.stale is False
    assert len(report.devices) == 0
    assert len(report.low_battery_alerts) == 0


def test_peripheral_telemetry_valid_list_format(tmp_path: Path):
    status_file = tmp_path / "status.json"
    data = [
        {
            "name": "Logitech G502 LIGHTSPEED",
            "level": 85,
            "charging": False,
            "online": True,
            "kind": "mouse",
            "seconds_left": 36000,
            "text": "Logitech G502 LIGHTSPEED: 85%",
        },
        {
            "name": "SteelSeries Arctis Nova 7",
            "level": 12,
            "charging": False,
            "online": True,
            "kind": "headset",
            "seconds_left": 1800,
            "text": "SteelSeries Arctis Nova 7: 12%",
        },
        {
            "name": "DualSense Wireless Controller",
            "level": 10,
            "charging": True,
            "online": True,
            "kind": "controller",
            "text": "DualSense: 10% (charging)",
        },
    ]
    status_file.write_text(json.dumps(data), encoding="utf-8")

    provider = PeripheralTelemetryProvider(status_file=status_file)
    report = provider.get_telemetry()

    assert report.available is True
    assert report.stale is False
    assert len(report.devices) == 3

    mouse = report.devices[0]
    assert mouse.name == "Logitech G502 LIGHTSPEED"
    assert mouse.kind == "mouse"
    assert mouse.level == 85
    assert mouse.charging is False

    headset = report.devices[1]
    assert headset.name == "SteelSeries Arctis Nova 7"
    assert headset.kind == "headset"
    assert headset.level == 12

    # Controller is <= 15% but charging, so it should NOT alert
    # Headset is 12%, not charging, online -> should trigger alert!
    assert len(report.low_battery_alerts) == 1
    assert "SteelSeries Arctis Nova 7" in report.low_battery_alerts[0]
    assert "12%" in report.low_battery_alerts[0]


def test_peripheral_telemetry_valid_dict_format(tmp_path: Path):
    status_file = tmp_path / "status.json"
    now = time.time()
    data = {
        "running": True,
        "updated_unix": now,
        "devices": [
            {
                "name": "Razer BlackShark V2 Pro",
                "level": 55,
                "charging": False,
                "online": True,
                "kind": "headset",
            }
        ],
    }
    status_file.write_text(json.dumps(data), encoding="utf-8")

    provider = PeripheralTelemetryProvider(status_file=status_file, stale_threshold_seconds=60.0)
    report = provider.get_telemetry()

    assert report.available is True
    assert report.stale is False
    assert len(report.devices) == 1
    assert report.devices[0].name == "Razer BlackShark V2 Pro"
    assert report.devices[0].level == 55


def test_peripheral_telemetry_stale_detection(tmp_path: Path):
    status_file = tmp_path / "status.json"
    # updated 400 seconds ago, threshold is 60 seconds
    past_time = time.time() - 400
    data = {
        "running": True,
        "updated_unix": past_time,
        "devices": [
            {
                "name": "WLmouse Beast X",
                "level": 90,
                "charging": False,
                "online": True,
                "kind": "mouse",
            }
        ],
    }
    status_file.write_text(json.dumps(data), encoding="utf-8")

    provider = PeripheralTelemetryProvider(status_file=status_file, stale_threshold_seconds=60.0)
    report = provider.get_telemetry()

    assert report.available is True
    assert report.stale is True


def test_peripheral_telemetry_not_running(tmp_path: Path):
    status_file = tmp_path / "status.json"
    data = {
        "running": False,
        "updated_unix": time.time(),
        "devices": [],
    }
    status_file.write_text(json.dumps(data), encoding="utf-8")

    provider = PeripheralTelemetryProvider(status_file=status_file)
    report = provider.get_telemetry()

    assert report.available is True
    assert report.stale is True


def test_peripheral_telemetry_corrupted_json(tmp_path: Path):
    status_file = tmp_path / "status.json"
    status_file.write_text("{ corrupt json: ... [", encoding="utf-8")

    provider = PeripheralTelemetryProvider(status_file=status_file)
    report = provider.get_telemetry()

    assert report.available is False
    assert report.stale is True


def test_system_peripherals_endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    status_file = tmp_path / "status.json"
    status_file.write_text(
        json.dumps(
            [
                {
                    "name": "8BitDo Ultimate Controller",
                    "level": 70,
                    "charging": True,
                    "online": True,
                    "kind": "controller",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HALO_BATTERY_STATUS_PATH", str(status_file))

    # Re-instantiate or ensure provider picks up path
    from agent_workspace.core import peripheral_telemetry

    monkeypatch.setattr(
        peripheral_telemetry,
        "_global_provider",
        PeripheralTelemetryProvider(status_file=status_file),
    )

    client = TestClient(app)
    response = client.get("/v1/system/peripherals")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert len(body["devices"]) == 1
    assert body["devices"][0]["name"] == "8BitDo Ultimate Controller"
    assert body["devices"][0]["charging"] is True
