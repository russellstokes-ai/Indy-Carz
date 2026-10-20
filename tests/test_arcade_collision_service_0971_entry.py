"""ROM-free tests: actual original 0971 entry and its three early returns."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_service_0971_entry import (
    START, STOP, GATE, OUTPUT, THRESHOLD, SECOND_GATE,
    FullHandlerUnverified, independent, execute_original, verify,
)


def state(gate: int = 1, threshold: int = 0,
          secondary: int = 0, output: int = 127) -> bytes:
    slot = bytearray(256)
    slot[GATE], slot[THRESHOLD] = gate, threshold
    slot[SECOND_GATE], slot[OUTPUT] = secondary, output
    return bytes(slot)


class Original0971EntryTests(unittest.TestCase):
    def test_stage_boundaries_and_physical_slot_mapping(self):
        self.assertEqual((START, STOP), (0x0971, 0x0985))
        self.assertEqual(
            (GATE, OUTPUT, THRESHOLD, SECOND_GATE),
            (0xB1, 0xCE, 0x7D, 0xA3),
        )

    def test_bit0_early_return_has_no_write(self):
        record = state(gate=0x81)
        self.assertEqual(independent(record, 90, 173), (record, 90, 173, "ret_at_0975"))

    def test_unsigned_threshold_branch_and_original_output(self):
        original = state(gate=0, threshold=3, secondary=0)
        changed, a, b, exit_label = independent(original, 56)
        self.assertEqual(
            (changed[OUTPUT], a, b, exit_label),
            (56, 3, 56, "ret_at_097F"),
        )
        self.assertEqual(original[OUTPUT], 127)

    def test_third_return_when_low_threshold_and_secondary_set(self):
        changed, a, b, exit_label = independent(
            state(gate=0, threshold=2, secondary=5), 18
        )
        self.assertEqual((changed[OUTPUT], a, b, exit_label),
                         (18, 5, 18, "ret_at_0984"))

    def test_threshold_branch_has_priority(self):
        _, _, _, exit_label = independent(
            state(gate=0, threshold=255, secondary=77), 99
        )
        self.assertEqual(exit_label, "ret_at_097F")

    def test_unverified_slow_path_is_rejected(self):
        for threshold in range(3):
            with self.assertRaises(FullHandlerUnverified):
                independent(state(gate=0, threshold=threshold, secondary=0), 0)

    def test_invalid_slot_a_or_untrusted_master_fails_closed(self):
        with self.assertRaises(ValueError):
            independent(state(), -1)
        with self.assertRaises(ValueError):
            independent(state(), 256)
        with self.assertRaises(ValueError):
            independent(bytes(255), 0)
        with self.assertRaises(ValueError):
            independent(state(), 0, 256)
        with self.assertRaises(ValueError):
            execute_original(bytes(0x90000), state(), 0)
        with self.assertRaisesRegex(ValueError, "checksum-verified"):
            verify(bytes(0x90000))


if __name__ == "__main__":
    unittest.main()
