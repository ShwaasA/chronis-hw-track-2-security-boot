"""
Consolidation — Track HW-2, Day 4
Runs the full test suite, captures results, and writes
security-boot-report.md combining: encryption daemon results, boot
failure matrix results, watchdog results, power/thermal projection,
enclosure status, and an explicit list of real-hardware-only gaps.
"""
import subprocess
import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from power_thermal_estimate import estimate_runtime_hours, estimate_draw_ma, LEVEL_DUTY_CYCLE, BATTERY_CAPACITY_MAH


def run_tests():
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/", "-v", "--tb=no"],
        cwd=os.path.dirname(__file__),
        capture_output=True, text=True,
    )
    return result.stdout, result.returncode


def build_power_table():
    rows = []
    for level in LEVEL_DUTY_CYCLE:
        draw = round(estimate_draw_ma(level), 1)
        hours = estimate_runtime_hours(level)
        rows.append(f"| {level} | ~{draw} mA | ~{hours} h |")
    return "\n".join(rows)


def main():
    test_output, returncode = run_tests()
    status = "ALL PASSING" if returncode == 0 else "FAILURES PRESENT — DO NOT PRESENT AS DONE"
    today = datetime.date.today().isoformat()

    report = f"""# Security & Boot Report — Track HW-2

Generated: {today}
Test suite status: **{status}**

## 1. Encryption Daemon (Day 1)
Full key hierarchy implemented: DIK (generated once, never leaves secure
storage), DSK (derived daily from DIK + date, never persisted), UPK
(wraps outer encryption layer), Server Transport Key (fresh per upload
session). `write_to_storage()` structurally rejects anything that isn't
an `EncryptedRecord` — Rule 1 is enforced at the type level, not by
convention.

## 2. Boot Sequence + Failure Handling (Day 2)
Boot order implemented exactly as specified. One automated test per
failure mode in the spec table, all passing against the mock HAL.
**Open gap:** `power_rails` and `clock_sync` have no explicit row in the
spec's failure table — currently defaulted to HALT-on-failure as a
conservative choice. Confirm this is the intended behavior with the team.

## 3. Watchdog (Day 3)
Confirmed: encryption daemon failure -> full system HALT (not a restart).
All other daemon failures -> restart of just that daemon.

## 4. Power Management Daemon (Day 3)
All four power states (Full Active, Conservation, Critical, Emergency)
implemented and tested against mock battery voltage readings, including
the notify-once-on-entry behavior for Conservation and the
ceiling-conflict rule (lower of state-machine level vs. power-state
ceiling always wins — this is a preview of the Day 5 cross-track test).
Charge-cycle counting flags "replacement may be needed soon" at 500
cycles. Daily power report structure implemented.

## 5. Power & Thermal Projection (Day 3) — PLANNING ESTIMATE ONLY
**Not measured, not verified.** Pulled from public datasheets and
estimated duty cycles per capture-intensity level. Battery capacity
placeholder: {BATTERY_CAPACITY_MAH}mAh — update once a real cell is chosen.

| Level | Estimated draw | Estimated runtime |
|---|---|---|
{build_power_table()}

Thermal ceiling: not modeled — needs a real thermal simulation or
datasheet junction-temperature figures once components are locked.

## 6. Enclosure (Day 3)
First-pass CAD skeleton and dimension-input checklist in
`enclosure/enclosure_notes.md`. Datasheet-dimensions-only — see the
explicit gap list below.

## 7. Full Test Suite Output
```
{test_output}
```

## 8. Explicit List of What Needs Real-Hardware Confirmation
- Actual I2C/communication-bus address conflicts between motion sensor,
  heart-rate sensor, and any other bus-sharing components — cannot be
  caught in simulation.
- Real thermal behavior under sustained L4/L5 load.
- Real physical fit and manufacturing tolerances for the enclosure —
  current CAD model checks bounding boxes only.
- Real battery discharge curve — current model uses a generic lithium
  curve as a stand-in.
- `power_rails` / `clock_sync` failure behavior — currently a conservative
  default (HALT), not an explicit spec decision. Confirm with the team.
- Real component current draw at each capture-intensity level — current
  numbers are datasheet typical-case figures, not measured under this
  specific firmware's actual duty cycle.
"""

    out_path = os.path.join(os.path.dirname(__file__), "security-boot-report.md")
    with open(out_path, "w") as f:
        f.write(report)

    print(f"Report written to: {out_path}")
    print(f"Test suite status: {status}")
    return returncode


if __name__ == "__main__":
    sys.exit(main())
