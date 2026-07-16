#!/usr/bin/env python3
"""
TUSB8044A EEPROM Reader
========================
Reads and dumps the full contents of the configuration EEPROM attached to a
TUSB8044A-based USB 3.2 Gen1 hub via the chip's internal HID-to-I2C bridge
interface (VID=0x0451, PID=0x82FF).

Target EEPROM : Microchip 24LC08BT-I/OT (8 Kbit, SOT-23, I2C)
                Four 256-byte banks accessed via 7-bit I2C addresses:
                    Bank 0 (0x000–0x0FF) : address 0x50
                    Bank 1 (0x100–0x1FF) : address 0x51
                    Bank 2 (0x200–0x2FF) : address 0x52
                    Bank 3 (0x300–0x3FF) : address 0x53

Output
------
    - Hex dump of Bank 0 (the configuration area: registers + strings)
    - Human-readable annotations for every key EEPROM register
    - Decoded manufacturer and product strings
    - Raw binary saved to TUSB8044A_EEPROM.bin (1024 bytes)

Requirements
------------
    pip install hidapi

Usage
-----
    python TUSB8044A_EEPROM_READ.py
    (Administrator privileges are not required for reads on most systems.)
"""

import hid
import time
import sys


# ── HID interface identifiers ─────────────────────────────────────────────────
VID = 0x0451   # Texas Instruments
PID = 0x82FF   # TUSB8044A internal HID-to-I2C bridge

# ── EEPROM bank mapping (24LC08B — 7-bit I2C addresses) ──────────────────────
# Control byte format: 1010 x B1 B0  (x = don't care, B1/B0 = bank select)
# 0x50 = 0b1010_000  → B1=0, B0=0 → Bank 0 (0x000–0x0FF)
# 0x51 = 0b1010_001  → B1=0, B0=1 → Bank 1 (0x100–0x1FF)
# 0x52 = 0b1010_010  → B1=1, B0=0 → Bank 2 (0x200–0x2FF)
# 0x53 = 0b1010_011  → B1=1, B0=1 → Bank 3 (0x300–0x3FF)
BANKS = [
    (0x50, 0x000),
    (0x51, 0x100),
    (0x52, 0x200),
    (0x53, 0x300),
]

# ── Read parameters ───────────────────────────────────────────────────────────
READ_CHUNK = 64   # Bytes requested per HID READ transaction

# ── Output file ───────────────────────────────────────────────────────────────
import pathlib
OUTPUT_FILE = str(pathlib.Path(__file__).parent / "TUSB8044A_EEPROM.bin")

# ── HID opcodes — TUSB8044A datasheet §8.3.3.1 ───────────────────────────────
OP_READ       = 0x01  # Read N bytes from I2C device
OP_WRITE_CONT = 0x03  # Write to I2C device without STOP (sets read address pointer)


# ══════════════════════════════════════════════════════════════════════════════
# Low-level I2C helpers
# ══════════════════════════════════════════════════════════════════════════════

def set_eeprom_address(dev: hid.device, i2c_addr: int, addr: int) -> None:
    """Set the EEPROM internal address pointer using a WRITE_CONT transaction.

    This is the first half of a 24LC08B random read (datasheet §8.2):
    the host sends the internal address byte to latch the pointer, without
    generating a STOP condition.  The subsequent READ picks up from that pointer.

    HID SET REPORT wire format (TUSB8044A §8.3.3.1):
        Byte 0  : HID report ID (0x00 — device uses no report IDs)
        Byte 1  : opcode (0x03 = WRITE_CONT)
        Byte 2  : I2C slave address (7-bit)
        Byte 3  : data-length LSB = 0x01 (one byte of data follows)
        Byte 4  : data-length MSB = 0x00
        Byte 5  : internal EEPROM address byte
    """
    report = bytes([
        0x00,          # HID report ID
        OP_WRITE_CONT,
        i2c_addr,
        0x01,          # payload length LSB
        0x00,          # payload length MSB
        addr & 0xFF,   # EEPROM internal address
    ])
    dev.write(report)
    time.sleep(0.005)
    dev.read(67, timeout_ms=200)   # drain the WRITE_CONT acknowledgment


