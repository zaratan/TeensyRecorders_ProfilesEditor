"""INI I/O — canonical-template strategy.

Loading: the user file is parsed into {section: {key: value}}. Missing keys
fall back to the embedded template defaults (initial_profile/Profiles.ini);
keys unknown to the current firmware are flagged so the UI can warn the user.

Saving: instead of mutating the user file line-by-line (which silently drops
new values for keys absent from older files), we *re-emit* a fresh INI by
walking the canonical template and substituting each key's value with the
user's current value. This guarantees the output is always complete and
aligned with the firmware schema, even when the input was an older format.

Quote style and line order are preserved from the template — never from the
user input. User-added comments and unknown keys are dropped on save.
"""
import os
import sys
from pathlib import Path

# Legacy → canonical key migrations. Applied at parse time so callers see only
# the canonical (firmware-readable) name. Today: the firmware's ExportProfiles
# writes "HeterSelectiveFilter" but its ImportProfiles reads
# "Pre-HeterSelectiveFilter" (cf. CModeGeneric.cpp:2039 vs 2464). A profile file
# that contains the export-side name has its value silently dropped at boot —
# we migrate to the read-side name on load.
LEGACY_ALIASES: dict[str, str] = {
    "HeterSelectiveFilter": "Pre-HeterSelectiveFilter",
}


def resource_path(relative_path: str) -> Path:
    """Resolve a path that works both from source and from a PyInstaller bundle."""
    if hasattr(sys, "_MEIPASS"):
        return Path(os.path.join(sys._MEIPASS, relative_path))
    return Path(os.path.abspath(relative_path))


# --- Low-level I/O -----------------------------------------------------------

def load_lines(path: Path | str) -> list[str]:
    """Read an INI file as a list of raw lines (newlines kept).

    Tries UTF-8 with BOM, plain UTF-8, then Latin-1. The fallback chain
    tolerates files exported by Windows tools (CP1252/Latin-1 accents in
    ``ProfileName``) and Notepad's BOM, both of which crashed the strict
    UTF-8 reader.
    """
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.readlines()
        except UnicodeDecodeError:
            continue
    # latin-1 decodes every byte, so reaching this is effectively impossible;
    # keep an explicit raise so a future regression surfaces.
    raise UnicodeDecodeError(
        "ini_utils", b"", 0, 1,
        f"Unable to decode {path} with utf-8-sig, utf-8 or latin-1",
    )


def load_template_lines() -> list[str]:
    """Load the canonical template embedded at initial_profile/Profiles.ini."""
    return load_lines(resource_path("initial_profile/Profiles.ini"))


def save_lines(lines: list[str], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


# --- Parsing -----------------------------------------------------------------

def parse_ini(lines: list[str]) -> dict[str, dict[str, str]]:
    """Parse INI lines into {section: {key: value}} with quotes stripped.

    Applies LEGACY_ALIASES so callers see canonical keys only. Comments and
    blank lines are skipped.
    """
    parsed: dict[str, dict[str, str]] = {}
    current: str | None = None
    for line in lines:
        s = line.strip()
        if not s or s.startswith(";"):
            continue
        if s.startswith("[") and s.endswith("]"):
            current = s[1:-1]
            parsed.setdefault(current, {})
            continue
        if current is None or "=" not in s:
            continue
        key, _, raw = s.partition("=")
        key = key.strip()
        raw = raw.strip()
        if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
            value = raw[1:-1]
        else:
            value = raw
        key = LEGACY_ALIASES.get(key, key)
        parsed[current][key] = value
    return parsed


# --- Backward-compat helper (used by current ui_editor.save_profile until the
# template-injection path is wired in). Kept short on purpose — new code should
# call parse_ini() and render_from_template() instead.

def get_value(lines: list[str], section: str, key: str, default: str = "") -> str:
    parsed = parse_ini(lines)
    return parsed.get(section, {}).get(key, default)


# --- Schema-diff helpers (used by the UI banner on load) ---------------------

def detect_missing_keys(
    user_parsed: dict[str, dict[str, str]],
    template_parsed: dict[str, dict[str, str]],
) -> list[tuple[str, str]]:
    """Keys present in the template's profile sections but absent from user file."""
    missing: list[tuple[str, str]] = []
    for section, template_keys in template_parsed.items():
        if not section.startswith("Profile_"):
            continue
        user_keys = user_parsed.get(section, {})
        for key in template_keys:
            if key not in user_keys:
                missing.append((section, key))
    return missing


def detect_dropped_keys(
    user_parsed: dict[str, dict[str, str]],
    template_parsed: dict[str, dict[str, str]],
) -> list[tuple[str, str]]:
    """Keys in user file's profile sections that the template (i.e. current
    firmware schema) doesn't recognise. Legacy aliases are already canonicalised
    by parse_ini, so a true "dropped" key is one that no longer exists at all.
    """
    dropped: list[tuple[str, str]] = []
    for section, user_keys in user_parsed.items():
        if not section.startswith("Profile_"):
            continue
        template_keys = template_parsed.get(section, {})
        for key in user_keys:
            if key not in template_keys:
                dropped.append((section, key))
    return dropped


# --- Rendering ---------------------------------------------------------------

def render_from_template(
    template_lines: list[str],
    overrides: dict[str, dict[str, str]],
) -> list[str]:
    """Walk the template and substitute each key's value with the user value.

    Args:
        template_lines: the canonical template lines (with trailing \\n).
        overrides: {section: {key: value}} — user-provided values that should
            replace the template defaults. Keys not in overrides keep the
            template's value (acts as a firmware-default backstop).

    Returns the rendered lines, ready to write. The order, comments, quoting
    style and line endings of the template are preserved.
    """
    output: list[str] = []
    current: str | None = None
    for line in template_lines:
        s = line.strip()
        if not s or s.startswith(";"):
            output.append(line)
            continue
        if s.startswith("[") and s.endswith("]"):
            current = s[1:-1]
            output.append(line)
            continue
        if current is None or "=" not in s:
            output.append(line)
            continue
        key, _, raw = s.partition("=")
        key_stripped = key.strip()
        raw_stripped = raw.strip()
        user_value = overrides.get(current, {}).get(key_stripped)
        if user_value is None:
            output.append(line)
            continue
        # Preserve the template's quote style (the firmware tolerates both, but
        # template style keeps round-trip diffs minimal).
        quoted = len(raw_stripped) >= 2 and raw_stripped[0] == '"' and raw_stripped[-1] == '"'
        nl = "\n" if line.endswith("\n") else ""
        if quoted:
            output.append(f"{key}=\"{user_value}\"{nl}")
        else:
            output.append(f"{key}={user_value}{nl}")
    return output


# --- Convenience for callers that want a full save in one call ---------------

def save_with_template(
    overrides: dict[str, dict[str, str]],
    out_path: Path,
) -> None:
    """Render the template with the given overrides and write to out_path."""
    template = load_template_lines()
    rendered = render_from_template(template, overrides)
    save_lines(rendered, out_path)


# --- Deprecated alias (kept until ui_editor is fully migrated) ---------------

load_profiles = load_lines
save_profiles = save_lines
