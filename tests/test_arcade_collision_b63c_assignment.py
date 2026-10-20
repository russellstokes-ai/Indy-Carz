"""ROM-free tests for the original B63C two-car correction application model."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_b63c_assignment import (
    START, END, independent, execute_original, verify,
)
from arcade_collision_geometry_push import u16


class TwoCarCorrectionTests(unittest.TestCase):
    def test_exact_stage_boundary(self):
        self.assertEqual((START, END), (0xB63C, 0xB67E))
        self.assertEqual(END-START, 66)

    def test_both_original_bit1_set_delegates(self):
        left, right = bytearray(256), bytearray(256)
        left[0x7C] = right[0x7C] = 2
        self.assertEqual(independent(bytes(left), bytes(right), 2, 3),
                         ("delegated_B4EE", bytes(left), bytes(right)))

    def test_only_second_car_receives_doubled_correction(self):
        left, right = bytearray(256), bytearray(256)
        left[0x7C] = 2
        decision, left_after, right_after = independent(bytes(left), bytes(right), 1, 2)
        self.assertEqual(decision, "IY:applied")
        self.assertEqual(left_after, bytes(left))
        self.assertEqual(u16(right_after, 0x00), 2)
        self.assertEqual(u16(right_after, 0x08), 2)
        self.assertEqual(u16(right_after, 0x0A), 4)
        self.assertEqual(u16(right_after, 0x12), 4)
        self.assertTrue(right_after[0x7C] & 0x40)

    def test_only_first_car_receives_doubled_correction(self):
        left, right = bytearray(256), bytearray(256)
        right[0x7C] = 2
        decision, left_after, right_after = independent(bytes(left), bytes(right), 1, 2)
        self.assertEqual(decision, "IX:applied")
        self.assertEqual(u16(left_after, 0), 2)
        self.assertEqual(u16(left_after, 0x0A), 4)
        self.assertEqual(right_after, bytes(right))

    def test_both_car_carry_affects_reversed_second_vector(self):
        left, right = bytearray(256), bytearray(256)
        left[0x12:0x14] = bytes.fromhex("ffff")
        decision, out_l, out_r = independent(bytes(left), bytes(right), 2, 3)
        self.assertEqual(decision, "IY:applied")
        self.assertEqual(u16(out_l, 0), 2)
        self.assertEqual(u16(out_l, 0x12), 2)
        # First translation's final ADD overflows 0xFFFF + 3.
        self.assertEqual(u16(out_r, 0), 0xFFFD)
        # Second SBC HL,DE additionally borrows from first SBC HL,BC.
        self.assertEqual(u16(out_r, 0x0A), 0xFFFC)

    def test_nonlocal_scheduler_escape_is_not_silent_success(self):
        zero = bytes(256)
        self.assertEqual(independent(zero, zero, 0x0500, 1)[0], "IX:escape_on_B")
        self.assertEqual(independent(zero, zero, 1, 0x0500)[0], "IX:escape_on_D")

    def test_fail_closed_on_invalid_master(self):
        with self.assertRaisesRegex(ValueError, "Unexpected original contact-assignment"):
            execute_original(bytes(0x90000), bytes(256), bytes(256), 1, 2)
        with self.assertRaisesRegex(ValueError, "checksum-verified original"):
            verify(bytes(0x90000), cases=0)
        with self.assertRaises(ValueError):
            independent(bytes(255), bytes(256), 1, 2)


if __name__ == "__main__":
    unittest.main()
