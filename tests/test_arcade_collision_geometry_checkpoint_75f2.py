"""ROM-free regression for eleven original Z80 75F2 geometry save words."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_collision_geometry_checkpoint_75f2 import (
    START,RET,STAGE_SHA,PAIRS,word,put,independent,original_opcodes,verify
)
from arcade_collision_bc8c_retry_restore import retry_model as fallback


def memory():
    ram=bytearray([0xC7]*8192)
    for i,(src,dst) in enumerate(PAIRS):
        put(ram,src,(0xCDEF+781*i)&65535)
        put(ram,dst,0x1030+i)
    return bytes(ram)


class Original75F2CheckpointTests(unittest.TestCase):
    def test_authenticated_11_word_stage_boundaries(self):
        self.assertEqual((START,RET),(0x75F2,0x7634))
        self.assertEqual(len(STAGE_SHA),64)
        self.assertEqual(len(PAIRS),11)

    def test_source_to_backup_address_order(self):
        self.assertEqual(PAIRS[0],(0xE72B,0xE749))
        self.assertEqual(PAIRS[1],(0xE735,0xE753))
        self.assertEqual(PAIRS[-1],(0xE767,0xE747))
        self.assertEqual(len({p[0] for p in PAIRS}),11)
        self.assertEqual(len({p[1] for p in PAIRS}),11)

    def test_only_original_saved_words_change(self):
        source=memory()
        result=independent(source)
        changed=result["ram"]
        destinations={dst+part-0xE000 for src,dst in PAIRS for part in (0,1)}
        for src,dst in PAIRS:
            self.assertEqual(word(changed,dst),word(source,src))
        self.assertTrue(all(changed[i]==source[i]
                            for i in range(8192) if i not in destinations))
        self.assertEqual(result["return_pc"],RET)

    def test_correct_original_write_order_and_exact_bytes(self):
        result=independent(memory())
        self.assertEqual(result["writes"],
                         [(dst,word(memory(),src)) for src,dst in PAIRS])
        self.assertEqual(len(result["writes"]),11)

    def test_checkpoint_roundtrips_through_original_c468_fallback(self):
        # Original BC8C 18-count reset restores the saved eleven words.
        source=memory()
        saved=bytearray(independent(source)["ram"])
        for src,dst in PAIRS:
            put(saved,src,0)
        saved[0xE92E-0xE000]=17
        result=fallback(bytes(saved),0xE080)
        self.assertEqual(result["next_pc"],0xBC9E)
        self.assertEqual(result["restored_words"],11)
        for src,dst in PAIRS:
            self.assertEqual(word(result["ram"],src),word(source,src))

    def test_wrap_zero_and_high_16bit_words(self):
        source=bytearray(memory())
        for n,(src,dst) in enumerate(PAIRS):
            put(source,src,(0xFFFF if n&1 else 0))
        result=independent(bytes(source))
        for src,dst in PAIRS:
            self.assertEqual(word(result["ram"],src),word(result["ram"],dst))

    def test_input_is_never_mutated(self):
        source=memory()
        saved=independent(source)
        self.assertEqual(source,memory())
        self.assertNotEqual(source,saved["ram"])

    def test_wrong_size_address_or_untrusted_rom_fails_closed(self):
        with self.assertRaises(ValueError):independent(bytes(127))
        with self.assertRaises(ValueError):put(bytearray(8192),0xFFFF,0)
        with self.assertRaises(ValueError):word(memory(),0xDFFF)
        with self.assertRaises(ValueError):original_opcodes(bytes(24),memory())
        with self.assertRaisesRegex(ValueError,"Authenticated"):
            verify(bytes(0x90000),0)


if __name__=="__main__":unittest.main()
