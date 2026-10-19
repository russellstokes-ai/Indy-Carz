"""ROM-free checks for recovered original-drive opcode stage executor."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_drive_opcode_parity import (
    original_flagged_lookup, original_weighted_stage,
)


class DriveOpcodeParityTests(unittest.TestCase):
    def setUp(self):
        self.master = bytearray(0x90000)
        self.xrom = bytearray(0x40000)
        self.master[0x7039:0x7043] = bytes.fromhex(
            "60 2e 60 22 fe ff 3a fe ff 47"
        )
        self.master[0x709C:0x70AC] = bytes.fromhex(
            "60 2e a6 22 fe ff 3a fe ff dd 86 54 dc 9c 0a 47"
        )
        self.master[0x0A9C:0x0AA0] = bytes.fromhex("3e ff b7 c9")
        for raw in range(256):
            for key in (0x60, 0xA6):
                index = 0x20000 + 2 * ((raw << 8) | key)
                self.xrom[index] = ((raw * key + 128) >> 8)

    def test_bounded_original_input_stage(self):
        self.assertEqual(original_flagged_lookup(self.master, self.xrom, 126), 47)
        self.assertEqual(original_flagged_lookup(self.master, self.xrom, 255), 96)

    def test_original_saturating_helper_on_carry(self):
        self.assertEqual(original_weighted_stage(self.master, self.xrom, 126, 150), 232)
        self.assertEqual(original_weighted_stage(self.master, self.xrom, 126, 200), 255)
        self.assertEqual(original_weighted_stage(self.master, self.xrom, 0, 255), 255)

    def test_reject_bad_opcode(self):
        self.master[0x709C] = 0
        with self.assertRaisesRegex(ValueError, "Unexpected original opcode"):
            original_weighted_stage(self.master, self.xrom, 0, 0)

    def test_godot_port_includes_exact_original_factors(self):
        gd = (Path(__file__).resolve().parents[1]
              / "scripts/mechanics/ArcadeDriveStages.gd").read_text()
        self.assertIn("0x60", gd)
        self.assertIn("0xA6", gd)
        self.assertIn("0xFF", gd)


if __name__ == "__main__":
    unittest.main()
