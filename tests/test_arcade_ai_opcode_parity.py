"""Synthetic AI-stage formula tests; the original ROM never enters the repo."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_ai_opcode_parity import independent_ai_input, original_ai_input, SIGNATURE, START, STOP


class OriginalAiStageTests(unittest.TestCase):
    def test_known_formula(self):
        self.assertEqual(independent_ai_input(0, 0), (0, 0))
        self.assertEqual(independent_ai_input(255, 0), (126, 127))
        self.assertEqual(independent_ai_input(255, 255), (126, 128))
        self.assertEqual(independent_ai_input(128, 64), (64, 0))
        self.assertEqual(independent_ai_input(1, 2), (0, 254))

    def test_bounded_original_sequence_synthetic(self):
        synthetic = bytearray(0x90000)
        synthetic[START:STOP] = SIGNATURE
        for original in (0, 1, 64, 127, 128, 254, 255):
            for difference in (0, 1, 60, 128, 255):
                self.assertEqual(original_ai_input(synthetic, original, difference),
                                 independent_ai_input(original, difference))

    def test_signature_precondition(self):
        with self.assertRaisesRegex(ValueError, "routine not found"):
            original_ai_input(bytes(0x90000), 1, 1)


if __name__ == "__main__":
    unittest.main()
