"""
Power Management Daemon — Track HW-2, Day 3
Converts a mock ADC voltage reading into battery %, enforces the four
power states and their restrictions, tracks charge cycles (Coulomb
counting) for battery health, and produces a daily power report.

This is deliberately separate from power_thermal_estimate.py: that file
answers "will the battery survive a day" (a static planning number from
datasheets). This file answers "does the device correctly change its own
behavior in real time as the battery drains" (the actual runtime logic).
"""
from enum import Enum


# Generic Li-ion discharge curve (voltage -> %). Stand-in for the real
# battery's actual discharge curve, which isn't known until hardware
# is selected and characterized.
VOLTAGE_TO_PERCENT = [
    (4.20, 100), (4.06, 90), (3.98, 80), (3.92, 70), (3.87, 60),
    (3.82, 50), (3.79, 40), (3.77, 30), (3.74, 20), (3.68, 10),
    (3.45, 5), (3.00, 0),
]


def voltage_to_percent(voltage: float) -> int:
    for v, pct in VOLTAGE_TO_PERCENT:
        if voltage >= v:
            return pct
    return 0


class PowerState(Enum):
    FULL_ACTIVE = "Full Active"
    CONSERVATION = "Conservation"
    CRITICAL = "Critical"
    EMERGENCY = "Emergency"


RESTRICTIONS = {
    PowerState.FULL_ACTIVE: {
        "camera_max_level": 5, "led_max_brightness": 100,
        "audio_max_quality_level": 5, "sync_enabled": True,
    },
    PowerState.CONSERVATION: {
        "camera_max_level": 4, "led_max_brightness": 50,
        "audio_max_quality_level": 4, "sync_enabled": True, "sync_throttled": True,
    },
    PowerState.CRITICAL: {
        "camera_max_level": 3, "led_max_brightness": 20,
        "audio_max_quality_level": 3, "sync_enabled": False,
    },
    PowerState.EMERGENCY: {
        "camera_max_level": 0, "led_max_brightness": 0,
        "audio_max_quality_level": 0, "sync_enabled": False,
        "bt_beacon_only": True, "wifi_off": True,
    },
}


def state_for_percent(pct: int) -> PowerState:
    if pct > 40:
        return PowerState.FULL_ACTIVE
    if pct >= 20:
        return PowerState.CONSERVATION
    if pct >= 5:
        return PowerState.CRITICAL
    return PowerState.EMERGENCY


class PowerManagementDaemon:
    def __init__(self):
        self.charge_cycles = 0.0          # Coulomb-counted, fractional
        self.is_charging = False
        self._last_state = None
        self.phone_notified_conservation_entry = False
        self.daily_active_seconds = {
            "camera": 0, "audio": 0, "motion": 0,
            "heart_rate": 0, "bluetooth": 0, "wifi": 0,
        }
        self.daily_energy_estimate_mah = 0.0

    def evaluate(self, voltage: float) -> dict:
        pct = voltage_to_percent(voltage)
        state = state_for_percent(pct)
        restrictions = RESTRICTIONS[state]

        # Phone gets notified ONCE, only on the exact call that transitions
        # into Conservation — must reset False on every other call, including
        # subsequent calls that are still in Conservation.
        if state == PowerState.CONSERVATION:
            self.phone_notified_conservation_entry = (self._last_state != PowerState.CONSERVATION)
        else:
            self.phone_notified_conservation_entry = False

        self._last_state = state
        return {"battery_percent": pct, "state": state, "restrictions": restrictions}

    def apply_ceiling(self, state_machine_level: int, voltage: float) -> int:
        """
        Day 5 cross-track rule: the LOWER of (capture-intensity level from
        HW-1's state machine, this daemon's camera ceiling) always wins.
        """
        power_ceiling = RESTRICTIONS[state_for_percent(voltage_to_percent(voltage))]["camera_max_level"]
        return min(state_machine_level, power_ceiling)

    def set_charging(self, charging_current_detected: bool):
        self.is_charging = charging_current_detected

    def record_charge_delta(self, fraction_of_full_cycle: float):
        """Coulomb counting: accumulate fractional charge/discharge cycles."""
        self.charge_cycles += abs(fraction_of_full_cycle)

    def needs_replacement_soon(self) -> bool:
        return self.charge_cycles >= 500

    def daily_report(self, date_str: str) -> dict:
        return {
            "date": date_str,
            "active_seconds": dict(self.daily_active_seconds),
            "partial_charge_cycles": round(self.charge_cycles, 3),
            "estimated_power_consumed_mah": self.daily_energy_estimate_mah,
        }
