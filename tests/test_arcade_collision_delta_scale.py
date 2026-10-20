"""ROM-free tests for original two-axis car-to-car separation scaling."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_delta_scale import (
    START, STOP, INSTRUCTION_SIGNATURE, independent_axis,
    original_z80_stage, signed16, verify,
)


def fake_master():
    result = bytearray(0x90000)
    result[START:STOP] = INSTRUCTION_SIGNATURE
    return bytes(result)


class CollisionDeltaScalingTests(unittest.TestCase):
    def test_original_z80_all_quadrant_boundaries(self):
        rom = fake_master()
        for signed in (-32768,-32767,-255,-129,-128,-9,-8,-5,-4,-1,
                       0,1,3,4,7,8,127,128,255,32767):
            word = signed & 0xFFFF
            expected = independent_axis(word)
            self.assertEqual(
                original_z80_stage(rom, word, word),
                (expected, expected),
                f"original signed separation {signed}",
            )
        self.assertEqual(independent_axis(0x0004), 1)
        self.assertEqual(independent_axis(0xFFFC), 0)
        self.assertEqual(independent_axis(0xFFFB), 255)
        self.assertEqual(independent_axis(0x7FFF), 0)

    def test_cross_axis_independent(self):
        rom = fake_master()
        for first in (0,1,3,4,8,255,0x100,0x7fff,0x8000,0xfffb,0xffff):
            for second in (0,1,4,255,0x8000,0xffff):
                self.assertEqual(
                    original_z80_stage(rom, first, second),
                    (independent_axis(first), independent_axis(second)),
                )

    def test_bad_bytecode_and_source_rejected(self):
        mutated = bytearray(fake_master())
        mutated[START + 2] = 0
        with self.assertRaisesRegex(ValueError, "instructions"):
            original_z80_stage(bytes(mutated), 1, 2)
        with self.assertRaisesRegex(ValueError, "Checksum"):
            verify(fake_master())
        with self.assertRaises(ValueError):
            signed16(-1)
        with self.assertRaises(ValueError):
            independent_axis(65536)


if __name__ == "__main__":
    unittest.main()
