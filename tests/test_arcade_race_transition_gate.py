"""ROM-free regression of 1991 arcade championship timer and 3-slot gate."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_race_transition_gate import (
    TIMER_START, TIMER_STOP, GATE_START, GATE_STOP,
    independent_timer, independent_gate, check_original, opcode_timer,
)


def slots(*pairs):
    return tuple(pairs)


class OriginalRaceTransitionTests(unittest.TestCase):
    def test_exact_original_cpu_stage_ranges(self):
        self.assertEqual((TIMER_START, TIMER_STOP), (0x6218, 0x6228))
        self.assertEqual((GATE_START, GATE_STOP), (0x627C, 0x62A9))

    def test_original_final_event_gets_distinct_counter(self):
        self.assertEqual([independent_timer(i) for i in range(15)],
                         [132]*14 + [198])

    def test_auto_advance_when_all_three_slots_pass_either_bit0(self):
        data = slots((1, 0), (0, 1), (1, 1))
        self.assertEqual(independent_gate(0, data, 133),
                         {"e7d2": 133, "next_pc": 0x62A9,
                          "readiness_gate": True, "countdown_decremented": False})

    def test_one_failing_slot_uses_original_16bit_timer(self):
        data = slots((1, 0), (0, 0), (1, 1))
        result = independent_gate(0, data, 132)
        self.assertEqual((result["next_pc"], result["e7d2"], result["readiness_gate"]),
                         (0x624C, 131, False))

    def test_global_e603_nonzero_forces_countdown(self):
        data = slots((1, 1), (1, 1), (1, 1))
        for global_byte in (1, 2, 128, 255):
            result = independent_gate(global_byte, data, 132)
            self.assertEqual((result["next_pc"], result["e7d2"]), (0x624C, 131))

    def test_final_countdown_tick_enters_round_selection(self):
        data = slots((0, 0), (1, 0), (0, 0))
        result = independent_gate(0, data, 1)
        self.assertEqual(result["next_pc"], 0x62A9)
        self.assertEqual(result["e7d2"], 0)
        self.assertFalse(result["readiness_gate"])
        self.assertTrue(result["countdown_decremented"])

    def test_zero_countdown_underflows_to_ffff_not_next_round(self):
        data = slots((0, 0), (0, 0), (0, 0))
        result = independent_gate(0, data, 0)
        self.assertEqual((result["next_pc"], result["e7d2"]), (0x624C, 0xFFFF))

    def test_original_bit0_only_not_any_nonzero_byte(self):
        data = slots((0xFE, 0x80), (2, 128), (0xF0, 0xFE))
        result = independent_gate(0, data, 10)
        self.assertFalse(result["readiness_gate"])
        self.assertEqual(result["e7d2"], 9)

    def test_other_slot_bytes_are_irrelevant(self):
        data = slots((0xFF, 0xC0), (0x84, 0xFF), (0xFF, 0x00))
        result = independent_gate(0, data, 1)
        self.assertTrue(result["readiness_gate"])

    def test_reject_invalid_state_and_untrusted_original_rom(self):
        with self.assertRaises(ValueError):
            independent_timer(15)
        with self.assertRaises(ValueError):
            independent_gate(0, slots((1, 1), (1, 1)), 0)
        with self.assertRaises(ValueError):
            independent_gate(256, slots((0,0),(0,0),(0,0)), 1)
        with self.assertRaises(ValueError):
            independent_gate(0, slots((0,0),(0,0),(0,0)), 65536)
        with self.assertRaisesRegex(ValueError, "checksum-verified"):
            check_original(bytes(0x90000))
        with self.assertRaises(ValueError):
            opcode_timer(bytes(0x90000), 0)


if __name__ == "__main__":
    unittest.main()
