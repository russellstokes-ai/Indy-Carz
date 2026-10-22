"""Fail closed when Godot exits zero despite failed script/runtime checks.

Godot 4.4 can print a GDScript compile error and still return exit status
zero from a partially loaded test script. CI must inspect the transcript.
"""

import argparse
import re
import sys


SUCCESS = re.compile(r"INDY-CARZ: ([1-9][0-9]*) headless checks passed\.")
ERROR_PREFIXES = ("SCRIPT ERROR:", "ERROR:", "WARNING:", "INDY-CARZ FAIL:")


def validate_output(output: str, exit_code: int) -> int:
    """Return the verified check count; reject failed or incomplete runs."""
    if exit_code != 0:
        raise ValueError(f"Godot process exit status {exit_code}")
    for line in output.splitlines():
        visible = line.lstrip()
        if visible.startswith(ERROR_PREFIXES):
            raise ValueError(f"Godot reported {visible}")
    checks = [SUCCESS.fullmatch(line.strip()) for line in output.splitlines()]
    counts = [int(match.group(1)) for match in checks if match is not None]
    if len(counts) != 1:
        raise ValueError("Godot lacks exactly one successful check marker")
    return counts[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exit-code", type=int, required=True)
    args = parser.parse_args()
    try:
        count = validate_output(sys.stdin.read(), args.exit_code)
    except ValueError as exc:
        print(f"Godot verification rejected: {exc}", file=sys.stderr)
        return 1
    print(f"Godot verification accepted: {count} clean checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
