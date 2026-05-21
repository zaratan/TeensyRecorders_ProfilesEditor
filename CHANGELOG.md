# 📜 Changelog - TeensyRecorders Profiles Editor

Toutes les modifications notables du projet sont documentées ici.

## [Unreleased]

### Ajouté
- **Bouton « Ouvrir un fichier… »** pour charger un `Profiles.ini` existant (auparavant l'app n'ouvrait que le template embarqué). Au chargement, le cache d'édition est vidé, la bannière d'info des dérives schéma est recalculée et le formulaire est reconstruit. Le chemin du fichier source est affiché sous l'en-tête.
- **Pipeline « template canonique »** pour la sauvegarde : au lieu de modifier le fichier `.ini` d'entrée ligne par ligne (silencieusement bloqué si la clé est absente), l'app régénère désormais le fichier de sortie à partir du `initial_profile/Profiles.ini` embarqué en y injectant les valeurs courantes. Effet : le fichier produit est toujours **complet** et **aligné firmware**, même quand l'entrée provient d'un firmware plus ancien.
- **Bannière d'information au chargement** : si le `.ini` chargé contient des clés inconnues du firmware actuel ou en manque, une bannière non bloquante apparaît sous le sélecteur de profil, avec un détail cliquable et un bouton pour la masquer pour la session. Plus de paramètre silencieusement perdu.
- **Migration automatique d'alias hérités** : un fichier contenant `HeterSelectiveFilter=N` est lu sous son nom canonique `Pre-HeterSelectiveFilter`, et ré-écrit ainsi à la sauvegarde (cf. bug firmware référencé en interne).
- **Domaine `Profile`** (`app/profile.py`) : nouveau dataclass minimal qui prépare l'introduction de la validation cross-field (Nyquist, `min < max`) en phase suivante.
- **6 paramètres valides** précédemment absents de l'UI alors que le firmware les lit/écrit : `MasterSlave` (rôle dans un cluster PRS-S), `TopAudioFreq` / `TopDuration` / `TopPeriod` (top synchro pour PRS-S Maître), `AffRLPerm` (verrou d'affichage RhinoLogger), `BatcorderMode` (nommage compatible Batcorder ecoObs — paramètre auparavant commenté dans `config.py`).
- **Libellés combos lisibles** : nouveau champ optionnel `choice_labels` dans `FIELDS` qui découple la valeur INI du libellé affiché. Appliqué à 14 combos `0/1` (présentés en **Non/Oui**), `ThresholdType` (**Relatif/Absolu**), `HeterodyneMode` (**Manuel/Auto**), `StereoMode` (**Stéréo/Mono droit/Mono gauche**), `LEDSynchro` (libellés FR explicites), suffixe « kHz » sur `SampFreqU`/`SampFreqA`, suffixe « dB » sur `NumericGain`, « éch. » sur `TopDuration`. La valeur écrite dans le `.ini` reste rigoureusement la même.

### Corrigé
- **Unités des durées d'événement** : `MinDuration` et `MaxDuration` étaient étiquetés en millisecondes alors que le firmware les lit en secondes (`DecodeInt` 1-99 s / 1-999 s). Saisir « 30 ms » pour une durée d'enregistrement produisait en réalité 30 s côté appareil.
- **Type du champ `PowerBank`** : exposé comme entier 0–255 (défaut 255), alors que le firmware utilise `DecodeBool` (strict 0/1). Toute autre valeur — y compris 255 — était silencieusement réinterprétée comme 0. Désormais combo `0`/`1`, défaut `0` (recommandation `ManuelTR.pdf §8.32`).
- **Modèle de microphone** : la chaîne `ICS40730` exposée par l'app n'existe pas dans la liste `sMTValues` du firmware (`SPU0410`, `ICS43730`, `FG23329`). Toute sauvegarde retombait sur le défaut firmware. Corrigé : `ICS43730`.
- **Asymétrie firmware `HeterSelectiveFilter` / `Pre-HeterSelectiveFilter`** : le firmware *écrit* la clé sans préfixe mais la *lit* avec le préfixe `Pre-`. Les valeurs écrites par l'app étaient ignorées au reboot. L'app utilise désormais le nom lisible par le firmware.
- **Bornes `RecTime` / `WaitTime`** : alignées sur le firmware (`RecTime` max 12 h, `WaitTime` max 24 h) au lieu d'un max trompeur à 3600 s.
- **Valeurs par défaut désalignées** : `AbsoluteThreshold` (-80 dB), `HeterLevel` (0.1), `NumericGain` (12 dB), `TemperaturePeriod` (60 s) maintenant alignées sur les défauts firmware.
- **Code mort** : suppression du bloc de validation `StartDate`/`EndDate` dans `build_form` (inatteignable car branché après le test `meta["type"] == "text"`). La validation regex `JJ/MM` est désormais effectivement appliquée au moment de la sauvegarde.

