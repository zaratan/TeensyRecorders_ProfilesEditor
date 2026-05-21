"""Inline notification banners — first-launch onboarding, schema drift.

Two banners live above the tab widget:

- ``build_onboarding_banner`` — shown until the user has either opened a
  real file or successfully saved one (tracked in ``QSettings`` as
  ``has_opened_file``). Tells the user they're editing the firmware
  defaults, with both pathways spelled out.
- ``build_drift_banner`` — shown when the loaded file's key set diverges
  from the firmware-current template. Carries the missing/dropped counts
  inline, a "Voir détails" button for the full list, and a dismiss
  button that suppresses *this exact drift signature* for the session.

Both builders take the data + callbacks they need and return a ready
``QFrame``. The caller decides where to drop the frame (each lives in
its own ``QVBoxLayout`` slot in the main window, so swapping is cheap).
"""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QToolButton,
)

from .config import AppColors

DriftSignature = tuple[tuple, tuple]


def build_onboarding_banner() -> QFrame:
    """Violet banner showing both entry paths (load existing / save new).
    Returns the frame ready to add to a layout."""
    banner = QFrame()
    banner.setStyleSheet(
        f"QFrame {{ background-color: {AppColors.ONBOARDING_BANNER_BG}; border-radius: 4px; }}"
        "QLabel { color: white; }"
    )
    bl = QHBoxLayout(banner)
    bl.setContentsMargins(10, 6, 6, 6)
    bl.setSpacing(8)
    msg = QLabel(
        "Aucun fichier ouvert — vous travaillez sur les valeurs par défaut firmware. "
        "Cliquez sur <b>Ouvrir un fichier…</b> pour modifier un <code>Profiles.ini</code> "
        "existant, ou éditez et <b>Sauvegardez</b> pour en créer un nouveau."
    )
    msg.setTextFormat(Qt.RichText)
    msg.setWordWrap(True)
    bl.addWidget(msg, stretch=1)
    return banner


def _summary_line(n_missing: int, n_dropped: int) -> str:
    """Pluralise + concatenate the two count phrases. Edge cases handled
    inline so the caller never sees a stray trailing dash."""
    parts: list[str] = []
    if n_missing:
        parts.append(
            f"{n_missing} paramètre{'s' if n_missing > 1 else ''} "
            f"initialisé{'s' if n_missing > 1 else ''} aux valeurs par défaut firmware"
        )
    if n_dropped:
        parts.append(
            f"{n_dropped} paramètre{'s' if n_dropped > 1 else ''} obsolète"
            f"{'s' if n_dropped > 1 else ''} retiré{'s' if n_dropped > 1 else ''} à la sauvegarde"
        )
    return " — ".join(parts) + "."


def build_drift_banner(
    missing_keys: list[tuple[str, str]],
    dropped_keys: list[tuple[str, str]],
    signature: DriftSignature,
    on_details: Callable[[], None],
    on_dismiss: Callable[[DriftSignature], None],
) -> QFrame:
    """Build the blue drift banner.

    Args:
        missing_keys / dropped_keys: drives the inline summary line.
        signature: opaque token passed back to ``on_dismiss`` so the
            caller can record which drift was acknowledged.
        on_details: invoked when the "Voir détails" button is clicked.
        on_dismiss: invoked with ``signature`` when the user dismisses
            the banner. Caller is responsible for hiding the frame.
    """
    banner = QFrame()
    banner.setStyleSheet(
        f"QFrame {{ background-color: {AppColors.DRIFT_BANNER_BG}; border-radius: 4px; }}"
        "QLabel { color: white; }"
    )
    bl = QHBoxLayout(banner)
    bl.setContentsMargins(10, 6, 6, 6)
    bl.setSpacing(8)

    msg = QLabel(_summary_line(len(missing_keys), len(dropped_keys)))
    msg.setWordWrap(True)
    bl.addWidget(msg, stretch=1)

    details_btn = QPushButton("Voir détails")
    details_btn.setCursor(Qt.PointingHandCursor)
    details_btn.setStyleSheet(
        "QPushButton { color: white; background: transparent; "
        f"border: 1px solid {AppColors.DRIFT_BANNER_BORDER}; border-radius: 3px; padding: 2px 8px; }}"
        f"QPushButton:hover {{ background-color: {AppColors.DRIFT_BANNER_HOVER}; }}"
    )
    details_btn.clicked.connect(on_details)
    bl.addWidget(details_btn)

    dismiss_btn = QToolButton()
    dismiss_btn.setText("×")
    dismiss_btn.setToolTip(
        "Masquer pour cette session — réapparaîtra au prochain lancement"
    )
    dismiss_btn.setCursor(Qt.PointingHandCursor)
    dismiss_btn.setStyleSheet(
        "QToolButton { color: white; background: transparent; border: none; "
        "font-weight: bold; padding: 2px 6px; }"
        "QToolButton:hover { color: #ffd; }"
    )

    def _dismiss():
        on_dismiss(signature)
        banner.hide()

    dismiss_btn.clicked.connect(_dismiss)
    bl.addWidget(dismiss_btn)

    return banner


def build_schema_mismatch_banner(
    file_version: str | None,
    expected_version: str,
) -> QFrame:
    """Amber banner that warns when the loaded file declares a firmware
    schema version different from the one this build is aligned with.

    A None ``file_version`` means the file predates the version marker —
    handled as a softer "unknown" notice rather than a mismatch.
    """
    banner = QFrame()
    banner.setStyleSheet(
        f"QFrame {{ background-color: {AppColors.SCHEMA_MISMATCH_BG}; border-radius: 4px; }}"
        "QLabel { color: white; }"
    )
    bl = QHBoxLayout(banner)
    bl.setContentsMargins(10, 6, 6, 6)
    bl.setSpacing(8)
    if file_version is None:
        text = (
            f"Le fichier ne déclare pas de version firmware. Cet éditeur "
            f"cible la version <b>{expected_version}</b> — vérifiez que "
            f"votre appareil tourne bien cette version avant de sauvegarder."
        )
    else:
        text = (
            f"Fichier déclaré pour le firmware <b>{file_version}</b>, "
            f"éditeur aligné sur <b>{expected_version}</b>. "
            f"Certains paramètres peuvent avoir changé de format — "
            f"vérifiez la compatibilité avant de sauvegarder."
        )
    msg = QLabel(text)
    msg.setTextFormat(Qt.RichText)
    msg.setWordWrap(True)
    bl.addWidget(msg, stretch=1)
    return banner


def format_drift_details(
    missing_keys: list[tuple[str, str]],
    dropped_keys: list[tuple[str, str]],
) -> str:
    """Plain-text body for the "Voir détails" dialog. Two sections:
    initialised-to-default first, then dropped-on-save."""
    lines: list[str] = []
    if missing_keys:
        lines.append("Initialisés aux valeurs par défaut firmware :")
        for section, key in missing_keys:
            lines.append(f"  • [{section}] {key}")
        lines.append("")
    if dropped_keys:
        lines.append("Inconnus du firmware actuel, retirés à la sauvegarde :")
        for section, key in dropped_keys:
            lines.append(f"  • [{section}] {key}")
    return "\n".join(lines)
