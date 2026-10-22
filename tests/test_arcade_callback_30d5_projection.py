"""ROM-free 30D5 callback arithmetic and exact Z80 outgoing flags."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_callback_30d5_projection import independent, IXS


class Original30D5CallbackTests(unittest.TestCase):
    def test_all_five_cars_and_all_256_initial_a_values(self):
        for ix in IXS:
            for initial_a in range(256):
                ram = bytearray(0x2000)
                ram[0x96F:0x971] = bytes([0x34, 0x12])
                ram[0x971:0x973] = bytes([0x78, 0x56])
                ram[0x94E:0x950] = bytes([0xBC, 0x9A])
                ram[0x735:0x737] = bytes([0x40, 0x90])
                ram[ix + 0x75 - 0xE000] = 0x80
                before = bytes(ram)
                result = independent(ram, ix, initial_a, 0xABCD)
                c = initial_a | 0x80
                self.assertEqual(result["bc"], (0xDF << 8) | c)
                self.assertEqual(result["de"], 0x9ABC)
                self.assertEqual(result["hl"], 0x2080)
                self.assertEqual((result["alt_bc"], result["alt_de"], result["alt_hl"]),
                                 (0x1234, 0x5678, 0xABCD))
                self.assertEqual(result["ram"][0x77D:0x781],
                                 bytes([0x34, 0x12, 0x78, 0x56]))
                self.assertEqual(result["f"], (c & 0x80) |
                                 (0x40 if c == 0 else 0) |
                                 (4 if c.bit_count() % 2 == 0 else 0) |
                                 1 | 0x12 | (0xDF & 0x28))
                self.assertEqual(result["next_pc"], 0xD958)
                self.assertFalse(result["complete"])
                self.assertEqual(bytes(ram), before)

    def test_signed_wrap_and_parity_flags(self):
        for word in (0, 0x7FFF, 0x8000, 0xFFFF):
            for ix in IXS:
                ram = bytearray(0x2000)
                ram[0x735] = word & 0xFF
                ram[0x736] = word >> 8
                result = independent(ram, ix, 0, 0)
                self.assertEqual(result["hl"], (word << 1) & 0xFFFF)
                self.assertEqual(result["f"] & 1, 1 if word >= 0x8000 else 0)
                self.assertEqual(result["f"] & 4, 4)

    def test_invalid_original_registers_and_ram_rejected(self):
        ram = bytes(8192)
        for a, hl in ((-1, 0), (256, 0), (1, -1), (1, 65536),
                      (True, 0), (0, None)):
            with self.assertRaises(ValueError):
                independent(ram, IXS[0], a, hl)
        with self.assertRaises(ValueError):
            independent(bytes(8191), IXS[0], 0, 0)
        with self.assertRaises(ValueError):
            independent(ram, 0xE680, 0, 0)


if __name__ == "__main__":
    unittest.main()
