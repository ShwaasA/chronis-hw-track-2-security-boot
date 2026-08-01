import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from watchdog import Watchdog, SystemHaltException, DaemonRestartSignal


def test_encryption_daemon_failure_halts_system():
    wd = Watchdog()
    with pytest.raises(SystemHaltException):
        wd.report_failure("encryption_daemon")


@pytest.mark.parametrize("daemon", [
    "camera_daemon", "audio_daemon", "motion_daemon",
    "heart_rate_daemon", "ble_daemon", "storage_daemon",
])
def test_other_daemon_failure_triggers_restart_not_halt(daemon):
    wd = Watchdog()
    with pytest.raises(DaemonRestartSignal) as exc_info:
        wd.report_failure(daemon)
    assert exc_info.value.daemon_name == daemon


def test_failure_is_logged_in_daemon_status():
    wd = Watchdog()
    with pytest.raises(DaemonRestartSignal):
        wd.report_failure("camera_daemon")
    assert wd.daemon_status["camera_daemon"] == "failed"
