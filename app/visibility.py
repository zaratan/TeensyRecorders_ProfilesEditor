"""Field visibility engine — pure functions, zero Qt.

A field is visible (= active, editable, full opacity) when its scope and
operating-mode preconditions are satisfied. ``compute_enabled_map`` returns
``{field_key: bool}`` from the four controllers (``OpMode``, ``SampFreqU``,
``ThresholdType``, device variant); the caller wires the result to
``widget.setEnabled(is_on)`` in the UI layer.

Rules are declared as a list of ``(condition_callable, disabled_keys)``
pairs in ``VISIBILITY_RULES``. Each rule fires when the predicate returns
True, marking every listed key as disabled. Order matters: ``Fixed P.
Proto.`` overrides explicitly come last because they shadow earlier
SampFreq/Threshold rules (the firmware imposes its own values regardless).

Why declarative-list rather than per-field ``visible_when``: the visibility
predicates are non-local — a field's state depends on **other** fields'
values. Encoding that as a per-field attribute would require a mini-DSL
to express conjunctions/disjunctions; pushing it into a flat list of
Python predicates keeps the abstraction at the right level (no inner-
platform effect) and makes each rule trivially testable. See the
discussion logged in ``config.py``.
"""

from collections.abc import Callable

from .config import FIELDS, OpMode, Device

# --- Per-mode field bundles --------------------------------------------------
#
# These tuples are the set of keys whose visibility is gated by a single
# OpMode value. Listed here (not inline in rules) so future readers can grep
# "HETERODYNE_KEYS" and find every field tied to that mode.

HETERODYNE_KEYS: tuple[str, ...] = (
    "HeterodyneMode", "AutoRecHeter", "RefreshGraphe", "HeterLevel",
    "HeterWithGraph", "Pre-TriggerAuto", "Pre-TriggerHeter",
    "Pre-HeterSelectiveFilter", "HeterAGC", "HeterAutoPlay",
)

SYNCHRO_KEYS: tuple[str, ...] = (
    "MasterSlave", "TopAudioFreq", "TopDuration", "TopPeriod", "LEDSynchro",
)

TIMED_KEYS: tuple[str, ...] = ("RecTime", "WaitTime")

# Fields the firmware overrides at every Fixed-P. Proto BeginMode
# (cf. CModeRecorder.cpp:1367-1389). Grey them out in the UI so the user
# understands their profile values are ignored in that mode.
FIXED_PROTO_KEYS: tuple[str, ...] = (
    "SampFreqU", "LowpassFilter", "HighpassFilter", "fHighpassFilter",
    "NumericGain", "Exp10",
    "MinFreqUS", "MaxFreqUS",
    "ThresholdType", "RelativeThreshold",
    "NbDetect",
    "MinDuration", "MaxDuration",
)

# Frequency-band fields gated by the chosen sample rate. ≥ 192 kHz means
# we're in the ultrasound branch; < 192 kHz drops to the audio branch.
US_BAND_KEYS: tuple[str, ...] = ("MinFreqUS", "MaxFreqUS", "HighpassFilter")
AUDIO_BAND_KEYS: tuple[str, ...] = ("MinFreqA", "MaxFreqA", "fHighpassFilter")


# --- Rule list ---------------------------------------------------------------
#
# Each rule is (predicate, keys_to_disable). The predicate receives a
# context dict ``ctx`` with at least op_mode/samp_us_khz/threshold_type/device.
# All rules execute; a field disabled by any rule stays disabled.
#
# Predicates are short Python lambdas — not strings, not dicts, not an AST.
# This is deliberate: see the visible_when discussion in config.py.

Rule = tuple[Callable[[dict], bool], tuple[str, ...]]

VISIBILITY_RULES: list[Rule] = [
    # --- OpMode-driven ---
    (lambda ctx: ctx["op_mode"] != OpMode.TIMED, TIMED_KEYS),
    (lambda ctx: ctx["op_mode"] != OpMode.RHINOLOGGER, ("AffRLPerm",)),
    (lambda ctx: ctx["op_mode"] != OpMode.HETERODYNE, HETERODYNE_KEYS),
    (lambda ctx: ctx["op_mode"] != OpMode.SYNCHRO, SYNCHRO_KEYS),

    # --- SampFreqU-driven (Nyquist branch) ---
    (lambda ctx: ctx["samp_us_khz"] >= 192, AUDIO_BAND_KEYS),
    (lambda ctx: ctx["samp_us_khz"] < 192, US_BAND_KEYS),

    # --- ThresholdType (relative vs absolute) ---
    (lambda ctx: ctx["threshold_type"] == "0", ("AbsoluteThreshold",)),
    (lambda ctx: ctx["threshold_type"] == "1", ("RelativeThreshold",)),

    # --- Fixed Point Protocol override (firmware imposes 12 params) ---
    # Must run after the SampFreq rules so it correctly disables those
    # fields too — the firmware's coercion supersedes the user's choice.
    (lambda ctx: ctx["op_mode"] == OpMode.FIXED_PROTO, FIXED_PROTO_KEYS),
]


# --- Public API --------------------------------------------------------------

def compute_enabled_map(
    op_mode: str,
    samp_us: str,
    threshold_type: str,
    device: str,
) -> dict[str, bool]:
    """Return ``{field_key: is_active}`` for every FIELDS key given the four
    controllers' current values.

    Arguments are raw strings as they come from the INI / widget cache:
    - ``op_mode``: one of ``OpMode.*`` values.
    - ``samp_us``: kHz integer as string ("24", "48", …, "500").
    - ``threshold_type``: ``"0"`` (relative) or ``"1"`` (absolute).
    - ``device``: one of ``Device.*`` values.

    Fields not gated by any rule stay enabled. Hardware-scoped fields (``AR``
    or ``PRS`` in ``FIELDS[k]["scope"]``) follow the device variant:
    AR-scoped only active on AR; PRS-scoped active on both PRS and PRS-S.
    The ``RhinoLogger`` scope is a mode marker, not a hardware variant —
    its gating goes through the OpMode rule above.
    """
    enabled: dict[str, bool] = {k: True for k in FIELDS}

    # --- Hardware scope ---
    ar_active = (device == Device.AR)
    prs_active = (device in (Device.PRS, Device.PRS_S))
    for k, meta in FIELDS.items():
        scope = meta.get("scope")
        if scope == "AR" and not ar_active:
            enabled[k] = False
        elif scope == "PRS" and not prs_active:
            enabled[k] = False

    # --- Build the rule context once ---
    try:
        samp_us_khz = int(samp_us)
    except (ValueError, TypeError):
        samp_us_khz = 384  # safe firmware default if cache is corrupted
    ctx = {
        "op_mode": op_mode,
        "samp_us_khz": samp_us_khz,
        "threshold_type": threshold_type,
        "device": device,
    }

    for predicate, keys in VISIBILITY_RULES:
        if predicate(ctx):
            for k in keys:
                enabled[k] = False

    return enabled


def opmode_disabled_for_device(mode: str, device: str) -> bool:
    """Whether the firmware would refuse this OpMode on this device variant.
    Mirrors ``CModeGeneric.cpp:873`` (HETER / AUDIOREC are AR-only) and
    ``CModeParams.cpp:1071+`` (SYNCHRO is PRS-S-only).
    """
    if mode in (OpMode.HETERODYNE, OpMode.AUDIO_REC):
        return device != Device.AR
    if mode == OpMode.SYNCHRO:
        return device != Device.PRS_S
    return False
