"""Synthetic test dataset — no original 1991 arcade grid coordinates included."""
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import arcade_start_grid_extraction as grid


def fake_master() -> bytes:
    master = bytearray(0x90000)
    signatures = (
        (0x1767, "3a 99 e6 87 85 6f"),
        (0x608F, "21 82 63 cd 67 17 dd 7e 69 4f 87 87 81"),
        (0x60A4, "fd 66 01 fd 6e 00 22 2b e7"),
        (0x60AD, "fd 66 03 fd 6e 02 22 35 e7"),
        (0x60B6, "fd 66 04 2e 00 22 67 e7 22 69 e7"),
    )
    for offset, signature in signatures:
        payload = bytes.fromhex(signature)
        master[offset:offset+len(payload)] = payload
    for course in range(14):
        ptr = 0x639E+25*course
        master[0x6382+2*course:0x6382+2*course+2] = ptr.to_bytes(2, "little")
        for car in range(5):
            address = ptr+5*car
            master[address:address+5] = ((course*100+car).to_bytes(2, "little") +
                                         (car*100+course).to_bytes(2, "little") +
                                         bytes([course]))
    # Artificial championship: every internal course once, course 2 repeated.
    master[0x1ABF:0x1ABF+15] = bytes(list(range(14)) + [2])
    master[0x2941:0x294D] = bytes.fromhex(
        "3a 9b e6 21 bf 1a cd 47 17 32 99 e6")
    bank3_offset = 0x28000 + 0x62B4 - 0x2000
    wrap = bytes.fromhex(
        "fe 0f 20 01 af 32 9b e6 21 bf 1a cd 47 17 32 99 e6")
    master[bank3_offset:bank3_offset+len(wrap)] = wrap
    return bytes(master)


class OriginalGridTests(unittest.TestCase):
    def test_original_grid_indexing_pipeline(self):
        image = fake_master()
        with patch.object(grid, "MASTER_SHA", hashlib.sha256(image).hexdigest()):
            report = grid.decode_course_grid(image)
        self.assertEqual(report["course_count"], 14)
        self.assertEqual(report["grid_slots_per_course"], 5)
        self.assertEqual(report["total_records"], 70)
        self.assertEqual(report["original_championship"]["rounds"], 15)
        self.assertEqual(report["original_championship"]["course_internal_index_per_round"], list(range(14)) + [2])
        self.assertEqual(report["original_championship"]["repeated_course_internal_index"], 2)
        self.assertEqual(report["original_course_grids"][0]["source_cpu_pointer"], "639E")
        self.assertEqual(report["original_course_grids"][-1]["source_cpu_pointer"], "64E3")
        self.assertEqual(report["original_course_grids"][12]["starting_grid"][4],
                         {"car_grid_index": 4, "state_E72B": 1204,
                          "state_E735": 412, "heading_byte_E768_and_E76A": 12})

    def test_reject_modified_original_program(self):
        image = bytearray(fake_master())
        image[0x1767] = 0
        with patch.object(grid, "MASTER_SHA", hashlib.sha256(image).hexdigest()):
            with self.assertRaisesRegex(ValueError, "1767"):
                grid.decode_course_grid(image)

    def test_reject_bad_grid_pointers(self):
        image = bytearray(fake_master())
        image[0x6384:0x6386] = (0x6590).to_bytes(2, "little")
        with patch.object(grid, "MASTER_SHA", hashlib.sha256(image).hexdigest()):
            with self.assertRaisesRegex(ValueError, "not uniformly"):
                grid.decode_course_grid(image)

    def test_original_rom_checksum_gate(self):
        with self.assertRaisesRegex(ValueError, "checksum-verified"):
            grid.decode_course_grid(fake_master())


if __name__ == "__main__":
    unittest.main()
