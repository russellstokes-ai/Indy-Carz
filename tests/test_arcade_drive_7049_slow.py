"""ROM-free boundary tests for original Z80 slow-drive stage 7049–709B."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from arcade_drive_7049_slow import independent, original_opcodes, verify_original


class Original7049SlowDrivingTests(unittest.TestCase):
    def test_no_borrow_continues_at_real_709c_with_b_preserved(self):
        actual = independent(0, 0, 255, 201, 7, 0x12, 4, 255)
        self.assertEqual((actual["branch"], actual["next_pc"], actual["b"]),
                         ("fast_709c", 0x709C, 0))
        self.assertEqual((actual["ix39"], actual["ix3a"], actual["ix31"]),
                         (185, 7, 0x12))

    def test_borrow_decrements_high_byte_without_fictitious_external_call(self):
        # E765=7FFF -> doubled FF FE -> first XROM=FE, scaling=9F;
        # B=FF saturates to FF, later XROM factors are 9E and 9D.
        actual = independent(255, 0x7FFF, 255, 0, 7, 0, 3, 0)
        self.assertEqual((actual["branch"], actual["next_pc"], actual["b"]),
                         ("fast_709c", 0x709C, 255))
        self.assertEqual((actual["ix39"], actual["ix3a"], actual["ix31"]),
                         (99, 6, 0))
        self.assertEqual(actual["subtrahend"], 157)

    def test_original_zero_high_byte_sets_status_bit_four(self):
        actual = independent(255, 0x7FFF, 255, 0, 1, 0x81, 3, 0)
        self.assertEqual((actual["ix39"], actual["ix3a"], actual["ix31"]),
                         (99, 0, 0x91))
        self.assertEqual(actual["next_pc"], 0x709C)

    def test_unknown_7e5e_call_stops_after_authenticated_mutations(self):
        actual = independent(255, 0x7FFF, 255, 0, 3, 0x00, 3, 3)
        self.assertEqual((actual["branch"], actual["next_pc"]),
                         ("external_7e5e", 0x7E5E))
        self.assertEqual((actual["ix39"], actual["ix3a"]), (99, 2))
        self.assertFalse(actual["complete"])

    def test_unknown_2ad1_call_stops_after_comparison(self):
        actual = independent(255, 0x7FFF, 255, 0, 3, 0, 2, 1)
        self.assertEqual((actual["branch"], actual["next_pc"]),
                         ("external_2ad1", 0x2AD1))
        self.assertFalse(actual["complete"])

    def test_out_of_range_and_unauthenticated_rom_fail_closed(self):
        with self.assertRaises(ValueError):
            independent(256, 0, 0, 0, 0, 0, 0, 0)
        with self.assertRaises(ValueError):
            original_opcodes(bytes(0x90000), 0, 0, 0, 0, 0, 0, 0, 0)
        with self.assertRaises(ValueError):
            verify_original(bytes(0x90000), cases=1)


if __name__ == "__main__":
    unittest.main()
