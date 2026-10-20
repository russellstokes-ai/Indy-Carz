"""Synthetic original-shaped vehicle states; no copyrighted arcade ROM data."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_b546_response import asr16, model, original, verify


def put16(state: bytearray, offset: int, value: int):
    state[offset:offset+2] = (value & 0xFFFF).to_bytes(2, "little")


def car(x=1000, previous_x=1006, y=3000, previous_y=3010, flag=0, final=0):
    state = bytearray(256)
    put16(state, 0x00, x)
    put16(state, 0x1E, previous_x)
    put16(state, 0x0A, y)
    put16(state, 0x28, previous_y)
    put16(state, 0x12, final)
    state[0x7C] = flag
    return bytes(state)


class OriginalTwoCarResponseTests(unittest.TestCase):
    def test_exact_signed_arithmetic_shift_and_wrap(self):
        self.assertEqual(asr16(0), 0)
        self.assertEqual(asr16(5), 2)
        self.assertEqual(asr16(65535), 65535)
        self.assertEqual(asr16(65534), 65535)
        self.assertEqual(asr16(0x8000), 0xC000)
        self.assertEqual(asr16(0x7FFF), 0x3FFF)

    def test_pair_correction_updates_both_and_wraps_counter(self):
        first, second = car(), car(x=7000, previous_x=6980, y=9000, previous_y=9020)
        result, a, b, counter = model(first, second, 255)
        self.assertEqual((result, counter), ("applied", 0))
        self.assertNotEqual(a, first)
        self.assertNotEqual(b, second)
        self.assertEqual(a[0x7C] & 0x40, 0x40)
        self.assertEqual(b[0x7C] & 0x40, 0x40)

    def test_one_or_both_cars_omit_correction_when_status_bit_one_set(self):
        first, second = car(flag=2), car()
        state, a, b, counter = model(first, second, 8)
        self.assertEqual((state, counter), ("applied", 9))
        self.assertEqual(a, first)
        self.assertNotEqual(b, second)

        first, second = car(), car(flag=2)
        state, a, b, counter = model(first, second, 3)
        self.assertEqual((state, counter), ("second_skipped", 4))
        self.assertNotEqual(a, first)
        self.assertEqual(b, second)

        first, second = car(flag=2), car(flag=2)
        state, a, b, counter = model(first, second, 3)
        self.assertEqual((state, counter), ("second_skipped", 4))
        self.assertEqual((a,b), (first,second))

    def test_original_carry_from_ix_changes_iy_position(self):
        second = car(x=0x1000, previous_x=0x1002, y=0x2000, previous_y=0x2000)
        high_wrap = car(final=0xFFFE) # final + 4 overflows, carry=1
        no_wrap = car(final=0)        # carry=0
        status, a, b, _ = model(high_wrap, second, 4)
        other, c, d, _ = model(no_wrap, second, 4)
        self.assertEqual((status, other), ("applied", "applied"))
        self.assertEqual(int.from_bytes(b[:2], "little"), 0x1000)
        self.assertEqual(int.from_bytes(d[:2], "little"), 0x1001)

    def test_abnormal_delta_calls_unresolved_original_handler(self):
        far = car(previous_x=14000, x=1000)
        result, a, b, counter = model(far, car(), 9)
        self.assertEqual((result,counter),("IX:escape_on_B",10))
        self.assertEqual(a, far)

    def test_requires_original_rom_for_bounded_opcode_verification(self):
        with self.assertRaisesRegex(ValueError, "checksum-verified"):
            verify(bytes(0x90000),1)
        with self.assertRaises(ValueError):
            original(bytes(50),car(),car(),0)


if __name__ == "__main__":
    unittest.main()
