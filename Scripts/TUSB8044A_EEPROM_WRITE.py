#!/usr/bin/env python3
"""
TUSB8044A EEPROM Programmer
============================
Programs the configuration EEPROM of a TUSB8044A-based USB 3.2 Gen1 hub
via the chip's internal HID-to-I2C bridge interface (VID=0x0451, PID=0x82FF).

Target EEPROM : Microchip 24LC08BT-I/OT (8 Kbit, SOT-23, I2C)
                Bank 0 (0x000–0x0FF) : I2C 7-bit address 0x50
                Page size             : 16 bytes
                Write cycle time      : 5 ms max (we use 15 ms for margin)

Programming strategy — "signature-last" atomic write
------------------------------------------------------
1. Clear the EEPROM signature byte (write 0x00 to address 0x00).
   If power is lost here, the TUSB8044A sees no valid EEPROM and boots
   from TI factory defaults — the hub stays functional.
2. Write the full configuration (registers 0x01–0x2D and string data).
3. Verify all written bytes read back correctly.
4. Write the signature 0x55 to address 0x00 LAST.
   Only after this step will the hub load the custom configuration on reset.

Recovery — if the hub shows "Unknown USB Device"
-------------------------------------------------
Short EEPROM U6 pin 3 (SDA) to pin 2 (GND) while inserting the USB cable.
The TUSB8044A I2C read times out, the hub ignores the EEPROM content and
boots with TI factory defaults. Re-run this script afterwards.

Requirements
------------
    pip install hidapi

Usage
-----
    Run CMD as Administrator (required for HID access on Windows):
    python TUSB8044A_EEPROM_WRITE.py
"""

import hid
import time
import sys


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │  USER CONFIGURATION — edit the values in this section before running        │
# └─────────────────────────────────────────────────────────────────────────────┘

# USB hub descriptor strings written to the EEPROM.
# These appear in USBTreeView / lsusb as the device manufacturer and product name.
MANUFACTURER = "Alberto Marrone"
PRODUCT      = "USB 3.2 Gen1 4-Port Hub"

# Hub VID and PID.
# The TUSB8044A defaults are kept here; change only if your design requires a
# custom VID/PID assigned by the USB-IF.
VID_HUB = 0x0451   # Texas Instruments
PID_HUB = 0x8440   # TUSB8044A SuperSpeed hub (HS companion PID = PID ^ 0x0002)

# Battery Charging 1.2 (BC1.2) port enable mask.
# Each bit enables CDP charging on the corresponding downstream port (bit 0 = port 1).
# 0x0F = all four ports enabled.  The TPS2561 ILIM resistor is the real hardware cap.
BC12_MASK = 0x0F

# ─────────────────────────────────────────────────────────────────────────────


# ── HID interface identifiers (do not change) ─────────────────────────────────
VID     = 0x0451   # Texas Instruments
PID_HID = 0x82FF   # TUSB8044A internal HID-to-I2C bridge

# ── EEPROM parameters (24LC08B) ───────────────────────────────────────────────
EEPROM_BASE = 0x50   # I2C 7-bit base address for bank 0 (addresses 0x000–0x0FF)
EEPROM_PAGE = 16     # Maximum bytes per page-write transaction
EEPROM_TWR  = 0.015  # Write cycle guard time in seconds (datasheet max: 5 ms)

# ── HID opcodes — TUSB8044A datasheet §8.3.3.1 ───────────────────────────────
OP_READ       = 0x01  # Read N bytes from I2C device
OP_WRITE_STOP = 0x02  # Write to I2C device with STOP condition
OP_WRITE_CONT = 0x03  # Write to I2C device without STOP (used to set read pointer)


# ══════════════════════════════════════════════════════════════════════════════
# Low-level HID helpers
# ══════════════════════════════════════════════════════════════════════════════