### Supprimé
- 4 paramètres exposés dans l'UI mais inconnus du firmware (silencieusement perdus à la sauvegarde) : `MaxFileLength`, `MinLevel`, `PreTrigger`, `THSensorEnable`. Aucune trace dans `ImportProfiles` / `ExportProfiles` du firmware.

### Interne
- Template `initial_profile/Profiles.ini` réparé : `PowerBank=255` → `0` ; `HeterSelectiveFilter` → `Pre-HeterSelectiveFilter` dans les 5 sections.
- Ajout d'un script `tests/test_schema_sync.py` (sans dépendance externe) qui vérifie que toutes les clés de `FIELDS` sont présentes dans toutes les sections `[Profile_N]` du template, et que les clés héritées d'un firmware ancien (`HeterSelectiveFilter` sans préfixe) ne réapparaissent pas.

---

## [0.6.1] - 2026-05-19
### Changé
- **Nom du bundle macOS** : `TeensyProfilesEditor.app` → `TeensyRecorders Profiles Editor.app`. Le nom complet (avec espaces) est désormais affiché par Finder et Spotlight, sans avoir besoin de l'override `CFBundleDisplayName`. Le workflow `release.yml` a été mis à jour en conséquence ; le nom des artefacts zip et du `.exe` Windows reste inchangé.

---

## [0.6.0] - 2026-05-18
### Ajouté
- **Dialog « À propos »** accessible via un bouton `?` en haut à droite (logo, version, description, lien doc, crédit).
- Curseur pointer (`Qt.PointingHandCursor`) sur tous les éléments cliquables : onglets (via une sous-classe `ClickableTabBar`), combos, boutons, icônes d'aide.
- Indentation des champs (12px) sous chaque sous-titre de section pour mieux délimiter visuellement les groupes.

### Changé
- **Refonte UX/UI complète** :
  - En-tête compact (titre + bouton `?`) à la place du bloc logo + description + lien qui occupait tout le haut de la fenêtre.
  - Sous-titres de section en small-caps gris (`#9a9a9a`, `letter-spacing: 0.5px`) avec séparateur fin, à la place des `<h3>` en gras.
  - Alignement des labels de formulaire à gauche, une seule colonne label/input cohérente.
  - Icône d'aide `i` discrète par défaut, surlignée en bleu au survol. Zone cliquable élargie à 28×28px.
  - `QLineEdit` paddés à `4px 8px` ; `QComboBox` natif macOS préservé (flèche système), seul le popup est restylé.
  - Espacement vertical des formulaires passé à 10px ; largeurs d'input bornées à 140–220px.
- Chaque onglet est désormais wrappé dans un `QScrollArea` ; le `QTabWidget` absorbe tout l'espace vertical disponible.
- Fenêtre redimensionnable librement (largeur max non plus plafonnée à 1000px) ; minimums passés à 420×500px.
- Dossier de sortie par défaut : `~/Documents` (résolu via `QStandardPaths.DocumentsLocation`, cross-platform).

### Corrigé
- **Version affichée dans le bundle** : `0.0.0+unknown` → version réelle. Un fichier `app/_version.py` est désormais généré par le `.spec` PyInstaller à partir de `pyproject.toml`. En dev, fallback sur `importlib.metadata`.
- **Dossier de sortie en bundle macOS** : auparavant `/` (le `.app` est lancé depuis `/` par Finder), désormais le dossier `Documents` de l'utilisateur.
- **Dark mode macOS** : ajout de `NSRequiresAquaSystemAppearance: False` dans l'`Info.plist` pour que le bundle hérite correctement de l'apparence système.

---

