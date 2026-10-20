"""ROM-free tests for the original arcade IX/IY collision position correction.

The real ROM stage is verified locally with tools/arcade_collision_geometry_push.py.
Here only synthetic machine instructions are generated from a general pattern.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_geometry_push import STARTS, ENDS, model, emulate, valid_high, verify


def fake_rom() -> bytes:
    original_shaped = bytearray(0x90000)
    for key, prefix in (("IX", 0xDD), ("IY", 0xFD)):
        # Two Z80 CP high-byte range guards; CALL C,$1689 is deliberately
        # treated as an escape rather than an assumed gameplay callback.
        ops = bytearray([
            0x78,0xFE,0x05,0x38,0x05,0xFE,0xFB,0xDC,0x89,0x16,
            0x7A,0xFE,0x05,0x38,0x05,0xFE,0xFB,0xDC,0x89,0x16,
        ])
        for i in range(10):
            low = 0x80 + 2*i
            high = low + 1
            ops += bytes([
                prefix, 0x66, high,
                prefix, 0x6E, low,
                0x09 if i < 5 else 0x19,
                prefix, 0x74, high,
                prefix, 0x75, low,
            ])
        ops += bytes([prefix, 0xCB, 0xFC, 0xF6, 0xC9])
        assert len(ops) == ENDS[key] - STARTS[key]
        original_shaped[STARTS[key]:ENDS[key]] = ops
    return bytes(original_shaped)


class ArcadeCollisionGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.synthetic_rom = fake_rom()

    def test_all_original_signed_guard_boundaries(self):
        for n in range(256):
            self.assertEqual(valid_high(n), n <= 4 or n >= 251)

    def test_first_five_and_last_five_positions_wrap(self):
        state = bytearray(256)
        for i in range(10):
            state[2*i:2*i+2] = (65530 + i).to_bytes(2, "little")
        state[0x7C] = 0x13
        status, updated = model(bytes(state), 0x000A, 0xFFFE)
        self.assertEqual(status, "applied")
        for i in range(10):
            expected = (65530 + i + (10 if i < 5 else 65534)) & 65535
            self.assertEqual(int.from_bytes(updated[2*i:2*i+2], "little"), expected)
        self.assertEqual(updated[0x7C], 0x53)
        self.assertEqual(updated[0x7D:], state[0x7D:])

    def test_synthetic_opcode_interpreter_matches_independent_model(self):
        for prefix in ("IX", "IY"):
            for bc in (0, 1, 4<<8 | 255, 0xFB00, 0xFFFF, 0x0500, 0xFAFF):
                for de in (0, 0x0400, 0xFBFF, 0xFFFF, 0x0500):
                    state = bytes((i*29 + (bc&255)) & 255 for i in range(256))
                    expected = model(state, bc, de)
                    actual, output, steps = emulate(
                        self.synthetic_rom, state, bc, de, prefix
                    )
                    self.assertEqual((actual, output), expected)
                    self.assertGreater(steps, 0)

    def test_fails_closed_for_bad_original_opcode(self):
        bad = bytearray(self.synthetic_rom)
        bad[0xB985 + 20 + 6] = 0xFF
        with self.assertRaisesRegex(ValueError, "Unsupported original response opcode"):
            emulate(bytes(bad), bytes(256), 0, 0, "IX")

    def test_full_rom_integrity_required_for_parity_run(self):
        with self.assertRaisesRegex(ValueError, "verified original"):
            verify(self.synthetic_rom, samples=1)
        with self.assertRaises(ValueError):
            model(bytes(255), 0, 0)


if __name__ == "__main__":
    unittest.main()
