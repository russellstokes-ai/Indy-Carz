"""ROM-free checks for original fixed 1190 -> bank4 20A8 selection stage."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_bank4_racer_selection import (
    START,STOP,CAR_POINTERS,independent,original_opcodes,verify,
)


def sample(*,e603=0,e677=0,e67d=0,e602=0,e63e=0,e674=2,
           ready=(0,0,0,0,0),status=(0,0,0,0,0),
           ordinals=(0,1,2,3,4)):
    return independent(e603,e677,e67d,e602,e63e,e674,
                       ready,status,ordinals)


class Bank4RacerSelectorTests(unittest.TestCase):
    def test_original_bank4_stage_and_car_pointer_count(self):
        self.assertEqual((START,STOP),(0x20A8,0x213F))
        self.assertEqual(CAR_POINTERS,(0xE080,0xE180,0xE280,0xE380,0xE480))

    def test_original_three_global_early_returns_in_priority_order(self):
        self.assertEqual(sample(e603=1,e677=2,e67d=3),
                         {"exit":"ret_20AC","a":1})
        self.assertEqual(sample(e677=2,e67d=3),
                         {"exit":"ret_20B2","a":2})
        self.assertEqual(sample(e67d=3),
                         {"exit":"ret_20B7","a":3})

    def test_e602_zero_uses_original_ff_sentinel_and_does_not_swap(self):
        result=sample(e602=0,e63e=0)
        self.assertEqual((result["ix"],result["b"],result["c"],result["swapped"]),
                         (0,255,2,False))

    def test_e602_nonzero_scans_ready_cars_from_fifth_to_first(self):
        for selected in range(5):
            flags=tuple(64 if i==selected else 0 for i in range(5))
            result=sample(e602=1,ready=flags)
            self.assertEqual(result["iy"],selected)
            self.assertEqual(result["b"],selected)

    def test_no_ready_flag_defaults_iy_first_car(self):
        result=sample(e602=1,ready=(0,0,0,0,0))
        self.assertEqual((result["iy"],result["b"]),(0,0))

    def test_countdown_picks_first_nonflagged_car_when_zero(self):
        result=sample(e63e=0,status=(0,1,1,1,1))
        self.assertEqual(result["ix"],0)
        # Original zero decrement is FF, so sign flag branches immediately.
        self.assertFalse(result["swapped"])

    def test_status_bit0_skips_original_decrement(self):
        result=sample(e63e=0,status=(1,0,0,0,0))
        self.assertEqual(result["ix"],1)

    def test_original_signed_cp_not_unsigned_carry(self):
        # Ready car ordinal 4, first selected car ordinal 0 -> swap to car 4.
        swapped=sample(e602=1,e63e=0,ready=(0,0,0,0,64))
        self.assertTrue(swapped["swapped"])
        self.assertEqual((swapped["ix"],swapped["c"]),(4,4))
        # Ready car ordinal 0, selected ordinal 4 -> signed negative, no swap.
        kept=sample(e602=1,e63e=5,status=(1,1,1,1,1),ready=(64,0,0,0,0))
        self.assertFalse(kept["swapped"])
        self.assertEqual((kept["ix"],kept["c"]),(4,2))

    def test_bad_byte_count_or_original_ordinals_rejected(self):
        with self.assertRaises(ValueError):sample(e603=256)
        with self.assertRaises(ValueError):sample(status=(0,0))
        with self.assertRaises(ValueError):sample(ordinals=(0,0,1,2,3))
        with self.assertRaises(ValueError):sample(ordinals=(255,1,2,3,4))

    def test_untrusted_original_rom_fails_closed(self):
        with self.assertRaises(ValueError):
            original_opcodes(bytes(0x90000),0,0,0,0,0,0,
                             (0,)*5,(0,)*5,(0,1,2,3,4))
        with self.assertRaisesRegex(ValueError,"Authenticated original"):
            verify(bytes(0x90000),0)


if __name__=="__main__":
    unittest.main()
