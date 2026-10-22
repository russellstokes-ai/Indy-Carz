"""Original-Z80-free tests of bounded early return gates inside 7E5E."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from arcade_drive_7e5e_returns import independent, original_opcodes, verify_original


class Original7E5EEarlyReturnTests(unittest.TestCase):
    def test_already_marked_car_returns_without_side_effects(self):
        actual = independent(0x40, 9, 1, 1, 7, 0, 4, 5, 1, 11)
        self.assertEqual((actual["branch"], actual["next_pc"], actual["ix3a"]),
                         ("return_flag", 0x7091, 11))

    def test_unresolved_event_dispatch_does_not_fake_effects(self):
        actual = independent(0, 1, 4, 0, 0, 128, 10, 10, 0, 4)
        self.assertEqual((actual["branch"], actual["next_pc"], actual["ix3a"]),
                         ("dispatch_7ea3", 0x7EA3, 4))
        self.assertFalse(actual["complete"])

    def test_special_signed_compare_sets_exact_original_high_byte(self):
        actual = independent(0, 0, 4, 0, 1, 128, 10, 10, 0, 4)
        self.assertEqual((actual["branch"], actual["next_pc"], actual["ix3a"]),
                         ("return_special", 0x7091, 0x48))

    def test_equal_comparison_is_an_original_early_return(self):
        actual = independent(0, 0, 3, 1, 3, 0, 10, 10, 0, 4)
        self.assertEqual((actual["branch"], actual["next_pc"]),
                         ("return_equal", 0x7091))

    def test_neighbor_return_requires_original_ix51_threshold(self):
        high = independent(0, 0, 3, 1, 3, 0, 11, 10, 30, 4)
        low = independent(0, 0, 3, 1, 3, 0, 11, 10, 29, 4)
        self.assertEqual((high["branch"], high["next_pc"]),
                         ("return_neighbor", 0x7091))
        self.assertEqual((low["branch"], low["next_pc"]),
                         ("dispatch_7ea3", 0x7EA3))

    def test_unauthenticated_rom_and_out_of_range_values_fail(self):
        with self.assertRaises(ValueError):
            independent(256, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        with self.assertRaises(ValueError):
            original_opcodes(bytes(0x90000), *(0 for _ in range(10)))
        with self.assertRaises(ValueError):
            verify_original(bytes(0x90000), 1)


if __name__ == "__main__":
    unittest.main()