## [0.5.0] - 2026-05-18
### Ajouté
- **Distribution macOS** : builds `.app` signés Apple Developer ID et notarisés, en versions Apple Silicon (`arm64`) et Intel (`x86_64`). Téléchargement → double-clic, sans warning Gatekeeper.
- **CI GitHub Actions** : workflow `release.yml` qui produit et publie automatiquement les binaires Windows + macOS sur la page Releases à chaque tag `v*`.
- `pyproject.toml` (gestion via [uv](https://docs.astral.sh/uv/)), `TeensyProfilesEditor.spec` (PyInstaller cross-platform), `entitlements.plist`, `launcher.py`.

### Changé
- Migration `pip + requirements.txt` → `uv + pyproject.toml`.
- `app/` est maintenant un vrai package Python (ajout de `__init__.py`, imports relatifs). Plus besoin de `PYTHONPATH=app`.
- Lancement en dev : `uv run dev` (au lieu de `PYTHONPATH=app python app/main.py`).
- Version de l'app lue dynamiquement depuis `pyproject.toml` via `importlib.metadata` (plus de constante hardcodée dans `config.py`).
- Le binaire Windows n'est plus commité dans `dist/` : il est produit par la CI et publié sur GitHub Releases.

### Supprimé
- `compiler/compiler.py` (remplacé par `TeensyProfilesEditor.spec`).
- `requirements.txt` (remplacé par `pyproject.toml`).
- `dist/TeensyProfilesEditor.exe` retiré du tracking git (toujours dans l'historique).

---

## [0.4] - 2026-01-22
### Ajouté
- Prise en charge complète des nouveaux paramètres introduits dans la version 1.03 :
  - **Fenêtre calendaire** : `StartDate`, `EndDate`
  - **Calcul solaire automatique** : `AutoStartStop`, `Latitude`, `Longitude`, `TUOffset`, `StartStopOffset`
  - **Gestion des fichiers** : `ZCFile`
  - **Alimentation** : `PowerBank`
- Support explicite des coordonnées GPS avec saisie décimale au format point (`.`), indépendant de la locale système.
- Chaque paramètre a maintenant une petite icone "information" qui donne une description brève du paramètre.

### Changé
- Amélioration de la gestion des placeholders (horaires, valeurs numériques).
- Les paramètres ont maintenant des noms clairs et compréhensibles
- Les paramètres ont été réorganisés sous formes de sous-groupes plus clairs

## Corrigé
- Quelques paramètres avaient un ordre incohérent.

---

## [0.3] - 2025-09-25
### Ajouté
- Support des champs numériques décimaux (float) avec validation (min, max, step).
- Ajout d’un onglet Hétérodyne dédié avec tous les paramètres associés (HeterodyneMode, AutoRecHeter, RefreshGraphe, etc.).
- Nouveaux paramètres pris en charge dans config.py :
  - **Horaires** : `RecTime`, `WaitTime`
  - **Audio** : `SampFreqA`, `LowpassFilter`, `HighpassFilter`, `fHighpassFilter`, `Exp10`
  - **Fréquences** : `MinFreqA`, `MaxFreqA`, `MinDuration`, `MaxDuration`, `ThresholdType`, `RelativeThreshold`, `AbsoluteThreshold`, `NbDetect`
  - **Capteurs** : `TemperaturePeriod`, `ContMesTemp`, `SaveNoise`
  - **Hétérodyne** : tous les champs spécifiques (10 paramètres)
- Validation et affichage améliorés pour tous les champs nouvellement ajoutés.

### Changé
- Réorganisation de config.py :
  - Conservation des sections de base (Profil, Horaires, Audio, Fichiers, Fréquences, Capteurs).
  - Ajout d’une seule section supplémentaire : Hétérodyne.
- Amélioration de la gestion des placeholders (horaires, valeurs numériques).

## Corrigé
- Les onglets très chargés ne débordent plus de la fenêtre grâce au QScrollArea.
- Meilleure robustesse lors de la validation des floats et des bornes numériques.
- Correction d’un problème mineur où certains champs affichaient une valeur vide au lieu de la valeur par défaut.

---

## [0.2] - 2025-09-24
### Changé
- Migration complète de l'interface graphique **DearPyGui → PySide6 (Qt)**.
- Nouvelle organisation du projet :
  - `app/main.py` : point d’entrée
  - `app/ui_editor.py` : interface Qt
  - `app/ini_utils.py` : utilitaires INI
  - `app/config.py` : définitions des champs et sections
- Ajout d’un en-tête avec logo, titre, description et lien cliquable vers la documentation.
- Ajout d’un séparateur sous l’entête et d’un footer `(c) Alexandre LANGLAIS - 2025 - v0.2`.
- Largeur et hauteur de fenêtre désormais bornées (300–1000px).
- Nouveau système de cache pour conserver les modifications entre onglets/profils avant sauvegarde.
- Sélection du dossier de sortie + prévisualisation du chemin choisi.
- Possibilité de renommer le fichier de sortie `.ini` avant sauvegarde.

### Corrigé
- Problèmes d’imports relatifs lors de la compilation PyInstaller → passage aux imports absolus et ajout de `resource_path` pour gérer les ressources embarquées.
- Validation des champs `StartTime` et `EndTime` au format `HH:MM`.
- Sauvegarde plus robuste : respect des bornes min/max et valeurs par défaut cohérentes.

---

## [0.1] - 2025-07-01
### Ajouté
- Première version POC fonctionnelle avec **DearPyGui**.
- Édition et validation des profils 2 à 5.
- Sauvegarde dans un fichier `.ini` prêt à être chargé sur un TeensyRecorders.
- Compilation standalone Windows avec PyInstaller.
