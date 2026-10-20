"""ROM-free checks for original conditional collision-car input helper."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_contact_input_gate import (
    START, STOP, GATE_OFFSET, SOURCE_OFFSET, OUTPUT_OFFSET,
    independent, execute_original, verify,
)


def slot(status: int = 0, source: int = 255, output: int = 34) -> bytes:
    data = bytearray(256)
    data[GATE_OFFSET], data[SOURCE_OFFSET], data[OUTPUT_OFFSET] = status, source, output
    return bytes(data)


class ContactInputGateTests(unittest.TestCase):
    def test_stage_boundaries_and_physical_slot_offsets(self):
        self.assertEqual((START, STOP), (0x0A30, 0x0A42))
        self.assertEqual((GATE_OFFSET, SOURCE_OFFSET, OUTPUT_OFFSET),
                         (0xB1, 0xF7, 0xD7))

    def test_bit0_clear_does_not_change_car(self):
        original = slot(status=0xF0)
        self.assertEqual(independent(original, 128), (original, 128, False))

    def test_bit0_set_updates_byte_and_preserves_accumulator(self):
        after, a, changed = independent(slot(status=1, source=255), 211)
        self.assertTrue(changed)
        self.assertEqual(after[OUTPUT_OFFSET], 126)
        self.assertEqual(a, 211)

    def test_source_shift_and_mask_boundaries(self):
        for source, expected in ((0, 0), (1, 0), (2, 0), (3, 0),
                                 (4, 2), (128, 64), (255, 126)):
            changed, _, _ = independent(slot(status=0x81, source=source), 0)
            self.assertEqual(changed[OUTPUT_OFFSET], expected)

    def test_unrelated_car_bytes_untouched(self):
        original = slot(status=0x21)
        updated, _, _ = independent(original, 17)
        self.assertEqual(
            [i for i in range(256) if original[i] != updated[i]], [OUTPUT_OFFSET]
        )

    def test_invalid_inputs_fail_closed(self):
        for bad in (-1, 256):
            with self.assertRaises(ValueError):
                independent(slot(), bad)
        with self.assertRaises(ValueError):
            independent(bytes(255), 0)
        with self.assertRaises(ValueError):
            execute_original(bytes(0x90000), slot(), 0)
        with self.assertRaisesRegex(ValueError, "Checksum-verified"):
            verify(bytes(0x90000))


if __name__ == "__main__":
    unittest.main()
