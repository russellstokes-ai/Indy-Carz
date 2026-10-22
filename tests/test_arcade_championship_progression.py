"""ROM-free tests for original arcade round initialisation and progression."""
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_championship_progression import (
    COURSES, INIT_START, INIT_STOP, ADVANCE_START, ADVANCE_STOP,
    independent, opcode, check_original,
)


class OriginalChampionshipProgressionTests(unittest.TestCase):
    def test_fixed_original_ranges(self):
        self.assertEqual((INIT_START, INIT_STOP), (0x2936, 0x2953))
        self.assertEqual((ADVANCE_START, ADVANCE_STOP), (0x62A9, 0x62C5))

    def test_exact_fifteen_original_events_and_repeat(self):
        self.assertEqual(len(COURSES), 15)
        self.assertEqual(COURSES[2], COURSES[14])
        self.assertEqual(set(COURSES), set(range(14)))

    def test_automatic_launch_always_resets_to_first_event(self):
        for selector in range(128, 256):
            for old_round in (0, 7, 14, 255):
                r = independent(selector, old_round, "initialize")
                self.assertEqual((r["round_counter"], r["course_index"], r["next_pc"]),
                                 (0, 13, 0x2953))

    def test_manual_event_selection_is_direct_not_advanced(self):
        for event in range(15):
            result = independent(event, 255, "initialize")
            self.assertEqual(result["round_counter"], event)
            self.assertEqual(result["course_index"], COURSES[event])
            self.assertEqual(result["next_pc"], 0x2953 if event == 0 else 0x2989)

    def test_original_automatic_wrap_after_fifteen_events(self):
        for i in range(15):
            result = independent(255, i, "advance")
            self.assertEqual(result["round_counter"], (i+1) % 15)
            self.assertEqual(result["course_index"], COURSES[(i+1) % 15])
            self.assertEqual(result["next_pc"], 0x62C5)
            self.assertEqual(result["next_call"], 0x2120)

    def test_manual_round_override_ignores_previous_index(self):
        for selected in range(15):
            for old_round in (0, selected, 14, 255):
                result = independent(selected, old_round, "advance")
                self.assertEqual(result["round_counter"], selected)
                self.assertEqual(result["course_index"], COURSES[selected])

    def test_signed_selector_boundary_modes(self):
        self.assertEqual(independent(0x80, 14, "advance")["round_counter"], 0)
        self.assertEqual(independent(0xFF, 13, "advance")["round_counter"], 14)
        self.assertEqual(independent(0x0E, 0, "advance")["round_counter"], 14)

    def test_reject_unverified_direct_indices(self):
        for selector in range(15, 128):
            with self.assertRaises(ValueError):
                independent(selector, 0, "initialize")
        with self.assertRaises(ValueError):
            independent(255, 15, "advance")
        with self.assertRaises(ValueError):
            independent(256, 0, "advance")
        with self.assertRaises(ValueError):
            independent(0, -1, "initialize")
        with self.assertRaises(ValueError):
            independent(0, 0, "unknown")

    def test_reject_untrusted_reference_rom(self):
        with self.assertRaisesRegex(ValueError, "checksum-verified"):
            check_original(bytes(0x90000))
        with self.assertRaises(ValueError):
            opcode(bytes(0x90000), 255, 0, "advance")


if __name__ == "__main__":
    unittest.main()
