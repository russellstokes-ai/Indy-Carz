"""Synthetic-only test of exact original Z80 collision-table lookup mechanism."""
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import arcade_collision_bank5_lookup as lookup

INDEX_STAGE = bytes.fromhex(
    "08 67 2e 0c 22 fc ff 2a fc ff 08 85 6f d2 b4 b4 24 "
    "29 29 29 29 fd 7e bd dd 96 bd e6 f0 32 22 e9 "
    "0f 0f 0f 0f b5 6f 54 5d 29 19 7c c6 20 67 7e b7 f0"
)


def synthetic_roms():
    m = bytearray(0x90000)
    m[0xB4A3:0xB4D4] = INDEX_STAGE
    m[0xAD64:0xAD6D] = bytes.fromhex("e6 f0 f6 05 32 08 e6 d3 f4")
    m[0xB3A6:0xB3B1] = bytes.fromhex("3a 08 e6 e6 f0 32 08 e6 d3 f4 c9")
    m[0xB4D4:0xB4EE] = bytes.fromhex(
        "ed 5b 28 e9 ed 53 2a e9 22 28 e9 32 19 e9 "
        "3a 27 e9 3c 32 27 e9 fe 03 da 06 b5"
    )
    m[0xB506:0xB510] = bytes.fromhex(
        "23 7e 32 1a e9 23 7e 32 1b e9"
    )
    table = bytearray(lookup.TABLE_BYTES)
    for row in range(lookup.GRID_HEIGHT):
        for col in range(lookup.GRID_WIDTH):
            for heading in range(lookup.HEADINGS):
                entry_index = ((row * 24 + col)*16 + heading)*3
                table[entry_index] = ((row*7 + col*3 + heading) & 127) | (
                    128 if (row+col+heading) % 3 == 0 else 0)
                table[entry_index+1] = row + 10
                table[entry_index+2] = col + 20
    m[lookup.BANK5_OFFSET:lookup.BANK5_OFFSET+lookup.TABLE_BYTES] = table
    x = bytearray(0x40000)
    for row in range(lookup.GRID_HEIGHT):
        addr = 2*((row<<8)|12)
        product = row * 12 * 2
        x[addr] = product & 255
        x[addr+1] = product >> 8
    return bytes(m), bytes(x), bytes(table)


class ContactTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master, cls.xrom, cls.table = synthetic_roms()

    def test_complete_record_dimensions_and_index_limits(self):
        self.assertEqual(len(INDEX_STAGE), lookup.END-lookup.START)
        self.assertEqual(lookup.TABLE_BYTES, 20736)
        self.assertEqual(lookup.independent_index(0, 0, 0), 0)
        self.assertEqual(lookup.independent_index(17, 23, 0xF0), 6911)
        self.assertEqual(lookup.independent_lookup(self.table, 17, 23, 0xF0)[0], 0x70FD)
        with self.assertRaises(ValueError):
            lookup.independent_index(18, 23, 0)
        with self.assertRaises(ValueError):
            lookup.independent_index(17, 24, 0)

    def test_original_opcode_interpreter_vs_independent_formula(self):
        for row in (0, 1, 5, 9, 11, 17):
            for col in (0, 1, 7, 15, 23):
                for heading in (0, 1, 4, 8, 12, 15):
                    ix = 250  # deliberate 8-bit heading wrapping
                    iy = (ix + 16*heading) & 255
                    expected = lookup.independent_lookup(self.table, row, col, (iy-ix)&255)
                    actual = lookup.execute_original(self.master, self.xrom, self.table,
                                                     row, col, iy, ix)
                    self.assertEqual(actual, expected, (row, col, heading))

    def test_subbyte_orientation_is_discarded(self):
        one = lookup.independent_lookup(self.table, 9, 12, 0x5A)
        two = lookup.independent_lookup(self.table, 9, 12, 0x50)
        self.assertEqual(one, two)
        self.assertNotEqual(one, lookup.independent_lookup(self.table, 9, 12, 0x60))

    def test_source_integrity_gate_requires_authentic_binary(self):
        with self.assertRaisesRegex(ValueError, "checksum-verified"):
            lookup.source_assertions(self.master, self.xrom)
        with patch.object(lookup, "MASTER_SHA", hashlib.sha256(self.master).hexdigest()), \
             patch.object(lookup, "XROM_SHA", hashlib.sha256(self.xrom).hexdigest()), \
             patch.object(lookup, "STAGE_SHA", hashlib.sha256(INDEX_STAGE).hexdigest()), \
             patch.object(lookup, "TABLE_SHA", hashlib.sha256(self.table).hexdigest()):
            self.assertEqual(lookup.source_assertions(self.master, self.xrom), self.table)

    def test_index_interpreter_fails_closed_on_unknown_opcode(self):
        mutated = bytearray(self.master)
        mutated[0xB4B4] = 0xFF
        with self.assertRaisesRegex(ValueError, "Unexpected original"):
            lookup.execute_original(bytes(mutated), self.xrom, self.table,
                                    0, 1, 10, 10)


if __name__ == "__main__":
    unittest.main()
