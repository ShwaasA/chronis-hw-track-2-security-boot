import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from power_management_daemon import PowerManagementDaemon, PowerState


@pytest.mark.parametrize("voltage,expected_state", [
    (4.20, PowerState.FULL_ACTIVE),      # 100%
    (3.80, PowerState.CONSERVATION),     # 40%
    (3.70, PowerState.CRITICAL),         # 10%
    (3.40, PowerState.EMERGENCY),        # 0%
])
def test_power_state_thresholds(voltage, expected_state):
    daemon = PowerManagementDaemon()
    result = daemon.evaluate(voltage)
    assert result["state"] == expected_state


def test_full_active_has_no_restrictions():
    daemon = PowerManagementDaemon()
    result = daemon.evaluate(4.20)
    assert result["restrictions"]["camera_max_level"] == 5
    assert result["restrictions"]["sync_enabled"] is True


def test_conservation_caps_camera_at_l4_and_led_at_50pct():
    daemon = PowerManagementDaemon()
    result = daemon.evaluate(3.80)  # 40% -> Conservation
    assert result["restrictions"]["camera_max_level"] == 4
    assert result["restrictions"]["led_max_brightness"] == 50


def test_conservation_notifies_phone_once_on_entry_only():
    daemon = PowerManagementDaemon()
    daemon.evaluate(4.20)                       # Full Active
    r1 = daemon.evaluate(3.80)                   # enters Conservation (40%) -> notify
    assert daemon.phone_notified_conservation_entry is True
    r2 = daemon.evaluate(3.79)                   # still Conservation (~40%) -> no re-notify
    assert daemon.phone_notified_conservation_entry is False


def test_critical_caps_camera_at_l3_and_disables_sync():
    daemon = PowerManagementDaemon()
    result = daemon.evaluate(3.70)  # 10% -> Critical
    assert result["restrictions"]["camera_max_level"] == 3
    assert result["restrictions"]["sync_enabled"] is False


def test_emergency_state_camera_off_and_wifi_off():
    daemon = PowerManagementDaemon()
    result = daemon.evaluate(3.30)
    assert result["restrictions"]["camera_max_level"] == 0
    assert result["restrictions"]["wifi_off"] is True
    assert result["restrictions"]["bt_beacon_only"] is True


def test_ceiling_conflict_lower_value_always_wins():
    """Day 5 integration rule, testable in isolation right now:
    state machine wants L5, battery is Critical (caps at L3) -> L3 wins."""
    daemon = PowerManagementDaemon()
    result_level = daemon.apply_ceiling(state_machine_level=5, voltage=3.70)
    assert result_level == 3


def test_ceiling_no_conflict_when_battery_is_healthy():
    daemon = PowerManagementDaemon()
    result_level = daemon.apply_ceiling(state_machine_level=2, voltage=4.20)
    assert result_level == 2  # state machine's own level wins, no ceiling hit


def test_charge_cycle_counting_flags_replacement_at_500():
    daemon = PowerManagementDaemon()
    for _ in range(500):
        daemon.record_charge_delta(1.0)
    assert daemon.needs_replacement_soon() is True


def test_below_500_cycles_no_flag_yet():
    daemon = PowerManagementDaemon()
    for _ in range(499):
        daemon.record_charge_delta(1.0)
    assert daemon.needs_replacement_soon() is False


def test_charging_detection_sets_distinct_state():
    daemon = PowerManagementDaemon()
    assert daemon.is_charging is False
    daemon.set_charging(True)
    assert daemon.is_charging is True


def test_daily_report_structure():
    daemon = PowerManagementDaemon()
    daemon.record_charge_delta(0.3)
    report = daemon.daily_report("2026-07-11")
    assert report["date"] == "2026-07-11"
    assert "active_seconds" in report
    assert report["partial_charge_cycles"] == 0.3
