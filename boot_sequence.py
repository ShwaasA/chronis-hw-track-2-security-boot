"""
Boot Sequence Manager — Track HW-2, Day 2
Enforces the exact boot order and the failure-handling table from the spec.

NOTE on power_rails and clock_sync: the spec's failure table only lists 9
components (security chip through WiFi). power_rails and clock_sync appear
in the boot ORDER but have no explicit row in the failure table. Treated
here as HALT-on-failure by default (power rails failing means nothing else
can run; clock_sync failing breaks date-based DSK derivation in the
encryption daemon) — flagged in FAILURE_BEHAVIOR_UNSPECIFIED below as a
gap to confirm with the team, not silently assumed.
"""
from enum import Enum


BOOT_ORDER = [
    "power_rails", "security_chip", "clock_sync", "storage_mount",
    "motion_sensor", "heart_rate_sensor", "camera", "display",
    "status_led", "bluetooth", "wifi",
]

# Components in BOOT_ORDER with no explicit row in the spec's failure table.
FAILURE_BEHAVIOR_UNSPECIFIED = {"power_rails", "clock_sync"}


class BootOutcome(Enum):
    HALT = "SYSTEM HALT"
    DEGRADED = "DEGRADED BOOT"
    CONTINUE = "CONTINUE NORMALLY"


FAILURE_BEHAVIOR = {
    "security_chip": (BootOutcome.HALT,
        "Never boot without encryption available. Alert phone."),
    "storage_mount": (BootOutcome.HALT,
        "No data capture allowed without storage. Alert phone."),
    "motion_sensor": (BootOutcome.DEGRADED,
        "Continue, using audio-only inputs for decision-making. Notify phone."),
    "heart_rate_sensor": (BootOutcome.DEGRADED,
        "Continue, without heart-rate-based features. Notify phone."),
    "camera": (BootOutcome.DEGRADED,
        "Audio-only boot — continue without video. Notify phone."),
    "display": (BootOutcome.CONTINUE,
        "Continue normally. Status LED takes over as status indicator."),
    "status_led": (BootOutcome.CONTINUE,
        "Continue normally. Log the failure only."),
    "bluetooth": (BootOutcome.CONTINUE,
        "Continue normally. Fall back to WiFi for syncing. Log it. Display shows icon."),
    "wifi": (BootOutcome.CONTINUE,
        "Continue normally. Store data locally until connectivity returns. Log it."),
}


class BootHaltException(Exception):
    pass


class BootSequenceManager:
    def __init__(self, mock_hal):
        """mock_hal: object exposing .check(component_name) -> bool (True=OK)."""
        self.hal = mock_hal
        self.log = []

    def boot(self):
        self.log = []
        for component in BOOT_ORDER:
            ok = self.hal.check(component)
            if ok:
                self.log.append((component, "OK"))
                continue

            if component in FAILURE_BEHAVIOR_UNSPECIFIED:
                self.log.append(
                    (component, "FAIL -> SYSTEM HALT (unspecified in table, "
                                 "conservative default — confirm with team)")
                )
                raise BootHaltException(
                    f"{component} failed — no explicit spec row, defaulting to HALT"
                )

            outcome, action = FAILURE_BEHAVIOR[component]
            self.log.append((component, f"FAIL -> {outcome.value}: {action}"))
            if outcome == BootOutcome.HALT:
                raise BootHaltException(f"{component} failed: {action}")

        return self.log
