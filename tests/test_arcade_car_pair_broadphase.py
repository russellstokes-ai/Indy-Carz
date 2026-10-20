"""ROM-free regression tests for original six-slot pairwise collision gates."""
import hashlib
from itertools import combinations
from unittest.mock import patch
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import arcade_car_pair_broadphase as pairs


def fake_master():
    rom = bytearray(0x90000)
    for index, pair in enumerate(combinations(range(6), 2)):
        pc = pairs.PAIR_START + index * pairs.PAIR_STRIDE
        rom[pc:pc + pairs.PAIR_STRIDE] = pairs.program_for_pair(pair, pc)
    rom[pairs.NARROW_PHASE:pairs.NARROW_PHASE + len(pairs.ENTRY_SIGNATURE)] = pairs.ENTRY_SIGNATURE
    rom[pairs.PAIR_END:pairs.PAIR_END + 4] = bytes.fromhex("3a 19 e9 b7")
    rom[0x18000:0x1c000] = rom[0xa000:0xe000]
    return bytes(rom)


class OriginalPairPrecheckTests(unittest.TestCase):
    def test_fifteen_ordered_pairs_and_single_alias(self):
        image = fake_master()
        with patch.object(pairs, "MASTER_SHA", hashlib.sha256(image).hexdigest()):
            pairs.validate_layout(image)
        self.assertEqual(pairs.PAIR_COUNT, 15)
        self.assertEqual(pairs.PAIRS[0], (0, 1))
        self.assertEqual(pairs.PAIRS[10], (2, 4))
        self.assertEqual(pairs.PAIRS[-1], (4, 5))
        self.assertEqual(pairs.PAIR_END, 0xB39F)
        self.assertEqual(image[0xa000:0xe000], image[0x18000:0x1c000])

    def test_original_z80_gate_decisions_and_borrow(self):
        rom = fake_master()
        cases = [
            (pairs.Car(0x5000,0x5000,0), pairs.Car(0x5000,0x5000,0), "status_skip"),
            (pairs.Car(0x5000,0x5000,0x80), pairs.Car(0x6000,0x5000,0), "axis0_skip"),
            (pairs.Car(0x5000,0x5000,0), pairs.Car(0x5000,0x6000,0x80), "axis1_skip"),
            (pairs.Car(0x5000,0x5000,0x80), pairs.Car(0x5000,0x5000,0), "narrow_phase_call"),
            (pairs.Car(0xffff,0xffff,0x80), pairs.Car(0,0,0), "narrow_phase_call"),
            (pairs.Car(0x5000,0x5000,0x80), pairs.Car(0x5000,0x4D01,0), "narrow_phase_call"),
        ]
        for index in range(15):
            for left, right, outcome in cases:
                with self.subTest(pair=index, outcome=outcome):
                    mathematical = pairs.model_broadphase(left, right)
                    original = pairs.original_pair_opcodes(rom, index, left, right)
                    self.assertEqual(original, mathematical)
                    self.assertEqual(original[0], outcome)
        self.assertEqual(
            pairs.model_broadphase(pairs.Car(0x5000,0x5000,0x80),
                                   pairs.Car(0x5000,0x5000,0))[2], 65535)

    def test_original_two_narrow_entry_rejections(self):
        rom = fake_master()
        cases = [
            (0x80,0x00,0,0,True),
            (0x81,0x81,0,0,False),
            (0x81,0x80,0,0,True),
            (0x80,0,2,0,False),
            (0x80,0,0,2,False),
            (0x81,0x81,2,2,False),
        ]
        for a0,b0,a1,b1,expected in cases:
            left, right = pairs.Car(0,0,a0,a1), pairs.Car(0,0,b0,b1)
            self.assertEqual(pairs.narrow_entry_model(left, right), expected)
            self.assertEqual(pairs.original_narrow_entry(rom, left, right), expected)

    def test_corruption_and_invalid_fields_fail_closed(self):
        rom = bytearray(fake_master())
        rom[pairs.PAIR_START + 10] ^= 1
        rom[0x18000:0x1c000] = rom[0xa000:0xe000]
        with patch.object(pairs, "MASTER_SHA", hashlib.sha256(rom).hexdigest()):
            with self.assertRaisesRegex(ValueError, "pair"):
                pairs.validate_layout(rom)
        with self.assertRaisesRegex(ValueError, "checksum"):
            pairs.validate_layout(fake_master())
        with self.assertRaises(ValueError):
            pairs.Car(-1, 0, 0)


if __name__ == "__main__":
    unittest.main()