def read_chunk(dev: hid.device, i2c_addr: int, length: int = READ_CHUNK) -> bytes:
    """Read `length` bytes from the EEPROM starting at the current address pointer.

    The address must have been set by set_eeprom_address() before calling this.

    HID SET REPORT for READ (TUSB8044A §8.3.3.1):
        Byte 0  : HID report ID (0x00)
        Byte 1  : opcode (0x01 = READ)
        Byte 2  : I2C slave address (7-bit)
        Byte 3  : number of bytes to read, LSB
        Byte 4  : number of bytes to read, MSB

    HID GET REPORT response (TUSB8044A §8.3.3.3):
        Byte 0  : status (0 = success)
        Byte 1  : returned-length LSB
        Byte 2  : returned-length MSB
        Byte 3+ : data
    """
    dev.write(bytes([
        0x00,
        OP_READ,
        i2c_addr,
        length & 0xFF,
        (length >> 8) & 0xFF,
    ]))
    time.sleep(0.030)   # allow time for the I2C read to complete

    resp = dev.read(67, timeout_ms=2000)
    if not resp:
        print("    [WARN] No response — returning zeros.")
        return bytes(length)

    status   = resp[0]
    data_len = resp[1] | (resp[2] << 8)

    if status != 0:
        print(f"    [WARN] I2C read status={status} "
              f"(1=timeout, 2=addr NAK, 3=data NAK) — returning zeros.")
        return bytes(length)

    return bytes(resp[3 : 3 + data_len])


def read_bank(dev: hid.device, i2c_addr: int, base_addr: int) -> bytes:
    """Read all 256 bytes from one EEPROM bank in READ_CHUNK-sized transactions."""
    data = bytearray()
    for offset in range(0, 0x100, READ_CHUNK):
        addr = base_addr + offset
        print(f"    [0x{addr:03X}] ", end="", flush=True)
        set_eeprom_address(dev, i2c_addr, addr)
        chunk = read_chunk(dev, i2c_addr)
        data.extend(chunk)
        print(f"read {len(chunk)} bytes")
    return bytes(data)


# ══════════════════════════════════════════════════════════════════════════════
# Output formatting
# ══════════════════════════════════════════════════════════════════════════════

def print_hex_dump(data: bytes, start: int = 0x000, end: int = 0x100) -> None:
    """Print a formatted hex + ASCII dump of data[start:end]."""
    for i in range(start, min(end, len(data)), 16):
        row   = data[i:i+16]
        hex_s = " ".join(f"{b:02X}" for b in row)
        asc_s = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        print(f"  0x{i:03X}: {hex_s:<47}  {asc_s}")


