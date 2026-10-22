"""The Godot smoke-test process must not conceal script/runtime failures."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from check_godot_test_output import validate_output


class GodotOutputGateTests(unittest.TestCase):
    GOOD = (
        "Godot Engine v4.4.1.stable.official\n"
        "INDY-CARZ: 227836 headless checks passed.\n"
    )

    def test_accepts_clean_nonzero_check_count(self):
        self.assertEqual(validate_output(self.GOOD, 0), 227836)

    def test_script_parse_failure_rejected_even_with_zero_exit_status(self):
        bad = self.GOOD + (
            'SCRIPT ERROR: Parse Error: The member "Control" shadows a native class.\n'
        )
        with self.assertRaisesRegex(ValueError, "SCRIPT ERROR"):
            validate_output(bad, 0)

    def test_viewport_runtime_error_rejected_even_if_checks_pass(self):
        bad = "ERROR: Condition \"!is_inside_tree()\" is true.\n" + self.GOOD
        with self.assertRaisesRegex(ValueError, "ERROR"):
            validate_output(bad, 0)

    def test_nonzero_exit_status_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "exit status 1"):
            validate_output(self.GOOD, 1)

    def test_missing_or_zero_check_marker_fails_closed(self):
        for output in ("Godot Engine v4.4.1\n", "INDY-CARZ: 0 headless checks passed.\n"):
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError, "successful check marker"):
                    validate_output(output, 0)


if __name__ == "__main__":
    unittest.main()