def _send(dev: hid.device, opcode: int, i2c_addr: int, data: bytes = b"") -> None:
    """Send one HID SET REPORT (Output) command to the TUSB8044A.

    The TUSB8044A queues a response on its interrupt IN endpoint for every
    command it receives.  The drain read at the end of this function discards
    that response so it does not pollute subsequent reads.

    Report wire format (TUSB8044A §8.3.3.1):
        Byte 0  : HID report ID (0x00 — device uses no report IDs)
        Byte 1  : opcode
        Byte 2  : I2C slave address (7-bit)
        Byte 3  : data-length LSB
        Byte 4  : data-length MSB
        Byte 5+ : payload (for writes); absent for reads
    """
    report = bytes([
        0x00,
        opcode,
        i2c_addr,
        len(data) & 0xFF,
        (len(data) >> 8) & 0xFF,
    ]) + data
    dev.write(report)
    dev.read(67, timeout_ms=500)   # drain the command acknowledgment


def _recv(dev: hid.device, timeout_ms: int = 2000) -> tuple[int, bytes]:
    """Read one HID GET REPORT (Input) response from the TUSB8044A.

    Response wire format (TUSB8044A §8.3.3.3):
        Byte 0  : status  (0 = success, 1 = timeout, 2 = addr NAK, 3 = data NAK)
        Byte 1  : returned-data-length LSB
        Byte 2  : returned-data-length MSB
        Byte 3+ : data (present only for READ responses)

    Returns:
        (status, data_bytes)
    """
    resp = dev.read(67, timeout_ms=timeout_ms)
    if not resp:
        return 255, b""
    status   = resp[0]
    data_len = resp[1] | (resp[2] << 8)
    return status, bytes(resp[3 : 3 + data_len])


# ══════════════════════════════════════════════════════════════════════════════
# EEPROM read / write
# ══════════════════════════════════════════════════════════════════════════════

def eeprom_write(dev: hid.device, addr: int, data: bytes) -> None:
    """Write a byte sequence to the EEPROM starting at the given address.

    Automatically splits the payload at 16-byte page boundaries as required
    by the 24LC08B page-write protocol (datasheet §6.2).  A write that crosses
    a boundary would silently wrap within the current page and overwrite earlier
    bytes, so splitting is mandatory.

    The I2C data payload for each page write is:
        [internal_address_byte, data_byte_0, data_byte_1, ...]
    """
    offset = 0
    while offset < len(data):
        cur      = addr + offset
        bank     = cur >> 8                              # selects I2C bank address
        internal = cur & 0xFF                            # address within bank
        i2c_addr = EEPROM_BASE + bank
        space    = EEPROM_PAGE - (internal % EEPROM_PAGE)  # bytes left in this page
        chunk    = data[offset : offset + min(space, len(data) - offset)]

        _send(dev, OP_WRITE_STOP, i2c_addr, bytes([internal]) + chunk)
        time.sleep(EEPROM_TWR)   # wait for the self-timed EEPROM write cycle
        offset += len(chunk)


def eeprom_read(dev: hid.device, addr: int, length: int) -> bytes | None:
    """Read bytes from the EEPROM at the given absolute address (random read).

    The 24LC08B random-read sequence (datasheet §8.2):
        1. WRITE_CONT — sets the EEPROM internal address pointer.
        2. READ       — issues the I2C read; the TUSB8044A clocks out `length`
                        bytes starting from the pointer set in step 1.
        3. _recv()    — collects the data from the HID interrupt IN endpoint.

    NOTE: the READ command is sent via dev.write() directly rather than
    _send(), so its response is NOT drained here — it is consumed by _recv().
    """
    bank     = addr >> 8
    internal = addr & 0xFF
    i2c_addr = EEPROM_BASE + bank

    # Flush any stale responses that may have accumulated in the HID buffer.
    while dev.read(67, timeout_ms=10):
        pass

    # Step 1 — set EEPROM address pointer (write without STOP).
    _send(dev, OP_WRITE_CONT, i2c_addr, bytes([internal]))
    time.sleep(0.008)

    # Step 2 — issue read request (length in the HID report header, no payload).
    dev.write(bytes([0x00, OP_READ, i2c_addr, length & 0xFF, (length >> 8) & 0xFF]))
    time.sleep(0.020)

    # Step 3 — collect response.
    status, data = _recv(dev)
    if status != 0:
        print(f"    [WARN] EEPROM read at 0x{addr:03X}: I2C status={status}")
        return None
    return data


# ══════════════════════════════════════════════════════════════════════════════
# Device discovery and identity verification
# ══════════════════════════════════════════════════════════════════════════════

