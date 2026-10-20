"""Synthetic-only regression tests for original 6912-record contact lookup.
No proprietary ROM or derived lookup records are included.
"""
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import arcade_collision_contact_table as ct

ORIGINAL_STAGE_SHAPE = bytes.fromhex(
    "08 67 2E 0C 22 FC FF 2A FC FF 08 85 6F D2 B4 B4 24 "
    "29 29 29 29 FD 7E BD DD 96 BD E6 F0 32 22 E9 "
    "0F 0F 0F 0F B5 6F 54 5D 29 19 7C C6 20 67 7E B7 F0"
)


def fake_data():
    m = bytearray(0x90000)
    x = bytearray(0x40000)
    m[ct.START:ct.STOP] = ORIGINAL_STAGE_SHAPE
    m[0xAD61:0xAD61+len(ct.BANK_SELECTION)] = ct.BANK_SELECTION
    m[0xB3A6:0xB3A6+len(ct.BANK_RESTORE)] = ct.BANK_RESTORE
    for first in range(18):
        index = 2 * ((first << 8) | 12)
        word = first*24
        x[index:index+2] = word.to_bytes(2, "little")
    for ordinal in range(6912):
        # Deliberately synthetic response data, not the arcade lookup table.
        i = ct.BANK5_OFFSET + ordinal*3
        m[i:i+3] = bytes((0x9B if ordinal < 4635 else 0, ordinal & 255,
                          (ordinal>>8) & 255))
    return bytes(m), bytes(x)


class OriginalContactLookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master, cls.xrom = fake_data()

    def test_original_stage_instruction_span(self):
        self.assertEqual(len(ORIGINAL_STAGE_SHAPE), ct.STOP-ct.START)
        self.assertEqual((ct.START, ct.STOP), (0xB4A3,0xB4D4))
        self.assertEqual(ct.TABLE_BYTES, 20736)

    def test_exact_original_indexing_and_gate(self):
        table = self.master[ct.BANK5_OFFSET:ct.BANK5_OFFSET+ct.TABLE_BYTES]
        for first, second, sector in ((0,0,0), (0,0,15), (0,23,15),
                                      (9,12,8), (17,23,15)):
            expected = ct.independent_contact(table, first, second, sector)
            actual = ct.original_z80(self.master,self.xrom,first,second,sector)
            self.assertEqual(actual,expected)
        self.assertEqual(ct.source_slot(17,23,15), 20733)
        self.assertEqual(ct.source_slot(0,0,0), 0)

    def test_all_6912_original_opcode_lookups_with_synthetic_table(self):
        table = self.master[ct.BANK5_OFFSET:ct.BANK5_OFFSET+ct.TABLE_BYTES]
        accepted = 0
        for first in range(18):
            for second in range(24):
                for sector in range(16):
                    actual = ct.original_z80(self.master,self.xrom,first,second,sector)
                    self.assertEqual(actual,ct.independent_contact(table,first,second,sector))
                    accepted += not actual[2]
        self.assertEqual(accepted,4635)

    def test_private_checksum_and_bank_selection_gate(self):
        with self.assertRaisesRegex(ValueError,"Original checksum"):
            ct.inspect(self.master,self.xrom)
        m = bytearray(self.master)
        m[0xAD68] ^= 1
        with patch.object(ct,"MASTER_SHA",hashlib.sha256(m).hexdigest()), \
             patch.object(ct,"XROM_SHA",hashlib.sha256(self.xrom).hexdigest()), \
             patch.object(ct,"STAGE_SHA",hashlib.sha256(m[ct.START:ct.STOP]).hexdigest()), \
             patch.object(ct,"CONTACT_TABLE_SHA",hashlib.sha256(m[ct.BANK5_OFFSET:ct.BANK5_OFFSET+ct.TABLE_BYTES]).hexdigest()):
            with self.assertRaisesRegex(ValueError,"bank-5 selection"):
                ct.inspect(bytes(m),self.xrom)

    def test_invalid_table_indices_rejected(self):
        for abc in ((18,0,0),(0,24,0),(0,0,16),(-1,0,0)):
            with self.assertRaises(ValueError):
                ct.source_slot(*abc)


if __name__ == "__main__":
    unittest.main()
