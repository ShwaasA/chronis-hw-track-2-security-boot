# Security & Boot Report — Track HW-2

Generated: 2026-07-12
Test suite status: **ALL PASSING**

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
placeholder: 300mAh — update once a real cell is chosen.

| Level | Estimated draw | Estimated runtime |
|---|---|---|
| L0 | ~206.0 mA | ~1.46 h |
| L1 | ~231.7 mA | ~1.29 h |
| L2 | ~271.1 mA | ~1.11 h |
| L3 | ~360.1 mA | ~0.83 h |
| L4 | ~437.0 mA | ~0.69 h |
| L5 | ~471.9 mA | ~0.64 h |

Thermal ceiling: not modeled — needs a real thermal simulation or
datasheet junction-temperature figures once components are locked.

## 6. Enclosure (Day 3)
First-pass CAD skeleton and dimension-input checklist in
`enclosure/enclosure_notes.md`. Datasheet-dimensions-only — see the
explicit gap list below.

## 7. Full Test Suite Output
```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /home/claude/chronis-aic/hw-track-2-security-boot
collecting ... collected 44 items

tests/test_boot_sequence.py::test_security_chip_failure_halts_system PASSED [  2%]
tests/test_boot_sequence.py::test_storage_mount_failure_halts_system PASSED [  4%]
tests/test_boot_sequence.py::test_motion_sensor_failure_degrades_boot_but_continues PASSED [  6%]
tests/test_boot_sequence.py::test_heart_rate_sensor_failure_degrades_boot_but_continues PASSED [  9%]
tests/test_boot_sequence.py::test_camera_failure_gives_audio_only_boot PASSED [ 11%]
tests/test_boot_sequence.py::test_display_failure_continues_normally PASSED [ 13%]
tests/test_boot_sequence.py::test_status_led_failure_logs_only PASSED    [ 15%]
tests/test_boot_sequence.py::test_bluetooth_failure_falls_back_to_wifi PASSED [ 18%]
tests/test_boot_sequence.py::test_wifi_failure_stores_locally PASSED     [ 20%]
tests/test_boot_sequence.py::test_full_success_boots_everything_in_exact_order PASSED [ 22%]
tests/test_boot_sequence.py::test_power_rails_failure_halts_as_conservative_default PASSED [ 25%]
tests/test_encryption_daemon.py::test_encrypt_produces_encrypted_record PASSED [ 27%]
tests/test_encryption_daemon.py::test_write_to_storage_accepts_encrypted_record PASSED [ 29%]
tests/test_encryption_daemon.py::test_write_to_storage_rejects_raw_bytes PASSED [ 31%]
tests/test_encryption_daemon.py::test_write_to_storage_rejects_plain_string PASSED [ 34%]
tests/test_encryption_daemon.py::test_write_to_storage_rejects_dict PASSED [ 36%]
tests/test_encryption_daemon.py::test_dsk_is_deterministic_within_same_day PASSED [ 38%]
tests/test_encryption_daemon.py::test_dsk_differs_across_days PASSED     [ 40%]
tests/test_encryption_daemon.py::test_dsk_never_persisted_only_cached_in_memory PASSED [ 43%]
tests/test_encryption_daemon.py::test_server_transport_key_is_fresh_each_session PASSED [ 45%]
tests/test_encryption_daemon.py::test_decrypt_roundtrip_via_same_daemon_keys PASSED [ 47%]
tests/test_power_management.py::test_power_state_thresholds[4.2-PowerState.FULL_ACTIVE] PASSED [ 50%]
tests/test_power_management.py::test_power_state_thresholds[3.8-PowerState.CONSERVATION] PASSED [ 52%]
tests/test_power_management.py::test_power_state_thresholds[3.7-PowerState.CRITICAL] PASSED [ 54%]
tests/test_power_management.py::test_power_state_thresholds[3.4-PowerState.EMERGENCY] PASSED [ 56%]
tests/test_power_management.py::test_full_active_has_no_restrictions PASSED [ 59%]
tests/test_power_management.py::test_conservation_caps_camera_at_l4_and_led_at_50pct PASSED [ 61%]
tests/test_power_management.py::test_conservation_notifies_phone_once_on_entry_only PASSED [ 63%]
tests/test_power_management.py::test_critical_caps_camera_at_l3_and_disables_sync PASSED [ 65%]
tests/test_power_management.py::test_emergency_state_camera_off_and_wifi_off PASSED [ 68%]
tests/test_power_management.py::test_ceiling_conflict_lower_value_always_wins PASSED [ 70%]
tests/test_power_management.py::test_ceiling_no_conflict_when_battery_is_healthy PASSED [ 72%]
tests/test_power_management.py::test_charge_cycle_counting_flags_replacement_at_500 PASSED [ 75%]
tests/test_power_management.py::test_below_500_cycles_no_flag_yet PASSED [ 77%]
tests/test_power_management.py::test_charging_detection_sets_distinct_state PASSED [ 79%]
tests/test_power_management.py::test_daily_report_structure PASSED       [ 81%]
tests/test_watchdog.py::test_encryption_daemon_failure_halts_system PASSED [ 84%]
tests/test_watchdog.py::test_other_daemon_failure_triggers_restart_not_halt[camera_daemon] PASSED [ 86%]
tests/test_watchdog.py::test_other_daemon_failure_triggers_restart_not_halt[audio_daemon] PASSED [ 88%]
tests/test_watchdog.py::test_other_daemon_failure_triggers_restart_not_halt[motion_daemon] PASSED [ 90%]
tests/test_watchdog.py::test_other_daemon_failure_triggers_restart_not_halt[heart_rate_daemon] PASSED [ 93%]
tests/test_watchdog.py::test_other_daemon_failure_triggers_restart_not_halt[ble_daemon] PASSED [ 95%]
tests/test_watchdog.py::test_other_daemon_failure_triggers_restart_not_halt[storage_daemon] PASSED [ 97%]
tests/test_watchdog.py::test_failure_is_logged_in_daemon_status PASSED   [100%]

============================== 44 passed in 0.11s ==============================

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
