# ⚡ USB 3.2 Gen 1 — 4-Port Hub

<p align="left">
  <img src="https://img.shields.io/badge/Hardware-Complete-brightgreen?style=for-the-badge&logo=altiumdesigner&logoColor=white"/>
  <img src="https://img.shields.io/badge/PCB-6--Layer-blue?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Altium_Designer-26-A5915F?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/USB-3.2_Gen1_5Gbps-0078D7?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Hub_IC-TUSB8044A-C75000?style=for-the-badge"/>
</p>

---

## 📋 Project Summary

This repository contains the complete hardware design for a USB 3.2 Gen 1 (5 Gbps) 4-port hub, designed as a portfolio project demonstrating high-speed PCB design methodology on a real-world USB system.

The hub is fully bus-powered over USB-C (UFP, up to 3A) and provides one USB-C downstream port with cold-socket via P-MOSFET logic, plus three USB-A downstream ports, all with per-port current limiting. No MCU is required: Type-C attach detection, power sequencing, and overcurrent protection are handled entirely in hardware.

The design focuses on:

- **Impedance-controlled routing** (90Ω differential, 6-layer stackup)
- **Hierarchical schematic** with multi-part component decomposition (TUSB8044A split across 5 sub-sheets)
- **Power delivery chain** with PG-chained sequencing and RC-delayed reset
- **USB-C cold socket implementation** using P-MOSFET gate logic (no VBUS before cable insertion, per USB Type-C specification)

---

![PCB 3D Top](Images/PCB_3D_Top.png)

🔗 **Schematic (PDF):** [View full schematic](Hardware/Exports/Schematic_USB_Hub_v1.0.pdf)

---

## 🔧 Key Specifications

| Parameter | Value |
|---|---|
| **Hub Controller** | TUSB8044A - USB 3.2 Gen 1 Hub controller, 64-pin VQFN |
| **Upstream Port** | USB-C (UFP/Sink, bus-powered, 5V/3A max) |
| **Downstream Ports** | 1× USB-C (DFP) + 3× USB-A |
| **Type-C Controllers** | 2× HD3SS3220IRNHT (UFP and DFP) |
| **Power Switches** | 2× TPS2561QDRCRQ1 (dual-channel, per-port current limiting) |
| **Power Tree** | 5V → 3.3V: TLV62569PDDCT (buck, 2A) → 1.1V: TPS74801RGWRM3 (LDO, 1.5A) |
| **Battery Charging** | BC 1.2 CDP enabled on all downstream ports |
| **Cold Socket** | Hardware P-MOSFET on USB-C downstream port |
| **PCB Layers** | 6-layer controlled-impedance |
| **Board Size** | 100 × 50 mm |
| **Design Tool** | Altium Designer 26 |

---

## 🏆 Hardware Engineering Highlights

### ⚡ SuperSpeed Signal Integrity

- All SS differential pairs routed on **L1 and L6 only**, each with an adjacent solid GND plane (L2 and L5) as the impedance reference.
- **Differential impedance: 90Ω ±10%**, calculated with Altium's built-in field solver on the 6-layer stackup.
- Prepreg L1–L2 and L5–L6: **2116, 0.12mm, Dk = 4.45**.
- **5W clearance rule (0.6mm)** enforced between SS/HS pairs and all other signals and copper pours.
- **Intra-pair skew ≤ 0.15mm** (≈ 1.2 ps) on all SuperSpeed pairs.
- AC coupling caps (100nF, 0402, X7R) on TX paths.
- **Polarity inversion** applied where needed: both TUSB8044A and HD3SS3220 support it natively, no via swaps required.

| Impedance Profile | Stackup |
|:---:|:---:|
| ![Impedance](Docs/Impedance/USB_SS_90ohm_Differential.png) | ![Stackup](Docs/Impedance/Stackup_PCBWay_1_6mm_6L.png) |

### 🧱 6-Layer Stackup

| Layer | Type | Function |
|---|---|---|
| L1 | Signal | USB SS/HS pairs, components |
| L2 | GND Plane | Solid reference, no splits |
| L3 | Signal | Slow signals only |
| L4 | Power | Polygon pours: 5V / 3.3V / 1.1V |
| L5 | GND Plane | Solid reference, no splits |
| L6 | Signal | USB SS/HS pairs, routing |


### 🔌 USB-C Cold Socket

Per USB Type-C specification, the downstream USB-C port VBUS must be de-energized when no cable is inserted. This is implemented with a single P-MOSFET (DMG2305UX) acting as a hardware AND gate:

