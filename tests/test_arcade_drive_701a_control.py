"""ROM-free checks for the original 701A gate after original 75F2 return."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from arcade_drive_701a_control import START, STAGE_SHA, independent, original_opcodes, verify_original


class OriginalDrive701AControlTests(unittest.TestCase):
    def test_stage_start_and_hash(self):
        self.assertEqual(START, 0x701A)
        self.assertEqual(len(STAGE_SHA), 64)

    def test_special_7d4c_call_fails_closed_before_unverified_effect(self):
        r = independent(ix5c=1, ix57=0xFF, ix31=0x10, ix33=1, counter=0xA5)
        self.assertEqual((r["branch"], r["next_pc"], r["counter"], r["b"]),
                         ("special_7d4c", 0x7D4C, 0xA5, None))

    def test_fast_drive_route_increment_wraps_and_uses_actual_slot1(self):
        r = independent(ix5c=0, ix57=255, ix31=0x10, ix33=0, counter=255)
        self.assertEqual((r["branch"], r["next_pc"], r["counter"], r["b"]),
                         ("fast_709c", 0x709C, 0, 96))

    def test_alternative_fast_bit0_gate(self):
        r = independent(ix5c=0, ix57=128, ix31=0, ix33=1, counter=6)
        self.assertEqual((r["branch"], r["counter"], r["b"]),
                         ("fast_709c", 7, 48))

    def test_slow_route_resets_original_ix_minus_1d_before_7049(self):
        r = independent(ix5c=0, ix57=128, ix31=0, ix33=0, counter=0xCC)
        self.assertEqual((r["branch"], r["next_pc"], r["counter"], r["b"]),
                         ("slow_7049", 0x7049, 0, 128))

    def test_rejects_fake_master_or_out_of_range_values(self):
        with self.assertRaises(ValueError):
            independent(-1, 0, 0, 0, 0)
        with self.assertRaises(ValueError):
            independent(0, 256, 0, 0, 0)
        with self.assertRaises(ValueError):
            original_opcodes(bytes(100), 0, 0, 0, 0, 0)
        with self.assertRaises(ValueError):
            verify_original(bytes(0x90000), 10)


if __name__ == "__main__":
    unittest.main()
