"""ROM-free tests for original rotated vehicle-contact acceptance maths."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import arcade_collision_contact_projection as projection

ORIGINAL_SHAPE = bytes.fromhex(
    "26 a2 dd 6e bd 56 26 a5 5e 61 6a 22 fc ff 3a fd ff "
    "60 6b 22 fc ff 2a fc ff 94 e8 e6 f8 cb 2f cb 2f cb 2f "
    "c6 09 fe 12 d0 08 60 6a 22 fc ff 3a fd ff 61 6b "
    "22 fc ff 2a fc ff 37 8c e8 e6 f8 cb 2f cb 2f cb 2f "
    "c6 0c fe 18 d0"
)


def original_shaped_memory():
    master = bytearray(0x90000)
    master[projection.START:projection.STOP] = ORIGINAL_SHAPE
    for angle in range(256):
        c,s = projection.trig8(angle)
        master[0xA200+angle] = c
        master[0xA500+angle] = s
    xrom = bytearray(0x40000)
    for x in range(256):
        for y in range(256):
            result = max(-32768, min(32767, projection.s8(x) * projection.s8(y) * 2)) & 65535
            offset = 2*((x << 8) | y)
            xrom[offset] = result & 255
            xrom[offset+1] = result >> 8
    return bytes(master), bytes(xrom)


class OrientedCollisionProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master, cls.xrom = original_shaped_memory()

    def test_original_instruction_stage_is_exact_length(self):
        self.assertEqual(len(ORIGINAL_SHAPE), projection.STOP - projection.START)
        self.assertEqual(projection.STOP, 0xB4A3)

    def test_analytic_projection_matches_opcode_interpretation(self):
        for angle in (0,1,8,32,64,96,127,128,160,192,224,255):
            for b in (0,1,8,32,64,127,128,192,254,255):
                for c in (0,1,16,63,127,128,240,255):
                    with self.subTest(angle=angle,b=b,c=c):
                        original = projection.original_projection(self.master,self.xrom,angle,b,c)
                        expected = projection.independent_projection(angle,b,c)
                        self.assertEqual(original,expected)

    def test_all_five_possible_original_outcomes(self):
        # Sweep a manageable sample without proprietary data to exercise
        # all overflow, range and successful-acceptance branches.
        decisions = set()
        for angle in range(0,256,8):
            for b in range(0,256,8):
                for c in range(0,256,8):
                    decisions.add(projection.independent_projection(angle,b,c))
        self.assertEqual(decisions,{
            "axis0_overflow","axis0_range","axis1_overflow",
            "axis1_range","passes_projection",
        })

    def test_bad_inputs_and_modified_opcode_fail_closed(self):
        with self.assertRaises(ValueError):
            projection.trig8(256)
        with self.assertRaises(ValueError):
            projection.mul_hi(-1,255)
        with self.assertRaises(ValueError):
            projection.independent_projection(0,0,256)
        modified = bytearray(self.master)
        modified[0xB475] ^= 0x01
        with self.assertRaisesRegex(ValueError,"Unexpected"):
            projection.original_projection(bytes(modified),self.xrom,0,127,127)
        with self.assertRaisesRegex(ValueError,"checksum-matched"):
            projection.verify(self.master,self.xrom)


if __name__ == "__main__":
    unittest.main()
