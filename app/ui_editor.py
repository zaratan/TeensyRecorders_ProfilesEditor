import re
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QFileDialog, QMessageBox, QFormLayout, QTabWidget, QTabBar, QFrame, QToolTip, QApplication, QScrollArea, QSizePolicy, QDialog, QToolButton
from PySide6.QtGui import QPixmap, QFont, QIntValidator, QDoubleValidator, QCursor
from PySide6.QtCore import Qt, QLocale, QTimer, QEvent

from .ini_utils import load_profiles, get_value, update_value, save_profiles
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

        self.ini_path = Path(ini_path)
        self.lines = load_profiles(self.ini_path)
        self.profile_id = "2"
        self.inputs = {}
        self.out_dir = Path(".")
        self.out_name = "Profiles_custom.ini"
        self.cache = {pid: {} for pid in PROFILE_LABELS.values()}

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

        # Sélecteur de profil
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel("Sélection du profil :"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(PROFILE_LABELS.keys())
        self.profile_combo.setCursor(Qt.PointingHandCursor)
        self.profile_combo.currentTextChanged.connect(self.change_profile)
        profile_layout.addWidget(self.profile_combo)
        layout.addLayout(profile_layout)

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
                self.cache[pid][key] = widget.currentText()

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
        pid = self.profile_id

        from .ini_utils import get_value
        for section_name, keys in SECTION_TITLES.items():
            group = QWidget()
            form_layout = QFormLayout()
            form_layout.setVerticalSpacing(10)
            form_layout.setHorizontalSpacing(12)
            form_layout.setLabelAlignment(Qt.AlignLeft)

            # -------- Sous-titre en tête d'un onglet
            title = SUBTITLES.get((section_name, None))
            if title:
                self.add_subtitle(form_layout, title)
            # ---------------------------------------

            for key in keys:

                # -------- Sous-titre dans les onglets
                title = SUBTITLES.get((section_name, key))
                if title:
                    self.add_subtitle(form_layout, title)

                meta = FIELDS[key]
                # ---------------------------------------

                meta = FIELDS[key]
                val = self.cache[pid].get(
                    key, get_value(self.lines, f"Profile_{pid}", key, str(meta.get("default", "")))
                )

                if meta["type"] == "text":
                    widget = QLineEdit(val)
                    if key in ["StartTime", "EndTime"]:
                        widget.setPlaceholderText("HH:MM")
                    widget.textChanged.connect(lambda v, k=key: self.update_cache(k, v))

                elif key in ["StartDate", "EndDate"]: # Autoriser "--/--" ou "jj/mm"
                    if val and val != "--/--" and not re.match(r"^(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])$", val):
                        QMessageBox.warning(self, "Erreur", f"{key} doit être au format JJ/MM ou --/--")
                        return

                elif meta["type"] == "combo":
                    widget = QComboBox()
                    widget.addItems(meta["choices"])
                    widget.setCursor(Qt.PointingHandCursor)
                    widget.setCurrentText(val if val in meta["choices"] else meta.get("default", meta["choices"][0]))
                    widget.currentTextChanged.connect(lambda v, k=key: self.update_cache(k, v))

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
                form_layout.addRow(self.make_label_with_helper(key), widget)

            group.setLayout(form_layout)

            scroll = QScrollArea()
            scroll.setWidget(group)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            self.tabs.addTab(scroll, section_name)

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

    def save_profile(self):
        self.sync_widgets_to_cache()
        section = f"Profile_{self.profile_id}"
        pid = self.profile_id

        for key, meta in FIELDS.items():
            val = self.cache[pid].get(key, get_value(self.lines, section, key, str(meta.get("default", ""))))

            if meta["type"] == "text":
                if key in ["ProfileName", "WavPrefix"]:
                    limit = meta.get("limit")
                    if limit and len(val) > limit:
                        QMessageBox.warning(self, "Erreur", f"{key} limité à {limit} caractères")
                        return
                    if re.search(r"[^A-Za-z0-9 _-]", val):
                        QMessageBox.warning(self, "Erreur", f"{key} contient des caractères interdits")
                        return
                elif key in ["StartTime", "EndTime"]:
                    if val and not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", val):
                        QMessageBox.warning(self, "Erreur", f"{key} doit être au format HH:MM (ex: 08:30)")
                        return

            elif meta["type"] == "int":
                try:
                    val_int = int(val)
                except ValueError:
                    val_int = meta.get("default", meta["min"])
                if not (meta["min"] <= val_int <= meta["max"]):
                    QMessageBox.warning(self, "Erreur", f"{key} doit être entre {meta['min']} et {meta['max']}")
                    return
                val = str(val_int)

            elif meta["type"] == "float":
                val = (val or "").strip().replace(",", ".") # On accepte les virgules dans la saisie
                try:
                    val_f = float(val)
                except ValueError:
                    val_f = meta.get("default", meta["min"])
                if not (meta["min"] <= val_f <= meta["max"]):
                    QMessageBox.warning(self, "Erreur", f"{key} doit être entre {meta['min']} et {meta['max']}")
                    return
                # arrondi si step défini
                step = meta.get("step")
                if step:
                    decimals = 6 if key in ("Latitude","Longitude") else 3
                    val_f = round(round((val_f - meta["min"]) / step) * step + meta["min"], decimals)
                val = str(val_f)

            self.lines = update_value(self.lines, section, key, val)

        self.out_name = self.out_name_edit.text().strip() or "Profiles_custom.ini"
        out_path = self.out_dir / self.out_name
        save_profiles(self.lines, out_path)
        QMessageBox.information(self, "Succès", f"Profil sauvegardé dans {out_path}")
