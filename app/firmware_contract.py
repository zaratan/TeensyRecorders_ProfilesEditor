"""Firmware ↔ app contract snapshot.

Hand-maintained mirror of the field-level constraints encoded in the
``DecodeInt``/``DecodeFloat``/``DecodeBool``/``DecodeEnum``/``DecodeString``
calls of ``CModeGeneric::ImportProfiles`` (firmware C++). The matching
test (``tests/test_firmware_alignment.py``) asserts that every entry in
``FIELDS`` rounds back to the corresponding firmware constraint, modulo
the documented ``unit_factor`` (Hz↔kHz) and the explicit divergences
catalogued below.

Why hand-maintain instead of parsing the .cpp at test time:
- Parsing C++ would tie the test to a regex on a foreign file, and
  the developer running the test would need the firmware checkout
  on disk. A snapshot is portable and reviewable in PR.
- A pin point divergence (e.g. ``RelativeThreshold`` chiropterology
  recommendation overriding the firmware default) is explicit in
  ``ACCEPTED_DIVERGENCES`` and signed off in code review, not buried
  in a comment three files away.

Update procedure (when the firmware bumps):
1. Re-grep the .cpp ``DecodeXxx`` calls.
2. Update the dict entries here.
3. Update ``FIRMWARE_SOURCE_REF`` to the new ``git sha`` / line range.
4. Run the alignment test — divergences flagged here must be either
   resolved in ``FIELDS`` or explicitly added to ``ACCEPTED_DIVERGENCES``.
"""

# Source: TeensyRecorders-master @ Const.h + CModeGeneric.cpp lines 2349-2510
# (ImportProfiles). Last refreshed against firmware version "0.8" as
# encoded in the first line of ``initial_profile/Profiles.ini``.
FIRMWARE_SOURCE_REF = "CModeGeneric.cpp:2349-2510 (firmware v0.8)"


