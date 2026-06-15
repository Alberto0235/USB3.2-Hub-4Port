# Bring-Up Procedure

## Prerequisites

- Multimeter
- Oscilloscope (recommended) or logic probe
- Power resistors for overcurrent test — see Step 6
- USB-C cable and host PC
- USB 3.0 flash drive (for per-port test)

---

## Step 1 — Visual Inspection

Check for solder bridges and cold joints on the TUSB8044A (0.5mm-pitch VQFN), the two HD3SS3220 (0.5mm-pitch VQFN), the TPS2561 switches, and all connector pads.

---

## Step 2 — Power-On (No USB Connection)

Do not connect USB yet. Apply 5V to the VBUS test point and measure:

- TP3 (5V_VBUS): 5.0V ±5%
- TP4 (3V3_VDD): 3.3V ±3%
- TP5 (1V1_VDD): 1.1V ±3%

If any rail is missing, check the corresponding regulator before proceeding.

---

## Step 3 — GRSTz Timing (Oscilloscope)

Probe TP8 (GRSTz) during power-on. The signal should rise to V_IH approximately 16ms after VBUS is applied — see [`Design_Decisions.md`](Design_Decisions.md) for the full timing breakdown (power-up sequencing + RC delay).

---

## Step 4 — USB Enumeration

Connect to a USB 3.x capable host. The hub should enumerate with the VID:PID programmed into the EEPROM (see Known Configuration below). Check Device Manager / `lsusb` for both the SuperSpeed and High-Speed hub interfaces.

---

## Step 5 — Per-Port Functional Test

Connect a USB 3.0 flash drive to each port in sequence. Verify the drive is recognized at SuperSpeed link rate and that data transfer works correctly.

---

## Step 6 — Overcurrent Test

> [!WARNING]
> This test dissipates several watts in a resistor. Use a resistor rated
> well above the calculated power, mount it on a heatsink or non-flammable
> surface, and limit test duration to avoid overheating components.

Rather than shorting VBUS directly, load each port with a resistor sized to exceed the TPS2561's configured current limit:

| Ports | R_ILIM | I_LIM (max, per datasheet) | Test Load Target | Resistor | Power Dissipated |
|---|---|---|---|---|---|
| 1–2 (TPS2561 #1) | 37.4kΩ | ≈ 1.64A | ≈ 2.0A | 2.5Ω | ≈ 10W |
| 3–4 (TPS2561 #2) | 56kΩ | ≈ 1.09A | ≈ 1.4A | 3.6Ω | ≈ 7W |

Procedure:

1. With the port powered and no other load attached, connect the test resistor across VBUS and GND on that port.
2. Probe the corresponding FAULTx pin (TPS2561) or OVERCURz pin (TUSB8044A) — it should assert when the load current exceeds the configured limit.
3. Remove the resistor and verify the FAULTx/OVERCURz signal deasserts and the port returns to normal operation, matching the behavior described in the TPS2561 datasheet.

---

## Known Configuration (Rev A)

- No USB PD — 5V only, max 3A negotiated from upstream
- Billboard disabled (no USB-C Alternate Mode implemented)
