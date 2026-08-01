import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from boot_sequence import BootSequenceManager, BootHaltException, BOOT_ORDER


class FakeHAL:
    """Mock hardware layer: OK for everything except one configured failure."""
    def __init__(self, fail_component=None):
        self.fail_component = fail_component

    def check(self, component):
        return component != self.fail_component


# --- One test per row in the failure table (per the Day 2 deliverable spec) ---

def test_security_chip_failure_halts_system():
    manager = BootSequenceManager(FakeHAL(fail_component="security_chip"))
    with pytest.raises(BootHaltException):
        manager.boot()


def test_storage_mount_failure_halts_system():
    manager = BootSequenceManager(FakeHAL(fail_component="storage_mount"))
    with pytest.raises(BootHaltException):
        manager.boot()


def test_motion_sensor_failure_degrades_boot_but_continues():
    manager = BootSequenceManager(FakeHAL(fail_component="motion_sensor"))
    log = manager.boot()  # must NOT raise
    assert ("motion_sensor", "FAIL -> DEGRADED BOOT: Continue, using audio-only "
            "inputs for decision-making. Notify phone.") in log


def test_heart_rate_sensor_failure_degrades_boot_but_continues():
    manager = BootSequenceManager(FakeHAL(fail_component="heart_rate_sensor"))
    log = manager.boot()
    statuses = dict(log)
    assert "DEGRADED BOOT" in statuses["heart_rate_sensor"]


def test_camera_failure_gives_audio_only_boot():
    manager = BootSequenceManager(FakeHAL(fail_component="camera"))
    log = manager.boot()
    statuses = dict(log)
    assert "Audio-only boot" in statuses["camera"]


def test_display_failure_continues_normally():
    manager = BootSequenceManager(FakeHAL(fail_component="display"))
    log = manager.boot()
    statuses = dict(log)
    assert "CONTINUE NORMALLY" in statuses["display"]


def test_status_led_failure_logs_only():
    manager = BootSequenceManager(FakeHAL(fail_component="status_led"))
    log = manager.boot()
    statuses = dict(log)
    assert "Log the failure only" in statuses["status_led"]


def test_bluetooth_failure_falls_back_to_wifi():
    manager = BootSequenceManager(FakeHAL(fail_component="bluetooth"))
    log = manager.boot()
    statuses = dict(log)
    assert "Fall back to WiFi" in statuses["bluetooth"]


def test_wifi_failure_stores_locally():
    manager = BootSequenceManager(FakeHAL(fail_component="wifi"))
    log = manager.boot()
    statuses = dict(log)
    assert "Store data locally" in statuses["wifi"]


# --- Boot order + success path ---

def test_full_success_boots_everything_in_exact_order():
    manager = BootSequenceManager(FakeHAL(fail_component=None))
    log = manager.boot()
    assert [c for c, _ in log] == BOOT_ORDER
    assert all(status == "OK" for _, status in log)


def test_power_rails_failure_halts_as_conservative_default():
    manager = BootSequenceManager(FakeHAL(fail_component="power_rails"))
    with pytest.raises(BootHaltException):
        manager.boot()