# kind ∈ {"int", "float", "bool", "enum", "string"}
# For int/float: min/max/default are firmware-native units (Hz for the
# frequency fields, seconds for durations, etc. — no kHz pre-division).
# For enum: ``choices`` is the ordered ``sXXXValues[]`` array and
# ``default`` is the index of the firmware default constant.
# For string: ``limit`` is the firmware buffer size minus the null byte.
FIRMWARE_CONTRACT: dict[str, dict] = {
    # ---- Profil ----
    "ProfileName": {"kind": "string", "limit": 11, "default": None},  # locale-dependent default
    "OpMode":      {"kind": "enum",   "choices": [
        "Auto record", "Heterodyne", "Audio Rec.", "Timed recording",
        "Fixed P. Proto.", "Walkin. Protoc.", "Road Protocol",
        "RhinoLogger", "Microphone test", "Synchro",
    ], "default": "Auto record"},  # MAXPROT entries; app exposes only 7 (cf. notes in config.py)
    "MasterSlave": {"kind": "int",    "min": 0,    "max": 9,      "default": 0},

    # ---- Horaires ----
    "StartTime":   {"kind": "string", "limit": 5,  "default": "22:00"},
    "EndTime":     {"kind": "string", "limit": 5,  "default": "06:00"},
    "RecTime":     {"kind": "int",    "min": 1,    "max": 43200,  "default": 1},
    "WaitTime":    {"kind": "int",    "min": 1,    "max": 86400,  "default": 1},

    # ---- Dates ----
    "StartDate":   {"kind": "string", "limit": 5,  "default": "--/--"},
    "EndDate":     {"kind": "string", "limit": 5,  "default": "--/--"},

    # ---- Soleil / Auto Start-Stop ----
    "AutoStartStop":   {"kind": "bool", "default": False},
    "Latitude":        {"kind": "float", "min": -90.0,  "max": 90.0,   "default": 0.001},
    "Longitude":       {"kind": "float", "min": -180.0, "max": 180.0,  "default": 0.001},
    "TUOffset":        {"kind": "int",   "min": -720,   "max": 720,    "default": 1},
    "StartStopOffset": {"kind": "int",   "min": -60,    "max": 60,     "default": 1},

    # ---- Audio ----
    "SampFreqU":      {"kind": "enum",  "choices": ["24","48","96","192","250","384","500"], "default": "384"},
    # SampFreqA: DecodeEnum accepts MAXFE entries (incl. "192", "250", "384",
    # "500"), but CModeGeneric.cpp:826-827 immediately coerces anything ≥
    # FE192KHZ back to FE48KHZ. Effective firmware-honoured set is just
    # ["24","48","96"] — that's what the app exposes.
    "SampFreqA":      {"kind": "enum",  "choices": ["24","48","96"],                          "default": "48"},
    "NumericGain":    {"kind": "enum",  "choices": ["0","6","12","18","24"], "default": "12"},
    "LowpassFilter":  {"kind": "bool",  "default": False},
    "HighpassFilter": {"kind": "int",   "min": 0,    "max": 25,   "default": 0},
    "fHighpassFilter":{"kind": "float", "min": 0.0,  "max": 25.0, "default": 0.1},
    "Exp10":          {"kind": "bool",  "default": True},
    "StereoMode":     {"kind": "enum",  "choices": ["Stereo","MonoRight","MonoLeft"], "default": "Stereo"},
    "MicrophoneType": {"kind": "enum",  "choices": ["SPU0410","ICS43730","FG23329"],  "default": "ICS43730"},
    "TopAudioFreq":   {"kind": "int",   "min": 1,    "max": 50,   "default": 2},
    "TopDuration":    {"kind": "enum",  "choices": ["256","512","1024"], "default": "256"},
    "TopPeriod":      {"kind": "int",   "min": 0,    "max": 10,   "default": 0},

    # ---- Hétérodyne (Const.h:715-740, HAM_MAX=4, HSF_MAX=4) ----
    "HeterodyneMode":           {"kind": "int",   "min": 0,    "max": 3,    "default": 0},
    "AutoRecHeter":             {"kind": "bool",  "default": False},
    "RefreshGraphe":            {"kind": "float", "min": 0.2,  "max": 2.0,  "default": 1.0},
    "HeterLevel":               {"kind": "float", "min": 0.1,  "max": 0.9,  "default": 0.1},
    "Pre-TriggerAuto":          {"kind": "int",   "min": 0,    "max": 15,   "default": 1},
    "Pre-TriggerHeter":         {"kind": "int",   "min": 1,    "max": 15,   "default": 1},
    "Pre-HeterSelectiveFilter": {"kind": "int",   "min": 0,    "max": 3,    "default": 0},
    "HeterAutoPlay":            {"kind": "bool",  "default": False},
    "HeterWithGraph":           {"kind": "bool",  "default": True},
    "HeterAGC":                 {"kind": "bool",  "default": True},

    # ---- Fichiers ----
    "WavPrefix":     {"kind": "string", "limit": 5, "default": "PRec_"},
    "LEDSynchro":    {"kind": "enum",   "choices": ["NO","REC","3 REC"], "default": "REC"},
    "BatcorderMode": {"kind": "bool",   "default": False},
    "ZCFile":        {"kind": "bool",   "default": False},

    # ---- Fréquences (firmware native: Hz; UI: kHz via unit_factor=1000) ----
    "MinFreqUS":  {"kind": "int", "min": 100, "max": 150000, "default": 10000},
    "MaxFreqUS":  {"kind": "int", "min": 100, "max": 150000, "default": 120000},
    "MinFreqA":   {"kind": "int", "min": 100, "max": 96000,  "default": 100},
    "MaxFreqA":   {"kind": "int", "min": 100, "max": 96000,  "default": 48000},
    "MinDuration":{"kind": "int", "min": 1,   "max": 99,     "default": 1},
    "MaxDuration":{"kind": "int", "min": 1,   "max": 999,    "default": 10},
    "ThresholdType":     {"kind": "bool", "default": False},
    "RelativeThreshold": {"kind": "int",  "min": 5,    "max": 99,   "default": 15},
    "AbsoluteThreshold": {"kind": "int",  "min": -110, "max": -30,  "default": -80},
    "NbDetect":          {"kind": "int",  "min": 1,    "max": 8,    "default": 3},

    # ---- Capteurs / RhinoLogger / Alimentation ----
    "ContMesTemp":       {"kind": "bool", "default": False},
    "TemperaturePeriod": {"kind": "int",  "min": 10, "max": 3600, "default": 60},
    "SaveNoise":         {"kind": "bool", "default": False},
    "AffRLPerm":         {"kind": "bool", "default": False},
    "PowerBank":         {"kind": "bool", "default": False},
}


