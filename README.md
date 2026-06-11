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

![PCB 3D Top](Hardware/Exports/PCB_3D_Top.png)

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
│   ├── PCB_3D_Top.png
│   ├── PCB_3D_Bottom.png
│   ├── PCB_Layout.png
│   ├── Stackup.png
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
│   │   └── USB3.2_Hub_4Port_RevA.zip
│   │
│   ├── Assembly/
│   │   ├── BOM.xlsx
│   │   └── PickPlace.csv
│   │
│   └── Stackup/
│       └── PCBWay_6Layer_Stackup.pdf
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
| **Altium Designer** | 26.6.0 | Schematic capture, 6-layer PCB layout |

---

## ⚠️ Disclaimer

This project is provided for educational and portfolio purposes. The board has not yet been manufactured or tested. The author assumes no liability for any issues arising from the use of this material.

---

## 👤 Author

**Alberto Marrone**
[LinkedIn](your-linkedin-url)