- **Source** → PWRCTL1 from TUSB8044A (3.3V when hub active)
- **Gate** → ID pin of HD3SS3220 DFP
- **Drain** → EN1 of TPS2561 power switch

When no cable is present, the ID pin floats and the 100kΩ Gate-Source resistor keeps the MOSFET off, VBUS stays at 0V. On cable insertion, HD3SS3220 pulls ID LOW, turning on the MOSFET and enabling VBUS. USB-A ports use direct PWRCTL→EN connections (hot socket, per spec).

### 🔋 Power Sequencing

### 🛡️ ESD Protection

| Location | Component | Protection |
|---|---|---|
| SS lines (all ports) | PUSB3FR4Z (Nexperia) | 0.29pF |
| USB 2.0 + CC lines | TPD4E05U06 (TI) | 0.5pF |
| VBUS (all ports) | SMAJ5.0A | TVS, clamps surges |

---

## 📁 Repository Structure

```text
USB3.2-Hub-4Port/
│
├── Images/
│   ├── PCB_3D.png
│   ├── PCB_3D_Top.png
│   ├── PCB_3D_Bottom.png
│   ├── Layerstack_Visualizer.png
│   ├── Stackup.png
│   ├── D90_Impedance_Profile.png
│   └── Schematic_Overview.png
│
├── Hardware/
│   ├── Altium/
│   │   ├── USB3.2_Hub_4Port.PrjPcb
│   │   ├── USB3.2_Hub_4Port.PcbDoc
│   │   ├── Top_Level.SchDoc
│   │   ├── Hub_Core.SchDoc
│   │   ├── Power.SchDoc
│   │   ├── Upstream.SchDoc
│   │   ├── Downstream_Port_1.SchDoc
│   │   ├── Downstream_Port_2.SchDoc
│   │   ├── Downstream_Port_3-4.SchDoc
│   │   ├── USB3.2_Hub_4Port.BomDoc
│   │   ├── USB3.2_Hub_4Port.PrjPcbVariants
│   │   └── USB3.2_Hub_4Port.PrjPcbStructure
│   │
│   └── Exports/
│       ├── Schematic_USB_Hub_v1.0.pdf
│       └── Draftsman_USB_Hub_v1.0.pdf
│
├── Manufacturing/
│   ├── Gerbers/
│   │   └── Gerber_USB3.2_Hub_4Port_v1.0.zip
│   │
│   ├── Assembly/
│   │   ├── BOM.xlsx
│   │   └── PickPlace.csv
│   │
│   └── Stackup/
│       ├── PCBWay_6Layer_Stackup.pdf
│       └── USB3.2_Hub_4Port_Stackup.png
│
├── Docs/
│   ├── Design_Notes.md
│   ├── Routing_Guidelines.md
│   └── Bringup.md
│
└── README.md
```

---

## 🛠️ Tools Used

| Tool | Version | Purpose |
|---|---|---|
| **Altium Designer** | 26.7.1 | Schematic capture, 6-layer PCB layout |

---

## ⚠️ Disclaimer

This project is provided for educational and portfolio purposes. The board has not yet been manufactured or tested. The author assumes no liability for any issues arising from the use of this material.

---

## 👤 Author

**Alberto Marrone**
[LinkedIn](your-linkedin-url)












# ⚡ USB 3.2 Gen 1 — 4-Port Hub

<p align="left">
  <img src="https://img.shields.io/badge/PCB-6--Layer-blue?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Altium_Designer-26-A5915F?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/USB-3.2_Gen1_5Gbps-0078D7?style=for-the-badge&logo=usb&logoColor=white"/>
  <img src="https://img.shields.io/badge/Hub_Controller-TUSB8044A-C75000?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Sponsored_by-PCBWay-FF6600?style=for-the-badge"/>
</p>

---

## 📋 Project Summary

This repository contains the complete hardware design for a USB 3.2 Gen 1
(5 Gbps) 4-port hub — a portfolio project built to apply and document
high-speed PCB design methodology end-to-end, from controller selection
through impedance-controlled layout to manufacturing.

The hub is fully bus-powered over USB-C (UFP, up to 3A) and exposes one
USB-C downstream port with cold-socket compliance via discrete P-MOSFET
logic, plus three USB-A downstream ports — each with independent current
limiting. The entire control logic (Type-C attach detection, power
sequencing, overcurrent handling) runs without a microcontroller.

**Design focus areas:**

- Impedance-controlled SuperSpeed and High-Speed routing (90Ω differential, 6-layer stackup)
- Hierarchical schematic with multi-part component decomposition (TUSB8044A split across 5 sub-sheets)
- Power delivery chain with sequenced enable and RC-delayed reset
- USB-C cold socket implementation per Type-C specification

