"""ROM-free regression for actual original B4EE two-slot branch selection."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from arcade_collision_b4ee_fallback_dispatch import START, STOP, independent, execute_original, verify


def slot(status: int)->bytes:
    r=bytearray(256)
    r[0x7C]=status
    r[0x1E:0x20]=b'\xEF\xBE'
    r[0x40:0x42]=b'\x20\x20'
    return bytes(r)


class FallbackDispatchTests(unittest.TestCase):
    def test_original_span(self):
        self.assertEqual((START, STOP),(0xB4EE,0xB506))

    def test_neither_set_restores_two(self):
        a,b=slot(0),slot(0)
        left,right,count=independent(a,b)
        self.assertEqual(count,2)
        self.assertEqual(left[0:2],b'\xEF\xBE')
        self.assertEqual(right[0:2],b'\xEF\xBE')
        self.assertEqual(left[0x7C]&0x43,0x43)
        self.assertEqual(right[0x7C]&0x43,0x43)

    def test_first_only(self):
        left,right,count=independent(slot(0),slot(1))
        self.assertEqual(count,1)
        self.assertEqual(left[0:2],b'\xEF\xBE')
        self.assertEqual(right[0:2],b'\x00\x00')

    def test_second_only(self):
        left,right,count=independent(slot(1),slot(0))
        self.assertEqual(count,1)
        self.assertEqual(left[0:2],b'\x00\x00')
        self.assertEqual(right[0:2],b'\xEF\xBE')

    def test_both_set_skips_fallback(self):
        a,b=slot(1),slot(1)
        self.assertEqual(independent(a,b),(a,b,0))

    def test_invalid_fails_closed(self):
        with self.assertRaises(ValueError):independent(bytes(255),bytes(256))
        with self.assertRaises(ValueError):execute_original(bytes(0x90000),slot(0),slot(0))
        with self.assertRaisesRegex(ValueError,'Checksum-verified'):
            verify(bytes(0x90000),0)


if __name__=='__main__':unittest.main()
