"""ROM-free tests of original collision-response angular decision and carry."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from test_arcade_collision_angle_opcode_parity import synthetic_memory
from arcade_collision_response_gate import (
    START, BRANCH_POINT, independent_direction_branch,
    execute_original_stage, verify,
)
from arcade_collision_angle_opcode_parity import (
    TABLE_BEGIN, TABLE_END, independent_angle_with_carry,
)

ORIGINAL_SHAPED_GATE = bytes.fromhex(
    "cd 00 a6 fd 66 9f fd 6e 9e dd 56 9f dd 5e 9e "
    "ed 52 29 29 29 44 fd 66 a9 fd 6e a8 "
    "dd 56 a9 dd 5e a8 ed 52 29 29 29 4c "
    "57 cd 00 a6 92 fe 40 da ac b5 fe c0 d2 ac b5"
)


def synthetic_master():
    m = bytearray(synthetic_memory())
    assert len(ORIGINAL_SHAPED_GATE) == BRANCH_POINT-START
    m[START:BRANCH_POINT] = ORIGINAL_SHAPED_GATE
    return bytes(m)


class CollisionDirectionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.memory = synthetic_master()

    def test_returned_carry_is_part_of_the_original_interface(self):
        table = self.memory[TABLE_BEGIN:TABLE_END]
        for b,c in ((0,0),(127,127),(128,0),(255,255),(0,128),(128,128)):
            value, idx, carry = independent_angle_with_carry(table,b,c)
            self.assertEqual(carry in (0,1),True)
            self.assertEqual(value, self.memory[TABLE_BEGIN+2*idx] if b<128 and c<128 else value)

    def test_original_classifier_vs_independent_model(self):
        fields = (0,1,127,128,255,0x1fff,0x2000,0x7fff,0x8000,0xffff)
        for b,c in ((0,0),(1,255),(255,1),(127,128),(128,127),(255,255)):
            for i in range(0,len(fields)-3,2):
                words = (fields[i], fields[i+1], fields[i+2], fields[i+3])
                args = (b,c,*words)
                expected = independent_direction_branch(self.memory,*args)
                observed = execute_original_stage(self.memory,*args)
                self.assertEqual(observed,expected, args)

    def test_signed_wrap_starts_from_previous_carry(self):
        table = self.memory[TABLE_BEGIN:TABLE_END]
        # Both the original NEG path and the B-negative quadrant may leave
        # carry set, which is consumed by the immediately following SBC HL,DE.
        self.assertEqual(independent_angle_with_carry(table,128,0)[2], 1)
        self.assertEqual(independent_angle_with_carry(table,0,128)[2], 1)
        self.assertEqual(independent_angle_with_carry(table,127,127)[2], 0)

    def test_checksum_and_opcode_integrity(self):
        with self.assertRaisesRegex(ValueError,"checksum-verified"):
            verify(self.memory,random_cases=1,edge_cases=1)
        corrupt=bytearray(self.memory)
        corrupt[START]=0x76
        with self.assertRaisesRegex(ValueError,"Unrecognised"):
            execute_original_stage(bytes(corrupt),0,0,1,2,3,4)


if __name__ == "__main__":
    unittest.main()
