# Design Decisions

## Why 6 layers instead of 4

USB 3.2 Gen 1 SS pairs at 5Gbps require a continuous, 
uninterrupted GND reference plane directly adjacent to 
the signal layer. With 4 layers (Sig/GND/PWR/Sig), the 
bottom signal layer references the power plane — which 
has splits for 5V/3.3V/1.1V. Any SS trace crossing a 
plane split sees an impedance discontinuity and a broken 
return path. 6 layers allows L1→L2(GND) and L6→L5(GND), 
giving both signal layers a solid reference.

## Why 2116 prepreg instead of 7628

The 7628 weave is coarser — the glass fiber bundles are 
larger and more spaced. At 5Gbps, if one trace of a 
differential pair runs over glass fiber and the other 
over resin, they see different Dk values and arrive at 
the receiver slightly skewed (fiber weave effect). The 
2116 has a much finer weave, making the dielectric more 
homogeneous and reducing skew caused by the substrate 
itself. It also gives a thinner prepreg (0.12mm vs 
0.18mm), which means narrower traces for 90Ω — 0.136mm 
instead of ~0.25mm — making QFN breakout feasible.

## Why LDO for 1.1V instead of a second buck

The 1.1V rail powers the TUSB8044A core and PLL. Buck 
converters introduce switching noise at their operating 
frequency and harmonics. A LDO (TPS74801) provides a 
cleaner supply with no switching noise, which is 
important for PLL stability. The voltage drop is only 
2.2V at ~680mA (1.5W dissipated), which is acceptable 
given the TPS74801's RθJA of 35.6°C/W — TJ ≈ 78°C, 
well within the 125°C limit. TI's own reference design 
for the TUSB8044A uses an LDO for this rail.

## Why HD3SS3220 for USB-C CC logic

The TUSB8044A handles the USB data path but does not 
include CC logic for USB-C orientation detection and 
current advertisement. The HD3SS3220 adds a 2:1 SS MUX 
that routes the correct SS pair based on cable 
orientation (detected via CC), plus Rp/Rd termination 
for DFP/UFP mode. It operates in GPIO mode (no I2C 
required), keeping the design MCU-free.

## Why cold socket on USB-C downstream only

USB-A ports are defined as "hot socket" by the USB spec 
— VBUS is always present on the connector. USB-C 
requires VBUS to be de-energized before cable insertion 
(cold socket). The P-MOSFET implementation uses the 
HD3SS3220 ID pin as an attach signal: VBUS is only 
enabled after the CC controller confirms a valid device 
is connected.

## Why 5W spacing (0.6mm) around SS differential pairs

A copper pour placed too close to a microstrip trace 
acts as a coplanar ground, reducing the effective 
impedance from the target 90Ω. The 5W rule (clearance 
= 5× trace width = 5 × 0.136mm = 0.68mm ≈ 0.6mm) 
ensures the copper pour has negligible effect on 
differential impedance.