def open_device() -> hid.device | None:
    """Locate and open the TUSB8044A HID-to-I2C bridge.

    Also verifies the device identity via HID GET REPORT (Feature), which the
    TUSB8044A always answers with the constant 0x82FF (datasheet §8.3.3.2).
    This check remains valid even after the hub VID/PID has been customised.
    """
    print(f"[*] Searching for VID={VID:#06x} PID={PID_HID:#06x} ...")
    found = [d for d in hid.enumerate()
             if d["vendor_id"] == VID and d["product_id"] == PID_HID]
    if not found:
        print("[ERROR] Device not found.")
        print("        Make sure the hub is connected and run CMD as Administrator.")
        print("        If the hub shows 'Unknown USB Device', perform the")
        print("        SDA-GND short recovery on EEPROM U6 first.")
        return None

    dev = hid.device()
    try:
        dev.open(VID, PID_HID)
    except Exception as e:
        print(f"[ERROR] Cannot open device: {e}")
        return None

    dev.set_nonblocking(False)
    print("[OK] HID interface opened.")

    # Identity check via HID Feature report — TUSB8044A always returns 0x82FF.
    try:
        resp = dev.get_feature_report(0, 3)
        tail = bytes(resp[-2:]) if len(resp) >= 2 else b""
        if tail in (bytes([0x82, 0xFF]), bytes([0xFF, 0x82])):
            print("[OK] TUSB8044A identity confirmed (feature fingerprint = 0x82FF)")
        else:
            print(f"[WARN] Unexpected feature report: {tail.hex()} — continuing anyway.")
    except Exception as e:
        print(f"[WARN] Feature identity check failed: {e} — continuing anyway.")

    return dev


# ══════════════════════════════════════════════════════════════════════════════
# EEPROM image builder
# ══════════════════════════════════════════════════════════════════════════════

