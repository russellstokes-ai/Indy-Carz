"""ROM-free tests for original second bank4 1190 farcall initializer."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_bank4_race_init_2000 import (
    CAR_POINTERS,SOURCE_SIGNATURES,independent_flags,independent_globals,
    original_flags,original_globals,verify,
)


class Bank4RaceInitializerTests(unittest.TestCase):
    def test_original_five_car_pointer_order(self):
        self.assertEqual(CAR_POINTERS,(0xE080,0xE180,0xE280,0xE380,0xE480))
        self.assertEqual(SOURCE_SIGNATURES[0][:2],(0x2000,0x2031))
        self.assertEqual(SOURCE_SIGNATURES[1][:2],(0x2031,0x208C))

    def test_original_five_status_bit6_clears(self):
        r=independent_flags((0xFF,)*5,(1,1,1),(1,1,1))
        self.assertEqual(r["status_7e"],[0xBF]*5)
        self.assertEqual((r["e602"],r["e61c"]),(0,0))

    def test_first_three_reenabled_only_when_both_gates_clear(self):
        r=independent_flags((0,0,0,0x40,0x40),
                             (0,1,0),(0,0,3))
        self.assertEqual(r["status_7e"],[64,0,0,0,0])
        self.assertEqual(r["e602"],1)

    def test_status_only_one_of_first_three_is_enough(self):
        for i in range(3):
            car=[0,0,0]
            linked=[1,1,1]
            car[i]=0;linked[i]=0
            r=independent_flags((0,)*5,tuple(car),tuple(linked))
            self.assertEqual(r["e602"],1)
            self.assertEqual(sum(bool(x&64) for x in r["status_7e"]),1)

    def test_only_bits_0_and_1_of_linked_byte_matter(self):
        r=independent_flags((0,)*5,(0,0,0),(0xFC,0x04,0x80))
        self.assertEqual(r["status_7e"],[64,64,64,0,0])

    def test_signed_cp_ff_makes_127_through_254_skip_adjustment(self):
        for special in (127,128,200,254):
            for e641 in (0,1,2,255):
                actual=independent_globals(special,e641,0)
                self.assertEqual((actual["e63e"],actual["e674"]),(0,0))

    def test_e676_ff_or_zero_have_distinct_original_modes(self):
        self.assertEqual(independent_globals(255,2,0)["e674"],1)
        self.assertEqual(independent_globals(0,2,0)["e674"],2)
        self.assertEqual(independent_globals(255,2,0)["e63e"],0)

    def test_first_and_second_e641_threshold_cases(self):
        self.assertEqual(independent_globals(1,1,0)["e63e"],0)
        self.assertEqual(independent_globals(1,1,0)["e674"],3)
        self.assertEqual(independent_globals(2,1,0)["e674"],4)
        self.assertEqual(independent_globals(2,2,0)["e63e"],1)
        self.assertEqual(independent_globals(2,2,0)["e674"],3)
        self.assertEqual(independent_globals(3,3,0)["e63e"],2)
        self.assertEqual(independent_globals(3,3,0)["e674"],3)
        self.assertEqual(independent_globals(4,3,0)["e674"],4)

    def test_two_original_fourteen_entry_course_control_tables(self):
        self.assertEqual(
            [independent_globals(0,0,i)["e638"] for i in range(14)],
            [2,4,2,2,2,2,2,2,4,2,2,4,2,4]
        )
        self.assertTrue(all(independent_globals(0,0,i)["e623"]==80
                            for i in range(14)))

    def test_out_of_domain_bytes_or_course_rejected(self):
        with self.assertRaises(ValueError):
            independent_flags((0,)*4,(0,)*3,(0,)*3)
        with self.assertRaises(ValueError):
            independent_flags((0,)*5,(256,0,0),(0,)*3)
        for args in ((-1,0,0),(0,256,0),(0,0,14)):
            with self.assertRaises(ValueError):independent_globals(*args)

    def test_fake_original_machine_is_rejected(self):
        with self.assertRaises(ValueError):
            original_flags(bytes(0x90000),(0,)*5,(0,)*3,(0,)*3)
        with self.assertRaises(ValueError):
            original_globals(bytes(0x90000),0,0,0)
        with self.assertRaisesRegex(ValueError,"Authenticated original"):
            verify(bytes(0x90000),0)


if __name__=="__main__":unittest.main()
