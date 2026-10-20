"""No ROMs needed: verify 80186 odd/even interleaving and ROM_RELOAD mirroring."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_audio_inventory import restore_audio_image, restore_dac_region


class SoundBankMappingTests(unittest.TestCase):
    def setUp(self):
        self.roms = {
            "e-302-33021-01.u3": bytes([0x33]) * 0x20000,
            "e-302-33024-01.u6": bytes([0x66]) * 0x20000,
            "e-302-33022-01.u4": bytes([0x44]) * 0x20000,
            "e-302-33023-01.u5": bytes([0x55]) * 0x20000,
            "e-302-33025-01.u8": bytes([0x88]) * 0x20000,
            "e-302-33026-01.u9": bytes([0x99]) * 0x20000,
        }

    def test_odd_even_rom_regions(self):
        image = restore_audio_image(self.roms)
        self.assertEqual(len(image), 0x100000)
        self.assertEqual(image[0x20000:0x20004], bytes([0x66, 0x33, 0x66, 0x33]))
        self.assertEqual(image[0x60000:0x60004], bytes([0x55, 0x44, 0x55, 0x44]))

    def test_high_sound_rom_is_mirrored_at_c0000(self):
        image = restore_audio_image(self.roms)
        self.assertEqual(image[0xC0000:0xC0004], bytes([0x55, 0x44, 0x55, 0x44]))
        self.assertEqual(image[0xFFFFE:0x100000], bytes([0x55, 0x44]))

    def test_dac_roms_are_contiguous(self):
        dac = restore_dac_region(self.roms)
        self.assertEqual(len(dac), 0x40000)
        self.assertEqual((dac[0], dac[0x1FFFF], dac[0x20000], dac[0x3FFFF]),
                         (0x88, 0x88, 0x99, 0x99))


if __name__ == "__main__":
    unittest.main()
