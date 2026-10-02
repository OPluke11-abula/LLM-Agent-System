from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DeviceKind = Literal["mouse", "keyboard", "headset", "controller", "bluetooth", "other"]


class PeripheralDevice(BaseModel):
    name: str
    level: Optional[int] = None
    charging: bool = False
    online: bool = True
    kind: DeviceKind = "other"
    seconds_left: Optional[int] = None
    text: str = ""


class PeripheralTelemetryReport(BaseModel):
    available: bool = False
    stale: bool = False
    source: str = "HaloBattery"
    updated_unix: Optional[float] = None
    devices: List[PeripheralDevice] = Field(default_factory=list)
    low_battery_alerts: List[str] = Field(default_factory=list)


def resolve_default_status_file_path() -> Optional[Path]:
    """Resolve the default status file path for HaloBattery telemetry."""
    custom_path = os.environ.get("HALO_BATTERY_STATUS_PATH")
    if custom_path:
        return Path(custom_path)

    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "HaloBattery" / "status.json"

    # Fallback to user home directory if APPDATA not present
    return Path.home() / ".config" / "HaloBattery" / "status.json"


class PeripheralTelemetryProvider:
    """Non-invasive provider for workstation peripheral battery and status telemetry.

    Adheres to PAP Single Responsibility: reads external JSON status without direct
    USB/HID driver bindings. Gracefully falls back when HaloBattery is inactive.
    """

    def __init__(self, status_file: Optional[Path] = None, stale_threshold_seconds: float = 300.0) -> None:
        self.status_file = status_file or resolve_default_status_file_path()
        self.stale_threshold_seconds = stale_threshold_seconds
        self._cached_report: Optional[PeripheralTelemetryReport] = None

    def get_telemetry(self) -> PeripheralTelemetryReport:
        if not self.status_file or not self.status_file.is_file():
            return PeripheralTelemetryReport(
                available=False,
                stale=False,
                devices=[],
                low_battery_alerts=[],
            )

        try:
            with open(self.status_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.debug(f"Peripheral telemetry file read skipped or incomplete: {e}")
            if self._cached_report is not None:
                # Return cached report marked as stale
                cached = self._cached_report.model_copy(deep=True)
                cached.stale = True
                return cached
            return PeripheralTelemetryReport(available=False, stale=True)

        now = time.time()
        devices_raw = []
        updated_unix: Optional[float] = None
        running = True

        if isinstance(raw_data, list):
            devices_raw = raw_data
        elif isinstance(raw_data, dict):
            devices_raw = raw_data.get("devices", [])
            updated_unix = raw_data.get("updated_unix")
            running = raw_data.get("running", True)
        else:
            return PeripheralTelemetryReport(available=False, stale=True)

        # Check staleness
        is_stale = False
        if not running:
            is_stale = True
        elif updated_unix is not None and (now - updated_unix > self.stale_threshold_seconds):
            is_stale = True

        parsed_devices: List[PeripheralDevice] = []
        alerts: List[str] = []

        for d in devices_raw:
            if not isinstance(d, dict):
                continue
            kind_str = str(d.get("kind", "other")).lower()
            if kind_str not in ("mouse", "keyboard", "headset", "controller", "bluetooth"):
                kind_str = "other"

            level_val = d.get("level")
            level_int = int(level_val) if isinstance(level_val, (int, float)) else None

            device = PeripheralDevice(
                name=str(d.get("name", "Unknown Device")),
                level=level_int,
                charging=bool(d.get("charging", False)),
                online=bool(d.get("online", True)),
                kind=kind_str,  # type: ignore[arg-type]
                seconds_left=d.get("seconds_left"),
                text=str(d.get("text", "")),
            )
            parsed_devices.append(device)

            # Detect low battery alert (threshold <= 15%, not charging, device is online)
            if device.online and not device.charging and device.level is not None and device.level <= 15:
                alerts.append(f"{device.name} 電量僅剩 {device.level}%，建議及時充電")

        report = PeripheralTelemetryReport(
            available=True,
            stale=is_stale,
            updated_unix=updated_unix,
            devices=parsed_devices,
            low_battery_alerts=alerts,
        )
        self._cached_report = report
        return report


_global_provider: Optional[PeripheralTelemetryProvider] = None


def get_peripheral_provider() -> PeripheralTelemetryProvider:
    global _global_provider
    if _global_provider is None:
        _global_provider = PeripheralTelemetryProvider()
    return _global_provider