# Intentional drift between FIELDS and FIRMWARE_CONTRACT. Each entry must
# state which attribute(s) diverge and *why*. The alignment test ignores
# the listed attributes for the listed key.
#
# Format: ``"FieldKey": ({"attr1", "attr2"}, "reason")``
ACCEPTED_DIVERGENCES: dict[str, tuple[set[str], str]] = {
    "RelativeThreshold": (
        {"default"},
        "App default 18 dB matches chiropterology guidance (firmware 15 dB "
        "is technically valid but routinely tweaked up). Documented in helper.",
    ),
    "MaxFreqA": (
        {"default"},
        "App default 20 kHz (human audible upper bound) vs firmware 48 kHz. "
        "Aligned with the embedded template; 48 kHz remains valid.",
    ),
    "Latitude": (
        {"default", "step"},
        "App uses ~Paris (48.857918) as a sensible non-zero default + step "
        "0.000001 for GPS-grade precision; firmware default 0.001 is a "
        "step-size placeholder rather than a geographic anchor.",
    ),
    "Longitude": (
        {"default", "step"},
        "Same rationale as Latitude — Paris (2.348615) as sensible default + "
        "0.000001 step.",
    ),
    "TUOffset": (
        {"default"},
        "App default 60 (= UTC+1, France winter) is more useful than the "
        "firmware default of 1 minute. Firmware bounds (-720..720) preserved.",
    ),
    "RecTime": (
        {"default"},
        "App default 60 s (one-minute clip) — friendlier first impression "
        "than the firmware 1 s. Firmware bounds (1..43200) preserved.",
    ),
    "WaitTime": (
        {"default"},
        "App default 540 s (9 min) — usable cadence default, vs firmware 1 s.",
    ),
    "OpMode": (
        {"choices"},
        "App exposes 7 modes vs firmware 10. Walkin. Protoc. / Road Protocol / "
        "Microphone test are firmware-coerced at every cold boot "
        "(CModeGeneric.cpp:864-873), so persisting them in a profile is "
        "silently ineffective. Documented at FIELDS['OpMode'] in config.py.",
    ),
    "ProfileName": (
        {"default"},
        "Firmware default is locale-dependent (txtDefProfilesNames[lang][i]); "
        "the app doesn't pre-fill — user supplies their own name.",
    ),
    "StartTime": (
        {"limit"},
        "Firmware DecodeString limit is 5 (HH:MM); the app validates the "
        "HH:MM regex which strictly enforces the same length.",
    ),
    "EndTime": (
        {"limit"},
        "Same as StartTime — regex validation supersedes the explicit limit.",
    ),
    "HeterAGC": (
        {"default"},
        "App default Off (combo='0') vs firmware default On (true). "
        "Documented helper notes AGC's drawbacks (pumping, weak-signal "
        "loss) — chiropterology guidance recommends starting with AGC off.",
    ),
    "StartStopOffset": (
        {"default"},
        "App default 0 (no offset) — chiropterology guidance is to align "
        "exactly on sunset/sunrise. Firmware default 1 minute is arbitrary.",
    ),
}
