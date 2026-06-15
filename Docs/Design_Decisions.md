# Design Decisions

## Why a 6-Layer Stackup

The primary design goal was maintaining controlled impedance and continuous return paths for all USB 3.2 Gen 1 SuperSpeed signals.

A conventional 4-layer stackup (Signal / GND / Power / Signal) would force one of the two outer signal layers to reference the power plane. Since the design contains multiple voltage domains (5V, 3.3V, and 1.1V), the power plane requires splits and polygon boundaries that can interrupt high-frequency return currents.

The selected 6-layer stackup allows both outer signal layers to reference solid, uninterrupted ground planes:

* L1 → referenced to L2 (GND)
* L6 → referenced to L5 (GND)

This guarantees a continuous return path for all SuperSpeed and High-Speed USB signals regardless of routing location.

Additional benefits include:

* Improved EMI performance
* Easier impedance control
* Better isolation between high-speed and low-speed signals
* Dedicated internal power distribution layer
* Easier routing

The final stackup is:

| Layer | Function                        |
| ----- | ------------------------------- |
| L1    | High-speed signals & components |
| L2    | Solid GND plane                 |
| L3    | Low-speed control signals       |
| L4    | Power distribution              |
| L5    | Solid GND plane                 |
| L6    | High-speed signals & components |

---

## Why 2116 Prepreg for the Outer High-Speed Layers

The impedance-controlled USB pairs are routed exclusively on the outer layers (L1 and L6).

Between these layers the 2116 prepreg was selected instead of the coarser 7628 weave.

Compared to 7628, 2116 provides:

* A more homogeneous dielectric environment
* Reduced fiber-weave induced skew
* Thinner dielectric spacing
* More practical trace geometries for USB routing

The thinner dielectric also reduces the trace width required to achieve 90Ω differential impedance.

Using the selected stackup:

* Dielectric thickness = 0.12mm
* Differential impedance target = 90Ω
* Resulting geometry for the Diff pairs = 0.136mm trace width / 0.127mm gap

These dimensions allow straightforward breakout from the TUSB8044A and HD3SS3220 without excessive layer transitions.

The internal dielectric layers continue to use standard materials where signal integrity requirements are less critical.

---

## Why an LDO for the 1.1V Core Rail

The TUSB8044A requires a dedicated 1.1V rail for its internal core and PLL circuitry.

Two approaches were evaluated:

1. Secondary buck converter
2. Linear regulator

A buck converter would improve efficiency but introduce switching ripple and high-frequency noise directly onto the PLL supply.

The selected TPS74801 LDO provides:

* Low output noise
* High PSRR
* Simplified sequencing
* Reduced risk of PLL-related stability issues

Thermal analysis showed the additional dissipation remains acceptable within the expected operating conditions.

This approach is also consistent with Texas Instruments reference implementations for the TUSB8044A family.

---

## Why HD3SS3220 for USB-C Control

The TUSB8044A manages the USB hub functionality but does not provide USB Type-C attach detection or SuperSpeed orientation management.

The HD3SS3220 was selected because it combines:

* USB Type-C CC controller
* Orientation detection
* SuperSpeed lane switching
* Current advertisement logic

This keeps the design fully hardware-controlled while maintaining compliance with USB Type-C requirements.

---

## Why USB-C Cold Socket Implementation

USB Type-C ports must not present VBUS until a valid attachment has been detected through the CC pins. To satisfy this requirement, the downstream USB-C port uses a hardware-controlled enable path:

HD3SS3220 → PMOS → TPS2561 Enable

When no cable is present:

* CC detection remains inactive
* The PMOS remains off
* VBUS is disconnected

Once a valid attachment is detected:

* The HD3SS3220 asserts its ID output
* The PMOS turns on
* The TPS2561 power switch is enabled
* VBUS becomes available at the connector

No firmware is required.

The three USB-A ports remain permanently powered because USB-A connectors are allowed to operate as hot-socket ports.

---

## Why Copper Clearance Matters

High-speed differential pairs were routed with a minimum clearance of approximately 0.6mm from surrounding copper features. The objective is to prevent nearby copper from acting as an unintended coplanar reference plane and avoid crosstalk.

If copper is placed too close to a microstrip pair:

* Effective impedance decreases
* Field distribution changes
* Differential impedance may deviate from the target value
* Crosstalk

The selected clearance follows the 5W guideline and keeps impedance variation negligible compared to manufacturing tolerances. This spacing was applied consistently around all HighSpeed and SuperSpeed differential pairs throughout the design.

---

## Why a Hardware-Only Architecture

A design goal from the beginning was eliminating unnecessary firmware. Functions often delegated to a microcontroller are instead handled through dedicated hardware:

* USB-C attach detection
* Orientation detection
* Power sequencing
* Current limiting
* Overcurrent reporting
* Reset timing

Advantages include:

* Reduced system complexity
* Faster startup
* No firmware maintenance
* Lower validation effort
* Fewer failure modes

The final design contains no MCU and requires no software for normal operation.
