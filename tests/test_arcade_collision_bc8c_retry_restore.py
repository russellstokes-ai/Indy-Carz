"""ROM-free regression of verified 1991 arcade BC8C collision retry/rollback."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_collision_bc8c_retry_restore import (
    CAR_IX,ENTRY_START,ENTRY_STOP,RETRY_START,HELPER_START,HELPER_STOP,
    RESTORE_PAIRS,RAM_LEN,entry_model,retry_model,original_opcodes,
    get8,get16,put8,put16,verify
)

def memory():
    return bytearray((i*17+7)&255 for i in range(RAM_LEN))

class OriginalCollisionBC8CTests(unittest.TestCase):
    def test_original_cpu_stage_and_11_pairs(self):
        self.assertEqual((ENTRY_START,ENTRY_STOP,RETRY_START),(0xBC8C,0xBCFA,0xBCA5))
        self.assertEqual((HELPER_START,HELPER_STOP),(0xC468,0xC487))
        self.assertEqual(len(RESTORE_PAIRS),11)
        self.assertEqual(RESTORE_PAIRS[-1],(0xE747,0xE767))

    def test_entry_restores_bank_control_and_clears_original_bit(self):
        s=memory();ix=CAR_IX[0]
        put8(s,0xE608,0xA3);put8(s,0xE976,0x05)
        put8(s,ix+0x31,0xFF);put8(s,0xE92E,0xE9);put8(s,0xE92C,0xAC)
        out=entry_model(bytes(s),ix)
        self.assertEqual(out['port_f4'],(0xA5,))
        self.assertEqual(get8(out['ram'],0xE608),0xA5)
        self.assertEqual(get8(out['ram'],ix+0x31),0x7F)
        self.assertEqual((get8(out['ram'],0xE92E),get8(out['ram'],0xE92C)),(1,0))
        self.assertEqual(out['next_pc'],0xBCFA)
        self.assertEqual(out['restored_words'],0)

    def test_original_bank_or_is_not_nibble_replacement(self):
        s=memory();put8(s,0xE608,0xA3);put8(s,0xE976,0xC5)
        result=entry_model(bytes(s),CAR_IX[0])
        self.assertEqual(result['port_f4'],(0xE5,))

    def test_entry_keeps_the_other_original_car_records(self):
        s=memory()
        out=entry_model(bytes(s),CAR_IX[2])['ram']
        for ix in (CAR_IX[0],CAR_IX[1],CAR_IX[3],CAR_IX[4]):
            self.assertEqual(get8(out,ix+0x31),get8(s,ix+0x31))

    def test_original_retry_count_17_still_processes_collision(self):
        s=memory();put8(s,0xE92E,16)
        out=retry_model(bytes(s),CAR_IX[0])
        self.assertEqual(out['next_pc'],0xBCFA)
        self.assertEqual(out['counter'],17)
        self.assertEqual(out['restored_words'],0)
        self.assertEqual(get16(out['ram'],0xE72B),get16(s,0xE72B))

    def test_original_retry_count_18_restores_saved_geometry(self):
        s=memory();ix=CAR_IX[0]
        put8(s,0xE92E,17)
        for pos,(src,dst) in enumerate(RESTORE_PAIRS):
            put16(s,src,0x1000+pos)
            put16(s,dst,0xBA00+pos)
        result=retry_model(bytes(s),ix)
        self.assertEqual(result['next_pc'],0xBC9E)
        self.assertEqual(result['counter'],18)
        self.assertEqual(result['restored_words'],11)
        for pos,(_,dest) in enumerate(RESTORE_PAIRS):
            self.assertEqual(get16(result['ram'],dest),0x1000+pos)

    def test_original_c468_resets_angle_velocity_and_three_car_fields(self):
        s=memory();ix=CAR_IX[1]
        put8(s,0xE92E,17)
        put8(s,0xE768,0x52)
        result=retry_model(bytes(s),ix)
        self.assertEqual(get8(result['ram'],0xE76A),0x52)
        self.assertEqual(get16(result['ram'],0xE76B),0xCC00)
        self.assertEqual(get16(result['ram'],0xE765),0)
        for relative in (0x41,0x4C,0x4D):
            self.assertEqual(get8(result['ram'],ix+relative),0)

    def test_original_counter_ff_wrap_returns_to_collision_path(self):
        s=memory();put8(s,0xE92E,255)
        result=retry_model(bytes(s),CAR_IX[0])
        self.assertEqual((result['counter'],result['next_pc'],result['restored_words']),
                         (0,0xBCFA,0))

    def test_all_first_18_checks_without_guessing_collision_action(self):
        s=memory()
        for before in range(17):
            put8(s,0xE92E,before)
            self.assertEqual(retry_model(bytes(s),CAR_IX[0])['next_pc'],0xBCFA)
        put8(s,0xE92E,17)
        self.assertEqual(retry_model(bytes(s),CAR_IX[0])['next_pc'],0xBC9E)

    def test_fallback_retains_original_unrelated_RAM(self):
        s=memory();put8(s,0xE92E,17);put8(s,0xE604,0x6B)
        result=retry_model(bytes(s),CAR_IX[3])
        self.assertEqual(get8(result['ram'],0xE604),0x6B)

    def test_fail_closed_original_unknown_car_slot(self):
        s=bytes(memory())
        for ix in (0xE000,0xE580,0x0000,0xE680):
            with self.assertRaises(ValueError):entry_model(s,ix)
            with self.assertRaises(ValueError):retry_model(s,ix)

    def test_fail_closed_truncated_RAM_and_untrusted_ROM(self):
        with self.assertRaises(ValueError):entry_model(bytes(100),CAR_IX[0])
        with self.assertRaises(ValueError):retry_model(bytes(100),CAR_IX[0])
        with self.assertRaises(ValueError):
            original_opcodes(bytes(100),bytes(memory()),CAR_IX[0],'entry')
        with self.assertRaisesRegex(ValueError,'checksum-verified'):
            verify(bytes(0x90000),0,0)

    def test_all_counter_start_values_deterministic(self):
        s=memory()
        for initial in range(256):
            put8(s,0xE92E,initial)
            result=retry_model(bytes(s),CAR_IX[0])
            self.assertEqual(result['counter'],(initial+1)&255)
            self.assertEqual(result['restored_words'],
                             11 if (initial+1)&255>=18 else 0)

if __name__=='__main__':unittest.main()
