import re
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QFileDialog, QMessageBox, QFormLayout, QTabWidget, QTabBar, QFrame, QToolTip, QApplication, QScrollArea, QSizePolicy, QDialog, QToolButton
from PySide6.QtGui import QPixmap, QFont, QIntValidator, QDoubleValidator, QCursor
from PySide6.QtCore import Qt, QLocale, QTimer, QEvent, QStandardPaths

from .ini_utils import (
    detect_dropped_keys,
    detect_missing_keys,
    load_lines,
    load_template_lines,
    parse_ini,
    save_with_template,
)
from .config import FIELDS, SECTION_TITLES, PROFILE_LABELS, BUILD_VERSION, SUBTITLES


class HelperPopup(QFrame):
    def __init__(self, helper: str, source: "HelperLabel"):
        super().__init__(None, Qt.ToolTip)
        self._source = source
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setStyleSheet("""
            QFrame {
                background-color: #2b78ff;
                border-radius: 6px;
            }
            QLabel {
                color: white;
                padding: 8px 12px;
                font-size: 12px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        text = QLabel(helper, self)
        text.setWordWrap(True)
        text.setMaximumWidth(280)
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
        self.setToolTip(helper)
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
        version.setStyleSheet("color: #8a8a8a;")
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

        credit = QLabel("© Alexandre LANGLAIS — 2026")
        credit.setStyleSheet("color: #8a8a8a; font-size: 11px;")
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
        self.setMinimumWidth(420)
        self.setMinimumHeight(500)
        # Input + helper styling. Keep QComboBox itself unstyled to preserve
        # the native macOS drop-down arrow, but restyle the popup list.
        self.setStyleSheet("""
            QLineEdit {
                padding: 4px 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                padding: 4px 0;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 14px;
                min-height: 22px;
                color: #e0e0e0;
                border: none;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #2b78ff;
                color: white;
            }
            HelperLabel {
                color: #8a8a8a;
                background-color: transparent;
                border: 1px solid #5a5a5a;
                border-radius: 7px;
                font-weight: bold;
                font-size: 10px;
            }
            HelperLabel:hover {
                color: white;
                background-color: #2b78ff;
                border: 1px solid #2b78ff;
            }
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
        about_btn.setStyleSheet("""
            QToolButton {
                color: #8a8a8a;
                background-color: transparent;
                border: 1px solid #5a5a5a;
                border-radius: 14px;
                font-weight: bold;
            }
            QToolButton:hover {
                color: white;
                background-color: #2b78ff;
                border: 1px solid #2b78ff;
            }
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
        self.source_path_label = QLabel(str(self.ini_path.resolve()))
        self.source_path_label.setStyleSheet("color: gray;")
        self.source_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
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
        layout.addLayout(profile_layout)

        # Schema-drift banner slot: an empty layout that hosts the (re)built
        # banner. Keeping it as a dedicated slot lets us swap the banner on
        # every file reload without messing with insertion indices.
        self.drift_banner_slot = QVBoxLayout()
        self.drift_banner_slot.setContentsMargins(0, 0, 0, 0)
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
        self.out_dir_label.setStyleSheet("color: gray;")
        self.out_dir_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        dir_layout.addWidget(self.out_dir_label, stretch=1)
        layout.addLayout(dir_layout)

        # Sauvegarde
        save_layout = QHBoxLayout()
        save_btn = QPushButton("Sauvegarder")
        save_btn.setCursor(Qt.PointingHandCursor)
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
        footer = QLabel(f"© Alexandre LANGLAIS - 2026 - v{BUILD_VERSION}")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(footer)

        self.setLayout(layout)

    def _parse_user_file(self) -> None:
        """Re-read self.ini_path from disk and refresh drift detection."""
        self.lines = load_lines(self.ini_path)
        self.user_parsed = parse_ini(self.lines)
        self.missing_keys = detect_missing_keys(self.user_parsed, self.template_parsed)
        self.dropped_keys = detect_dropped_keys(self.user_parsed, self.template_parsed)

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
        self.ini_path = Path(path)
        self._parse_user_file()
        # New file = fresh starting point: discard pending edits.
        self.cache = {pid: {} for pid in PROFILE_LABELS.values()}
        self.source_path_label.setText(str(self.ini_path.resolve()))
        self._refresh_drift_banner()
        self.build_form()

    def _refresh_drift_banner(self) -> None:
        """Tear down the previous banner (if any) and rebuild it from the
        current missing/dropped state. Hides itself when there's nothing to
        report.
        """
        if self.drift_banner is not None:
            self.drift_banner_slot.removeWidget(self.drift_banner)
            self.drift_banner.deleteLater()
            self.drift_banner = None

        if not self.missing_keys and not self.dropped_keys:
            return

        n_missing = len(self.missing_keys)
        n_dropped = len(self.dropped_keys)
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
        summary = " — ".join(parts) + "."

        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background-color: #2b4d7a; border-radius: 4px; }"
            "QLabel { color: white; }"
        )
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(10, 6, 6, 6)
        bl.setSpacing(8)

        msg = QLabel(summary)
        msg.setWordWrap(True)
        bl.addWidget(msg, stretch=1)

        details_btn = QPushButton("Voir détails")
        details_btn.setCursor(Qt.PointingHandCursor)
        details_btn.setStyleSheet(
            "QPushButton { color: white; background: transparent; "
            "border: 1px solid #6e8fb5; border-radius: 3px; padding: 2px 8px; }"
            "QPushButton:hover { background-color: #3a6094; }"
        )
        details_btn.clicked.connect(self._show_drift_details)
        bl.addWidget(details_btn)

        dismiss_btn = QToolButton()
        dismiss_btn.setText("✕")
        dismiss_btn.setCursor(Qt.PointingHandCursor)
        dismiss_btn.setStyleSheet(
            "QToolButton { color: white; background: transparent; border: none; "
            "font-weight: bold; padding: 2px 6px; }"
            "QToolButton:hover { color: #ffd; }"
        )
        dismiss_btn.clicked.connect(banner.hide)
        bl.addWidget(dismiss_btn)

        self.drift_banner_slot.addWidget(banner)
        self.drift_banner = banner

    def _show_drift_details(self) -> None:
        lines: list[str] = []
        if self.missing_keys:
            lines.append("Initialisés aux valeurs par défaut firmware :")
            for section, key in self.missing_keys:
                lines.append(f"  • [{section}] {key}")
            lines.append("")
        if self.dropped_keys:
            lines.append("Inconnus du firmware actuel, retirés à la sauvegarde :")
            for section, key in self.dropped_keys:
                lines.append(f"  • [{section}] {key}")
        QMessageBox.information(
            self, "Différences avec le schéma firmware", "\n".join(lines)
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
        label.setStyleSheet("""
            QLabel {
                color: #9a9a9a;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
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

    # Label avec helper
    def make_label_with_helper(self, key: str):
        meta = FIELDS.get(key, {})
        text = meta.get("tag", key)
        helper = meta.get("helper", "")

        container = QWidget()
        row = QHBoxLayout(container)
        # Indent labels under section headers to break the visual wall of
        # identical rows. Section subtitles stay flush left for hierarchy.
        row.setContentsMargins(12, 0, 0, 0)
        row.setSpacing(6)

        label = QLabel(text)
        row.addWidget(label)

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
                val = self.cache[pid].get(
                    key,
                    self.user_parsed.get(section, {}).get(key, str(meta.get("default", ""))),
                )

                if meta["type"] == "text":
                    widget = QLineEdit(val)
                    if key in ["StartTime", "EndTime"]:
                        widget.setPlaceholderText("HH:MM")
                    elif key in ["StartDate", "EndDate"]:
                        widget.setPlaceholderText("JJ/MM ou --/--")
                    widget.textChanged.connect(lambda v, k=key: self.update_cache(k, v))

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

                elif meta["type"] == "int":
                    widget = QLineEdit(val)
                    widget.setValidator(QIntValidator(meta["min"], meta["max"]))
                    widget.setPlaceholderText(f"Entier {meta['min']}–{meta['max']}")
                    widget.textChanged.connect(lambda v, k=key: self.update_cache(k, v))

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

    def _current_value(self, key: str) -> str:
        """Read the current value of a field — widget first (truth in UI),
        then cache, then disk, then FIELDS default."""
        widget = self.inputs.get(key)
        if isinstance(widget, QComboBox):
            data = widget.currentData()
            if data is not None:
                return str(data)
        elif isinstance(widget, QLineEdit):
            return widget.text().strip()
        pid = self.profile_id
        cached = self.cache.get(pid, {}).get(key)
        if cached is not None:
            return cached
        section = f"Profile_{pid}"
        return self.user_parsed.get(section, {}).get(
            key, str(FIELDS.get(key, {}).get("default", ""))
        )

    def _compute_enabled_map(self) -> dict[str, bool]:
        """Decide which fields are active given the current OpMode /
        SampFreqU / ThresholdType. Fields not mentioned default to enabled.
        """
        enabled: dict[str, bool] = {k: True for k in FIELDS}
        op_mode = self._current_value("OpMode")
        samp_us = self._current_value("SampFreqU")
        threshold_type = self._current_value("ThresholdType")

        # --- OpMode-driven rules
        if op_mode != "Timed recording":
            for k in ("RecTime", "WaitTime"):
                enabled[k] = False
        if op_mode != "RhinoLogger":
            enabled["AffRLPerm"] = False
        if op_mode != "Heterodyne":
            for k in (
                "HeterodyneMode", "AutoRecHeter", "RefreshGraphe", "HeterLevel",
                "HeterWithGraph", "Pre-TriggerAuto", "Pre-TriggerHeter",
                "Pre-HeterSelectiveFilter", "HeterAGC", "HeterAutoPlay",
            ):
                enabled[k] = False
        if op_mode != "Synchro":
            for k in ("MasterSlave", "TopAudioFreq", "TopDuration",
                      "TopPeriod", "LEDSynchro"):
                enabled[k] = False

        # --- SampFreqU-driven rules. Ultrasound when SampFreq ≥ 192 kHz;
        # audio band and the float-step HP filter take over below.
        try:
            sf_khz = int(samp_us)
        except (ValueError, TypeError):
            sf_khz = 384
        if sf_khz >= 192:
            for k in ("MinFreqA", "MaxFreqA", "fHighpassFilter"):
                enabled[k] = False
        else:
            for k in ("MinFreqUS", "MaxFreqUS", "HighpassFilter"):
                enabled[k] = False

        # --- ThresholdType: relative (0) vs absolute (1)
        if threshold_type == "0":
            enabled["AbsoluteThreshold"] = False
        elif threshold_type == "1":
            enabled["RelativeThreshold"] = False

        # --- Fixed P. Proto. (PROTFIXE) is the only Vigie-Chiro protocol
        # persisted in a profile (Pédestre / Routier are coerced to
        # RECAUTO/PHETER at every cold boot, so they aren't even offered in
        # the OpMode combo). Point Fixe overrides 12 params at BeginMode
        # (cf. CModeRecorder.cpp:1367-1384) — we grey them out so the user
        # understands their profile values are ignored in that mode.
        if op_mode == "Fixed P. Proto.":
            for k in (
                "SampFreqU", "LowpassFilter", "HighpassFilter", "fHighpassFilter",
                "NumericGain", "Exp10",
                "MinFreqUS", "MaxFreqUS",
                "ThresholdType", "RelativeThreshold",
                "NbDetect",
                "MinDuration", "MaxDuration",
            ):
                enabled[k] = False

        return enabled

    def apply_conditional_visibility(self) -> None:
        """Grey out fields that don't apply to the current OpMode / SampFreq /
        ThresholdType / Vigie-Chiro protocol. Greyed widgets keep their value
        (no reset on toggle). Subtitle headers grey out when all the fields
        below them are inactive."""
        enabled = self._compute_enabled_map()
        for key, widget in self.inputs.items():
            is_on = enabled.get(key, True)
            widget.setEnabled(is_on)
            label = self.field_label.get(key)
            if label is not None:
                label.setEnabled(is_on)
        # Subtitles inherit greying when none of their fields are still active.
        for subtitle_widget, fields in self.subtitle_groups:
            any_active = any(enabled.get(k, True) for k in fields) if fields else True
            subtitle_widget.setEnabled(any_active)

    def change_profile(self, label):
        self.sync_widgets_to_cache()
        self.profile_id = PROFILE_LABELS[label]
        self.build_form()

    # --- Sauvegarde ---
    def select_output_dir(self):
        dir_ = QFileDialog.getExistingDirectory(self, "Choisir un dossier")
        if dir_:
            self.out_dir = Path(dir_)
            self.out_dir_label.setText(str(self.out_dir.resolve()))

    def _validate_and_normalize(self, key: str, raw: str) -> tuple[str | None, str | None]:
        """Validate a single value against its FIELDS spec.

        Returns (normalized_value, error_message). Exactly one of the two is
        None: a valid value returns (str, None); an invalid value returns
        (None, "humain message"). Caller decides how to surface the error
        (border, MessageBox, etc.).
        """
        meta = FIELDS[key]
        val = raw
        if meta["type"] == "text":
            if key in ("ProfileName", "WavPrefix"):
                limit = meta.get("limit")
                if limit and len(val) > limit:
                    return None, f"limité à {limit} caractères"
                if re.search(r"[^A-Za-z0-9 _-]", val):
                    return None, "contient des caractères interdits"
                return val, None
            if key in ("StartTime", "EndTime"):
                if val and not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", val):
                    return None, "format attendu HH:MM (ex: 08:30)"
                return val, None
            if key in ("StartDate", "EndDate"):
                # Accept "--/--" (no limit) or "JJ/MM" (firmware tolerates
                # impossible combos like 31/02; we don't over-validate).
                if val and val != "--/--" and not re.match(
                    r"^(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])$", val
                ):
                    return None, "format attendu JJ/MM ou --/--"
                return val, None
            return val, None

        if meta["type"] == "int":
            try:
                val_int = int(val)
            except (ValueError, TypeError):
                val_int = meta.get("default", meta["min"])
            if not (meta["min"] <= val_int <= meta["max"]):
                return None, f"hors bornes (attendu {meta['min']}–{meta['max']})"
            return str(val_int), None

        if meta["type"] == "float":
            normalized = (val or "").strip().replace(",", ".")  # accept comma input
            try:
                val_f = float(normalized)
            except (ValueError, TypeError):
                val_f = meta.get("default", meta["min"])
            if not (meta["min"] <= val_f <= meta["max"]):
                return None, f"hors bornes (attendu {meta['min']}–{meta['max']})"
            step = meta.get("step")
            if step:
                decimals = 6 if key in ("Latitude", "Longitude") else 3
                val_f = round(round((val_f - meta["min"]) / step) * step + meta["min"], decimals)
            return str(val_f), None

        # combo: stored as-is (the choice value was already extracted via userData)
        return val, None

    def _validate_cross_field(self, enabled: dict[str, bool]) -> list[tuple[str, str]]:
        """Return [(key, message), ...] for cross-field constraint violations.
        Skips checks involving greyed-out fields so the user isn't yelled at
        about a mode they're not in."""

        def as_int(k: str) -> int | None:
            try:
                return int(self._current_value(k))
            except (ValueError, TypeError):
                return None

        errors: list[tuple[str, str]] = []

        if enabled.get("MinFreqUS") and enabled.get("MaxFreqUS"):
            lo, hi = as_int("MinFreqUS"), as_int("MaxFreqUS")
            if lo is not None and hi is not None and lo >= hi:
                errors.append(("MaxFreqUS", "doit être supérieure à la Fréquence US min"))

        if enabled.get("MinFreqA") and enabled.get("MaxFreqA"):
            lo, hi = as_int("MinFreqA"), as_int("MaxFreqA")
            if lo is not None and hi is not None and lo >= hi:
                errors.append(("MaxFreqA", "doit être supérieure à la Fréquence audio min"))

        lo_d, hi_d = as_int("MinDuration"), as_int("MaxDuration")
        if lo_d is not None and hi_d is not None and lo_d > hi_d:
            errors.append(("MaxDuration", "doit être supérieure ou égale à la Durée min"))

        # Nyquist: max active frequency (Hz) must be ≤ SampFreq/2.
        # SampFreqU is stored as a kHz string ("384"). Nyquist_Hz = kHz × 500.
        samp_us = self._current_value("SampFreqU")
        try:
            nyquist = int(samp_us) * 500
        except (ValueError, TypeError):
            nyquist = None
        if nyquist is not None:
            if enabled.get("MaxFreqUS"):
                hi = as_int("MaxFreqUS")
                if hi is not None and hi > nyquist:
                    errors.append((
                        "MaxFreqUS",
                        f"dépasse la limite Nyquist ({nyquist} Hz à {samp_us} kHz)",
                    ))
            if enabled.get("MaxFreqA"):
                hi = as_int("MaxFreqA")
                if hi is not None and hi > nyquist:
                    errors.append((
                        "MaxFreqA",
                        f"dépasse la limite Nyquist ({nyquist} Hz à {samp_us} kHz)",
                    ))

        return errors

    def _set_field_error(self, key: str, has_error: bool) -> None:
        """Apply / remove a red border on a field. QLineEdit gets a clean
        border; QComboBox styling is light to avoid breaking the native
        macOS drop-down arrow."""
        widget = self.inputs.get(key)
        if widget is None:
            return
        if has_error:
            widget.setStyleSheet(
                "QLineEdit { border: 1px solid #e74c3c; padding: 4px 8px; } "
                "QComboBox { border: 1px solid #e74c3c; }"
            )
            self.field_errors.add(key)
        else:
            widget.setStyleSheet("")
            self.field_errors.discard(key)

    def _clear_field_errors(self) -> None:
        for key in list(self.field_errors):
            self._set_field_error(key, False)

    def _collect_overrides(self) -> dict[str, dict[str, str]]:
        """Build the {section: {key: value}} overrides dict from the user file
        plus the current UI cache. The cache takes precedence over disk values,
        so unedited fields keep their on-disk value (or template default if
        absent from disk).
        """
        overrides: dict[str, dict[str, str]] = {}
        # [Common] passed through unchanged (the app doesn't edit it).
        if "Common" in self.user_parsed:
            overrides["Common"] = dict(self.user_parsed["Common"])
        # Profile_1 is read-only firmware-side ("always Beginner"); preserve as-is.
        if "Profile_1" in self.user_parsed:
            overrides["Profile_1"] = dict(self.user_parsed["Profile_1"])
        # Profile_2..5: layer cache on top of disk values.
        for pid in PROFILE_LABELS.values():
            section = f"Profile_{pid}"
            merged = dict(self.user_parsed.get(section, {}))
            merged.update(self.cache.get(pid, {}))
            overrides[section] = merged
        return overrides

    def save_profile(self):
        self.sync_widgets_to_cache()
        pid = self.profile_id
        section = f"Profile_{pid}"

        # Wipe any leftover error borders from the previous attempt.
        self._clear_field_errors()

        errors: list[tuple[str, str]] = []  # (key, human message)
        enabled = self._compute_enabled_map()

        # 1. Per-field validation. Greyed-out fields skip validation: they
        # keep their existing value (no reset) and aren't a concern for the
        # current mode, so reporting their issues would just be noise.
        for key, meta in FIELDS.items():
            if not enabled.get(key, True):
                continue
            raw = self.cache[pid].get(
                key,
                self.user_parsed.get(section, {}).get(key, str(meta.get("default", ""))),
            )
            normalized, err = self._validate_and_normalize(key, raw)
            if err is not None:
                errors.append((key, err))
            else:
                self.cache[pid][key] = normalized

        # 2. Cross-field constraints (ordering, Nyquist).
        errors.extend(self._validate_cross_field(enabled))

        if errors:
            # Highlight every faulty field, switch to the tab of the first one,
            # surface a single summary dialog. The user fixes everything in
            # one pass instead of one-MessageBox-per-error.
            for key, _ in errors:
                self._set_field_error(key, True)
            first_key = errors[0][0]
            tab_idx = self.field_tab_index.get(first_key)
            if tab_idx is not None:
                self.tabs.setCurrentIndex(tab_idx)
            lines = [
                f"  • {FIELDS.get(k, {}).get('tag', k)} : {msg}"
                for k, msg in errors
            ]
            QMessageBox.warning(
                self,
                "Erreurs de validation",
                "Veuillez corriger les paramètres suivants :\n\n" + "\n".join(lines),
            )
            return

        # Render the output file from the canonical template, injecting the
        # validated values. This guarantees the output is always complete and
        # firmware-aligned, regardless of what was missing in the input.
        self.out_name = self.out_name_edit.text().strip() or "Profiles_custom.ini"
        out_path = self.out_dir / self.out_name
        save_with_template(self._collect_overrides(), out_path)
        QMessageBox.information(self, "Succès", f"Profil sauvegardé dans {out_path}")
