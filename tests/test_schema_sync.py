#!/usr/bin/env python3
"""
Schema-sync sanity check.

Runs without pytest. Verifies that:
1. Every key declared in app/config.py FIELDS is present in initial_profile/Profiles.ini.
2. Every Profile_N section in the template contains the same set of keys (no missing/extra
   per profile).
3. No legacy key names (e.g. HeterSelectiveFilter without Pre- prefix) leak into the
   template — they would be silently ignored by the firmware.

Usage:
    python tests/test_schema_sync.py
Exits 0 on success, 1 on failure.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "initial_profile" / "Profiles.ini"
CONFIG = ROOT / "app" / "config.py"

# Keys the firmware reads under a different name than what ExportProfiles writes.
# The app MUST emit the read-side name; emitting the export-side name causes the
# firmware to silently fall back to the default. See plan Phase 0.2.
FIRMWARE_READ_ALIASES = {
    # Export name (firmware writes this)   → Read name (firmware reads this)
    "HeterSelectiveFilter": "Pre-HeterSelectiveFilter",
}


def parse_template(path: Path) -> dict[str, set[str]]:
    """Return {section_name: set(keys)} from an INI-style file."""
    sections: dict[str, set[str]] = {}
    current = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith(";"):
            continue
        if s.startswith("[") and s.endswith("]"):
            current = s[1:-1]
            sections.setdefault(current, set())
            continue
        if current and "=" in s:
            key = s.split("=", 1)[0].strip()
            sections[current].add(key)
    return sections


def parse_fields_keys(path: Path) -> set[str]:
    """Extract every key of the FIELDS dict in config.py via regex.

    Looks for lines like:    "MasterSlave": {"type": "int", ...},
    """
    text = path.read_text(encoding="utf-8")
    # FIELDS opens at module level; capture until its closing brace.
    match = re.search(r"FIELDS\s*=\s*\{(.*?)^\}", text, re.DOTALL | re.MULTILINE)
    if not match:
        raise SystemExit("Could not locate FIELDS = {...} block in config.py")
    body = match.group(1)
    keys = set(re.findall(r'^\s*"([\w\-]+)"\s*:\s*\{', body, re.MULTILINE))
    return keys


def main() -> int:
    if not TEMPLATE.exists():
        print(f"FAIL: template not found at {TEMPLATE}", file=sys.stderr)
        return 1
    if not CONFIG.exists():
        print(f"FAIL: config not found at {CONFIG}", file=sys.stderr)
        return 1

    sections = parse_template(TEMPLATE)
    fields = parse_fields_keys(CONFIG)
    errors: list[str] = []

    # 1. All profile sections must share the same key set.
    profile_sections = {n: keys for n, keys in sections.items() if n.startswith("Profile_")}
    if not profile_sections:
        errors.append("No [Profile_N] sections found in template.")
    else:
        ref_name, ref_keys = next(iter(profile_sections.items()))
        for name, keys in profile_sections.items():
            missing = ref_keys - keys
            extra = keys - ref_keys
            if missing:
                errors.append(f"Section [{name}] is missing keys vs [{ref_name}]: {sorted(missing)}")
            if extra:
                errors.append(f"Section [{name}] has extra keys vs [{ref_name}]: {sorted(extra)}")

        # 2. Every FIELDS key must be present in every profile section
        #    (except ProfileName-ish identification keys handled at top-level).
        for name, keys in profile_sections.items():
            absent = fields - keys
            if absent:
                errors.append(
                    f"FIELDS keys absent from [{name}]: {sorted(absent)}"
                )

    # 3. Legacy export-side names must not appear (firmware would ignore them).
    for section_keys in sections.values():
        for legacy, modern in FIRMWARE_READ_ALIASES.items():
            if legacy in section_keys and modern not in section_keys:
                errors.append(
                    f"Template uses legacy key '{legacy}' instead of '{modern}'. "
                    f"Firmware will silently drop this value at read time."
                )

    if errors:
        print("Schema sync FAILED:\n  - " + "\n  - ".join(errors), file=sys.stderr)
        return 1

    print(
        f"OK — {len(fields)} FIELDS keys aligned with template "
        f"({len(profile_sections)} profile sections)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
