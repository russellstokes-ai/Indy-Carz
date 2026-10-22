"""ROM-free tests of exact original bank4 213F-22B9 post-metric effects."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_bank4_post_metric_dispatch import (
    START, STOP, independent, original_opcodes, verify,
)


class OriginalPostMetricTests(unittest.TestCase):
    def test_full_bounded_source_span(self):
        self.assertEqual((START,STOP), (0x213F,0x22BA))

    def test_three_original_routing_paths(self):
        cases = [
            ((31918,21225,32254,2,130,255,203,237,175,184,198,142,52939,3),
             ("225A","return_nc_226F",54779,185,14)),
            ((14928,3715,33843,2,244,127,90,177,153,188,229,98,3863,224),
             ("2247","return_nc_2268",54331,189,130)),
            ((3399,23068,52401,4,230,1,169,156,236,29,30,117,13098,217),
             ("228F","return_c_229D",19653,29,101)),
        ]
        for params,values in cases:
            observed=independent(*params)
            self.assertEqual(
                (observed["route"],observed["exit"],observed["e61c"],
                 observed["fifth_event"],observed["linked_3a"]),values)

    def test_original_1c8c_rng_gate_and_saved_state(self):
        values=(37652,37419,8077,4,142,1,66,227,100,82,114,108,64451,161)
        r=independent(*values)
        self.assertTrue(r["rng_used"])
        self.assertEqual((r["rng_state"],r["fifth_event"]),(19201,83))

    def test_original_fifth_car_field_39_reset(self):
        values=(60857,1475,20550,4,39,4,145,224,228,244,195,8,36603,71)
        r=independent(*values)
        self.assertEqual(r["fifth_39"],0)

    def test_opaque_original_follow_on_actions_not_treated_as_ret(self):
        b=(24899,2179,43316,4,152,0,82,155,48,68,4,95,7731,242)
        c=(26858,44170,14126,2,42,1,93,231,209,212,76,0,24450,123)
        self.assertEqual(independent(*b)["exit"],"external_10EB")
        self.assertEqual(independent(*c)["exit"],"external_10E6")

    def test_16bit_difference_is_wrapped_not_floating_point(self):
        a=(31918,21225,32254,2,130,255,203,237,175,184,198,142,52939,3)
        r=independent(*a)
        self.assertEqual(r["initial_metric_delta"],(a[1]-a[0])&65535)

    def test_checked_input_domains(self):
        a=[0]*14
        a[3]=2
        independent(*a)
        for index,bad in ((0,65536),(3,3),(4,256),(12,-1),(13,256)):
            args=a.copy();args[index]=bad
            with self.assertRaises(ValueError):
                independent(*args)

    def test_private_original_rom_mandatory_for_opcode_parity(self):
        vals=(31918,21225,32254,2,130,255,203,237,175,184,198,142,52939,3)
        with self.assertRaises(ValueError):
            original_opcodes(bytes(0x90000),*vals)
        with self.assertRaisesRegex(ValueError,"Authenticated"):
            verify(bytes(0x90000),0)


if __name__=="__main__":
    unittest.main()
