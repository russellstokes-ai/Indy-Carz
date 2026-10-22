"""ROM-free exact six-slot first-round linked data reset tests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_round_zero_linked_reset import (
    START, STOP, HELPER, HELPER_STOP,
    SLOTS, CLEARED_OFFSETS, independent, opcode, verify,
)


class OriginalRoundZeroLinkedResetTests(unittest.TestCase):
    def test_original_cpu_stage_and_pointer_helper(self):
        self.assertEqual((START, STOP), (0x2953, 0x298A))
        self.assertEqual((HELPER, HELPER_STOP), (0x1783, 0x178D))

    def test_six_original_slots_not_only_five_car_records(self):
        self.assertEqual(SLOTS,
                         (0xE580, 0xE480, 0xE380, 0xE280, 0xE180, 0xE080))
        self.assertEqual(len(SLOTS), 6)

    def test_original_offsets_include_repeated_byte_clears(self):
        self.assertEqual(CLEARED_OFFSETS, (1, 3, 2, 4, 5, 9, 3, 2, 12))
        self.assertEqual(len(set(CLEARED_OFFSETS)), 7)

    def test_full_original_linked_writes_are_ordered(self):
        pointers = (0xE600, 0xE620, 0xE640, 0xE660, 0xE680, 0xE6A0)
        result = independent(pointers)
        self.assertEqual(len(result["writes"]), 54)
        self.assertEqual(result["writes"][:9],
                         [((pointers[0]+off) & 65535, 0) for off in CLEARED_OFFSETS])
        self.assertEqual(result["writes"][-9:],
                         [((pointers[-1]+off) & 65535, 0) for off in CLEARED_OFFSETS])
        self.assertEqual(result["slot_visits"], list(SLOTS))

    def test_original_z80_dec_b_loops_six_times(self):
        result = independent((0, 0, 0, 0, 0, 0))
        self.assertEqual((result["final_ix"], result["final_b"], result["stop_pc"]),
                         (0xDF80, 0xFF, 0x2989))
        self.assertEqual(result["destinations_per_slot"], 9)

    def test_pointer_aliases_retain_duplicate_writes(self):
        result = independent((0xE600,)*6)
        self.assertEqual(result["writes"][:9], result["writes"][-9:])
        self.assertEqual(len(result["writes"]), 54)

    def test_carry_over_ffff_does_not_clip_original_bus_address(self):
        result = independent((0xFFFC,)*6)
        self.assertEqual(result["writes"][0][0], 0xFFFD)
        self.assertEqual(result["writes"][1][0], 0xFFFF)
        self.assertEqual(result["writes"][2][0], 0xFFFE)
        self.assertEqual(result["writes"][3][0], 0x0000)
        self.assertEqual(result["writes"][5][0], 0x0005)

    def test_invalid_pointers_and_fake_original_fail_closed(self):
        with self.assertRaises(ValueError):
            independent((1, 2, 3))
        with self.assertRaises(ValueError):
            independent((0, 0, 0, 0, 0, 65536))
        with self.assertRaises(ValueError):
            opcode(bytes(0x90000), (0, 0, 0, 0, 0, 0))
        with self.assertRaisesRegex(ValueError, "checksum-verified"):
            verify(bytes(0x90000), 0)


if __name__ == "__main__":
    unittest.main()