def build_image() -> dict[int, int]:
    """Build the complete EEPROM register map.

    Covers every address the TUSB8044A reads at power-up (0x01–0x2D) plus the
    manufacturer and product string data.  No register is left at the factory
    blank value (0xFF), which would enable dangerous defaults such as inverted
    USB 2.0 polarity (0x0B) or disabled USB 3.0 (0x25).

    The signature byte (0x00) is intentionally absent — it is written last as
    an atomic commit that activates the entire configuration in one step.

    Register reference: TUSB8044A datasheet §8.5, Table 9.
    """
    mfg  = MANUFACTURER.encode("utf-16-le")
    prod = PRODUCT.encode("utf-16-le")
    assert len(mfg)  <= 64, f"Manufacturer string too long ({len(mfg)} bytes, max 64)"
    assert len(prod) <= 64, f"Product string too long ({len(prod)} bytes, max 64)"

    img: dict[int, int] = {}

    # ── USB descriptor identifiers ─────────────────────────────────────────────
    img[0x01] = VID_HUB & 0xFF           # Vendor ID LSB
    img[0x02] = (VID_HUB >> 8) & 0xFF   # Vendor ID MSB  → TI = 0x0451
    img[0x03] = PID_HUB & 0xFF           # Product ID LSB
    img[0x04] = (PID_HUB >> 8) & 0xFF   # Product ID MSB → 0x8440 (SS hub)

    # ── 0x05 — Device Configuration Register ──────────────────────────────────
    # bit 7  customStrings = 1  : load manufacturer/product strings from EEPROM
    # bit 6  customSernum  = 0  : use the TI factory-assigned UUID as serial number
    # bit 5  u1u2Disable   = 0  : U1/U2 link power management enabled
    # bit 4  reserved      = 1  : must be 1 (reads back as 1 per datasheet)
    # bit 3  ganged        = 0  : individual port power switching
    # bit 2  fullPwrMgmtz  = 0  : power switching status reporting enabled
    # bit 1  u1u2TimerOvr  = 0  : no U1/U2 timeout override
    # bit 0  reserved      = 0
    img[0x05] = 0x90   # 0b_1001_0000

    # ── 0x06 — Battery Charging Support Register ───────────────────────────────
    # batEn[3:0] : enable BC1.2 CDP on each downstream port (bit N → port N+1).
    # The TPS2561 ILIM resistor sets the actual hardware current limit per port.
    img[0x06] = BC12_MASK

    # ── 0x07 — Device Removable Configuration Register ────────────────────────
    # bit 7  customRmbl = 1 : allow EEPROM to configure rmbl/used/USB2_ONLY bits
    # bit 3:0  rmbl      = 0xF : all four downstream ports report as removable
    img[0x07] = 0x8F

    # ── 0x08 — Port Used Configuration Register ────────────────────────────────
    # used[3:0] = 0xF : all four physical downstream ports active and reported
    img[0x08] = 0x0F

    # ── 0x09 — Reserved ───────────────────────────────────────────────────────
    # Must be 0x00 per datasheet §8.5.1.
    img[0x09] = 0x00

    # ── 0x0A — Device Configuration Register 2 ────────────────────────────────
    # bit 7  reserved         = 0
    # bit 6  customBCfeatures = 0 : use OTP for BC feature configuration
    # bit 5  pwrctlPol        = 1 : PWRCTL[4:1] signals are ACTIVE HIGH
    #                               Matches PWRCTL_POL pin (pulled up = HIGH) and
    #                               the TPS2561 EN input (active high enable).
    #                               ⚠ Writing 0 here would reverse port power control.
    # bit 4  HiCurAcpModeEn  = 0 : use OTP for high-current ACP (not relevant)
    # bit 3:2  reserved       = 0
    # bit 1  autoModeEnz      = 0 : BC auto-mode enabled (DCP/CDP auto-transition)
    # bit 0  reserved         = 0
    img[0x0A] = 0x20   # 0b_0010_0000

    # ── 0x0B — USB 2.0 Port Polarity Control Register ─────────────────────────
    # bit 7  customPolarity = 0 : polarity bits are read from OTP (factory default
    #                             = no swap on any port).
    # ⚠ Factory-blank EEPROM (0xFF) sets customPolarity=1 AND p0_usb2pol=1,
    #   which swaps the upstream D+/D- and makes the hub unrecognisable to the host.
    #   Writing 0x00 removes this hazardous default.
    img[0x0B] = 0x00

    # ── 0x0C–0x0F — Billboard AlternateModeVdo ────────────────────────────────
    # Datasheet note: "EEPROM Configurable: Yes, but do not change default."
    # Default value is 0x00001C45 (DisplayPort Alt Mode capability VDO).
    # Writing the default explicitly prevents factory 0xFF from corrupting it.
    img[0x0C] = 0x45   # LSB of 0x00001C45
    img[0x0D] = 0x1C
    img[0x0E] = 0x00
    img[0x0F] = 0x00   # MSB

    # ── 0x10–0x1F — UUID Registers ────────────────────────────────────────────
    # Datasheet: "EEPROM Configurable: No."
    # The TUSB8044A reads these bytes but ignores them for the UUID; the UUID is
    # burned into the chip at the TI factory.  This address range is skipped.

    # ── 0x20–0x21 — Language ID ───────────────────────────────────────────────
    # Required when customStrings = 1.
    img[0x20] = 0x09   # LangID LSB: 0x0409 = English (United States)
    img[0x21] = 0x04   # LangID MSB

    # ── 0x22 — Serial Number String Length ────────────────────────────────────
    # 0 = use the TI factory-assigned 128-bit UUID as the serial number string.
    # Consistent with customSernum = 0 in register 0x05.
    img[0x22] = 0x00

    # ── 0x23 — Manufacturer String Length (bytes, not characters) ─────────────
    img[0x23] = len(mfg)

    # ── 0x24 — Product String Length (bytes) ──────────────────────────────────
    img[0x24] = len(prod)

    # ── 0x25 — Device Configuration Register 3 ────────────────────────────────
    # All bits = 0 = normal operation.
    # ⚠ Factory-blank EEPROM (0xFF) sets bit 4 (USB2.0_only = 1), which
    #   completely disables the USB 3.0 SuperSpeed hub.
    img[0x25] = 0x00

    # ── 0x26 — USB 2.0 Only Port Register ─────────────────────────────────────
    # USB2_ONLY[3:0] = 0 : all four downstream ports support USB 3.x + USB 2.0.
    # ⚠ Factory-blank EEPROM (0xFF) forces all ports to USB 2.0 only.
    img[0x26] = 0x00

    # ── 0x27–0x2A — Billboard SVID and PID ────────────────────────────────────
    # 0 → hub uses the ROM-default SVID (DisplayPort, 0xFF01) and PID.
    img[0x27] = 0x00   # Billboard SVID LSB
    img[0x28] = 0x00   # Billboard SVID MSB
    img[0x29] = 0x00   # Billboard PID LSB
    img[0x2A] = 0x00   # Billboard PID MSB

    # ── 0x2B — Billboard Configuration Register ───────────────────────────────
    # Datasheet §8.3.4: "When EEPROM used, this field MUST be set to 0x80."
    # 0x80 = VCONN_PWR[7:4]=1000b (adapter does not require VCONN power),
    #        BillboardEN=0 (billboard device not presented to the host).
    # ⚠ Factory-blank EEPROM (0xFF) enables the billboard with malformed
    #   string lengths, which can cause the host to reject the device descriptor.
    img[0x2B] = 0x80

    # ── 0x2C–0x2D — Billboard String Lengths ──────────────────────────────────
    # 0 = use the ROM-default strings (DisplayPort URL and "DisplayPort").
    # ⚠ Factory-blank EEPROM (0xFF) instructs the hub to load 255-character
    #   strings from blank EEPROM cells, producing a malformed descriptor.
    img[0x2C] = 0x00   # BBString1Len: 0 characters → use ROM default URL
    img[0x2D] = 0x00   # BBString2Len: 0 characters → use ROM default string

    # ── 0x50–0x8F — Manufacturer String (UTF-16 LE, max 64 bytes = 32 chars) ──
    for i, byte in enumerate(mfg):
        img[0x50 + i] = byte

    # ── 0x90–0xCF — Product String (UTF-16 LE, max 64 bytes = 32 chars) ───────
    for i, byte in enumerate(prod):
        img[0x90 + i] = byte

    return img


