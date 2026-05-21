from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QFileDialog, QMessageBox, QFormLayout, QTabWidget, QTabBar, QFrame, QApplication, QScrollArea, QSizePolicy, QDialog, QToolButton
from PySide6.QtGui import QPixmap, QFont, QIntValidator, QDoubleValidator
from PySide6.QtCore import Qt, QLocale, QTimer, QEvent, QStandardPaths, QSettings, QSignalBlocker

from .ini_utils import (
    detect_dropped_keys,
    detect_missing_keys,
    load_lines,
    load_template_lines,
    parse_ini,
    parse_schema_version,
    save_with_template,
)
from .config import (
    FIELDS, SECTION_TITLES, PROFILE_LABELS, BUILD_VERSION, SUBTITLES,
    SCOPE_BADGES, OpMode, Device, AppColors, FIRMWARE_SCHEMA_VERSION,
)
from . import banners, validation, visibility

# Field keys whose values are needed for cross-field validation. Materialised
# from FIELDS' min/max relations + Nyquist; kept as a module constant so the
# per-profile validation loop reads only the keys it actually uses (saving
# 48 dict lookups per profile).
_CROSS_FIELD_KEYS = (
    "MinFreqUS", "MaxFreqUS", "MinFreqA", "MaxFreqA",
    "MinDuration", "MaxDuration", "SampFreqU",
)


def _theme_colors() -> dict[str, str]:
    """Return the gray-scale tokens used across the UI, adapted to the current
    system color scheme. Hex values were calibrated for WCAG AA (≥ 4.5:1 on
    text, ≥ 3:1 on UI borders) against the respective backgrounds.

    The previous version used hex values tuned for dark mode only; in light
    mode they fell to ~2.6:1 on white — illegible for the path label, footer,
    section subtitles, and the helper "i" icon.
    """
    app = QApplication.instance()
    is_dark = False
    if app is not None:
        # styleHints().colorScheme() is Qt 6.5+. The Qt 6 prebuilt wheels we
        # ship already satisfy that, but guard anyway so a older Qt at dev
        # time falls through to the dark defaults rather than crashing.
        try:
            is_dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
        except AttributeError:
            is_dark = True
    if is_dark:
        # Slightly lifted from the prior hex (#a0a0a0, #9a9a9a, …) so each
        # gray clears AA on the dark window background (#1e1e1e ish).
        return {
            "secondary_text": "#b0b0b0",  # path label, output dir, footer
            "subtitle":       "#a8a8a8",  # section small-caps
            "tertiary_text":  "#9a9a9a",  # ? button text, helper "i" text
            "border":         "#7a7a7a",  # ? button border, helper "i" border
        }
    return {
        "secondary_text": "#666666",  # 5.7:1 on white
        "subtitle":       "#6a6a6a",  # 5.5:1
        "tertiary_text":  "#6c6c6c",  # 5.4:1
        "border":         "#9a9a9a",  # 3:1 — UI-component AA
    }


