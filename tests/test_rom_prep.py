"""Unit tests for MAME Indy Heat ROM bank mapping; use synthetic bytes only."""
import unittest
from tools.prepare_indyheat_rom import rotate_memory, rebuild_regions, REGION_SIZES, ROMS


class PrepTests(unittest.TestCase):
    def test_rotate_32kb_block(self):
        region = bytearray(0x18000)
        region[:0x10000] = b"\x77" * 0x10000
        region[0x10000:0x12000] = b"A" * 0x2000
        region[0x12000:0x18000] = b"B" * 0x6000
        rotate_memory(region)
        self.assertEqual(region[0x0000:0x2000], b"\x77" * 0x2000)
        self.assertEqual(region[0x10000:0x16000], b"B" * 0x6000)
        self.assertEqual(region[0x16000:0x18000], b"A" * 0x2000)

    def test_region_size_alignment(self):
        for region_name in ("master", "slave"):
            self.assertEqual((REGION_SIZES[region_name] - 0x10000) % 0x8000, 0)

    def test_manifest_regions_in_bounds(self):
        for filename, digest, operations in ROMS:
            self.assertEqual(len(digest), 40)
            for region_name, dst, length, offset, stride in operations:
                self.assertGreater(length, 0)
                self.assertLessEqual(dst + (length - 1) * stride + 1, REGION_SIZES[region_name])


if __name__ == "__main__":
    unittest.main()