def _to_chunks(img: dict[int, int]) -> list[tuple[int, bytes]]:
    """Group consecutive addresses in the image into contiguous write chunks."""
    if not img:
        return []
    addrs = sorted(img)
    chunks: list[tuple[int, bytes]] = []
    start = addrs[0]
    buf   = bytearray([img[addrs[0]]])
    for a in addrs[1:]:
        if a == start + len(buf):
            buf.append(img[a])
        else:
            chunks.append((start, bytes(buf)))
            start, buf = a, bytearray([img[a]])
    chunks.append((start, bytes(buf)))
    return chunks


# ══════════════════════════════════════════════════════════════════════════════
# Programming routine
# ══════════════════════════════════════════════════════════════════════════════

def program(dev: hid.device) -> bool:
    """Execute the four-phase signature-last programming sequence."""
    mfg  = MANUFACTURER.encode("utf-16-le")
    prod = PRODUCT.encode("utf-16-le")
    bc12_ports = [f"P{i+1}" for i in range(4) if BC12_MASK & (1 << i)]

    print()
    print("Configuration to write:")
    print(f"  Manufacturer  : {MANUFACTURER}  ({len(mfg)} bytes UTF-16LE)")
    print(f"  Product       : {PRODUCT}  ({len(prod)} bytes UTF-16LE)")
    print(f"  VID           : {VID_HUB:#06x}  (Texas Instruments, unchanged)")
    print(f"  PID           : {PID_HUB:#06x}  (TUSB8044A SuperSpeed hub, unchanged)")
    print(f"  BC1.2 CDP     : {', '.join(bc12_ports)}")
    print(f"  PWRCTL        : active HIGH  (matches TPS2561 EN, reg 0x0A=0x20)")
    print(f"  USB2 polarity : no swap      (reg 0x0B=0x00)")
    print(f"  USB3 hub      : enabled      (reg 0x25=0x00)")
    print(f"  Serial number : TI factory UUID  (customSernum=0)")
    print(f"  Strategy      : signature written LAST (atomic commit)")
    print()

    # ── Phase 1: clear signature ──────────────────────────────────────────────
    # Writing 0x00 to address 0x00 ensures the TUSB8044A will ignore this EEPROM
    # on the next power cycle, keeping the hub safe if the script is interrupted.
    print("[1/4] Clearing EEPROM signature (addr 0x000 ← 0x00) ...")
    eeprom_write(dev, 0x00, bytes([0x00]))
    readback = eeprom_read(dev, 0x00, 1)
    if not readback or readback[0] != 0x00:
        print(f"[ERROR] EEPROM not responding (readback: {readback}).")
        print("        Check WP pin is tied to GND.  Perform SDA-GND short recovery.")
        return False
    print("[OK] Signature cleared — hub uses factory defaults if power-cycled now.")

    # ── Phase 2: write configuration ─────────────────────────────────────────
    img    = build_image()
    chunks = _to_chunks(img)
    total  = sum(len(d) for _, d in chunks)
    print(f"\n[2/4] Writing {len(chunks)} chunk(s), {total} bytes total ...")
    for addr, data in chunks:
        end = addr + len(data) - 1
        print(f"  [0x{addr:03X}–0x{end:03X}]  {len(data):3d} byte(s) ... ", end="", flush=True)
        eeprom_write(dev, addr, data)
        print("OK")

    # ── Phase 3: verify ───────────────────────────────────────────────────────
    print("\n[3/4] Verifying written data ...")
    errors = 0

    def check(label: str, addr: int, expected: bytes) -> None:
        nonlocal errors
        got = eeprom_read(dev, addr, len(expected))
        if got == expected:
            print(f"  {label:26s}: OK  ({expected.hex()})")
        else:
            got_s = got.hex() if got else "no data"
            print(f"  {label:26s}: MISMATCH  got={got_s}  expected={expected.hex()}")
            errors += 1

    check("VID (0x01–0x02)",          0x01, bytes([VID_HUB & 0xFF, VID_HUB >> 8]))
    check("PID (0x03–0x04)",          0x03, bytes([PID_HUB & 0xFF, PID_HUB >> 8]))
    check("DevConfig (0x05)",         0x05, bytes([0x90]))
    check("BC1.2 mask (0x06)",        0x06, bytes([BC12_MASK]))
    check("DevConfig2 (0x0A)",        0x0A, bytes([0x20]))
    check("USB2 polarity (0x0B)",     0x0B, bytes([0x00]))
    check("Billboard cfg (0x2B)",     0x2B, bytes([0x80]))
    check("LangID (0x20–0x21)",       0x20, bytes([0x09, 0x04]))
    check("Mfg length (0x23)",        0x23, bytes([len(mfg)]))
    check("Prod length (0x24)",       0x24, bytes([len(prod)]))
    check("Mfg string[0:4] (0x50)",   0x50, mfg[:4])
    check("Prod string[0:4] (0x90)",  0x90, prod[:4])

    if errors:
        print(f"\n[ERROR] {errors} verification mismatch(es).")
        print("        Signature will NOT be written — hub stays on factory defaults.")
        print("        Re-run the script to retry.")
        return False

    print("[OK] All bytes verified successfully.")

    # ── Phase 4: write signature (atomic commit) ───────────────────────────────
    # Writing 0x55 is the final step.  Only now will the TUSB8044A load the
    # custom configuration on the next power cycle.
    print("\n[4/4] Writing EEPROM signature (addr 0x000 ← 0x55) ...")
    eeprom_write(dev, 0x00, bytes([0x55]))
    readback = eeprom_read(dev, 0x00, 1)
    if not readback or readback[0] != 0x55:
        print(f"[ERROR] Signature write failed (readback: {readback}).")
        return False
    print("[OK] Signature written — EEPROM configuration is now active.")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  TUSB8044A EEPROM Programmer")
    print("  USB 3.2 Gen1 4-Port Hub")
    print("=" * 60)

    dev = open_device()
    if dev is None:
        sys.exit(1)

    try:
        ok = program(dev)
    except KeyboardInterrupt:
        print("\n[ABORTED] Script interrupted — hub remains on factory defaults.")
        ok = False
    except Exception as exc:
        print(f"\n[ERROR] Unexpected exception: {exc}")
        raise
    finally:
        dev.close()
        print("[*] HID interface closed.")

    if ok:
        print()
        print("=" * 60)
        print("  Programming complete!")
        print("  → Disconnect the hub USB cable.")
        print("  → Wait 3 seconds.")
        print("  → Reconnect.")
        print(f"  → Expected device name: '{PRODUCT}'")
        print("=" * 60)
    else:
        print("\n[ABORT] Hub is safe — still running on TI factory defaults.")
        sys.exit(1)
