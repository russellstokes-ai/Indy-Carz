"""Synthetic tests: no proprietary ROM data required."""
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_rom_recovery import (
    MASTER_NAMES, SLAVE_NAMES, XROM_NAMES, ROMS,
    bank_metadata, read_and_verify_roms, reconstruct_regions, rotate_memory,
)

class RomRecoveryTests(unittest.TestCase):
    def make_fake_roms(self):
        roms = {name: bytes([i + 1]) * expected[0]
                for i, (name, expected) in enumerate(ROMS.items())}
        # Differentiate the two ROM_CONTINUE halves.
        roms[SLAVE_NAMES[1]] = b"A" * 0x20000 + b"B" * 0x20000
        roms[SLAVE_NAMES[2]] = b"C" * 0x20000 + b"D" * 0x20000
        # Differentiate the master ROM_RELOAD halves.
        roms[MASTER_NAMES[0]] = b"E" * 0x10000 + b"F" * 0x10000
        return roms

    def test_rom_continue_and_reload(self):
        images = reconstruct_regions(self.make_fake_roms())
        master, slave = images["master"], images["slave"]
        self.assertEqual((len(master), len(slave)), (0x90000, 0x160000))
        self.assertEqual(master[0x00000], ord("E"))
        self.assertEqual(master[0x0ffff], ord("E"))
        self.assertEqual(master[0x10000], ord("E"))  # second ROM_LOAD overlaps
        self.assertEqual(master[0x20000], ord("F"))
        self.assertEqual(slave[0x20000], ord("A"))
        self.assertEqual(slave[0x120000], ord("B"))
        self.assertEqual(slave[0x40000], ord("C"))
        self.assertEqual(slave[0x140000], ord("D"))

    def test_even_odd_xrom_interleave(self):
        roms = self.make_fake_roms()
        roms[XROM_NAMES[0]] = b"\x12" * 0x20000
        roms[XROM_NAMES[1]] = b"\x34" * 0x20000
        xrom = reconstruct_regions(roms)["xrom"]
        self.assertEqual(xrom[:8], bytes.fromhex("1234123412341234"))
        self.assertEqual(len(xrom), 0x40000)

    def test_rotate_memory_keeps_fixed_prefix(self):
        base = bytearray(b"P" * 0x10000 + b"A" * 0x2000 +
                         b"B" * 0x2000 + b"C" * 0x2000 + b"D" * 0x2000)
        rotate_memory(base)
        self.assertEqual(base[:0x10000], b"P" * 0x10000)
        self.assertEqual(base[0x10000:0x12000], b"B" * 0x2000)
        self.assertEqual(base[0x12000:0x14000], b"C" * 0x2000)
        self.assertEqual(base[0x14000:0x16000], b"D" * 0x2000)
        self.assertEqual(base[0x16000:0x18000], b"A" * 0x2000)

    def test_bank_table_matches_mame(self):
        banks = bank_metadata(0x160000)
        self.assertEqual(banks["master_bank_region_offsets"][0], "002000")
        self.assertEqual(banks["master_bank_region_offsets"][15], "088000")
        self.assertEqual(banks["slave_bank_control_to_region_offset"]["00"], "002000")
        self.assertEqual(banks["slave_bank_control_to_region_offset"]["01"], "010000")
        self.assertEqual(banks["slave_bank_control_to_region_offset"]["11"], "018000")
        self.assertEqual(banks["slave_bank_control_to_region_offset"]["21"], "110000")

    def test_reject_incomplete_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "indyheat.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("README.txt", "not the game")
            with self.assertRaisesRegex(ValueError, "Missing rev-1 program ROMs"):
                read_and_verify_roms(archive)

if __name__ == "__main__":
    unittest.main()
