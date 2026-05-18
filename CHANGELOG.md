# 📜 Changelog - TeensyRecorders Profiles Editor

Toutes les modifications notables du projet sont documentées ici.

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
