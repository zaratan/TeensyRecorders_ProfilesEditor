#!/usr/bin/env python3
"""Schema-sync sanity check.

Runs without pytest. Verifies that:
1. Every key declared in app/config.py FIELDS is present in every
   Profile_N section of initial_profile/Profiles.ini.
2. Every Profile_N section in the template contains the same key set.
3. No legacy key names (e.g. HeterSelectiveFilter without the Pre- prefix)
   leak into the template — they would be silently ignored by the firmware.
4. Every FIELDS entry uses only known attributes (typo guard) and combos
   with `choice_labels` have len(choices) == len(choice_labels).

Usage:
    python tests/test_schema_sync.py
Exits 0 on success, 1 on failure.
"""

import sys
from pathlib import Path

# Make app/ importable when running the script directly.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import FIELDS, SCOPE_BADGES  # noqa: E402
from app.ini_utils import LEGACY_ALIASES, load_template_lines, parse_ini  # noqa: E402

# Whitelist of attributes any FIELDS entry may carry. Typing a new optional
# attribute (e.g. "choise_labels") triggers a fail here rather than a silent
# behaviour bug at runtime.
ALLOWED_FIELD_ATTRS = {
    "type", "min", "max", "step", "default",
    "choices", "choice_labels", "tag", "helper", "limit", "scope",
}


def main() -> int:
    template_lines = load_template_lines()
    sections = parse_ini(template_lines)
    profile_sections = {n: keys for n, keys in sections.items() if n.startswith("Profile_")}
    errors: list[str] = []

    if not profile_sections:
        errors.append("No [Profile_N] sections found in template.")
    else:
        # 1. All profile sections must share the same key set.
        ref_name, ref_keys = next(iter(profile_sections.items()))
        for name, keys in profile_sections.items():
            missing = set(ref_keys) - set(keys)
            extra = set(keys) - set(ref_keys)
            if missing:
                errors.append(f"[{name}] missing keys vs [{ref_name}]: {sorted(missing)}")
            if extra:
                errors.append(f"[{name}] extra keys vs [{ref_name}]: {sorted(extra)}")

        # 2. Every FIELDS key must be present in every profile section.
        fields = set(FIELDS.keys())
        for name, keys in profile_sections.items():
            absent = fields - set(keys)
            if absent:
                errors.append(f"FIELDS keys absent from [{name}]: {sorted(absent)}")

    # 3. Legacy export-side names must not appear (firmware would ignore them).
    for section_keys in sections.values():
        for legacy, modern in LEGACY_ALIASES.items():
            if legacy in section_keys and modern not in section_keys:
                errors.append(
                    f"Template uses legacy key '{legacy}' instead of '{modern}'. "
                    f"Firmware will silently drop this value at read time."
                )

    # 4. FIELDS entries use only known attributes; choice_labels length matches.
    for key, meta in FIELDS.items():
        extras = set(meta.keys()) - ALLOWED_FIELD_ATTRS
        if extras:
            errors.append(f"FIELDS[{key!r}] has unknown attributes: {sorted(extras)}")
        choices = meta.get("choices")
        choice_labels = meta.get("choice_labels")
        if choices is not None and choice_labels is not None:
            if len(choices) != len(choice_labels):
                errors.append(
                    f"FIELDS[{key!r}]: len(choices)={len(choices)} ≠ "
                    f"len(choice_labels)={len(choice_labels)}"
                )
        scope = meta.get("scope")
        if scope is not None and scope not in SCOPE_BADGES:
            errors.append(f"FIELDS[{key!r}] uses unknown scope {scope!r}; "
                          f"known: {sorted(SCOPE_BADGES)}")

    if errors:
        print("Schema sync FAILED:\n  - " + "\n  - ".join(errors), file=sys.stderr)
        return 1

    print(
        f"OK — {len(FIELDS)} FIELDS keys aligned with template "
        f"({len(profile_sections)} profile sections), "
        f"{sum(1 for m in FIELDS.values() if m.get('scope'))} scoped."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
