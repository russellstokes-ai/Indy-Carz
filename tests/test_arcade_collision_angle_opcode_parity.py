"""Private-ROM-free original angle arithmetic and bounded opcode tests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_angle_opcode_parity import (
    CODE_BEGIN, CODE_END, TABLE_BEGIN, TABLE_END,
    arithmetic_shift_byte, independent_angle, independent_angle_with_carry,
    execute_original, verify,
)

# Representative synthetic instructions implementing the recovered original
# Z80 control-flow grammar; no original ROM images or LUT data are included.
SYNTHETIC_ANGLE_PROGRAM = bytes.fromhex(
    "79 b7 f2 10 a6 2f cd 10 a6 ed 44 c9 cb 3f cb 28 "
    "fe 10 30 f8 4f 78 b7 f2 26 a6 2f cd 26 a6 2f "
    "c6 81 c9 cb 3f cb 29 fe 10 30 f8 6f 79 87 "
    "87 87 87 b5 87 6f 3e a0 ce 00 67 7e c9"
)


def synthetic_memory():
    master = bytearray(0x90000)
    assert len(SYNTHETIC_ANGLE_PROGRAM) == CODE_END-CODE_BEGIN
    master[CODE_BEGIN:CODE_END] = SYNTHETIC_ANGLE_PROGRAM
    for index in range(256):
        master[TABLE_BEGIN+2*index] = (index*3+7) & 255
        master[TABLE_BEGIN+2*index+1] = 0
    return bytes(master)


class OriginalAngleStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.memory = synthetic_memory()
        cls.table = cls.memory[TABLE_BEGIN:TABLE_END]

    def test_signed_arithmetic_shift(self):
        self.assertEqual(arithmetic_shift_byte(255), 255)
        self.assertEqual(arithmetic_shift_byte(128), 192)
        self.assertEqual(arithmetic_shift_byte(127), 63)
        self.assertEqual(arithmetic_shift_byte(0), 0)

    def test_normalised_quantisation_index_examples(self):
        self.assertEqual(independent_angle(self.table, 0, 0), (7, 0))
        self.assertEqual(independent_angle(self.table, 16, 16)[1], 136)
        self.assertEqual(independent_angle(self.table, 128, 255)[1], 15)
        self.assertNotEqual(independent_angle(self.table, 127, 128)[0],
                            independent_angle(self.table, 127, 127)[0])
        with self.assertRaises(ValueError):
            independent_angle(bytes(511), 0, 0)
        with self.assertRaises(ValueError):
            independent_angle(self.table, 256, 0)

    def test_bounded_original_instructions_and_independent_model(self):
        for b in (0, 1, 7, 15, 16, 32, 64, 127, 128, 192, 240, 255):
            for c in (0, 1, 7, 15, 16, 32, 64, 127, 128, 192, 240, 255):
                expected, index = independent_angle(self.table, b, c)
                observed, address, instructions = execute_original(self.memory, b, c)
                self.assertEqual(observed, expected, (b, c))
                self.assertEqual(address, TABLE_BEGIN + 2*index)
                self.assertLess(instructions, 128)
                modeled, modeled_index, modeled_carry = independent_angle_with_carry(
                    self.table, b, c)
                with_flags = execute_original(self.memory, b, c, include_flags=True)
                self.assertEqual((modeled, modeled_index), (expected, index))
                self.assertEqual((with_flags[0], with_flags[1], with_flags[3]),
                                 (expected, TABLE_BEGIN + 2*index, modeled_carry))

    def test_wrong_original_rom_never_accepted(self):
        with self.assertRaisesRegex(ValueError, "verified 1991"):
            verify(self.memory)

    def test_unknown_opcode_fails_closed(self):
        corrupt = bytearray(self.memory)
        corrupt[CODE_BEGIN] = 0x76
        with self.assertRaisesRegex(ValueError, "Unrecognised"):
            execute_original(bytes(corrupt), 1, 1)


if __name__ == "__main__":
    unittest.main()
