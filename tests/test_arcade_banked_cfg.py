"""ROM-free checks of structural Z80 instruction lengths and bank mapping."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_banked_cfg import instruction, bank_window, MASTER_BANKS


class Z80StructuralTests(unittest.TestCase):
    def check(self, payload, size, kind, target=None, port=None):
        result = instruction(bytes.fromhex(payload), 0)
        self.assertEqual(result, (size, kind, target, port), payload)

    def test_branch_and_input_opcode_lengths(self):
        self.check("00", 1, "step")
        self.check("18 FE", 2, "jump", 0)
        self.check("20 02", 2, "condjump", 4)
        self.check("C3 12 20", 3, "jump", 0x2012)
        self.check("CD 90 14", 3, "call", 0x1490)
        self.check("DB 09", 2, "step", port=0x09)
        self.check("D3 F4", 2, "step", port=0xF4)
        self.check("C9", 1, "ret")
        self.check("C0", 1, "condret")
        self.check("E9", 1, "indirect")

    def test_index_prefix_and_extended_opcode_lengths(self):
        self.check("DD 21 80 E0", 4, "step")
        self.check("DD 6E F5", 3, "step")
        self.check("FD 36 01 7F", 4, "step")
        self.check("DD CB FE 46", 4, "step")
        self.check("CB 7C", 2, "step")
        self.check("ED 4B 20 00", 4, "step")
        self.check("ED 4D", 2, "ret")
        self.check("DD FD CB FF 46", 5, "step")

    def test_bank_reconstruction(self):
        region = bytes((i >> 15) & 0xFF for i in range(0x90000))
        self.assertEqual(len(MASTER_BANKS), 16)
        for selector, offset in enumerate(MASTER_BANKS):
            window = bank_window(region, "master", selector)
            self.assertEqual(window[0], region[0])
            self.assertEqual(window[0x2000], region[offset])
            self.assertEqual(window[0x9fff], region[offset + 0x7fff])

    def test_slave_bank_reload_layout(self):
        slave = bytes([0x11]) * 0x20000 + bytes([0x22]) * 0x140000
        self.assertEqual(bank_window(slave, "slave", 0)[0x2000], 0x11)
        self.assertEqual(bank_window(slave, "slave", 1)[0x2000], 0x11)
        self.assertEqual(bank_window(slave, "slave", 0x21)[0x2000], 0x22)

    def test_invalid_original_image_refused(self):
        from arcade_banked_cfg import inspect
        with self.assertRaisesRegex(ValueError, "master"):
            inspect(bytes(0x90000), bytes(0x160000))


if __name__ == "__main__":
    unittest.main()