> [!NOTE]
> This is Revision A. The board has been sent for manufacturing and assembly
> through PCBWay — bring-up results and assembled board photos will be added
> once received.

---

## 🖼️ Board Preview

<p align="center">
  <img src="Images/PCB_3D_Top.png" width="450"/>
  <img src="Images/PCB_3D_Bottom.png" width="450"/>
</p>

<p align="center"><i>3D render — top and bottom layers, Altium Designer</i></p>

---

## 🧩 Schematic Overview

<p align="center">
  <img src="Images/Schematic_Overview.png" width="800"/>
</p>

🔗 **Full schematic (PDF):** [View all sheets](Hardware/Exports/Schematic_USB_Hub_v1.0.pdf)

---

## 🔧 Key Specifications

| Parameter | Value |
|---|---|
| **Hub Controller** | TUSB8044A — USB 3.2 Gen 1, 5 Gbps, 64-pin VQFN |
| **Upstream Port** | USB-C (UFP/Sink, bus-powered, 5V/3A max) |
| **Downstream Ports** | 1× USB-C (DFP) + 3× USB-A |
| **Type-C Controllers** | 2× HD3SS3220IRNHT (UFP + DFP) |
| **Power Switches** | 2× TPS2561QDRCRQ1 (dual-channel, per-port current limiting) |
| **Power Tree** | 5V → 3.3V (TLV62569P buck) → 1.1V (TPS74801 LDO) |
| **Battery Charging** | BC 1.2 CDP enabled on all downstream ports |
| **Cold Socket** | Hardware P-MOSFET on USB-C downstream port |
| **PCB Layers** | 6-layer, impedance-controlled |
| **Board Size** | 100 × 50 mm |
| **Design Tool** | Altium Designer 26 |

---

## 🏆 Hardware Engineering Highlights

### 📡 Signal Integrity

All differential pairs are routed on **L1 and L6**, each referenced to a
solid GND plane (L2 and L5) with no splits. Routing follows the 5W rule
(0.6mm clearance) from any other signal or copper pour.

| Parameter | SuperSpeed (USB 3.x) | High-Speed (USB 2.0) |
|---|---|---|
| Target impedance | 90Ω ±10% | 90Ω ±15% |
| Trace width / gap | 0.136mm / 0.127mm | per Altium field solver |
| Intra-pair skew | ≤ 0.15mm (≈1.2ps) | ≤ 3.8mm |
| Max via count | 2 | 4 |
| AC coupling | 100nF, 0402, X7R — TX paths only | — |

> [!TIP]
> Both the TUSB8044A and HD3SS3220 support **native polarity inversion** on
> SuperSpeed pairs — P/N can be swapped freely during routing with no via
> tricks or register configuration required.

<p align="center">
  <img src="Docs/Impedance/D90_Impedance_Profile.png" width="600"/>
</p>

<p align="center"><i>90Ω differential impedance profile — Altium field solver, 2116 prepreg, Dk = 4.45</i></p>

### 🧱 6-Layer Stackup

| Layer | Type | Function |
|---|---|---|
| L1 | Signal | USB SS/HS pairs, components |
| L2 | GND Plane | Solid reference, no splits |
| L3 | Signal | Slow signals only (I2C, PWRCTL, OVERCUR) |
| L4 | Power | Polygon pours: 5V / 3.3V / 1.1V |
| L5 | GND Plane | Solid reference, no splits |
| L6 | Signal | USB SS/HS pairs, routing |

<p align="center">
  <img src="Manufacturing/Stackup/USB3.2_Hub_4Port_Stackup.png" width="600"/>
</p>

> [!NOTE]
> Prepreg between L1–L2 and L5–L6 uses **2116 weave** instead of the
> coarser 7628. The finer glass weave reduces the fiber-weave effect,
> keeping the dielectric more homogeneous under the SuperSpeed pairs and
> minimizing intra-pair skew. See [`Docs/Design_Decisions.md`](Docs/Design_Decisions.md)
> for the full reasoning.

### 🔌 USB-C Cold Socket

Per the USB Type-C specification, the downstream USB-C port's VBUS must
remain de-energized until a cable is detected. This is implemented with a
single P-MOSFET (DMG2305UX) acting as a hardware enable gate:

- **Source** → PWRCTL1 (TUSB8044A, 3.3V when hub is active)
- **Gate** → ID pin of the downstream HD3SS3220
- **Drain** → EN1 of the TPS2561 power switch

