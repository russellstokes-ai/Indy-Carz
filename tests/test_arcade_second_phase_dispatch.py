"""Synthetic ROM-free tests for original Z80 per-car event dispatch parsing."""
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import arcade_second_phase_dispatch as second

KNOWN = [
    (0x32,5,0x6C1C), (0x32,3,0x6DFA), (0x32,4,0x6E06),
    (0x31,5,0x6EA6), (0x7E,2,0x6A18), (0x31,4,0x6A3A),
    (0x32,6,0x6B61), (0x32,7,0x6BA2), (0x33,3,0x6A51),
]


def dummy_original_shape():
    region = bytearray(0x90000)
    for i,(offset,bit,target) in enumerate(KNOWN):
        pc = 0x3006 + 7*i
        region[pc:pc+7] = bytes([
            0xDD, 0xCB, offset, 0x46 + 8*bit,
            0xC4, target & 255, target >> 8,
        ])
    for i,(offset,bit,target) in enumerate(KNOWN):
        # Original seven flag-clearing handlers; two are non-clearing at entry.
        if i not in (5, 7):
            region[target:target+4] = bytes([
                0xDD, 0xCB, offset, 0x86 + 8*bit
            ])
    region[0x3045:0x304D] = bytes.fromhex("dd 7e 34 e6 30 c4 3b 11")
    region[0x304D:0x3050] = bytes.fromhex("cd 9d 68")
    for address, signature in second.SPATIAL_BRANCH_SIGNATURES.items():
        b = bytes.fromhex(signature)
        region[address:address+len(b)] = b
    return bytes(region)


class SecondPhaseDispatchTests(unittest.TestCase):
    def test_original_flag_dispatch_table(self):
        region = dummy_original_shape()
        handlers = second.parse_postevent_handlers(region)
        self.assertEqual(len(handlers), 9)
        self.assertEqual(sum(bool(x["clears_trigger_flag_on_entry"]) for x in handlers), 7)
        self.assertFalse(handlers[5]["clears_trigger_flag_on_entry"])
        self.assertFalse(handlers[7]["clears_trigger_flag_on_entry"])
        self.assertEqual(
            [(int(v["state_ix_offset"],16), v["state_bit"],int(v["target_pc"],16))
             for v in handlers], KNOWN)
        self.assertEqual(second.parse_spatial_branch(region)["course_event_call"],
                         "2F4F -> 7AB4")

    def test_checksum_verification_and_report(self):
        region = dummy_original_shape()
        with patch.object(second, "MASTER_HASH", hashlib.sha256(region).hexdigest()):
            r = second.extract(region)
        self.assertEqual(r["per_car_second_callback"], "2F1E")
        self.assertEqual(len(r["conditional_state_handlers"]), 9)
        self.assertEqual(r["immediately_clearing_handlers"], 7)
        self.assertIn("OPEN", r["spatial_branch"]["meaning"])

    def test_mutated_opcode_rejected(self):
        region = bytearray(dummy_original_shape())
        region[0x3029 + 4] = 0xCD  # unconditional CALL is NOT the arcade opcode
        with self.assertRaisesRegex(ValueError,"CALL NZ"):
            second.parse_postevent_handlers(bytes(region))
        region = bytearray(dummy_original_shape())
        region[0x2F4F] = 0
        with self.assertRaisesRegex(ValueError,"2F49"):
            second.parse_spatial_branch(bytes(region))

    def test_proprietary_rom_hash_required(self):
        with self.assertRaisesRegex(ValueError,"Checksum-verified"):
            second.extract(dummy_original_shape())


if __name__ == "__main__":
    unittest.main()
