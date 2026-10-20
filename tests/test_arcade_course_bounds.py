"""Synthetic-only tests for original course-indexed spatial gate rules."""
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import arcade_course_bounds as bounds


def fake_master():
    data = bytearray(0x90000)
    for at, sig in bounds.SIGNATURES:
        raw = bytes.fromhex(sig)
        data[at:at+len(raw)] = raw
    for c in range(bounds.COUNT):
        data[bounds.AXIS_E72C_TABLE+2*c:bounds.AXIS_E72C_TABLE+2*c+2] = bytes([10+c, 20+c])
        data[bounds.AXIS_E736_TABLE+2*c:bounds.AXIS_E736_TABLE+2*c+2] = bytes([30+c, 38+c])
    return bytes(data)


class ArcadeCourseBoundsTests(unittest.TestCase):
    def test_upper_exclusive_lower_inclusive(self):
        self.assertTrue(bounds.accept_coordinate(10, 20, 10))
        self.assertTrue(bounds.accept_coordinate(10, 20, 19))
        self.assertFalse(bounds.accept_coordinate(10, 20, 20))
        self.assertFalse(bounds.accept_coordinate(10, 20, 9))

    def test_original_six_unit_relative_gate(self):
        self.assertTrue(bounds.accept_spatial_gate(40, 40, (38, 45), 25, (20, 30)))
        self.assertFalse(bounds.accept_spatial_gate(40, 30, (38, 45), 25, (20, 30)))
        self.assertFalse(bounds.accept_spatial_gate(40, 40, (38, 45), 31, (20, 30)))
        self.assertTrue(bounds.accept_spatial_gate(0, 255, (0, 10), 25, (20, 30)))

    def test_fourteen_course_bounds(self):
        image = fake_master()
        with patch.object(bounds, "EXPECTED_SHA", hashlib.sha256(image).hexdigest()):
            result = bounds.extract(image)
        self.assertEqual(result["course_count"], 14)
        self.assertEqual(len(result["course_dependent_spatial_bounds"]), 14)
        self.assertEqual(
            result["course_dependent_spatial_bounds"][13]["RAM_E95B_comparison_axis_E72C"],
            {"inclusive_min": 23, "exclusive_max": 33})

    def test_refuse_corrupted_spatial_comparison(self):
        image = bytearray(fake_master())
        image[0x7ACA] = 0
        with patch.object(bounds, "EXPECTED_SHA", hashlib.sha256(image).hexdigest()):
            with self.assertRaisesRegex(ValueError, "7ACA"):
                bounds.extract(image)

    def test_checksum_gate(self):
        with self.assertRaisesRegex(ValueError, "Verified original arcade"):
            bounds.extract(fake_master())


if __name__ == "__main__":
    unittest.main()
