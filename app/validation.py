"""Field validation — pure functions, zero Qt.

Two layers:
- ``validate_and_normalize(key, raw)`` checks a single field against its
  ``FIELDS`` spec, returning ``(normalized_value | None, error_message | None)``.
- ``validate_cross_field(values, enabled)`` checks the ordering /
  Nyquist constraints that involve multiple fields at once.
- ``validate_master_slave_collision(profiles_values, device)`` checks the
  cluster-wide invariant that at most one PRS-S profile in Synchro mode
  carries ``MasterSlave=0`` (the master role).

All three are pure: they take primitive Python values and return primitive
Python values. The UI layer pulls inputs from widgets / cache, calls these,
and threads the errors back into bordering / focus / dialog.

Values are expected in **UI units** — the frequency fields use kHz here,
not Hz; the conversion to disk format happens elsewhere (cf.
``ui_editor._ui_to_ini``).
"""

import re

from .config import FIELDS, OpMode, Device

# --- Single-field validation -------------------------------------------------

# Public per-field guards, applied in addition to the type/range checks
# below. Listed in module scope so a future reader can grep them.
TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
DATE_RE = re.compile(r"^(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])$")
NAME_DISALLOWED_RE = re.compile(r"[^A-Za-z0-9 _-]")


def validate_and_normalize(key: str, raw: str) -> tuple[str | None, str | None]:
    """Validate a raw input against the FIELDS spec for ``key``.

    Returns ``(normalized_value, error_message)`` with exactly one of the
    two being None:
    - ``(str, None)`` on success — ``str`` is the cleaned value to cache.
    - ``(None, str)`` on failure — ``str`` is a French human message
      suitable for a tooltip / dialog.

    Empty inputs are explicitly rejected with "champ requis" for numeric
    fields and the two name-like text fields (``ProfileName``,
    ``WavPrefix``). Time/date strings tolerate an empty value (meaning
    "no schedule" / "no limit") — the firmware applies its own default.
    """
    meta = FIELDS[key]
    val = (raw or "").strip()
    kind = meta["type"]

    if kind == "text":
        if key in ("ProfileName", "WavPrefix"):
            if not val:
                return None, "champ requis"
            limit = meta.get("limit")
            if limit and len(val) > limit:
                return None, f"limité à {limit} caractères"
            if NAME_DISALLOWED_RE.search(val):
                return None, "contient des caractères interdits"
            return val, None
        if key in ("StartTime", "EndTime"):
            if val and not TIME_RE.match(val):
                return None, "format attendu HH:MM (ex: 08:30)"
            return val, None
        if key in ("StartDate", "EndDate"):
            # Accept "--/--" (no limit) or "JJ/MM". Firmware tolerates
            # impossible combos like 31/02; we don't over-validate.
            if val and val != "--/--" and not DATE_RE.match(val):
                return None, "format attendu JJ/MM ou --/--"
            return val, None
        return val, None

    if kind == "int":
        if not val:
            return None, "champ requis"
        try:
            val_int = int(val)
        except (ValueError, TypeError):
            return None, "valeur numérique attendue"
        if not (meta["min"] <= val_int <= meta["max"]):
            return None, f"hors bornes (attendu {meta['min']}–{meta['max']})"
        return str(val_int), None

    if kind == "float":
        if not val:
            return None, "champ requis"
        normalized = val.replace(",", ".")  # accept comma input
        try:
            val_f = float(normalized)
        except (ValueError, TypeError):
            return None, "valeur numérique attendue"
        if not (meta["min"] <= val_f <= meta["max"]):
            return None, f"hors bornes (attendu {meta['min']}–{meta['max']})"
        step = meta.get("step")
        if step:
            # Lat/Lon kept at 6 decimals (~ 0.1 m at the equator); other
            # floats land at 3, which covers the 0.1-step frequency fields
            # without spurious trailing 9s.
            decimals = 6 if key in ("Latitude", "Longitude") else 3
            val_f = round(round((val_f - meta["min"]) / step) * step + meta["min"], decimals)
        return str(val_f), None

    # combo: stored as-is (the choice value was already extracted via userData)
    return val, None


