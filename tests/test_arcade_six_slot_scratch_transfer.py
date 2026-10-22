"""ROM-free original six-slot 48-word master Z80 scratch transfer tests."""
import unittest,sys
from pathlib import Path
from random import Random
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_six_slot_scratch_transfer import (
    SLOT_STARTS,SCRATCH,COPIED_BYTES,WORDS,RAM_BASE,RAM_LEN,
    LOAD_SHA,SAVE_SHA,direct,original_opcode_transfers,verify
)


def fake_master()->bytes:
    binary=bytearray(0x90000)
    for n in range(WORDS):
        dst=SCRATCH+2*n
        binary[0x61D4+4*n:0x61D4+4*n+4]=bytes((0xE1,0x22,dst&255,dst>>8))
        src=SCRATCH+2*(WORDS-1-n)
        binary[0x62A0+4*n:0x62A0+4*n+4]=bytes((0x2A,src&255,src>>8,0xE5))
    return bytes(binary)


class OriginalScratchTransferTests(unittest.TestCase):
    def test_original_sixtyfour_words_not_guessed(self):
        self.assertEqual(WORDS,48)
        self.assertEqual(COPIED_BYTES,96)
        self.assertEqual(SCRATCH,0xE72B)
        self.assertEqual(len(LOAD_SHA),64)
        self.assertEqual(len(SAVE_SHA),64)

    def test_exact_six_physical_slot_starts(self):
        self.assertEqual(SLOT_STARTS,
                         (0xE000,0xE100,0xE200,0xE300,0xE400,0xE500))

    def test_original_opcode_vs_independent_model_every_slot(self):
        master=fake_master()
        rng=Random(0x61CE)
        for ix in SLOT_STARTS:
            for _ in range(12):
                ram=rng.randbytes(RAM_LEN)
                for loading in (True,False):
                    self.assertEqual(original_opcode_transfers(
                        master,ram,ix,loading),direct(ram,ix,loading))

    def test_load_copies_only_first_96_bytes_to_scratch(self):
        ram=bytearray(range(256))*32
        for slot in SLOT_STARTS:
            result=direct(bytes(ram),slot,True)
            start=slot-RAM_BASE
            dst=SCRATCH-RAM_BASE
            self.assertEqual(result[dst:dst+96],ram[start:start+96])
            self.assertEqual(result[start:start+256],ram[start:start+256])

    def test_save_preserves_original_high_160_bytes(self):
        ram=bytearray(RAM_LEN)
        ram[SCRATCH-RAM_BASE:SCRATCH-RAM_BASE+96]=bytes(range(96))
        for slot in SLOT_STARTS:
            base=slot-RAM_BASE
            ram[base+96:base+256]=bytes([0xA7])*160
            saved=direct(bytes(ram),slot,False)
            self.assertEqual(saved[base:base+96],bytes(range(96)))
            self.assertEqual(saved[base+96:base+256],bytes([0xA7])*160)

    def test_original_load_save_roundtrip_without_other_writes(self):
        rng=Random(0x629A)
        for slot in SLOT_STARTS:
            ram=rng.randbytes(RAM_LEN)
            back=direct(direct(ram,slot,True),slot,False)
            self.assertEqual(back,ram[:SCRATCH-RAM_BASE]+
                             ram[slot-RAM_BASE:slot-RAM_BASE+96]+
                             ram[SCRATCH-RAM_BASE+96:])

    def test_source_opcode_mutation_fails_closed(self):
        master=bytearray(fake_master())
        for addr in (0x61D4,0x62A0):
            mutated=bytearray(master);mutated[addr]^=1
            with self.assertRaises(ValueError):
                original_opcode_transfers(bytes(mutated),bytes(RAM_LEN),0xE000,addr==0x61D4)

    def test_invalid_ram_length_or_car_index_rejected(self):
        with self.assertRaises(ValueError):direct(bytes(10),0xE000,True)
        with self.assertRaises(ValueError):direct(bytes(RAM_LEN),0xE600,True)
        with self.assertRaises(ValueError):
            original_opcode_transfers(fake_master()[:5],bytes(RAM_LEN),0xE000,True)

    def test_forged_original_master_rejected(self):
        with self.assertRaisesRegex(ValueError,"checksum-verified"):
            verify(bytes(0x90000),0)


if __name__=="__main__":unittest.main()
