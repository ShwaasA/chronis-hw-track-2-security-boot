# Chronis — Hardware Track 2: Security & Boot Logic

## Overview

This repository contains the implementation for **Chronis Hardware Track 2 – Security & Boot Logic**.

The objective of this track is to establish a secure system architecture from the beginning by ensuring that **all persistent data is encrypted before storage**, while implementing a robust boot process, watchdog supervision, and power management using a fully simulated hardware environment.

The project is designed so that the mock implementations can later be replaced with real hardware drivers with minimal architectural changes.

---

## Objectives

* Build a mock cryptographic interface compatible with the planned secure hardware chip
* Enforce encryption-before-storage across the entire system
* Implement the complete secure boot sequence with deterministic failure handling
* Develop watchdog monitoring for critical system daemons
* Create a battery-aware power management daemon
* Estimate power consumption and thermal behavior
* Produce a first-pass enclosure design based on component datasheets
* Consolidate testing and simulation results into a final engineering report

---

# Repository Structure

```text
.
├── crypto/                 # Mock cryptographic interface
├── encryption_daemon/      # Encryption pipeline & key hierarchy
├── boot_manager/           # Boot sequencing logic
├── watchdog/               # Daemon monitoring
├── power_management/       # Battery & power state logic
├── thermal_estimation/     # Runtime and thermal calculations
├── enclosure/              # CAD models and component placement
├── tests/                  # Automated simulation tests
├── reports/
│   └── security-boot-report.md
└── README.md
```

---

# Features

## Security Architecture

* Mock hardware security chip interface
* Device Identity Key (DIK)
* Daily derived Data Session Keys (DSK)
* User Public Key (UPK) encryption layer
* Session-based Server Transport Keys
* Signing and verification support
* Secure key hierarchy

---

## Encryption Daemon

Implements the project's primary security guarantee:

> **Rule 1 — Nothing is written to storage unless it has already been encrypted and signed.**

Storage interfaces only accept authenticated encrypted data types, preventing accidental or intentional bypasses.

---

## Secure Boot Manager

Implements the required hardware initialization order:

```
Power Rails
    ↓
Security Chip
    ↓
Clock Sync
    ↓
Storage
    ↓
Motion Sensor
    ↓
Heart-Rate Sensor
    ↓
Camera
    ↓
Display
    ↓
Status LED
    ↓
Bluetooth
    ↓
WiFi
```

Each component follows the specified recovery or degradation strategy defined in the project specification.

---

## Failure Simulation

The mock hardware layer allows individual components to fail independently.

Automated tests verify:

* Security chip failure → System halt
* Storage failure → System halt
* Motion sensor degradation
* Heart-rate degradation
* Camera audio-only mode
* Display fallback
* LED logging
* Bluetooth WiFi fallback
* WiFi offline storage mode

---

## Watchdog Daemon

Continuously monitors all system daemons.

Behavior:

* Encryption daemon failure → Immediate system halt
* Other daemon failures → Automatic daemon restart

---

## Power Management

Implements four battery operating states.

| State        | Battery | Behavior                                 |
| ------------ | ------- | ---------------------------------------- |
| Full Active  | >40%    | No restrictions                          |
| Conservation | 20–40%  | Reduced camera, LED and sync performance |
| Critical     | <20%    | Camera/audio limited, syncing disabled   |
| Emergency    | <5%     | Camera off, WiFi off, beacon mode only   |

Additional features include:

* Battery percentage estimation
* Charging detection
* Charge cycle tracking
* Battery health estimation
* Daily JSON power reports

---

## Power & Thermal Projection

Simulation-based estimation using public component datasheets.

Includes:

* Current draw estimation
* Runtime projection
* Thermal ceiling estimate
* Capture intensity analysis (L0–L5)

> These values are planning estimates and require validation on real hardware.

---

## Enclosure Design

First-pass CAD enclosure created using public component dimensions.

Design considerations include:

* Wearability
* Camera and microphone exposure
* Charging access
* Component placement
* Thermal constraints

The enclosure serves as a preliminary mechanical layout and has **not yet been validated using physical hardware**.

---

# Testing

The repository includes automated simulation tests covering:

* Encryption enforcement
* Boot failure matrix
* Watchdog recovery
* Power state transitions
* Battery simulation
* Charging detection
* Battery health logic

Run the test suite:

```bash
pytest
```

---

# Engineering Report

The final report is available in:

```
reports/security-boot-report.md
```

It includes:

* Encryption architecture validation
* Boot sequence verification
* Watchdog test results
* Power management validation
* Thermal estimation
* Enclosure design
* Known hardware limitations

---

# Known Limitations

This project is validated entirely in simulation.

The following require testing on actual hardware:

* Secure element integration
* Hardware cryptographic acceleration
* Real sensor communication
* Bus timing and address conflicts
* Power consumption accuracy
* Thermal performance
* Battery discharge characteristics
* Physical enclosure fit
* Camera alignment
* Mechanical durability
* Waterproofing and wearability

---

# Technology Stack

* Python
* Pytest
* Mock Hardware Layer
* Software Cryptography Libraries
* JSON Reporting
* CAD (FreeCAD)

---

# Future Work

* Replace mock cryptographic interface with the production secure chip
* Integrate real sensor drivers
* Validate power estimates on hardware
* Perform thermal testing
* Optimize battery life
* Refine enclosure after prototype assembly
* End-to-end hardware validation

---

# Status

**Track:** Hardware Track 2 – Security & Boot Logic

**Development Stage:** Simulation Complete

**Hardware Validation:** Pending

---

## License

This repository is part of the **Chronis** project and is intended for educational and development purposes.