# --- Cross-field validation --------------------------------------------------

def validate_cross_field(
    values: dict[str, str],
    enabled: dict[str, bool],
) -> list[tuple[str, str]]:
    """Return ``[(field_key, message), …]`` for ordering / Nyquist
    constraint violations.

    Skips checks involving greyed-out fields so the user isn't yelled at
    about a mode they're not in. ``values`` must contain at least
    ``MinFreqUS``, ``MaxFreqUS``, ``MinFreqA``, ``MaxFreqA``,
    ``MinDuration``, ``MaxDuration``, ``SampFreqU`` — all in UI units
    (kHz for the frequency fields, seconds for the durations).
    """

    def as_int(k: str) -> int | None:
        try:
            return int(values.get(k, ""))
        except (ValueError, TypeError):
            return None

    def as_float(k: str) -> float | None:
        try:
            return float(values.get(k, "").replace(",", "."))
        except (ValueError, TypeError):
            return None

    errors: list[tuple[str, str]] = []

    if enabled.get("MinFreqUS") and enabled.get("MaxFreqUS"):
        lo, hi = as_float("MinFreqUS"), as_float("MaxFreqUS")
        if lo is not None and hi is not None and lo >= hi:
            errors.append(("MaxFreqUS", "doit être supérieure à la Fréquence ultrason min"))

    if enabled.get("MinFreqA") and enabled.get("MaxFreqA"):
        lo, hi = as_float("MinFreqA"), as_float("MaxFreqA")
        if lo is not None and hi is not None and lo >= hi:
            errors.append(("MaxFreqA", "doit être supérieure à la Fréquence audio min"))

    lo_d, hi_d = as_int("MinDuration"), as_int("MaxDuration")
    if lo_d is not None and hi_d is not None and lo_d > hi_d:
        errors.append(("MaxDuration", "doit être supérieure ou égale à la Durée min"))

    # Nyquist: ``MaxFreqX_kHz`` must be ≤ ``SampFreqU_kHz / 2``. Both
    # values are UI-format kHz, so the comparison is unit-consistent.
    samp_us = values.get("SampFreqU", "")
    try:
        nyquist_khz = int(samp_us) / 2
    except (ValueError, TypeError):
        nyquist_khz = None
    if nyquist_khz is not None:
        if enabled.get("MaxFreqUS"):
            hi = as_float("MaxFreqUS")
            if hi is not None and hi > nyquist_khz:
                errors.append((
                    "MaxFreqUS",
                    f"dépasse la limite Nyquist ({nyquist_khz:g} kHz à {samp_us} kHz)",
                ))
        if enabled.get("MaxFreqA"):
            hi = as_float("MaxFreqA")
            if hi is not None and hi > nyquist_khz:
                errors.append((
                    "MaxFreqA",
                    f"dépasse la limite Nyquist ({nyquist_khz:g} kHz à {samp_us} kHz)",
                ))

    return errors


# --- Cluster-wide validation -------------------------------------------------

def validate_master_slave_collision(
    profiles_values: dict[str, dict[str, str]],
    device: str,
) -> list[tuple[str, str, str]]:
    """Return ``[(profile_id, "MasterSlave", message), …]`` if two or more
    Synchro profiles share the master role (``MasterSlave=0``).

    Only relevant when the device is ``PRS-S`` — a PR/AR/PRS device has no
    cluster semantics. ``profiles_values`` is ``{pid: {key: value}}`` and
    must include the ``OpMode`` and ``MasterSlave`` entries for each
    profile considered.
    """
    if device != Device.PRS_S:
        return []
    masters: list[str] = []
    for pid, vals in profiles_values.items():
        if (
            vals.get("OpMode") == OpMode.SYNCHRO
            and vals.get("MasterSlave") == "0"
        ):
            masters.append(pid)
    if len(masters) <= 1:
        return []
    msg = (
        f"plusieurs profils Synchro avec Maître (0) dans le cluster — "
        f"profils en conflit : {', '.join(masters)}"
    )
    return [(pid, "MasterSlave", msg) for pid in masters]
