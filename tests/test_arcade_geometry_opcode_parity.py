"""ROM-free acceptance tests for recovered Indy Heat 8-coordinate geometry."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_geometry_opcode_parity import CORNERS, execute_original, model_corners, verify


class OriginalCarGeometryTests(unittest.TestCase):
    def test_original_rectangle_at_zero_degrees(self):
        result = model_corners(0, 10000, 20000)
        self.assertEqual(result[0xE73D], 9746)
        self.assertEqual(result[0xE737], 10254)
        self.assertEqual(result[0xE73B], 10254)
        self.assertEqual(result[0xE739], 9746)
        self.assertEqual(result[0xE733], 20381)
        self.assertEqual(result[0xE72D], 19619)
        self.assertEqual(result[0xE731], 20381)
        self.assertEqual(result[0xE72F], 19619)
        self.assertEqual(set(result), set(CORNERS))

    def test_original_diagonal_corner_offsets(self):
        base = model_corners(32, 10000, 20000)
        self.assertEqual(base[0xE73D], 10091)
        self.assertEqual(base[0xE737], 9909)
        self.assertEqual(base[0xE73B], 10455)
        self.assertEqual(base[0xE739], 9545)
        self.assertEqual(base[0xE733], 20455)
        self.assertEqual(base[0xE72D], 19545)
        self.assertEqual(base[0xE731], 20091)
        self.assertEqual(base[0xE72F], 19909)

    def test_two_axis_symmetry_and_wrap(self):
        for angle in (0, 1, 32, 64, 127, 128, 192, 255):
            for x, y in ((0, 0), (65535, 65535), (10000, 20000)):
                r = model_corners(angle, x, y)
                self.assertEqual((r[0xE73D]+r[0xE737]) & 65535, 2*x & 65535)
                self.assertEqual((r[0xE73B]+r[0xE739]) & 65535, 2*x & 65535)
                self.assertEqual((r[0xE733]+r[0xE72D]) & 65535, 2*y & 65535)
                self.assertEqual((r[0xE731]+r[0xE72F]) & 65535, 2*y & 65535)

    def test_private_rom_integrity_gate(self):
        with self.assertRaisesRegex(ValueError, "Original privately"):
            verify(bytes(0x90000))
        with self.assertRaisesRegex(ValueError, "Original MAME-rotated"):
            execute_original(bytes(2), 0, 0, 0)
        with self.assertRaises(ValueError):
            model_corners(300, 0, 0)


if __name__ == "__main__":
    unittest.main()
