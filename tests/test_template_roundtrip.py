#!/usr/bin/env python3
"""Template I/O roundtrip sanity check.

Guards the architectural invariant of the template-canonical save pipeline:
loading the embedded template and re-rendering it with no overrides must
produce a byte-identical file. Without this, drift between the parse and
render passes would silently corrupt user files at save time.

Also exercises override injection (string fields preserve quoting, int
fields are emitted unquoted) and the legacy alias migration.

Usage:
    python tests/test_template_roundtrip.py
Exits 0 on success, 1 on failure.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.ini_utils import (  # noqa: E402
    LEGACY_ALIASES,
    load_template_lines,
    parse_ini,
    render_from_template,
    detect_missing_keys,
    detect_dropped_keys,
)


def main() -> int:
    template_lines = load_template_lines()
    parsed = parse_ini(template_lines)
    errors: list[str] = []

    # 1. Empty overrides → output equals template byte-for-byte.
    rendered_empty = render_from_template(template_lines, {})
    if rendered_empty != template_lines:
        errors.append(
            "render_from_template({}) is not lossless on the template "
            f"(diff at line {next((i for i, (a, b) in enumerate(zip(template_lines, rendered_empty)) if a != b), -1)})"
        )

    # 2. Re-injecting the parsed values produces the same output.
    rendered_self = render_from_template(template_lines, parsed)
    if rendered_self != template_lines:
        errors.append("render_from_template(parsed_template) is not lossless")

    # 3. Override on a string field preserves the template's quote style.
    overrides = {"Profile_2": {"ProfileName": "MyTest"}}
    rendered = "".join(render_from_template(template_lines, overrides))
    if 'ProfileName="MyTest"' not in rendered:
        errors.append("String override did not preserve template's double quotes")

    # 4. Override on an int field emits unquoted.
    overrides = {"Profile_2": {"MinFreqUS": "20000"}}
    rendered = "".join(render_from_template(template_lines, overrides))
    if "MinFreqUS=20000" not in rendered:
        errors.append("Int override did not emit unquoted value")
    if 'MinFreqUS="20000"' in rendered:
        errors.append("Int override wrongly added quotes around the value")

    # 5. Missing key detection works.
    truncated = [line for line in template_lines if "MasterSlave=" not in line]
    user_parsed = parse_ini(truncated)
    missing = detect_missing_keys(user_parsed, parsed)
    if not any(k == "MasterSlave" for _, k in missing):
        errors.append(f"Missing-key detection didn't flag MasterSlave; got {missing[:5]}")

    # 6. Dropped key detection works.
    augmented = []
    for line in template_lines:
        augmented.append(line)
        if line.startswith("[Profile_2]"):
            augmented.append("LegacyBogus=42\n")
    user_parsed = parse_ini(augmented)
    dropped = detect_dropped_keys(user_parsed, parsed)
    if ("Profile_2", "LegacyBogus") not in dropped:
        errors.append("Dropped-key detection didn't flag 'LegacyBogus'")

    # 7. Legacy alias migration: parse rewrites the key on the way in.
    fake_legacy = "[Profile_1]\nHeterSelectiveFilter=1\n"
    parsed_legacy = parse_ini(fake_legacy.splitlines(keepends=True))
    p1 = parsed_legacy.get("Profile_1", {})
    canonical = LEGACY_ALIASES["HeterSelectiveFilter"]
    if p1.get(canonical) != "1":
        errors.append(
            f"Legacy alias migration failed: expected {canonical}=1, got {p1}"
        )
    if "HeterSelectiveFilter" in p1:
        errors.append("Legacy key name leaked through parse_ini")

    if errors:
        print("Template roundtrip FAILED:\n  - " + "\n  - ".join(errors), file=sys.stderr)
        return 1

    print(
        f"OK — template roundtrip lossless "
        f"({len(template_lines)} lines, {len(parsed)} sections), "
        f"override injection / drift detection / alias migration all green."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
