"""ROM-free original 2B77 bus-sequence regression tests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_event_2b77_bus import independent, IXS


class Original2B77BusTests(unittest.TestCase):
    def seed(self, ix, base, control=0xA7, first=0xA0, second=0xF0):
        ram = bytearray(0x2000)
        ram[ix + 0x12 - 0xE000] = base & 255
        ram[ix + 0x13 - 0xE000] = base >> 8
        ram[0x608] = control
        ram[0x613] = first
        ram[0x615] = second
        ram[0x616] = 0x83
        ram[0x900:0x908] = bytes((i * 19 + 7) & 255 for i in range(8))
        return ram

    def test_original_bank_order_and_exact_bus_values(self):
        for ix in IXS:
            ram = self.seed(ix, 0x4F34)
            before = bytes(ram)
            result = independent(ram, ix)
            self.assertEqual(result["next_pc"], 0x2BCC)
            self.assertEqual(result["bank_writes"], (0xA7, 0xF7, 0x07))
            self.assertEqual(len(result["memory_writes"]), 8)
            self.assertEqual(result["de"], 0x503C)
            self.assertEqual(result["hl"], 0x83F0)
            self.assertEqual(result["a"], 7)
            self.assertEqual(result["ram"][0x608], 7)
            self.assertEqual(bytes(ram), before)
            self.assertEqual(
                result["memory_writes"],
                tuple((0xA7, 0x503C + i, ram[0x900 + 2 * i])
                      for i in range(4)) +
                tuple((0xF7, 0x503C + i, ram[0x901 + 2 * i])
                      for i in (3, 2, 1, 0)))

    def test_original_inc_e_wraps_without_incrementing_d(self):
        for low in (0xF6, 0xF7, 0xF8, 0xFF):
            ram = self.seed(IXS[0], 0x4F00 | low)
            result = independent(ram, IXS[0])
            target = (0x4F00 | low) + 0x108
            high, lo = target & 0xFF00, target & 255
            addresses = [high | ((lo + i) & 255) for i in range(4)]
            self.assertEqual([x[1] for x in result["memory_writes"][:4]], addresses)
            self.assertEqual([x[1] for x in result["memory_writes"][4:]],
                             list(reversed(addresses)))

    def test_bank_control_or_preserves_original_low_nibble(self):
        ram = self.seed(IXS[0], 0x6F40, 0x02, 0x09, 0x80)
        result = independent(ram, IXS[0])
        self.assertEqual(result["bank_writes"], (0x0B, 0x8B, 0x0B))

    def test_invalid_input_rejected(self):
        with self.assertRaises(ValueError):
            independent(bytes(0x2000), 0xE680)
        with self.assertRaises(ValueError):
            independent(bytes(0x1000), IXS[0])


if __name__ == "__main__":
    unittest.main()