With no cable inserted, the ID pin floats and a 100kΩ gate-source resistor
holds the MOSFET off — VBUS stays at 0V. On attach, the HD3SS3220 detects
the Rd termination on CC and pulls ID low, enabling VBUS. USB-A ports use
direct PWRCTL → EN connections, as hot-socket behavior is permitted there
by spec.

### 🔋 Power Sequencing

> [!IMPORTANT]
> The TUSB8044A requires GRSTz to remain asserted for ≥3ms after both
> VDD (1.1V) and VDD33 (3.3V) are within their recommended operating range.

t = 0ms      VBUS 5V applied

t ≈ 0.5ms    Buck PG releases → LDO EN

t ≈ 3.8ms    LDO soft-start complete (Css = 2.2nF, tSS ≈ 3.3ms)

t ≈ 4.3ms    LDO PG releases → RC delay begins

t ≈ 16ms     GRSTz reaches VIH → TUSB8044A exits reset

The RC delay accounts for the TUSB8044A's internal pull-up on GRSTz
(R_int ≈ 14.5–25kΩ): with an external 100kΩ resistor and 1µF capacitor,
R_eq ≈ 12.66kΩ gives t(VIH) ≈ 11.8ms — comfortably above the 3ms minimum.

### 🛡️ ESD Protection

| Net | Protection Device | Spec |
|---|---|---|
| SuperSpeed lines (all ports) | PUSB3FR4Z | 0.29pF, ±15kV |
| USB 2.0 + CC lines | TPD4E05U06 | 0.5pF, IEC 61000-4-2 |
| VBUS (all ports) | SMAJ5.0A | TVS clamp |

---

## 📦 PCBWay Manufacturing

> [!NOTE]
> This prototype run is sponsored by **PCBWay**. The board has been sent for
> fabrication and assembly — this section will be updated with photos and a
> short write-up once the boards arrive and bring-up is complete.

During file submission, PCBWay's review caught a via incorrectly placed
under an SMD pad before production — their team flagged it quickly with
clear feedback, which was a nice catch ahead of a 6-layer impedance-controlled
run. Once the boards land, I'll add real photos and an honest assessment of
build quality here.

<p align="left">
  <img src="https://img.shields.io/badge/PCB_Manufacturing-PCBWay-FF6600?style=for-the-badge&logo=pcbway"/>
</p>

---

## 📁 Repository Structure

```text
USB3.2-Hub-4Port/
│
├── Images/
│   ├── PCB_3D.png
│   ├── PCB_3D_Top.png
│   ├── PCB_3D_Bottom.png
│   ├── Layerstack_Visualizer.png
│   ├── Stackup.png
│   ├── D90_Impedance_Profile.png
│   └── Schematic_Overview.png
│
├── Hardware/
│   ├── Altium/
│   │   ├── USB3.2_Hub_4Port.PrjPcb
│   │   ├── USB3.2_Hub_4Port.PcbDoc
│   │   ├── Top_Level.SchDoc
│   │   ├── Hub_Core.SchDoc
│   │   ├── Power.SchDoc
│   │   ├── Upstream.SchDoc
│   │   ├── Downstream_Port_1.SchDoc
│   │   ├── Downstream_Port_2.SchDoc
│   │   ├── Downstream_Port_3-4.SchDoc
│   │   ├── USB3.2_Hub_4Port.BomDoc
│   │   ├── USB3.2_Hub_4Port.PrjPcbVariants
│   │   └── USB3.2_Hub_4Port.PrjPcbStructure
│   │
│   └── Exports/
│       ├── Schematic_USB_Hub_v1.0.pdf
│       └── Draftsman_USB_Hub_v1.0.pdf
│
├── Manufacturing/
│   ├── Gerbers/
│   │   └── Gerber_USB3.2_Hub_4Port_v1.0.zip
│   │
│   ├── Assembly/
│   │   ├── BOM.xlsx
│   │   └── PickPlace.csv
│   │
│   └── Stackup/
│       ├── PCBWay_6Layer_Stackup.pdf
│       └── USB3.2_Hub_4Port_Stackup.png
│
├── Docs/
│   ├── Design_Decisions.md
│   ├── Routing_Guidelines.md
│   └── Bringup.md
│
└── README.md
```

---

## ⚠️ Disclaimer

This project is provided for educational and portfolio purposes. The board
is currently in manufacturing/assembly and has not yet undergone functional
validation. The author assumes no liability for any issues arising from the
use of this material.

---

## 👤 Author

**Alberto Marrone**
MSc Student, Electronics Engineering — Politecnico di Milano
[LinkedIn](your-linkedin-url) · [GitHub](https://github.com/Alberto0235)