def annotate_registers(data: bytes) -> None:
    """Print human-readable annotations for every key EEPROM register."""

    def show(label: str, addr: int, length: int = 1, note: str = "") -> None:
        raw     = data[addr : addr + length]
        hex_str = " ".join(f"{b:02X}" for b in raw)
        print(f"  0x{addr:02X}  {label:22s}: {hex_str}  {note}")

    print()
    print("=== KEY REGISTER VALUES ===")
    show("Signature",        0x00, note="(0x55 = EEPROM valid, any other = ignored)")
    show("VID",              0x01, 2,   f"= 0x{data[0x02]:02X}{data[0x01]:02X}")
    show("PID",              0x03, 2,   f"= 0x{data[0x04]:02X}{data[0x03]:02X}")
    show("DevConfig",        0x05, note="bit7=customStrings, bit4=1 (reserved)")
    show("BC1.2 mask",       0x06, note="bit N enables BC1.2 CDP on port N+1")
    show("DevRemovable",     0x07, note="bit7=customRmbl, bits3:0=rmbl mask")
    show("PortUsed",         0x08, note="bits3:0 = active port mask")
    show("Reserved",         0x09, note="must be 0x00")
    show("DevConfig2",       0x0A, note="bit5=pwrctlPol (0x20 → active HIGH)")
    show("USB2 polarity",    0x0B, note="0x00 = no swap  |  0xFF = swap D+/D- ⚠")
    show("Billboard VDO",    0x0C, 4,   f"= 0x{data[0x0F]:02X}{data[0x0E]:02X}"
                                         f"{data[0x0D]:02X}{data[0x0C]:02X}")
    print()
    show("LangID",           0x20, 2,   "(0x09 0x04 = English United States)")
    show("SerialLen",        0x22, note="0x00 = use TI factory UUID")
    show("MfgStringLen",     0x23, note=f"= {data[0x23]} bytes ({data[0x23]//2} chars)")
    show("ProdStringLen",    0x24, note=f"= {data[0x24]} bytes ({data[0x24]//2} chars)")
    show("DevConfig3",       0x25, note="0x00 = USB3 enabled  |  bit4=1 disables SS ⚠")
    show("USB2_ONLY",        0x26, note="0x00 = all ports USB3+2  |  0x0F = USB2 only ⚠")
    show("BB_SVID",          0x27, 2)
    show("BB_PID",           0x29, 2)
    show("BB_Config",        0x2B, note="must be 0x80 when EEPROM is used")
    show("BBString1Len",     0x2C, note="0 = use ROM-default URL string")
    show("BBString2Len",     0x2D, note="0 = use ROM-default Alt Mode string")

    print()
    print("=== STRING DATA ===")
    mfg_len  = data[0x23]
    prod_len = data[0x24]
    mfg_raw  = data[0x50 : 0x50 + mfg_len]
    prod_raw = data[0x90 : 0x90 + prod_len]

    print(f"  Manufacturer (0x50–0x{0x50 + mfg_len - 1:02X}): {mfg_raw.hex()}")
    try:
        print(f"    → \"{mfg_raw.decode('utf-16-le')}\"")
    except Exception as exc:
        print(f"    → DECODE ERROR: {exc}")

    print(f"  Product      (0x90–0x{0x90 + prod_len - 1:02X}): {prod_raw.hex()}")
    try:
        print(f"    → \"{prod_raw.decode('utf-16-le')}\"")
    except Exception as exc:
        print(f"    → DECODE ERROR: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 55)
    print("  TUSB8044A EEPROM Reader")
    print("  USB 3.2 Gen1 4-Port Hub")
    print("=" * 55)

    dev = hid.device()
    try:
        print(f"[*] Opening VID={VID:#06x} PID={PID:#06x} ...")
        dev.open(VID, PID)
        dev.set_nonblocking(False)
        print("[OK] Device opened\n")

        full = bytearray()

        for i2c_addr, base in BANKS:
            print(f"[*] Reading Bank {base >> 8}  "
                  f"(I2C 0x{i2c_addr:02X}, EEPROM 0x{base:03X}–0x{base + 0xFF:03X})")
            bank_data = read_bank(dev, i2c_addr, base)
            full.extend(bank_data)
            print()

        full = bytes(full)
        print(f"[OK] Read {len(full)} bytes total.")

        # Save binary
        with open(OUTPUT_FILE, "wb") as f:
            f.write(full)
        print(f"[OK] Saved to {OUTPUT_FILE}\n")

        # Hex dump of the configuration bank (Bank 0)
        print("=== HEX DUMP — Bank 0 / Configuration Area (0x000–0x0FF) ===")
        print_hex_dump(full, 0x000, 0x100)

        # Register annotations and string decode
        annotate_registers(full)

    except Exception as exc:
        print(f"[ERROR] {exc}")
        raise
    finally:
        dev.close()
        print("\n[*] Device closed.")


if __name__ == "__main__":
    main()
