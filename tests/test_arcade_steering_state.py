"""ROM-free sanity checks for original Z80 steering accumulator arithmetic."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from arcade_steering_opcode_parity import model_stage


class SteeringStateTests(unittest.TestCase):
    def test_original_bank3_centring_rule(self):
        # Direct bank-3 source: zero input drifts towards midpoint 0x80.
        self.assertEqual(model_stage(3, 0, 0, bytes(0x40000)), (8, False))
        self.assertEqual(model_stage(3, 0, 255, bytes(0x40000)), (247, False))
        # Overflow path changes bit 7 and asks for downstream handling.
        self.assertEqual(model_stage(3, 62, 200, bytes(0x40000)), (196, True))

    def test_original_bank0_xrom_rule(self):
        xrom = bytearray(0x40000)
        # The X-ROM word's high byte at (signed_input << 8 | 0x7F).
        for signed, upper in [(-12, 0xF4), (0, 0), (12, 0x0B)]:
            addr = (((signed & 255) << 8) | 0x7F)
            xrom[addr * 2 + 1] = upper
        self.assertEqual(model_stage(0, 0, 0, xrom), (4, False))
        self.assertEqual(model_stage(0, -12, 150, xrom), (130, False))
        self.assertEqual(model_stage(0, 12, 240, xrom), (134, True))

    def test_godot_contains_exact_paths(self):
        source = (ROOT / "scripts/mechanics/ArcadeSteeringState.gd").read_text()
        self.assertIn("XROM_BANK_0", source)
        self.assertIn("DIRECT_BANK_3", source)
        self.assertIn("centering_bias", source.replace("centring_bias", "centering_bias"))
        self.assertIn("updated ^= 0x80", source)
        self.assertIn("VALID_MAGNITUDES", source)


if __name__ == "__main__":
    unittest.main()
