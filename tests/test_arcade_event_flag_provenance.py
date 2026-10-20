"""No original ROM needed: event-flag SET provenance and bank mapping checks."""
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import arcade_event_flag_provenance as flags


def synthetic_master():
    m = bytearray(0x90000)
    handlers = [
        (0x32,5,0x6C1C), (0x32,3,0x6DFA), (0x32,4,0x6E06),
        (0x31,5,0x6EA6), (0x7E,2,0x6A18), (0x31,4,0x6A3A),
        (0x32,6,0x6B61), (0x32,7,0x6BA2), (0x33,3,0x6A51),
    ]
    for i,(field,bit,handler) in enumerate(handlers):
        pc=0x3006+7*i
        m[pc:pc+7]=bytes((0xDD,0xCB,field,0x46+8*bit,
                          0xC4,handler&255,handler>>8))
    m[0x3045:0x304D]=bytes.fromhex("DD 7E 34 E6 30 C4 3B 11")
    m[0x304D:0x3050]=bytes.fromhex("CD 9D 68")
    for (field,bit),sites in flags.KNOWN_SET_SITES.items():
        for bank,pc in sites:
            at=flags.BANK_OFFSETS[bank]+pc-0x2000
            m[at:at+4]=bytes((0xDD,0xCB,field,0xC6+8*bit))
    b1_at=flags.BANK_OFFSETS[1]+0x375A-0x2000
    m[b1_at:b1_at+4]=bytes.fromhex("FD CB 33 DE")
    return bytes(m)


class OriginalFlagProvenanceTests(unittest.TestCase):
    def test_nine_consumers_and_bank_aware_sources(self):
        m=synthetic_master()
        with patch.object(flags,"MASTER_SHA",hashlib.sha256(m).hexdigest()):
            result=flags.inspect(m)
        self.assertEqual(result["original_event_flag_consumers"],9)
        self.assertEqual(result["original_instruction_aligned_producer_sites"],11)
        self.assertEqual(result["flag_records"][0]["known_aligned_set_sites"],
                         [{"bank":1,"pc":"3B89"}, {"bank":1,"pc":"454E"},
                          {"bank":1,"pc":"5697"}])
        self.assertEqual(result["two_record_status_site"]["iy_status_set_pc"],"375A")
        self.assertEqual(result["flag_records"][7]["handler_pc"],"6BA2")

    def test_raw_matches_not_confused_with_confirmed_sources(self):
        m=bytearray(synthetic_master())
        pc=0x7000
        m[pc:pc+4]=bytes.fromhex("DD CB 32 EE") # extra unclassified candidate
        with patch.object(flags,"MASTER_SHA",hashlib.sha256(m).hexdigest()):
            result=flags.inspect(bytes(m))
        self.assertEqual(result["original_instruction_aligned_producer_sites"],11)
        self.assertIn({"bank":0, "cpu_pc":"7000",
                       "evidence":"raw exact opcode signature; execution not established"},
                      result["flag_records"][0]["raw_candidate_set_sites"])

    def test_corrupt_critical_source_rejected(self):
        m=bytearray(synthetic_master())
        at=flags.BANK_OFFSETS[1]+0x526A-0x2000
        m[at+3]=0
        with patch.object(flags,"MASTER_SHA",hashlib.sha256(m).hexdigest()):
            with self.assertRaisesRegex(ValueError,"526A"):
                flags.inspect(bytes(m))

    def test_reject_unverified_master_image(self):
        with self.assertRaisesRegex(ValueError,"Verified original"):
            flags.inspect(synthetic_master())


if __name__=="__main__":
    unittest.main()