class HelperPopup(QFrame):
    def __init__(self, helper: str, source: "HelperLabel"):
        super().__init__(None, Qt.ToolTip)
        self._source = source
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {AppColors.PRIMARY};
                border-radius: 6px;
            }}
            QLabel {{
                color: white;
                padding: 8px 12px;
                font-size: 12px;
                line-height: 145%;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        text = QLabel(helper, self)
        text.setWordWrap(True)
        # Wider popup (360 vs 280) so 50-90 word helpers don't wrap into 8+
        # narrow lines. Rich text is explicit so <b>…</b> and <br> behave
        # consistently across platforms.
        text.setMaximumWidth(360)
        text.setTextFormat(Qt.RichText)
        layout.addWidget(text)
        self.adjustSize()
        self.move(source.mapToGlobal(source.rect().bottomLeft()))
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            global_pos = event.globalPosition().toPoint()
            if self.frameGeometry().contains(global_pos):
                return False
            local = self._source.mapFromGlobal(global_pos)
            if self._source.rect().contains(local):
                return False
            QTimer.singleShot(0, self.close)
        return False

    def closeEvent(self, event):
        if HelperLabel._active is not None and HelperLabel._active[0] is self:
            HelperLabel._active = None
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(event)


class HelperLabel(QLabel):
    _active = None

    def __init__(self, helper: str, parent=None):
        super().__init__("i", parent)
        self._helper = helper
        # Deliberately NOT calling setToolTip(): the native Qt tooltip renders
        # our rich-text helper as plain text (visible <b> tags, no list breaks),
        # which duplicates the click popup with worse formatting. The popup is
        # the only documented path to the helper text.
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        active = HelperLabel._active
        if active is not None:
            popup, owner = active
            HelperLabel._active = None
            popup.close()
            if owner is self:
                event.accept()
                return
        self.show_popup()
        event.accept()

    def show_popup(self):
        popup = HelperPopup(self._helper, self)
        HelperLabel._active = (popup, self)
        popup.show()


class ClickableTabBar(QTabBar):
    """QTabBar that shows the pointing-hand cursor over each tab.

    setCursor() on a QTabBar only covers the empty area outside the tabs,
    so we react to mouse moves and pick the cursor based on tabAt(pos).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        if self.tabAt(event.position().toPoint()) >= 0:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)


class AboutDialog(QDialog):
    def __init__(self, logo_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("À propos")
        self.setModal(True)
        theme = _theme_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        logo = QLabel()
        pixmap = QPixmap(str(logo_path))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaledToHeight(96, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        title = QLabel("TeensyRecorders Profiles Editor")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        version = QLabel(f"Version {BUILD_VERSION}")
        version.setStyleSheet(f"color: {theme['tertiary_text']};")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        desc = QLabel(
            "Outil pour éditer et sauvegarder facilement vos fichiers Profiles.ini.\n"
            "Edition des profils avec validation automatique des valeurs."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        link = QLabel(
            '<a href="https://framagit.org/PiBatRecorderPojects/TeensyRecorders/blob/master/Update/ManuelTR.pdf">'
            "Documentation des TeensyRecorders</a>"
        )
        link.setOpenExternalLinks(True)
        link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link.setAlignment(Qt.AlignCenter)
        layout.addWidget(link)

        credit = QLabel("© Alexandre LANGLAIS & Zaratan — 2026")
        credit.setStyleSheet(f"color: {theme['tertiary_text']}; font-size: 11px;")
        credit.setAlignment(Qt.AlignCenter)
        layout.addWidget(credit)

        close_btn = QPushButton("Fermer")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class ProfileEditor(QWidget):
    def __init__(self, ini_path, logo_path="img/logo_PR.png"):
        super().__init__()
        self.logo_path = logo_path
        self.setWindowTitle("TeensyRecorders Profiles Editor")
        # 720×700 fits the 3 banners + header + 2 toolbars + tab strip + form
        # + footer without truncating the "Passive Stéréo Synchro (PRS-S)"
        # device combo or forcing a horizontal scrollbar. Smaller windows
        # are perfectly readable; below this the layout starts to clip.
        self.setMinimumWidth(720)
        self.setMinimumHeight(700)
        # Resolve theme once per window. Color scheme changes during the
        # session require a relaunch (rare on macOS), so caching is fine.
        self._theme = _theme_colors()
        # Input + helper styling. Keep QComboBox itself unstyled to preserve
        # the native macOS drop-down arrow, but restyle the popup list.
        self.setStyleSheet(f"""
            QLineEdit {{
                padding: 4px 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                padding: 4px 0;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 6px 14px;
                min-height: 22px;
                color: #e0e0e0;
                border: none;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {AppColors.PRIMARY};
                color: white;
            }}
            HelperLabel {{
                color: {self._theme['tertiary_text']};
                background-color: transparent;
                border: 1px solid {self._theme['border']};
                border-radius: 7px;
                font-weight: bold;
                font-size: 10px;
            }}
            HelperLabel:hover {{
                color: white;
                background-color: {AppColors.PRIMARY};
                border: 1px solid {AppColors.PRIMARY};
            }}
        """)

        # Template is loaded once (embedded resource, never reloaded at runtime);
        # the user file is loaded eagerly here and can be swapped via "Ouvrir".
        self.template_lines = load_template_lines()
        self.template_parsed = parse_ini(self.template_lines)
        self.ini_path = Path(ini_path)
        self.lines: list[str] = []
        self.user_parsed: dict[str, dict[str, str]] = {}
        self.missing_keys: list[tuple[str, str]] = []
        self.dropped_keys: list[tuple[str, str]] = []
        self.profile_id = "2"
        self.inputs = {}
        self.out_dir = self._default_output_dir()
        self.out_name = "Profiles_custom.ini"
        self.cache = {pid: {} for pid in PROFILE_LABELS.values()}
        self.drift_banner: QFrame | None = None
        # Signatures of drift states the user has explicitly dismissed in this
        # session. Each signature is (sorted missing tuple, sorted dropped
        # tuple); a banner with a previously-dismissed signature is silently
        # skipped on rebuild, so reopening a file with the same drift profile
        # doesn't keep nagging the user.
        self._dismissed_drift_signatures: set[tuple] = set()
        self.schema_banner: QFrame | None = None
        self.file_schema_version: str | None = None
        # Parse the user file once at load. user_parsed is the authoritative
        # snapshot of disk values; widget edits land in self.cache and override
        # user_parsed at save time.
        self._parse_user_file()

        layout = QVBoxLayout()

        # --- En-tête compact ---
        header_layout = QHBoxLayout()
        title = QLabel("TeensyRecorders Profiles Editor")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch(1)

        about_btn = QToolButton()
        about_btn.setText("?")
        about_btn.setToolTip("À propos")
        about_btn.setCursor(Qt.PointingHandCursor)
        about_btn.setMouseTracking(True)
        about_btn.setFixedSize(28, 28)
        about_btn.setStyleSheet(f"""
            QToolButton {{
                color: {self._theme['tertiary_text']};
                background-color: transparent;
                border: 1px solid {self._theme['border']};
                border-radius: 14px;
                font-weight: bold;
            }}
            QToolButton:hover {{
                color: white;
                background-color: {AppColors.PRIMARY};
                border: 1px solid {AppColors.PRIMARY};
            }}
        """)
        about_btn.clicked.connect(self.show_about)
        header_layout.addWidget(about_btn)
        layout.addLayout(header_layout)

        # Source file row: "Ouvrir un fichier..." + path label
        source_layout = QHBoxLayout()
        open_btn = QPushButton("Ouvrir un fichier…")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setToolTip("Charger un fichier Profiles.ini existant")
        open_btn.clicked.connect(self.open_ini_file)
        source_layout.addWidget(open_btn)
        self.source_path_label = QLabel()
        self.source_path_label.setStyleSheet(f"color: {self._theme['secondary_text']};")
        self.source_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # Width cap so a long resolved path doesn't push the layout; full
        # path stays available via tooltip.
        self.source_path_label.setMaximumWidth(360)
        self._set_source_path_label(self.ini_path)
        source_layout.addWidget(self.source_path_label, stretch=1)
        layout.addLayout(source_layout)

        # Sélecteur de profil
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel("Sélection du profil :"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(PROFILE_LABELS.keys())
        self.profile_combo.setCursor(Qt.PointingHandCursor)
        self.profile_combo.currentTextChanged.connect(self.change_profile)
        profile_layout.addWidget(self.profile_combo)
        profile_layout.addSpacing(20)
        # Device type — drives which scoped fields stay active. Persisted
        # across sessions in QSettings so the user doesn't re-select on
        # every launch.
        profile_layout.addWidget(QLabel("Type d'appareil :"))
        self.device_combo = QComboBox()
        # userData carries the device token used by _compute_enabled_map
        # (matches SCOPE_BADGES keys for AR/PRS, plus the bare PR baseline).
        self.device_combo.addItem("Passive Recorder (PR)", Device.PR)
        self.device_combo.addItem("Active Recorder (AR)", Device.AR)
        self.device_combo.addItem("Passive Stéréo (PRS)", Device.PRS)
        self.device_combo.addItem("Passive Stéréo Synchro (PRS-S)", Device.PRS_S)
        self.device_combo.setCursor(Qt.PointingHandCursor)
        saved_device = QSettings().value("device_type", Device.PR)
        idx = self.device_combo.findData(saved_device)
        if idx >= 0:
            self.device_combo.setCurrentIndex(idx)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        profile_layout.addWidget(self.device_combo)
        profile_layout.addStretch(1)
        layout.addLayout(profile_layout)

        # First-launch onboarding banner slot. Shown when the user has never
        # opened a real file via "Ouvrir un fichier…" so they understand they
        # are currently editing the embedded demo template, not their device's
        # Profiles.ini. Lives in its own slot above the drift banner.
        self.onboarding_banner: QFrame | None = None
        self.onboarding_banner_slot = QVBoxLayout()
        self.onboarding_banner_slot.setContentsMargins(0, 8, 0, 0)
        layout.addLayout(self.onboarding_banner_slot)
        self._refresh_onboarding_banner()

        # Schema-mismatch banner slot (amber): louder than the blue drift
        # banner because a firmware version mismatch can corrupt fields the
        # drift detector wouldn't catch.
        self.schema_banner_slot = QVBoxLayout()
        self.schema_banner_slot.setContentsMargins(0, 8, 0, 0)
        layout.addLayout(self.schema_banner_slot)
        self._refresh_schema_banner()

        # Schema-drift banner slot: an empty layout that hosts the (re)built
        # banner. Keeping it as a dedicated slot lets us swap the banner on
        # every file reload without messing with insertion indices. Small
        # top margin so the banner doesn't kiss the device combo above.
        self.drift_banner_slot = QVBoxLayout()
        self.drift_banner_slot.setContentsMargins(0, 8, 0, 0)
        layout.addLayout(self.drift_banner_slot)
        self._refresh_drift_banner()

        # Onglets
        self.tabs = QTabWidget()
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabs.setTabBar(ClickableTabBar())
        layout.addWidget(self.tabs, stretch=1)
        self.build_form()

        # Dossier sortie
        dir_layout = QHBoxLayout()
        browse_btn = QPushButton("Choisir dossier sortie")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self.select_output_dir)
        dir_layout.addWidget(browse_btn)

        self.out_dir_label = QLabel(str(self.out_dir.resolve()))
        self.out_dir_label.setStyleSheet(f"color: {self._theme['secondary_text']};")
        self.out_dir_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # Width cap mirrors the source_path_label above so a long resolved
        # path doesn't push the layout; full path stays available via tooltip.
        self.out_dir_label.setMaximumWidth(360)
        self.out_dir_label.setToolTip(str(self.out_dir.resolve()))
        dir_layout.addWidget(self.out_dir_label, stretch=1)
        layout.addLayout(dir_layout)

        # Sauvegarde
        save_layout = QHBoxLayout()
        save_btn = QPushButton("Sauvegarder")
        save_btn.setCursor(Qt.PointingHandCursor)
        # Primary action style — distinguishes Save from the secondary
        # "Choisir dossier sortie" button above it.
        save_btn.setStyleSheet(
            f"QPushButton {{ background-color: {AppColors.PRIMARY}; color: white; "
            "padding: 8px 20px; font-weight: 600; border: none; "
            "border-radius: 4px; }"
            f"QPushButton:hover {{ background-color: {AppColors.PRIMARY_HOVER}; }}"
            f"QPushButton:pressed {{ background-color: {AppColors.PRIMARY_PRESSED}; }}"
            # Visible focus ring for keyboard navigation (Tab) — without this
            # the primary action becomes invisible to keyboard-only users.
            "QPushButton:focus { outline: 2px solid #b0c8ff; outline-offset: 1px; }"
        )
        save_btn.clicked.connect(self.save_profile)
        save_layout.addWidget(save_btn)

        self.out_name_edit = QLineEdit(self.out_name)
        self.out_name_edit.setPlaceholderText("Nom du fichier de sortie (ex: Profiles_custom.ini)")
        save_layout.addWidget(self.out_name_edit, stretch=1)
        layout.addLayout(save_layout)

        # Footer
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)

        layout.addWidget(separator)
        footer = QLabel(f"© Alexandre LANGLAIS & Zaratan - 2026 - v{BUILD_VERSION}")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"color: {self._theme['secondary_text']}; font-size: 10px;")
        layout.addWidget(footer)

        self.setLayout(layout)

    def _set_source_path_label(self, path: Path) -> None:
        """Show the filename inline, stash the full path in the tooltip."""
        resolved = str(path.resolve())
        self.source_path_label.setText(path.name)
        self.source_path_label.setToolTip(resolved)

    def _parse_user_file(self) -> None:
        """Re-read self.ini_path from disk and refresh drift / schema-version detection."""
        self.lines = load_lines(self.ini_path)
        self.user_parsed = parse_ini(self.lines)
        self.missing_keys = detect_missing_keys(self.user_parsed, self.template_parsed)
        self.dropped_keys = detect_dropped_keys(self.user_parsed, self.template_parsed)
        # Stash the declared firmware schema version for the mismatch banner.
        # None = the file predates the marker (older firmware exports).
        self.file_schema_version = parse_schema_version(self.lines)

    def open_ini_file(self) -> None:
        """User-triggered: load a different Profiles.ini, reset cache, rebuild form."""
        # Default to the save folder — users typically re-open a file they just
        # saved, so this avoids a needless folder hop. Falls back to home if
        # the save folder doesn't exist yet.
        start_dir = self.out_dir if self.out_dir.exists() else Path.home()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir un fichier Profiles.ini",
            str(start_dir),
            "Fichiers INI (*.ini);;Tous les fichiers (*)",
        )
        if not path:
            return
        # Stash previous state so we can restore it on parse failure — the
        # user shouldn't lose their session because they clicked on a bad file.
        previous_path = self.ini_path
        self.ini_path = Path(path)
        try:
            self._parse_user_file()
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            self.ini_path = previous_path
            QMessageBox.critical(
                self,
                "Fichier illisible",
                f"Impossible de lire « {Path(path).name} ».\n\n"
                f"Détail technique : {exc}\n\n"
                f"Le fichier précédent reste chargé.",
            )
            return
        # Mark that the user has explicitly loaded a real file at least once —
        # silences the first-launch onboarding banner from now on.
        QSettings().setValue("has_opened_file", True)
        # New file = fresh starting point: discard pending edits.
        self.cache = {pid: {} for pid in PROFILE_LABELS.values()}
        self._set_source_path_label(self.ini_path)
        self._refresh_onboarding_banner()
        self._refresh_schema_banner()
        self._refresh_drift_banner()
        self.build_form()

    def _refresh_schema_banner(self) -> None:
        """Show the amber schema-mismatch banner when the loaded file's
        declared firmware version differs from the one this build targets.
        Embedded template self-loads at the matching version, so the slot
        is empty for the default profile."""
        if self.schema_banner is not None:
            self.schema_banner_slot.removeWidget(self.schema_banner)
            self.schema_banner.deleteLater()
            self.schema_banner = None
        # Match → nothing to show. Mismatch (or missing marker, which is a
        # softer "we don't know what you have") → banner.
        if self.file_schema_version == FIRMWARE_SCHEMA_VERSION:
            return
        banner = banners.build_schema_mismatch_banner(
            self.file_schema_version, FIRMWARE_SCHEMA_VERSION,
        )
        self.schema_banner_slot.addWidget(banner)
        self.schema_banner = banner

    def _refresh_onboarding_banner(self) -> None:
        """Show the violet onboarding banner unless ``has_opened_file`` is
        set in QSettings. Builder lives in ``app/banners.py``."""
        if self.onboarding_banner is not None:
            self.onboarding_banner_slot.removeWidget(self.onboarding_banner)
            self.onboarding_banner.deleteLater()
            self.onboarding_banner = None
        if QSettings().value("has_opened_file", False, type=bool):
            return
        banner = banners.build_onboarding_banner()
        self.onboarding_banner_slot.addWidget(banner)
        self.onboarding_banner = banner

    def _refresh_drift_banner(self) -> None:
        """Rebuild the drift banner from current missing/dropped state.
        Skips when there's nothing to report, or when the user has already
        dismissed this exact signature in the session. Builder lives in
        ``app/banners.py``."""
        if self.drift_banner is not None:
            self.drift_banner_slot.removeWidget(self.drift_banner)
            self.drift_banner.deleteLater()
            self.drift_banner = None
        if not self.missing_keys and not self.dropped_keys:
            return
        signature = (
            tuple(sorted(self.missing_keys)),
            tuple(sorted(self.dropped_keys)),
        )
        if signature in self._dismissed_drift_signatures:
            return
        banner = banners.build_drift_banner(
            self.missing_keys,
            self.dropped_keys,
            signature,
            on_details=self._show_drift_details,
            on_dismiss=self._dismissed_drift_signatures.add,
        )
        self.drift_banner_slot.addWidget(banner)
        self.drift_banner = banner

    def _show_drift_details(self) -> None:
        QMessageBox.information(
            self,
            "Différences avec le schéma firmware",
            banners.format_drift_details(self.missing_keys, self.dropped_keys),
        )

    @staticmethod
    def _default_output_dir() -> Path:
        # Qt resolves the platform-specific Documents folder (macOS, Windows,
        # Linux with locale awareness). Falls back to home if the user has no
        # Documents directory configured.
        docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        if docs and Path(docs).exists():
            return Path(docs)
        return Path.home()

    def show_about(self):
        dialog = AboutDialog(self.logo_path, self)
        dialog.exec()

    # --- Cache ---
    def sync_widgets_to_cache(self):
        pid = self.profile_id
        if pid not in self.cache:
            self.cache[pid] = {}
        for key, widget in self.inputs.items():
            if isinstance(widget, QLineEdit):
                self.cache[pid][key] = widget.text().strip()
            elif isinstance(widget, QComboBox):
                # Prefer userData (raw INI value); fall back to display text for
                # widgets created without choice_labels (legacy combos).
                data = widget.currentData()
                self.cache[pid][key] = data if data is not None else widget.currentText()

    def update_cache(self, key, value):
        self.cache[self.profile_id][key] = str(value).strip()

    # --- Sous-titre ---
    def add_subtitle(self, form_layout, text):
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 18, 0, 6)
        layout.setSpacing(6)

        label = QLabel(text.upper())
        label.setStyleSheet(f"""
            QLabel {{
                color: {self._theme['subtitle']};
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
        """)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # Reserve generous vertical room — macOS dark theme otherwise clips
        # the top of small-caps text inside a QFormLayout spanning row.
        label.setMinimumHeight(label.fontMetrics().height() + 16)
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(label)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet("color: rgba(255, 255, 255, 0.12);")
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        form_layout.addRow(container)
        return container

    @staticmethod
    def _make_scope_badge(scope_key: str) -> QLabel | None:
        """Coloured chip (AR / PRS / RL) shown next to fields scoped to a
        specific hardware variant or operating mode. Returns None if the
        key is unknown."""
        info = SCOPE_BADGES.get(scope_key)
        if info is None:
            return None
        badge = QLabel(info["label"])
        badge.setStyleSheet(
            f"QLabel {{ background-color: {info['color']}; color: white; "
            f"border-radius: 3px; padding: 1px 5px; font-size: 9px; "
            f"font-weight: bold; }}"
        )
        badge.setToolTip(info["tooltip"])
        badge.setAlignment(Qt.AlignCenter)
        return badge

    # Label avec helper
    def make_label_with_helper(self, key: str):
        meta = FIELDS.get(key, {})
        text = meta.get("tag", key)
        helper = meta.get("helper", "")
        scope = meta.get("scope")

        container = QWidget()
        row = QHBoxLayout(container)
        # Indent labels under section headers to break the visual wall of
        # identical rows. Section subtitles stay flush left for hierarchy.
        row.setContentsMargins(12, 0, 0, 0)
        row.setSpacing(6)

        label = QLabel(text)
        row.addWidget(label)

        # Scope badge sits right after the label, before the helper icon, so
        # the chip reads as a noun-modifier on the field name itself.
        if scope:
            badge = self._make_scope_badge(scope)
            if badge is not None:
                row.addWidget(badge)

        if helper:
            info = HelperLabel(helper)
            info.setFixedSize(14, 14)
            info.setAlignment(Qt.AlignCenter)
            # Wrap the small "i" in a larger hit area to meet HIG cliquable
            # target size (28×28), while keeping the visible icon at 14×14.
            info_hit = QWidget()
            info_hit.setFixedSize(28, 28)
            hit_layout = QHBoxLayout(info_hit)
            hit_layout.setContentsMargins(0, 0, 0, 0)
            hit_layout.setSpacing(0)
            hit_layout.addWidget(info, alignment=Qt.AlignCenter)
            row.addWidget(info_hit)

        row.addStretch(1)
        return container


    # --- Formulaire ---
    def build_form(self):
        self.inputs.clear()
        self.tabs.clear()
        # Per-build tracking for conditional visibility + multi-error save:
        #   field_tab_index[key]   → which tab the field lives in (for auto-switch)
        #   field_label[key]       → its label container (so we can grey it
        #                            together with the input)
        #   subtitle_groups        → (subtitle widget, [field keys below it]) so
        #                            we can grey the subtitle once every field
        #                            beneath it is inactive
        self.field_tab_index: dict[str, int] = {}
        self.field_label: dict[str, QWidget] = {}
        self.field_errors: set[str] = set()
        self.subtitle_groups: list[tuple[QWidget, list[str]]] = []
        pid = self.profile_id
        section = f"Profile_{pid}"

        for tab_index, (section_name, keys) in enumerate(SECTION_TITLES.items()):
            group = QWidget()
            form_layout = QFormLayout()
            form_layout.setVerticalSpacing(10)
            form_layout.setHorizontalSpacing(12)
            form_layout.setLabelAlignment(Qt.AlignLeft)

            # -------- Sous-titre en tête d'un onglet
            title = SUBTITLES.get((section_name, None))
            if title:
                sub = self.add_subtitle(form_layout, title)
                self.subtitle_groups.append((sub, []))
            # ---------------------------------------

            for key in keys:

                # -------- Sous-titre dans les onglets
                title = SUBTITLES.get((section_name, key))
                if title:
                    sub = self.add_subtitle(form_layout, title)
                    self.subtitle_groups.append((sub, []))

                # Track this field under the most recently added subtitle (if any).
                if self.subtitle_groups:
                    self.subtitle_groups[-1][1].append(key)

                meta = FIELDS[key]
                # ---------------------------------------

                meta = FIELDS[key]
                # _read_profile_value handles the disk-Hz → UI-kHz conversion
                # for fields that carry a unit_factor, so the widget always
                # shows the user-facing format.
                val = self._read_profile_value(pid, key)

                if meta["type"] == "text":
                    widget = QLineEdit(val)
                    if key in ["StartTime", "EndTime"]:
                        widget.setPlaceholderText("HH:MM")
                    elif key in ["StartDate", "EndDate"]:
                        widget.setPlaceholderText("JJ/MM ou --/--")
                    widget.textChanged.connect(lambda v, k=key: self.update_cache(k, v))
                    widget.textChanged.connect(lambda _v, k=key: self._live_clear_error(k))

                elif meta["type"] == "combo":
                    widget = QComboBox()
                    widget.setCursor(Qt.PointingHandCursor)
                    # choice_labels lets us show "Non/Oui" / "Relatif/Absolu" / "kHz" /
                    # "dB" in the UI while still saving the raw INI value (choices[i]).
                    # The userData carries the INI value; the display text is the label.
                    choices = meta["choices"]
                    labels = meta.get("choice_labels", choices)
                    for choice_val, label in zip(choices, labels):
                        widget.addItem(label, choice_val)
                    current = val if val in choices else meta.get("default", choices[0])
                    widget.setCurrentIndex(choices.index(current))
                    widget.currentIndexChanged.connect(
                        lambda i, k=key, c=choices: self.update_cache(k, c[i])
                    )
                    widget.currentIndexChanged.connect(
                        lambda _i, k=key: self._live_clear_error(k)
                    )

                elif meta["type"] == "int":
                    widget = QLineEdit(val)
                    widget.setValidator(QIntValidator(meta["min"], meta["max"]))
                    widget.setPlaceholderText(f"Entier {meta['min']}–{meta['max']}")
                    widget.textChanged.connect(lambda v, k=key: self.update_cache(k, v))
                    widget.textChanged.connect(lambda _v, k=key: self._live_clear_error(k))

                elif meta["type"] == "float":
                    widget = QLineEdit(val)
                    decimals = 6 if key in ("Latitude", "Longitude") else 3 # 3 décimales par défaut sauf pour les coordonnées GPS
                    validator = QDoubleValidator(meta["min"], meta["max"], decimals)
                    validator.setNotation(QDoubleValidator.StandardNotation)

                    if key in ("Latitude", "Longitude"):
                        validator.setLocale(QLocale.c())  # locale "C" => '.' comme séparateur
                        widget.setPlaceholderText("Coordonnées WGS84 avec point décimal")
                    else:
                        # Optionnel : garder la locale système pour les autres floats
                        validator.setLocale(QLocale.system())

                    widget.setValidator(validator)
                    widget.textChanged.connect(lambda v, k=key: self.update_cache(k, v))
                    widget.textChanged.connect(lambda _v, k=key: self._live_clear_error(k))

                widget.setMinimumWidth(140)
                widget.setMaximumWidth(220)
                self.inputs[key] = widget
                self.field_tab_index[key] = tab_index
                label_container = self.make_label_with_helper(key)
                self.field_label[key] = label_container
                form_layout.addRow(label_container, widget)

            group.setLayout(form_layout)

            scroll = QScrollArea()
            scroll.setWidget(group)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            self.tabs.addTab(scroll, section_name)

        # All widgets are created — now wire conditional visibility on the
        # three controller combos. Wiring AFTER populate avoids spurious
        # apply_conditional_visibility() calls during widget creation.
        for ctrl_key in ("OpMode", "SampFreqU", "ThresholdType"):
            ctrl = self.inputs.get(ctrl_key)
            if isinstance(ctrl, QComboBox):
                ctrl.currentIndexChanged.connect(self._on_controller_changed)
        self.apply_conditional_visibility()

    def _on_controller_changed(self, _index: int) -> None:
        # Slot wrapper that ignores the index arg from currentIndexChanged.
        self.apply_conditional_visibility()

    def _on_device_changed(self, _index: int) -> None:
        # Persist the device-type choice and refresh greying.
        QSettings().setValue("device_type", self.device_combo.currentData())
        self.apply_conditional_visibility()
        # If the device switch forced the firmware-coercion path (e.g. user
        # was on Heterodyne, switched to PR), tell them — silent mutation
        # of a profile value is exactly the thing the drift banner exists
        # to prevent.
        coerced = getattr(self, "_last_coerced_mode", None)
        if coerced:
            QMessageBox.information(
                self,
                "Mode incompatible avec ce type d'appareil",
                f"Le mode « {coerced} » n'est pas supporté par le matériel "
                f"sélectionné. L'enregistrement a basculé sur « Auto record ». "
                f"Vous pouvez choisir un autre mode dans le menu déroulant.",
            )
            self._last_coerced_mode = None

    def _current_value(self, key: str) -> str:
        """Read the current value of a field — widget first (truth in UI),
        then cache, then disk, then FIELDS default. Always reflects the
        *displayed* profile; for cross-profile reads (e.g. save-time
        validation of profiles not currently shown), use
        ``_read_profile_value(pid, key)`` instead.
        """
        widget = self.inputs.get(key)
        if isinstance(widget, QComboBox):
            data = widget.currentData()
            if data is not None:
                return str(data)
        elif isinstance(widget, QLineEdit):
            return widget.text().strip()
        return self._read_profile_value(self.profile_id, key)

    def _read_profile_value(self, pid: str, key: str) -> str:
        """Read a field value for an arbitrary profile, always in UI units.
        Order: cache (live edits, already in UI units) → user_parsed (disk
        snapshot, converted to UI units if the key carries a ``unit_factor``)
        → FIELDS default. ``save_profile`` uses this to validate
        Profile_3/4/5 while Profile_2 is on screen.
        """
        cached = self.cache.get(pid, {}).get(key)
        if cached is not None:
            return cached
        section = f"Profile_{pid}"
        raw_disk = self.user_parsed.get(section, {}).get(key)
        if raw_disk is not None:
            return self._ini_to_ui(key, raw_disk)
        return str(FIELDS.get(key, {}).get("default", ""))

    @staticmethod
    def _ini_to_ui(key: str, val: str) -> str:
        """Disk-format → UI-format conversion. Two transforms:

        1. ``unit_factor`` divisor (Hz → kHz on the 4 Min/Max Freq
           fields). Every non-factor field passes through unchanged at
           this step.
        2. For non-GPS floats, strip trailing-zero noise: the firmware
           writes values with ``%f`` (6 decimals), so reading "1.000000"
           back into a ``QLineEdit`` shows the user a wall of zeros that
           overstates the actual precision. ``:g`` collapses to "1",
           "0.5", "0.1" while preserving real precision when it exists.
           Lat/Lon are excluded — those DO need 6 decimals.
        """
        meta = FIELDS.get(key, {})
        factor = meta.get("unit_factor")
        if factor:
            try:
                converted = float(val) / factor
            except (ValueError, TypeError):
                return val
            return format(converted, "g")
        if meta.get("type") == "float" and key not in ("Latitude", "Longitude"):
            try:
                return format(float(val), "g")
            except (ValueError, TypeError):
                return val
        return val

    @staticmethod
    def _ui_to_ini(key: str, val: str) -> str:
        """UI-format → disk-format conversion. The inverse of
        ``_ini_to_ui``: multiplies the UI value by ``unit_factor`` and
        rounds to int. A "10.5" kHz UI input becomes "10500" on disk.
        """
        factor = FIELDS.get(key, {}).get("unit_factor")
        if not factor:
            return val
        try:
            return str(int(round(float(val) * factor)))
        except (ValueError, TypeError):
            return val

    def _compute_enabled_map(self, pid: str | None = None) -> dict[str, bool]:
        """Thin wrapper over ``visibility.compute_enabled_map``. Sources the
        four controllers (OpMode / SampFreqU / ThresholdType / device) from
        widgets when ``pid`` targets the displayed profile, from cache
        otherwise. The pure engine lives in ``app/visibility.py``.
        """
        if pid is None or pid == self.profile_id:
            op_mode = self._current_value("OpMode")
            samp_us = self._current_value("SampFreqU")
            threshold_type = self._current_value("ThresholdType")
        else:
            op_mode = self._read_profile_value(pid, "OpMode")
            samp_us = self._read_profile_value(pid, "SampFreqU")
            threshold_type = self._read_profile_value(pid, "ThresholdType")
        device_type = self.device_combo.currentData() if hasattr(self, "device_combo") else Device.PR
        return visibility.compute_enabled_map(op_mode, samp_us, threshold_type, device_type)

    def _refresh_opmode_combo_items(self) -> str | None:
        """Disable OpMode entries that the firmware would refuse for the
        current device. Mirrors CModeGeneric.cpp:873 (PHETER / AUDIOREC are
        AR-only) and CModeParams.cpp:1071+ (SYNCHRO is PRS-S-only). If the
        currently-selected mode becomes invalid, fall back to 'Auto record'.

        Returns the name of the mode that was coerced away (so the caller
        can surface a notice), or None if no coercion happened.
        """
        device = self.device_combo.currentData() if hasattr(self, "device_combo") else Device.PR
        opmode = self.inputs.get("OpMode")
        if not isinstance(opmode, QComboBox):
            return None
        model = opmode.model()
        for i in range(opmode.count()):
            choice_val = opmode.itemData(i)
            item = model.item(i)
            if item is not None:
                item.setEnabled(not visibility.opmode_disabled_for_device(choice_val, device))
        # If the currently-selected mode just became invalid, switch to
        # Auto record (the firmware would coerce to the same default).
        # Block signals on the fallback so we don't re-enter
        # apply_conditional_visibility recursively through the OpMode
        # currentIndexChanged → _on_controller_changed wire.
        current_item = model.item(opmode.currentIndex())
        if current_item is not None and not current_item.isEnabled():
            coerced_from = opmode.currentData()
            fallback = opmode.findData(OpMode.AUTO_RECORD)
            if fallback >= 0:
                with QSignalBlocker(opmode):
                    opmode.setCurrentIndex(fallback)
                return coerced_from
        return None

    def apply_conditional_visibility(self) -> None:
        """Grey out fields that don't apply to the current OpMode / SampFreq /
        ThresholdType / Vigie-Chiro protocol / device type. Greyed widgets
        keep their value (no reset on toggle). Subtitle headers grey out
        when all the fields below them are inactive. OpMode combo items
        invalid for the current device are also disabled."""
        # Capture any OpMode coercion (e.g. user switches device PR → no AR,
        # so Heterodyne can't stay selected). Stashed on self so the explicit
        # user action that triggered the change (_on_device_changed) can
        # surface a notice — but only that path, not the silent boot-time
        # apply where the file already had an invalid mode.
        self._last_coerced_mode = self._refresh_opmode_combo_items()
        enabled = self._compute_enabled_map()
        for key, widget in self.inputs.items():
            is_on = enabled.get(key, True)
            widget.setEnabled(is_on)
            label = self.field_label.get(key)
            if label is not None:
                label.setEnabled(is_on)
        # Subtitle visibility cascade: hide a subtitle entirely when none of
        # the fields beneath it are active (vs the previous ``setEnabled``
        # which only dimmed it — an orphan dimmed subtitle with no fields
        # below is visual noise that confuses the reader). When at least
        # one field remains active, keep the subtitle visible at full
        # opacity (Qt's setEnabled cascade would handle this automatically,
        # but we're explicit so future maintainers see the intent).
        for subtitle_widget, fields in self.subtitle_groups:
            any_active = any(enabled.get(k, True) for k in fields) if fields else True
            subtitle_widget.setVisible(any_active)

        # Tab activation: disable the click and dim the label when no field
        # in that tab is active for the current mode. setTabEnabled handles
        # both behaviours (greyed text + uncliquable). If the currently-shown
        # tab is the one that just got disabled, switch to the first active
        # one so the user isn't stranded on a blank-looking view.
        tab_active = {i: False for i in range(self.tabs.count())}
        for key, is_on in enabled.items():
            tab_idx = self.field_tab_index.get(key)
            if tab_idx is None:
                continue
            if is_on:
                tab_active[tab_idx] = True
        for tab_idx, has_active in tab_active.items():
            self.tabs.setTabEnabled(tab_idx, has_active)
        if not self.tabs.isTabEnabled(self.tabs.currentIndex()):
            for i in range(self.tabs.count()):
                if self.tabs.isTabEnabled(i):
                    self.tabs.setCurrentIndex(i)
                    break

    def change_profile(self, label):
        self.sync_widgets_to_cache()
        # Preserve the active tab across profile switches: the user is
        # usually comparing the same parameter across profiles.
        prev_tab = self.tabs.currentIndex()
        self.profile_id = PROFILE_LABELS[label]
        self.build_form()
        if 0 <= prev_tab < self.tabs.count() and self.tabs.isTabEnabled(prev_tab):
            self.tabs.setCurrentIndex(prev_tab)

    # --- Sauvegarde ---
    def select_output_dir(self):
        dir_ = QFileDialog.getExistingDirectory(self, "Choisir un dossier")
        if dir_:
            self.out_dir = Path(dir_)
            resolved = str(self.out_dir.resolve())
            self.out_dir_label.setText(resolved)
            self.out_dir_label.setToolTip(resolved)

    def _validate_and_normalize(self, key: str, raw: str) -> tuple[str | None, str | None]:
        """Delegate to ``validation.validate_and_normalize`` (pure, Qt-free).
        Kept as an instance method for call-site stability."""
        return validation.validate_and_normalize(key, raw)

    def _validate_cross_field(self, enabled: dict[str, bool], pid: str | None = None) -> list[tuple[str, str]]:
        """Build the per-profile values dict and delegate to
        ``validation.validate_cross_field``. The materialised dict only
        carries the keys the cross-field engine actually reads.
        """
        if pid is None or pid == self.profile_id:
            values = {k: self._current_value(k) for k in _CROSS_FIELD_KEYS}
        else:
            values = {k: self._read_profile_value(pid, k) for k in _CROSS_FIELD_KEYS}
        return validation.validate_cross_field(values, enabled)

    def _set_field_error(self, key: str, has_error: bool, message: str | None = None) -> None:
        """Apply / remove a red border on a field. QLineEdit gets a clean
        border; QComboBox styling is light to avoid breaking the native
        macOS drop-down arrow. When applying an error, the message (if
        provided) is also set as the widget's tooltip so the user can see
        the rule recap after dismissing the validation dialog."""
        widget = self.inputs.get(key)
        if widget is None:
            return
        if has_error:
            # 2 px border so the visual reads clearly on Retina; padding is
            # nudged to keep the field height stable.
            widget.setStyleSheet(
                f"QLineEdit {{ border: 2px solid {AppColors.ERROR}; padding: 3px 7px; }} "
                f"QComboBox {{ border: 2px solid {AppColors.ERROR}; }}"
            )
            if message is not None:
                widget.setToolTip(message)
            self.field_errors.add(key)
        else:
            widget.setStyleSheet("")
            widget.setToolTip("")
            self.field_errors.discard(key)

    def _clear_field_errors(self) -> None:
        for key in list(self.field_errors):
            self._set_field_error(key, False)

    def _live_clear_error(self, key: str) -> None:
        """Wired on every input widget. Re-runs single-field validation as the
        user types/picks; clears the red border + error tooltip the moment
        the value becomes valid. No-op when the field isn't currently flagged
        (avoids running the validator on every keystroke for fields that were
        never erroneous in the first place).
        """
        if key not in self.field_errors:
            return
        raw = self._current_value(key)
        _, err = self._validate_and_normalize(key, raw)
        if err is None:
            self._set_field_error(key, False)

    def _collect_overrides(self) -> dict[str, dict[str, str]]:
        """Build the {section: {key: value}} overrides dict from the user file
        plus the current UI cache. The cache takes precedence over disk values,
        so unedited fields keep their on-disk value (or template default if
        absent from disk). Cache values are in UI units; ``_ui_to_ini``
        translates them back to the disk format before merging (so the 4
        frequency fields land as Hz integers in the output INI even though
        the user typed kHz in the form).
        """
        overrides: dict[str, dict[str, str]] = {}
        # [Common] passed through unchanged (the app doesn't edit it).
        if "Common" in self.user_parsed:
            overrides["Common"] = dict(self.user_parsed["Common"])
        # Profile_1 is read-only firmware-side ("always Beginner"); preserve as-is.
        if "Profile_1" in self.user_parsed:
            overrides["Profile_1"] = dict(self.user_parsed["Profile_1"])
        # Profile_2..5: layer cache on top of disk values, converting back to
        # disk units on the way out.
        for pid in PROFILE_LABELS.values():
            section = f"Profile_{pid}"
            merged = dict(self.user_parsed.get(section, {}))
            for k, v in self.cache.get(pid, {}).items():
                merged[k] = self._ui_to_ini(k, v)
            overrides[section] = merged
        return overrides

    def save_profile(self):
        self.sync_widgets_to_cache()

        # Wipe any leftover error borders from the previous attempt.
        self._clear_field_errors()

        # Errors are collected across ALL 4 editable profiles, not just the
        # one currently displayed. Without this, a user who edits Profile_3,
        # switches back to Profile_2, and saves would write whatever invalid
        # state Profile_3 was left in — silently, since validation only ran
        # on the visible profile. (cf. lead-engineer review C1.)
        all_errors: list[tuple[str, str, str]] = []  # (pid, key, human message)
        enabled_by_pid: dict[str, dict[str, bool]] = {}

        for pid in PROFILE_LABELS.values():
            section = f"Profile_{pid}"
            # Each profile gets its own enabled map: a field greyed in
            # Profile_2 (because its OpMode != Heterodyne) may be active in
            # Profile_3 (which IS Heterodyne). _compute_enabled_map(pid)
            # reads that profile's controllers from cache, not widgets.
            enabled = self._compute_enabled_map(pid)
            enabled_by_pid[pid] = enabled

            # 1. Per-field validation. Greyed-out fields are still validated
            # so we never write garbage that the firmware would silently
            # reject — but their errors are NOT surfaced (the field isn't
            # relevant in this profile's current mode). Invalid greyed
            # values are silently coerced to the firmware default.
            for key, meta in FIELDS.items():
                # Reads in UI units; ``_validate_and_normalize`` checks
                # against the FIELDS min/max which are also in UI units.
                raw = self._read_profile_value(pid, key)
                normalized, err = self._validate_and_normalize(key, raw)
                is_active = enabled.get(key, True)
                if err is not None:
                    if is_active:
                        all_errors.append((pid, key, err))
                    else:
                        self.cache.setdefault(pid, {})[key] = str(
                            meta.get("default", meta.get("min", ""))
                        )
                else:
                    self.cache.setdefault(pid, {})[key] = normalized

            # 2. Cross-field constraints (ordering, Nyquist) for this profile.
            for key, msg in self._validate_cross_field(enabled, pid):
                all_errors.append((pid, key, msg))

        # 3. Cluster-wide check (C7): on PRS-S in Synchro mode, the cluster
        # needs exactly one Master (MasterSlave=0). Delegated to
        # ``validation.validate_master_slave_collision``.
        device_type = self.device_combo.currentData() if hasattr(self, "device_combo") else Device.PR
        profiles_values = {
            pid: {
                "OpMode": self._read_profile_value(pid, "OpMode"),
                "MasterSlave": self._read_profile_value(pid, "MasterSlave"),
            }
            for pid in PROFILE_LABELS.values()
        }
        all_errors.extend(validation.validate_master_slave_collision(profiles_values, device_type))

        if all_errors:
            # If errors live on a profile that isn't currently shown, switch
            # to that profile first so the highlights/focus land somewhere
            # visible. Group errors by profile for the summary dialog.
            first_pid = all_errors[0][0]
            if first_pid != self.profile_id:
                label = next(
                    (lbl for lbl, p in PROFILE_LABELS.items() if p == first_pid),
                    None,
                )
                if label is not None:
                    # Update the combo (which fires change_profile → build_form).
                    self.profile_combo.setCurrentText(label)

            # Highlight every faulty field on the currently-displayed profile;
            # other profiles' errors live in the dialog only (no widget to
            # paint), but switching to them will rebuild the form and they
            # can re-trigger save to see them locally.
            for pid, key, msg in all_errors:
                if pid == self.profile_id:
                    self._set_field_error(key, True, msg)
            first_visible = next(
                ((k, m) for p, k, m in all_errors if p == self.profile_id),
                None,
            )
            if first_visible is not None:
                k, _ = first_visible
                tab_idx = self.field_tab_index.get(k)
                if tab_idx is not None:
                    self.tabs.setCurrentIndex(tab_idx)
                widget = self.inputs.get(k)
                if widget is not None:
                    widget.setFocus()

            # Group lines by profile so the user reads them as 4 sections
            # max ("Profile 2 :", "Profile 3 :", …) instead of a flat list.
            pid_to_label = {v: k for k, v in PROFILE_LABELS.items()}
            grouped: dict[str, list[str]] = {}
            for pid, key, msg in all_errors:
                grouped.setdefault(pid, []).append(
                    f"  • {FIELDS.get(key, {}).get('tag', key)} : {msg}"
                )
            sections_out: list[str] = []
            for pid in PROFILE_LABELS.values():
                if pid not in grouped:
                    continue
                sections_out.append(f"{pid_to_label[pid]} :")
                sections_out.extend(grouped[pid])
                sections_out.append("")
            QMessageBox.warning(
                self,
                "Erreurs de validation",
                "Veuillez corriger les paramètres suivants :\n\n"
                + "\n".join(sections_out).strip(),
            )
            return

        # Render the output file from the canonical template, injecting the
        # validated values. This guarantees the output is always complete and
        # firmware-aligned, regardless of what was missing in the input.
        # Strip any path component from the user-typed name: ``Path("dir") /
        # "/abs"`` returns ``/abs`` (Path semantics), so an absolute path or a
        # "../escape" would let the save write anywhere on disk. We force a
        # bare filename under out_dir, and add the .ini extension if missing.
        raw_name = self.out_name_edit.text().strip() or "Profiles_custom.ini"
        bare = Path(raw_name).name or "Profiles_custom.ini"
        if not bare.lower().endswith(".ini"):
            bare += ".ini"
        self.out_name = bare
        out_path = self.out_dir / self.out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        save_with_template(self._collect_overrides(), out_path)
        # A successful save is enough to consider the user past the
        # onboarding stage even if they haven't loaded a file yet.
        QSettings().setValue("has_opened_file", True)
        self._refresh_onboarding_banner()
        QMessageBox.information(self, "Succès", f"Profil sauvegardé dans {out_path}")
