#!/usr/bin/env python3
"""Firmware ↔ FIELDS alignment check.

Asserts that every entry in ``FIRMWARE_CONTRACT`` (the hand-maintained
snapshot of the firmware's ``Decode*`` calls) is satisfied by the
corresponding entry in ``FIELDS`` — modulo the documented ``unit_factor``
(Hz↔kHz conversion for the 4 frequency fields) and the explicit
``ACCEPTED_DIVERGENCES`` catalogue.

What this catches:
- A firmware bump that adds / removes a field or shifts a bound — the
  test fails until either FIELDS is updated or the divergence is
  explicitly accepted in ``firmware_contract.py``.
- A typo in FIELDS that shifts a min/max/default away from what the
  firmware would silently coerce.
- A new ``unit_factor`` field that forgets to update the contract.

What this does NOT catch:
- The firmware itself changing behaviour without a value change (e.g.
  silent coercion of an in-range value, like the SampFreqA ≥ 192 → 48
  documented in firmware_contract.py).

Usage:
    python tests/test_firmware_alignment.py
Exits 0 on success, 1 on failure.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import FIELDS  # noqa: E402
from app.firmware_contract import (  # noqa: E402
    ACCEPTED_DIVERGENCES, FIRMWARE_CONTRACT, FIRMWARE_SOURCE_REF,
)


def _apply_unit_factor(field_meta: dict, attr: str, value):
    """Convert a FIELDS-side (UI) numeric attribute to its firmware-side
    (disk) equivalent. Lat/Lon and the 4 frequency fields use
    ``unit_factor`` to bridge units. No-op when there's no factor."""
    factor = field_meta.get("unit_factor")
    if not factor or not isinstance(value, (int, float)):
        return value
    if attr == "step":  # step is in UI units regardless
        return value
    converted = value * factor
    # The firmware stores ints for the freq fields; round so 0.1 × 1000
    # comes out as 100 not 99.999…
    return int(round(converted)) if field_meta.get("type") == "float" else converted


def _check_one(key: str, contract: dict, field: dict) -> list[str]:
    """Return a list of human-readable mismatches for a single field."""
    errors: list[str] = []
    accepted = ACCEPTED_DIVERGENCES.get(key, (set(), ""))[0]

    kind = contract["kind"]

    if kind == "int":
        # Some int-typed firmware fields are modeled as combos in FIELDS
        # when their range is a small discrete enum (e.g. HeterodyneMode
        # 0..3). Validate that every str-choice parses as int and lands
        # within the contract range.
        if field.get("type") == "combo":
            choices = field.get("choices", [])
            try:
                int_choices = sorted({int(c) for c in choices})
            except (ValueError, TypeError):
                errors.append(
                    f"{key}: combo modeling an int field but choices are "
                    f"non-numeric: {choices!r}"
                )
                int_choices = []
            if int_choices and (
                int_choices[0] < contract["min"]
                or int_choices[-1] > contract["max"]
            ):
                errors.append(
                    f"{key}.choices: int values {int_choices} fall outside "
                    f"contract range [{contract['min']}, {contract['max']}]"
                )
            if "default" not in accepted:
                try:
                    default_int = int(field.get("default", "0"))
                except (ValueError, TypeError):
                    default_int = None
                if default_int != contract["default"]:
                    errors.append(
                        f"{key}.default: FIELDS={field.get('default')!r} (→ "
                        f"{default_int!r}), contract={contract['default']!r}"
                    )
            return errors
        # Plain int field (QLineEdit + QIntValidator).
        for attr in ("min", "max", "default"):
            if attr in accepted:
                continue
            expected = contract[attr]
            actual = _apply_unit_factor(field, attr, field.get(attr))
            if actual != expected:
                errors.append(
                    f"{key}.{attr}: FIELDS={field.get(attr)!r} → firmware-units "
                    f"{actual!r}, contract={expected!r}"
                )

    elif kind == "float":
        for attr in ("min", "max", "default"):
            if attr in accepted:
                continue
            expected = contract[attr]
            actual = _apply_unit_factor(field, attr, field.get(attr))
            if actual != expected:
                errors.append(
                    f"{key}.{attr}: FIELDS={field.get(attr)!r} → firmware-units "
                    f"{actual!r}, contract={expected!r}"
                )

    elif kind == "bool":
        # FIELDS represent bools as combos with choices ["0", "1"]. The
        # default string maps back to bool: "1" → True, "0" → False.
        if "choices" not in accepted:
            if field.get("choices") != ["0", "1"]:
                errors.append(
                    f"{key}.choices: expected ['0','1'] for bool field, got "
                    f"{field.get('choices')!r}"
                )
        if "default" not in accepted:
            default_bool = field.get("default") == "1"
            if default_bool != contract["default"]:
                errors.append(
                    f"{key}.default: FIELDS={field.get('default')!r} (→ {default_bool}), "
                    f"contract={contract['default']!r}"
                )

    elif kind == "enum":
        if "choices" not in accepted:
            if field.get("choices") != contract["choices"]:
                errors.append(
                    f"{key}.choices: FIELDS={field.get('choices')!r}, "
                    f"contract={contract['choices']!r}"
                )
        if "default" not in accepted:
            if field.get("default") != contract["default"]:
                errors.append(
                    f"{key}.default: FIELDS={field.get('default')!r}, "
                    f"contract={contract['default']!r}"
                )

    elif kind == "string":
        if "limit" not in accepted:
            if field.get("limit") != contract["limit"]:
                errors.append(
                    f"{key}.limit: FIELDS={field.get('limit')!r}, "
                    f"contract={contract['limit']!r}"
                )

    return errors


def main() -> int:
    errors: list[str] = []

    # Every contract key must exist in FIELDS.
    missing_in_fields = sorted(set(FIRMWARE_CONTRACT) - set(FIELDS))
    if missing_in_fields:
        errors.append(
            f"FIELDS is missing entries documented in FIRMWARE_CONTRACT: "
            f"{missing_in_fields}"
        )

    # Every FIELDS key must exist in the contract — otherwise we expose a
    # field the firmware doesn't actually accept.
    missing_in_contract = sorted(set(FIELDS) - set(FIRMWARE_CONTRACT))
    if missing_in_contract:
        errors.append(
            f"FIRMWARE_CONTRACT is missing entries present in FIELDS: "
            f"{missing_in_contract}"
        )

    # Compare each field's constraints.
    for key in sorted(set(FIELDS) & set(FIRMWARE_CONTRACT)):
        errors.extend(_check_one(key, FIRMWARE_CONTRACT[key], FIELDS[key]))

    # Every ACCEPTED_DIVERGENCES key must point to a real field.
    stale_divergences = sorted(set(ACCEPTED_DIVERGENCES) - set(FIELDS))
    if stale_divergences:
        errors.append(
            f"ACCEPTED_DIVERGENCES references unknown FIELDS keys: "
            f"{stale_divergences}"
        )

    if errors:
        print("Firmware alignment FAILED:\n  - " + "\n  - ".join(errors), file=sys.stderr)
        print(f"\nSource pinned at: {FIRMWARE_SOURCE_REF}", file=sys.stderr)
        return 1

    print(
        f"OK — {len(FIRMWARE_CONTRACT)} firmware fields aligned with FIELDS "
        f"({len(ACCEPTED_DIVERGENCES)} explicit divergences). "
        f"Source: {FIRMWARE_SOURCE_REF}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
