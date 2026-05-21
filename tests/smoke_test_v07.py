#!/usr/bin/env python3
"""End-to-end smoke checks for the 0.7.0 fixes.

Exercises the bloquants from the 3-reviewer round:
- C2  out_name path traversal guard (no write outside out_dir)
- C4  encoding fallback (utf-8-sig / utf-8 / latin-1)
- C5  empty value rejected with a "champ requis" error
- C6  HeterodyneMode / Pre-HeterSelectiveFilter accept 0..3
- C1+C3+C7 per-profile validation, with cluster-wide MasterSlave collision
- 🔴-3 dismiss banner persistence by signature
- 🔴-4 first-launch onboarding banner shown then cleared on open
- B    live-clear of red border on correction

Uses QMessageBox monkey-patching to avoid blocking dialogs in headless mode.
Exits 0 on success, 1 on the first failure.
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Force offscreen on platforms where a display isn't guaranteed (CI, ssh).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

# Squash every modal dialog so the smoke test never hangs on a popup.
QMessageBox.information = staticmethod(lambda *a, **kw: 0)
QMessageBox.warning = staticmethod(lambda *a, **kw: 0)
QMessageBox.critical = staticmethod(lambda *a, **kw: 0)
QMessageBox.question = staticmethod(lambda *a, **kw: 0)

from PySide6.QtCore import QSettings  # noqa: E402

# Sandbox QSettings so we don't smear the host's keychain.
QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(
    QSettings.IniFormat,
    QSettings.UserScope,
    str(Path(tempfile.gettempdir()) / "tr-pe-smoke-settings"),
)
# Wipe any prior smoke run so each one starts from "first launch".
QSettings().clear()

from app.ini_utils import (  # noqa: E402
    load_lines,
    load_template_lines,
    parse_ini,
    render_from_template,
)
from app.config import FIELDS, PROFILE_LABELS  # noqa: E402


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


# --- C4: encoding fallback ----------------------------------------------------
def test_encoding_fallback() -> None:
    template = "".join(load_template_lines())
    # Inject a Latin-1 accent that fails strict UTF-8 decoding.
    laced = template.replace("PaRec", "Prêt_")
    with tempfile.NamedTemporaryFile("wb", suffix=".ini", delete=False) as f:
        f.write(laced.encode("latin-1"))
        path = Path(f.name)
    try:
        lines = load_lines(path)
        if not any("Prêt_" in ln for ln in lines):
            _fail("C4: latin-1 file read but accented chars lost")
    finally:
        path.unlink(missing_ok=True)
    # BOM-prefixed UTF-8 must also work.
    with tempfile.NamedTemporaryFile("wb", suffix=".ini", delete=False) as f:
        f.write(b"\xef\xbb\xbf" + template.encode("utf-8"))
        path = Path(f.name)
    try:
        lines = load_lines(path)
        parsed = parse_ini(lines)
        if "Profile_2" not in parsed:
            _fail("C4: BOM-prefixed file mis-parsed (Profile_2 missing)")
    finally:
        path.unlink(missing_ok=True)
    print("  ✓ C4: encoding fallback (latin-1 + utf-8 BOM)")


# --- C6: HeterodyneMode / Pre-HeterSelectiveFilter 0..3 -----------------------
def test_extended_combos() -> None:
    for key in ("HeterodyneMode", "Pre-HeterSelectiveFilter"):
        choices = FIELDS[key]["choices"]
        if choices != ["0", "1", "2", "3"]:
            _fail(f"C6: {key} should expose 0..3, got {choices}")
        labels = FIELDS[key].get("choice_labels")
        if labels is None or len(labels) != 4:
            _fail(f"C6: {key} needs 4 choice_labels, got {labels}")
    # Round-trip: a profile with HeterodyneMode=2 must keep value 2 after render.
    template = load_template_lines()
    overrides = {"Profile_2": {"HeterodyneMode": "2", "Pre-HeterSelectiveFilter": "3"}}
    rendered = "".join(render_from_template(template, overrides))
    if "HeterodyneMode=2" not in rendered or "Pre-HeterSelectiveFilter=3" not in rendered:
        _fail("C6: extended HeterodyneMode/Pre-HeterSelectiveFilter not round-tripped")
    print("  ✓ C6: HeterodyneMode/Pre-HeterSelectiveFilter accept 0..3")


# --- App-level checks need a QApplication + a working ini -------------------
def _build_editor(tmpdir: Path):
    from app.ui_editor import ProfileEditor

    ini_path = tmpdir / "Profiles.ini"
    ini_path.write_text("".join(load_template_lines()), encoding="utf-8")
    return ProfileEditor(str(ini_path))


def test_onboarding_then_dismiss(tmpdir: Path) -> None:
    QSettings().setValue("has_opened_file", False)
    editor = _build_editor(tmpdir)
    if editor.onboarding_banner is None:
        _fail("🔴-4: onboarding banner missing on first launch")
    # Simulate "the user opened a real file" — refresh should clear the banner.
    QSettings().setValue("has_opened_file", True)
    editor._refresh_onboarding_banner()
    if editor.onboarding_banner is not None:
        _fail("🔴-4: onboarding banner still present after has_opened_file=True")
    print("  ✓ 🔴-4: onboarding banner appears then vanishes")


def test_drift_dismiss_signature(tmpdir: Path) -> None:
    QSettings().setValue("has_opened_file", True)
    editor = _build_editor(tmpdir)
    # Inject a fake drift signature so the banner has something to show.
    editor.missing_keys = [("Profile_2", "Faux1"), ("Profile_2", "Faux2")]
    editor.dropped_keys = []
    editor._refresh_drift_banner()
    if editor.drift_banner is None:
        _fail("🔴-3: drift banner not built when keys are present")
    # Dismiss this signature.
    signature = (tuple(sorted(editor.missing_keys)), tuple(sorted(editor.dropped_keys)))
    editor._dismissed_drift_signatures.add(signature)
    editor._refresh_drift_banner()
    if editor.drift_banner is not None:
        _fail("🔴-3: dismissed drift signature still rendered the banner")
    # A DIFFERENT signature should still show.
    editor.missing_keys = [("Profile_3", "AutreClé")]
    editor._refresh_drift_banner()
    if editor.drift_banner is None:
        _fail("🔴-3: different drift signature was silenced too")
    print("  ✓ 🔴-3: dismiss banner persists by signature only")


def test_per_profile_validation(tmpdir: Path) -> None:
    QSettings().setValue("has_opened_file", True)
    editor = _build_editor(tmpdir)
    # Plant an invalid value in Profile_3 (NOT currently displayed; default is "2").
    editor.cache["3"]["MinFreqUS"] = ""  # empty → "champ requis"
    # Trigger save: should detect the error in Profile_3, switch to it, dialog.
    editor.save_profile()
    # After save_profile with errors, the editor should have switched to Profile_3.
    if editor.profile_id != "3":
        _fail(
            f"C1: per-profile validation didn't switch to faulty profile "
            f"(stayed on {editor.profile_id!r})"
        )
    print("  ✓ C1+C3: per-profile validation catches non-current profile")


def test_master_slave_collision(tmpdir: Path) -> None:
    QSettings().setValue("has_opened_file", True)
    editor = _build_editor(tmpdir)
    # Force device PRS-S, then plant two masters across two profiles.
    idx = editor.device_combo.findData("PRS-S")
    if idx >= 0:
        editor.device_combo.setCurrentIndex(idx)
    editor.cache["2"]["OpMode"] = "Synchro"
    editor.cache["2"]["MasterSlave"] = "0"
    editor.cache["3"]["OpMode"] = "Synchro"
    editor.cache["3"]["MasterSlave"] = "0"
    # Build a fresh form so widgets reflect the cache.
    editor.build_form()
    editor.save_profile()
    if "MasterSlave" not in editor.field_errors:
        _fail("C7: multiple masters not flagged on the displayed profile")
    print("  ✓ C7: MasterSlave collision detected on PRS-S cluster")


def test_live_clear_error(tmpdir: Path) -> None:
    from PySide6.QtWidgets import QLineEdit

    QSettings().setValue("has_opened_file", True)
    editor = _build_editor(tmpdir)
    # Set RelativeThreshold (int, active in default Auto record mode) to empty.
    widget = editor.inputs.get("RelativeThreshold")
    if not isinstance(widget, QLineEdit):
        _fail("B: RelativeThreshold widget not a QLineEdit")
    widget.setText("")  # invalid
    editor.save_profile()  # should mark error
    if "RelativeThreshold" not in editor.field_errors:
        _fail("B: empty RelativeThreshold not flagged at save")
    # Now type a valid value — live clear should fire.
    widget.setText("18")
    if "RelativeThreshold" in editor.field_errors:
        _fail("B: live clear didn't run when the value became valid")
    print("  ✓ B: red border live-clears once value becomes valid")


def test_khz_to_hz_conversion(tmpdir: Path) -> None:
    """The 4 Min/Max Freq fields are displayed in kHz, stored in Hz on disk.
    A user typing '15.5' in MinFreqUS must land as 'MinFreqUS=15500' in the
    written INI; reading back must show '15.5' in the UI again."""
    QSettings().setValue("has_opened_file", True)
    editor = _build_editor(tmpdir)

    # The disk template has MinFreqUS in Hz; the UI should show kHz.
    initial = editor.inputs["MinFreqUS"].text()
    try:
        initial_khz = float(initial)
    except ValueError:
        _fail(f"kHz: MinFreqUS widget shows non-numeric value: {initial!r}")
    if initial_khz > 200:  # would mean the widget is still in Hz
        _fail(f"kHz: MinFreqUS widget shows Hz, not kHz ({initial_khz})")

    # Type a kHz value, save, verify the disk file carries Hz.
    editor.inputs["MinFreqUS"].setText("15.5")
    editor.inputs["MaxFreqUS"].setText("110")
    editor.out_dir = tmpdir / "out_khz"
    editor.out_dir.mkdir(exist_ok=True)
    editor.out_name_edit.setText("converted.ini")
    editor.save_profile()
    out = editor.out_dir / "converted.ini"
    if not out.exists():
        _fail("kHz: save_profile didn't write the output file")
    body = out.read_text(encoding="utf-8")
    if "MinFreqUS=15500" not in body:
        _fail(f"kHz: '15.5' kHz did not become MinFreqUS=15500 (got body: …{body[body.find('MinFreqUS'):body.find('MinFreqUS')+60]}…)")
    if "MaxFreqUS=110000" not in body:
        _fail("kHz: '110' kHz did not become MaxFreqUS=110000")

    # Round-trip: re-open the file we just wrote, MinFreqUS widget should show 15.5 again.
    editor.ini_path = out
    editor._parse_user_file()
    editor.cache = {pid: {} for pid in PROFILE_LABELS.values()}
    editor.build_form()
    reloaded = editor.inputs["MinFreqUS"].text()
    try:
        if abs(float(reloaded) - 15.5) > 0.05:
            _fail(f"kHz round-trip: MinFreqUS reloaded as {reloaded!r}, expected 15.5")
    except ValueError:
        _fail(f"kHz round-trip: MinFreqUS reloaded as non-numeric {reloaded!r}")
    print("  ✓ kHz/Hz conversion: 15.5 kHz UI ↔ 15500 Hz on disk")


def test_out_name_path_guard(tmpdir: Path) -> None:
    QSettings().setValue("has_opened_file", True)
    editor = _build_editor(tmpdir)
    editor.out_dir = tmpdir / "out"
    editor.out_dir.mkdir(exist_ok=True)
    # Try to inject an absolute path — should be reduced to bare filename.
    editor.out_name_edit.setText("/tmp/evil/should_not_land_here.ini")
    editor.save_profile()
    forbidden = Path("/tmp/evil/should_not_land_here.ini")
    if forbidden.exists():
        forbidden.unlink()
        (Path("/tmp/evil")).rmdir()
        _fail("C2: absolute out_name was written outside out_dir")
    safe = editor.out_dir / "should_not_land_here.ini"
    if not safe.exists():
        _fail(f"C2: expected file {safe} was not written under out_dir")
    print("  ✓ C2: absolute out_name reduced to bare filename")


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    _ = app  # keep alive

    print("Running 0.7.0 smoke checks…")
    test_encoding_fallback()
    test_extended_combos()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        test_onboarding_then_dismiss(tmp)
        test_drift_dismiss_signature(tmp)
        test_per_profile_validation(tmp)
        test_master_slave_collision(tmp)
        test_live_clear_error(tmp)
        test_khz_to_hz_conversion(tmp)
        test_out_name_path_guard(tmp)
    print("All smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
