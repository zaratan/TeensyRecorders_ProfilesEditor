import re
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QFileDialog, QMessageBox, QFormLayout, QTabWidget, QFrame, QToolTip, QApplication
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


class ProfileEditor(QWidget):
    def __init__(self, ini_path, logo_path="img/logo_PR.png"):
        super().__init__()
        self.setWindowTitle("TeensyRecorders Profiles Editor")
        self.setMinimumWidth(300)
        self.setMaximumWidth(1000)
        self.setMinimumHeight(300)
        self.setMaximumHeight(1000)

        self.ini_path = Path(ini_path)
        self.lines = load_profiles(self.ini_path)
        self.profile_id = "2"
        self.inputs = {}
        self.out_dir = Path(".")
        self.out_name = "Profiles_custom.ini"
        self.cache = {pid: {} for pid in PROFILE_LABELS.values()}

        layout = QVBoxLayout()

        # --- En-tête ---
        header_layout = QHBoxLayout()
        logo_label = QLabel()
        pixmap = QPixmap(str(logo_path))
        if not pixmap.isNull():
            logo_label.setPixmap(pixmap.scaledToHeight(80, Qt.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignCenter)

        text_layout = QVBoxLayout()
        title = QLabel("TeensyRecorders Profiles Editor")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        desc = QLabel(
            "Outil pour éditer et sauvegarder facilement vos fichiers Profiles.ini.\n"
            "Edition des profils avec validation automatique des valeurs."
        )
        desc.setWordWrap(True)
        text_layout.addWidget(title)
        text_layout.addWidget(desc)

        link = QLabel(
            '<a href="https://framagit.org/PiBatRecorderPojects/TeensyRecorders/blob/master/Update/ManuelTR.pdf">'
            'Plus d\'infos sur la documentation des TeensyRecorders</a>'
        )
        link.setOpenExternalLinks(True)
        link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link.setStyleSheet("color: blue;")
        text_layout.addWidget(link)

        header_layout.addWidget(logo_label, stretch=1)
        header_layout.addLayout(text_layout, stretch=4)
        layout.addLayout(header_layout)

        separator_header = QFrame()
        separator_header.setFrameShape(QFrame.HLine)
        separator_header.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator_header)

        # Sélecteur de profil
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel("Sélection du profil :"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(PROFILE_LABELS.keys())
        self.profile_combo.currentTextChanged.connect(self.change_profile)
        profile_layout.addWidget(self.profile_combo)
        layout.addLayout(profile_layout)

        # Onglets
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.build_form()

        # Dossier sortie
        dir_layout = QHBoxLayout()
        browse_btn = QPushButton("Choisir dossier sortie")
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
        save_btn.clicked.connect(self.save_profile)
        save_layout.addWidget(save_btn)

        self.out_name_edit = QLineEdit(self.out_name)
        self.out_name_edit.setPlaceholderText("Nom du fichier de sortie (ex: Profiles_custom.ini)")
        save_layout.addWidget(self.out_name_edit, stretch=1)
        layout.addLayout(save_layout)

        # Footer
        layout.addStretch()
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)

        layout.addWidget(separator)
        footer = QLabel(f"© Alexandre LANGLAIS - 2026 - v{BUILD_VERSION}")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(footer)

        self.setLayout(layout)

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
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                margin-top: 12px;
                margin-bottom: 6px;
            }
        """)
        form_layout.addRow(label)

    # Label avec helper
    def make_label_with_helper(self, key: str):
        meta = FIELDS.get(key, {})
        text = meta.get("tag", key)
        helper = meta.get("helper", "")

        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        label = QLabel(text)
        row.addWidget(label)

        if helper:
            info = HelperLabel(helper)
            info.setFixedSize(16, 16)
            info.setAlignment(Qt.AlignCenter)
            info.setStyleSheet("""
                QLabel {
                    color: white;
                    background-color: #2b78ff;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 11px;
                }
            """)
            row.addWidget(info)

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

                self.inputs[key] = widget
                form_layout.addRow(self.make_label_with_helper(key), widget)

            group.setLayout(form_layout)
            self.tabs.addTab(group, section_name)

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
