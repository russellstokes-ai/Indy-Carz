"""ROM-free regressions: original three-racer event latches and call scheduling."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_race_signals import (
    race_event_model, global_gate_model, service_model,
    frame_call_schedule, bank_view,
)

class ArcadeRaceSignalsTests(unittest.TestCase):
    def test_priority_bit0_over_2_over_1(self):
        self.assertEqual(race_event_model(0b111,1),(0b110,1,False,"bit0"))
        self.assertEqual(race_event_model(0b110,1),(0b010,1,False,"bit2"))
        self.assertEqual(race_event_model(0b010,1),(0,0,True,"bit1_b_nonzero"))

    def test_only_one_original_event_bit_consumed(self):
        for status in range(256):
            new,_,_,_=race_event_model(status,1)
            changed=status^new
            self.assertIn(changed,(0,1,2,4))
            self.assertEqual(new|changed,status)
            expected=(1 if status&1 else 4 if status&4 else 2 if status&2 else 0)
            self.assertEqual(changed,expected)

    def test_event_bit1_depends_on_b(self):
        self.assertEqual(race_event_model(0x82,0),(0x80,255,False,"bit1_b_zero"))
        self.assertEqual(race_event_model(0x82,1),(0x80,0,True,"bit1_b_nonzero"))
        self.assertEqual(race_event_model(0x82,255),(0x80,0,True,"bit1_b_nonzero"))

    def test_no_pending_bit_preserves_status_but_sets_z(self):
        self.assertEqual(race_event_model(0xF8,1),(0xF8,0xF8,True,"no_pending_bit"))
        self.assertEqual(race_event_model(0,0),(0,0,True,"no_pending_bit"))

    def test_three_racer_original_global_gate(self):
        self.assertEqual(global_gate_model(0,(1,3,255)),
                         {"next_pc":0x556F,"e603":1,"calls":[0x105F]})
        self.assertEqual(global_gate_model(0,(1,2,1)),
                         {"next_pc":0x1069,"e603":0,"calls":[]})
        self.assertEqual(global_gate_model(0,(1,1,128))["next_pc"],0x1069)
        self.assertEqual(global_gate_model(7,(0,0,0))["next_pc"],0x556F)

    def test_gate_ignores_other_bits_and_requires_all_three(self):
        for flags in ((0xF1,0x81,0x21),(0xFF,1,3)):
            self.assertEqual(global_gate_model(0,flags)["calls"],[0x105F])
        self.assertEqual(global_gate_model(0,(0,1,1))["next_pc"],0x1069)

    def test_service_zero_guard_is_first(self):
        self.assertEqual(service_model(0,0,7),
                         {"next":"return_6C88","car_1e":7,"calls":[]})
        self.assertEqual(service_model(0,3,7)["next"],"return_6C88")
        self.assertEqual(service_model(1,3,7),
                         {"next":"return_6C8D","car_1e":7,"calls":[]})

    def test_service_tail_two_calls_then_jump(self):
        self.assertEqual(service_model(1,0,255),
                         {"next":"jump_103C","car_1e":254,
                          "calls":[("CALL",0x103C),("CALL",0x103C),("JP",0x103C)]})

    def test_original_frame_order_exact_three_racers(self):
        bank=bytearray(0x10000);pc=0x624C
        def write(*args):
            nonlocal pc
            bank[pc:pc+len(args)]=bytes(args);pc+=len(args)
        def call(addr):write(0xCD,addr&255,addr>>8)
        call(0x1078)
        for ix,ptr in ((0xE080,0xE094),(0xE180,0xE194),(0xE280,0xE294)):
            write(0xDD,0x21,ix&255,ix>>8)
            write(0x2A,ptr&255,ptr>>8)
            call(0x18C0);call(0x6C8E)
        write(0x21,2,0);call(0x1087)
        self.assertEqual(pc,0x627C)
        result=frame_call_schedule(bytes(bank))
        self.assertEqual([e[1] for e in result],
                         [0x1078,0x18C0,0x6C8E,0x18C0,0x6C8E,0x18C0,0x6C8E,0x1087])
        self.assertEqual([e[2] for e in result],
                         [None,0xE080,0xE080,0xE180,0xE180,0xE280,0xE280,0xE280])
        self.assertEqual(result[-1][-1],2)

    def test_bad_inputs_or_untrusted_rom_rejected(self):
        with self.assertRaises(ValueError):race_event_model(256,0)
        with self.assertRaises(ValueError):race_event_model(0,-1)
        with self.assertRaises(ValueError):global_gate_model(0,(0,0))
        with self.assertRaises(ValueError):global_gate_model(256,(0,0,0))
        with self.assertRaises(ValueError):service_model(1,0,256)
        with self.assertRaises(ValueError):bank_view(bytes(0x90000))

if __name__=="__main__":unittest.main()
