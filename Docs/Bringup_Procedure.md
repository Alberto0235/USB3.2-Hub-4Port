# Bring-Up Procedure

## Prerequisites
- Multimeter
- Oscilloscope (optional but recommended)
- USB-C cable and host PC

## Step 1 — Visual inspection
Check for solder bridges on TUSB8044A QFN (0.5mm pitch),
HD3SS3220, TPS2561, and connector pads.

## Step 2 — Power-on (no USB connection)
Do not connect USB yet. Apply 5V to VBUS test point.
Measure:
- TP3 (5V_VBUS): 5.0V ±5%
- TP4 (3V3_VDD): 3.3V ±3%
- TP5 (1V1_VDD): 1.1V ±3%

If any rail is missing, check the corresponding regulator
before proceeding.

## Step 3 — GRSTz timing (optional, oscilloscope)
Probe TP8 (GRSTz) during power-on. Verify the signal
rises after both 3.3V and 1.1V are stable, with a
delay > 3ms from LDO PG assertion.

## Step 4 — USB enumeration
Connect to a USB 3.x capable host. The hub should
enumerate as "Texas Instruments USB 3.2 Hub" (VID 0451,
PID 8440) in Device Manager / lsusb.

## Step 5 — Per-port functional test
Connect a USB 3.0 flash drive to each port in sequence.
Verify the drive is recognized and data transfer works.

## Step 6 — Overcurrent test
Short VBUS on a downstream port briefly.
Verify the corresponding fault LED illuminates and
the port recovers after the short is removed.

## Known limitations (Rev A)
- No USB PD — 5V only, max 3A from upstream
- Billboard disabled (no Alt Mode)
- EEPROM unpopulated by default (uses TI default VID/PID)
