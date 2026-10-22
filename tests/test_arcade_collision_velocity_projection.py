"""ROM-free checks for exact bounded original arcade collision projection."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_velocity_projection import (
    STAGE_START, STAGE_STOP, HEADING_OFFSET, SPEED_OFFSET,
    car_components, independent, sat_diff_byte, execute_original, verify,
)


def slot(angle: int = 0, speed: int = 0) -> bytes:
    out = bytearray(256)
    out[HEADING_OFFSET] = angle
    out[SPEED_OFFSET] = speed & 255
    return bytes(out)


class OriginalVelocityProjectionTests(unittest.TestCase):
    def test_bounded_stage_and_offsets(self):
        self.assertEqual((STAGE_START, STAGE_STOP), (0xB67E, 0xB6ED))
        self.assertEqual(STAGE_STOP-STAGE_START, 111)
        self.assertEqual((HEADING_OFFSET, SPEED_OFFSET), (0x3F, 0x41))

    def test_exact_signed_speed_rounding(self):
        # Original signed SRA then ADC 0; -1 rounds toward zero, not -1.
        self.assertEqual(car_components(slot(0, 0xFF)), (0, 0))
        self.assertEqual(car_components(slot(0, 127)), (0, 63))
        self.assertEqual(car_components(slot(64, 127)), (63, 0))
        self.assertEqual(car_components(slot(128, 128)), (0, 64))

    def test_per_car_vector_and_original_relative_difference(self):
        expected = (63, 0, 0, 63, 63, 193)
        self.assertEqual(independent(slot(64, 127), slot(0, 127), 0), expected)

    def test_event_bit5_swaps_active_cars(self):
        left, right = slot(0, 127), slot(64, 127)
        self.assertEqual(independent(left, right, 0x00), (0, 63, 63, 0, 193, 63))
        self.assertEqual(independent(left, right, 0x20), (63, 0, 0, 63, 63, 193))
        self.assertEqual(independent(left, right, 0xDF), independent(left, right, 0x00))

    def test_signed_overflow_helper(self):
        self.assertEqual(sat_diff_byte(127, -128 & 255), 127)
        self.assertEqual(sat_diff_byte(128, 127), 128)
        self.assertEqual(sat_diff_byte(200, 250), 206)
        self.assertEqual(sat_diff_byte(120, 20), 100)

    def test_original_inputs_fail_closed(self):
        left, right = slot(), slot()
        for bad in [-1, 256]:
            with self.assertRaises(ValueError):
                independent(left, right, bad)
        with self.assertRaises(ValueError):
            independent(bytes(255), right, 0)
        with self.assertRaises(ValueError):
            sat_diff_byte(256, 0)
        with self.assertRaisesRegex(ValueError, "Unexpected original opcode"):
            execute_original(bytes(0x90000), bytes(0x40000), left, right, 0)
        with self.assertRaisesRegex(ValueError, "Checksum-verified original arcade"):
            verify(bytes(0x90000), bytes(0x40000), cases=0)


if __name__ == "__main__":
    unittest.main()
