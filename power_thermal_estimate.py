"""
Power & Thermal Estimate — Track HW-2, Day 3
PLANNING ESTIMATE ONLY. Not measured, not verified. Pulled from public
component datasheets and reasonable duty-cycle assumptions per
capture-intensity level. Re-check every number here once real hardware
is in hand — this script exists to give the team a directional sense of
"will the battery survive a day," not a guaranteed spec.

Replace the numbers below with real datasheet figures before trusting
this for anything beyond a rough sanity check. Sources to pull from:
- ICM-42688-P datasheet (motion sensor / IMU)
- MAX30102 datasheet (heart-rate / PPG sensor)
- IMX219 datasheet (camera sensor)
- Radxa Zero 3W datasheet / power specs (BT/WiFi radio + SoC baseline)
"""

# Typical active-mode current draw in mA. PLACEHOLDER VALUES — replace
# with the exact figures from each component's datasheet.
COMPONENT_DRAW_MA = {
    "motion_sensor_icm42688": 0.85,   # low-power accel+gyro, active mode
    "heart_rate_max30102": 1.0,       # LED + photodiode, active mode
    "camera_imx219": 150,             # active streaming, scales with frame rate
    "bt_wifi_radio": 120,             # combined BT+WiFi, active TX
    "soc_base_radxa_zero3w": 200,     # baseline compute load
}

# Rough duty-cycle multiplier (0.0-1.0) per capture-intensity level,
# reflecting how "on" each subsystem is at that level. These are estimates
# to be refined once real frame-rate/sample-rate numbers are locked in.
LEVEL_DUTY_CYCLE = {
    "L0": {"camera": 0.00, "audio_bt_wifi": 0.05, "motion": 0.02, "hr": 0.02},
    "L1": {"camera": 0.05, "audio_bt_wifi": 0.20, "motion": 0.10, "hr": 0.10},
    "L2": {"camera": 0.15, "audio_bt_wifi": 0.40, "motion": 0.30, "hr": 0.30},
    "L3": {"camera": 0.50, "audio_bt_wifi": 0.70, "motion": 0.60, "hr": 0.60},
    "L4": {"camera": 0.85, "audio_bt_wifi": 0.90, "motion": 0.80, "hr": 0.80},
    "L5": {"camera": 1.00, "audio_bt_wifi": 1.00, "motion": 1.00, "hr": 1.00},
}

# PLACEHOLDER — update once a specific battery is selected for the enclosure.
BATTERY_CAPACITY_MAH = 300


def estimate_draw_ma(level: str) -> float:
    duty = LEVEL_DUTY_CYCLE[level]
    return (
        COMPONENT_DRAW_MA["soc_base_radxa_zero3w"]
        + COMPONENT_DRAW_MA["camera_imx219"] * duty["camera"]
        + COMPONENT_DRAW_MA["bt_wifi_radio"] * duty["audio_bt_wifi"]
        + COMPONENT_DRAW_MA["motion_sensor_icm42688"] * duty["motion"]
        + COMPONENT_DRAW_MA["heart_rate_max30102"] * duty["hr"]
    )


def estimate_runtime_hours(level: str) -> float:
    draw = estimate_draw_ma(level)
    return round(BATTERY_CAPACITY_MAH / draw, 2)


if __name__ == "__main__":
    print("=" * 60)
    print("POWER & THERMAL ESTIMATE — PLANNING NUMBER ONLY")
    print("NOT measured. NOT verified. Confirm against real hardware.")
    print("=" * 60)
    for level in LEVEL_DUTY_CYCLE:
        draw = round(estimate_draw_ma(level), 1)
        hours = estimate_runtime_hours(level)
        print(f"{level}: ~{draw} mA draw  ->  ~{hours} hours runtime "
              f"at {BATTERY_CAPACITY_MAH}mAh capacity")
    print()
    print("Thermal ceiling: NOT modeled here — needs a real thermal simulation")
    print("or datasheet junction-temperature figures once components are locked.")
    print("Flag this explicitly in security-boot-report.md as an open gap.")
