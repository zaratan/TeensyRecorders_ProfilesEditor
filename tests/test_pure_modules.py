#!/usr/bin/env python3
"""Unit tests for the pure modules extracted in S5.

Covers ``app/validation.py`` and ``app/visibility.py`` — both Qt-free, so
this script runs without a ``QApplication``. Pure Python assertions, no
pytest dependency (matching the project's no-pytest convention).

Usage:
    python tests/test_pure_modules.py
Exits 0 on success, 1 on the first failure.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Device, OpMode  # noqa: E402
from app.validation import (  # noqa: E402
    validate_and_normalize,
    validate_cross_field,
    validate_master_slave_collision,
)
from app.visibility import (  # noqa: E402
    compute_enabled_map,
    opmode_disabled_for_device,
)


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        _fail(msg)


# --- validate_and_normalize --------------------------------------------------

def test_validate_text() -> None:
    # ProfileName / WavPrefix: empty rejected
    _assert(
        validate_and_normalize("ProfileName", "")[1] == "champ requis",
        "empty ProfileName should be rejected with 'champ requis'",
    )
    _assert(
        validate_and_normalize("WavPrefix", "  ")[1] == "champ requis",
        "whitespace-only WavPrefix should be rejected",
    )
    # WavPrefix limit 5
    _assert(
        validate_and_normalize("WavPrefix", "abcdef")[1] == "limité à 5 caractères",
        "6-char WavPrefix should hit the limit",
    )
    # Disallowed characters
    _assert(
        validate_and_normalize("ProfileName", "Forêt")[1] == "contient des caractères interdits",
        "accented chars should be rejected by current regex",
    )
    # Happy path
    _assert(
        validate_and_normalize("ProfileName", "Site_42") == ("Site_42", None),
        "valid ProfileName should pass",
    )

    # Time fields: empty accepted, format checked
    _assert(
        validate_and_normalize("StartTime", "") == ("", None),
        "empty StartTime is allowed (means 'no schedule')",
    )
    _assert(
        validate_and_normalize("StartTime", "08:30") == ("08:30", None),
        "valid HH:MM should pass",
    )
    _assert(
        validate_and_normalize("StartTime", "25:00")[1] is not None,
        "25:00 should be rejected as out-of-range hour",
    )

    # Date fields: --/-- accepted
    _assert(
        validate_and_normalize("StartDate", "--/--") == ("--/--", None),
        "--/-- is the documented 'no limit' sentinel",
    )
    _assert(
        validate_and_normalize("StartDate", "15/06") == ("15/06", None),
        "valid JJ/MM should pass",
    )

    print("  ✓ validate_and_normalize: text")


def test_validate_int() -> None:
    _assert(
        validate_and_normalize("RelativeThreshold", "")[1] == "champ requis",
        "empty int should be rejected",
    )
    _assert(
        validate_and_normalize("RelativeThreshold", "abc")[1] == "valeur numérique attendue",
        "non-numeric int should be rejected",
    )
    _assert(
        validate_and_normalize("RelativeThreshold", "999")[1].startswith("hors bornes"),
        "out-of-range int should mention bounds",
    )
    _assert(
        validate_and_normalize("RelativeThreshold", "25") == ("25", None),
        "in-range int should pass",
    )

    print("  ✓ validate_and_normalize: int")


def test_validate_float() -> None:
    _assert(
        validate_and_normalize("MinFreqUS", "")[1] == "champ requis",
        "empty float should be rejected",
    )
    _assert(
        validate_and_normalize("MinFreqUS", "abc")[1] == "valeur numérique attendue",
        "non-numeric float should be rejected",
    )
    _assert(
        validate_and_normalize("MinFreqUS", "200")[1].startswith("hors bornes"),
        "out-of-range float should mention bounds (200 kHz > 150 max)",
    )
    # Comma decimal accepted (French keyboard convenience)
    val, err = validate_and_normalize("MinFreqUS", "15,5")
    _assert(err is None and val is not None, "comma decimal should be accepted")
    _assert(float(val) - 15.5 < 0.01, f"comma-decimal '15,5' should normalize to 15.5, got {val!r}")
    # Step snap on the freq field (step=0.1)
    val, err = validate_and_normalize("MinFreqUS", "15.27")
    _assert(err is None, "in-bounds value should pass")
    snapped = float(val)
    _assert(abs(snapped - 15.3) < 0.001, f"step-snap on 0.1: 15.27 → 15.3 expected, got {snapped}")

    print("  ✓ validate_and_normalize: float (incl. comma + step snap)")


def test_validate_combo() -> None:
    # Combo is passthrough — the choice was already verified by the widget.
    _assert(
        validate_and_normalize("OpMode", OpMode.HETERODYNE) == (OpMode.HETERODYNE, None),
        "combo should passthrough unchanged",
    )
    print("  ✓ validate_and_normalize: combo")


# --- validate_cross_field ----------------------------------------------------

def test_cross_field_ordering() -> None:
    enabled = {k: True for k in [
        "MinFreqUS", "MaxFreqUS", "MinFreqA", "MaxFreqA",
        "MinDuration", "MaxDuration",
    ]}
    values = {
        "MinFreqUS": "120", "MaxFreqUS": "15",       # inverted (in kHz)
        "MinFreqA": "0.5", "MaxFreqA": "20",
        "MinDuration": "10", "MaxDuration": "5",      # inverted
        "SampFreqU": "384",
    }
    errs = validate_cross_field(values, enabled)
    keys = [k for k, _ in errs]
    _assert("MaxFreqUS" in keys, f"MinFreqUS>MaxFreqUS should flag MaxFreqUS, got {keys}")
    _assert("MaxDuration" in keys, f"MinDuration>MaxDuration should flag MaxDuration, got {keys}")
    print("  ✓ validate_cross_field: ordering (min<max)")


def test_cross_field_nyquist() -> None:
    enabled = {k: True for k in ["MinFreqUS", "MaxFreqUS", "MaxFreqA", "MinFreqA"]}
    # SampFreqU=24 kHz → Nyquist = 12 kHz. MaxFreqUS=15 should fail.
    values = {
        "MinFreqUS": "5", "MaxFreqUS": "15",
        "MinFreqA": "0.1", "MaxFreqA": "10",
        "MinDuration": "1", "MaxDuration": "1",
        "SampFreqU": "24",
    }
    errs = validate_cross_field(values, enabled)
    nyquist_msgs = [m for k, m in errs if k == "MaxFreqUS" and "Nyquist" in m]
    _assert(nyquist_msgs, f"15 kHz at SampFreq=24 should fail Nyquist (12 kHz). Got: {errs}")
    print("  ✓ validate_cross_field: Nyquist (US)")


def test_cross_field_skips_greyed() -> None:
    # Mark MaxFreqUS greyed → the violation must not be reported.
    enabled = {"MinFreqUS": True, "MaxFreqUS": False,
               "MinFreqA": True, "MaxFreqA": True,
               "MinDuration": True, "MaxDuration": True}
    values = {
        "MinFreqUS": "120", "MaxFreqUS": "15",  # inverted but greyed
        "MinFreqA": "0.5", "MaxFreqA": "20",
        "MinDuration": "1", "MaxDuration": "10",
        "SampFreqU": "384",
    }
    errs = validate_cross_field(values, enabled)
    us_errs = [e for e in errs if e[0] == "MaxFreqUS"]
    _assert(us_errs == [], f"greyed MaxFreqUS should be skipped, got {us_errs}")
    print("  ✓ validate_cross_field: skips greyed fields")


# --- validate_master_slave_collision -----------------------------------------

def test_master_collision() -> None:
    profiles = {
        "2": {"OpMode": OpMode.SYNCHRO, "MasterSlave": "0"},
        "3": {"OpMode": OpMode.SYNCHRO, "MasterSlave": "0"},  # second master!
        "4": {"OpMode": OpMode.SYNCHRO, "MasterSlave": "1"},
        "5": {"OpMode": OpMode.AUTO_RECORD, "MasterSlave": "0"},  # not synchro → not a master
    }
    errs = validate_master_slave_collision(profiles, Device.PRS_S)
    flagged = sorted({pid for pid, _, _ in errs})
    _assert(flagged == ["2", "3"], f"expected colliding masters in Profile_2/3, got {flagged}")

    # Same data on a non-PRS-S device → no errors.
    _assert(
        validate_master_slave_collision(profiles, Device.PR) == [],
        "cluster check should be no-op on non-PRS-S devices",
    )

    # Single master → no collision.
    single = {"2": {"OpMode": OpMode.SYNCHRO, "MasterSlave": "0"}}
    _assert(
        validate_master_slave_collision(single, Device.PRS_S) == [],
        "single master is OK",
    )
    print("  ✓ validate_master_slave_collision")


# --- compute_enabled_map -----------------------------------------------------

def test_enabled_hardware_scope() -> None:
    # On PR, AR-scoped fields must be disabled.
    m = compute_enabled_map(OpMode.AUTO_RECORD, "384", "0", Device.PR)
    _assert(m["HeterodyneMode"] is False, "HeterodyneMode (AR scope) must be off on PR")
    _assert(m["MasterSlave"] is False, "MasterSlave (PRS scope) must be off on PR")
    _assert(m["MinFreqUS"] is True, "MinFreqUS has no scope, enabled by default")

    # On AR, AR-scoped fields are gated by OpMode (HeterodyneMode needs Heter).
    m = compute_enabled_map(OpMode.HETERODYNE, "384", "0", Device.AR)
    _assert(m["HeterodyneMode"] is True, "HeterodyneMode active on AR + Heter")
    _assert(m["MasterSlave"] is False, "MasterSlave still off on AR (PRS scope)")

    # On PRS-S, PRS-scoped + Synchro mode = MasterSlave active.
    m = compute_enabled_map(OpMode.SYNCHRO, "384", "0", Device.PRS_S)
    _assert(m["MasterSlave"] is True, "MasterSlave active on PRS-S + Synchro")
    print("  ✓ compute_enabled_map: hardware scope")


def test_enabled_sampfreq_branch() -> None:
    # SampFreqU >= 192 → audio band greyed, US band active.
    m = compute_enabled_map(OpMode.AUTO_RECORD, "384", "0", Device.PR)
    _assert(m["MinFreqUS"] is True and m["MaxFreqUS"] is True, "US band on at 384")
    _assert(m["MinFreqA"] is False and m["MaxFreqA"] is False, "audio band off at 384")
    # SampFreqU < 192 → audio band active, US band greyed.
    m = compute_enabled_map(OpMode.AUTO_RECORD, "96", "0", Device.PR)
    _assert(m["MinFreqA"] is True and m["MaxFreqA"] is True, "audio band on at 96")
    _assert(m["MinFreqUS"] is False and m["MaxFreqUS"] is False, "US band off at 96")
    print("  ✓ compute_enabled_map: SampFreq branch")


def test_enabled_threshold_type() -> None:
    m = compute_enabled_map(OpMode.AUTO_RECORD, "384", "0", Device.PR)
    _assert(m["RelativeThreshold"] is True, "Relative threshold on when type=0")
    _assert(m["AbsoluteThreshold"] is False, "Absolute threshold off when type=0")
    m = compute_enabled_map(OpMode.AUTO_RECORD, "384", "1", Device.PR)
    _assert(m["AbsoluteThreshold"] is True, "Absolute threshold on when type=1")
    _assert(m["RelativeThreshold"] is False, "Relative threshold off when type=1")
    print("  ✓ compute_enabled_map: ThresholdType")


def test_enabled_fixed_proto_overrides() -> None:
    # Fixed-P. Proto. forces 12 params to firmware constants — they should
    # be greyed even when the SampFreq/ThresholdType rules would normally
    # enable them.
    m = compute_enabled_map(OpMode.FIXED_PROTO, "384", "0", Device.PR)
    for k in (
        "SampFreqU", "MinFreqUS", "MaxFreqUS", "NbDetect",
        "MinDuration", "MaxDuration", "NumericGain",
    ):
        _assert(m[k] is False, f"Fixed P. Proto. must disable {k}")
    print("  ✓ compute_enabled_map: Fixed-Proto override")


def test_opmode_disabled_for_device() -> None:
    # Heterodyne / Audio Rec. only on AR
    _assert(opmode_disabled_for_device(OpMode.HETERODYNE, Device.PR), "Heter blocked on PR")
    _assert(not opmode_disabled_for_device(OpMode.HETERODYNE, Device.AR), "Heter ok on AR")
    _assert(opmode_disabled_for_device(OpMode.AUDIO_REC, Device.PRS), "AudioRec blocked on PRS")
    # Synchro only on PRS-S
    _assert(opmode_disabled_for_device(OpMode.SYNCHRO, Device.PRS), "Synchro blocked on PRS (need -S)")
    _assert(not opmode_disabled_for_device(OpMode.SYNCHRO, Device.PRS_S), "Synchro ok on PRS-S")
    # Auto Record allowed everywhere
    for dev in (Device.PR, Device.AR, Device.PRS, Device.PRS_S):
        _assert(
            not opmode_disabled_for_device(OpMode.AUTO_RECORD, dev),
            f"Auto record should be allowed on {dev}",
        )
    print("  ✓ opmode_disabled_for_device")


def main() -> int:
    print("Running pure-module unit tests…")
    test_validate_text()
    test_validate_int()
    test_validate_float()
    test_validate_combo()
    test_cross_field_ordering()
    test_cross_field_nyquist()
    test_cross_field_skips_greyed()
    test_master_collision()
    test_enabled_hardware_scope()
    test_enabled_sampfreq_branch()
    test_enabled_threshold_type()
    test_enabled_fixed_proto_overrides()
    test_opmode_disabled_for_device()
    print("All pure-module tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
