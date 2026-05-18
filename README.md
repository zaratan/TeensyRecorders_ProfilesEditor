<p align="center">
  <img src="img/logo_PR.png" alt="Logo" width="100"/>
</p>

<h1 align="center">TeensyRecorders Profiles Editor</h1>
<p align="center">
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  </a>
  <a href="https://pyinstaller.org/">
    <img src="https://img.shields.io/badge/Build-PyInstaller-green" alt="PyInstaller">
  </a>
  <a href="https://github.com/zaratan/TeensyRecorders_ProfilesEditor/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-lightgrey" alt="License">
  </a>
  <a href="https://github.com/zaratan/TeensyRecorders_ProfilesEditor/releases">
    <img src="https://img.shields.io/badge/Release-v0.5.0-orange" alt="Release">
  </a>
</p>

> Ce dépôt est un fork de [a-langlais/TeensyRecorders_ProfilesEditor](https://github.com/a-langlais/TeensyRecorders_ProfilesEditor) (projet original par [Alexandre Langlais](https://github.com/a-langlais)). Le fork ajoute la distribution macOS (`.app` signé/notarisé) et la CI GitHub Actions.

Un petit utilitaire graphique en **Python + PySide6 (Qt)** pour éditer et sauvegarder facilement les fichiers `Profiles.ini` utilisés par les enregistreurs [TeensyRecorders](https://framagit.org/PiBatRecorderPojects/TeensyRecorders).<br>
Les binaires Windows et macOS sont disponibles sur la [page des Releases GitHub de ce fork](https://github.com/zaratan/TeensyRecorders_ProfilesEditor/releases).<br>

Par défaut, les TeensyRecorders utilisent un fichier `Profiles.ini` statique composé de 5 profils, dont le premier n'est pas éditable par mesure de sécurité.<br>
Le projet est pensé pour fonctionner aussi bien en **mode script** qu’en **standalone compilé**.<br>

<p align="center">
    <img src="img/screen.gif" alt="Interface du programme" />
</p>

---

## ✨ Fonctionnalités

- Édition des **profils 2 à 5** (le profil 1 reste réservé au firmware)
- Validation automatique :
  - `ProfileName` → ≤ 11 caractères, alphanumérique, `_` et `-` autorisés
  - `WavPrefix` → ≤ 5 caractères
  - `StartTime` / `EndTime` → format `HH:MM`
  - `MaxFileLength` → 1–999 minutes (par défaut 60)
  - `MinFreqUS` / `MaxFreqUS` → cohérence des bornes
  - `MinLevel` → 0–100 dB (par défaut 15)
  - `PreTrigger` → 0–10
  - `THSensorEnable` et `GPSenable` → 0 ou 1
- Sélection du **dossier de sortie**
- Choix du **nom du fichier de sortie** (par défaut `Profiles_custom.ini`)

---

## 📂 Organisation du projet

```bash
TeensyRecorders_ProfilesEditor/
├── app/                          # Package Python de l'application
│   ├── __init__.py
│   ├── main.py                   # Point d'entrée (fonction run())
│   ├── ui_editor.py              # Interface PySide6
│   ├── ini_utils.py              # Fonctions utilitaires pour les fichiers INI
│   └── config.py                 # Champs, sections et configuration
│
├── img/                          # Ressources graphiques (logo, captures, icônes)
├── initial_profile/              # Fichier INI de référence
│
├── .github/workflows/release.yml # CI : build + signature + notarisation + release
├── launcher.py                   # Entry point PyInstaller
├── TeensyProfilesEditor.spec     # Spec PyInstaller cross-platform
├── entitlements.plist            # Entitlements signature macOS
├── pyproject.toml                # Métadonnées projet + dépendances (uv)
└── README.md
```

---

## 📦 Installation

### ⚡ Application standalone

Télécharger la dernière version depuis la [page des Releases du fork](https://github.com/zaratan/TeensyRecorders_ProfilesEditor/releases) :

- **macOS Apple Silicon** : `TeensyProfilesEditor-arm64.zip`
- **macOS Intel** : `TeensyProfilesEditor-x86_64.zip`
- **Windows** : `TeensyProfilesEditor.exe`

Sur macOS, l'application est **signée Apple Developer ID et notarisée** : il suffit de double-cliquer le `.zip` (Finder dézippe) puis l'application — pas de warning Gatekeeper, pas de manipulation terminal.

**Dernière version** : 0.5.0 - Compatible avec le firmware 1.03 des TR

Étapes pour charger les programmes :

- Une fois votre `*.ini` généré, déplacer le fichier sur la carte SD de l'appareil.
- Sur le menu principal, se déplacer sur `Modif. des profils` tout en bas
- Cliquer sur `Lect. fic. Profiles` et sélectionner le fichier généré
- Après retour au menu principal, sélectionner le profil voulu via la section `Profil`

---

### 🛠️ Mode développement

Le projet utilise [uv](https://docs.astral.sh/uv/) pour gérer l'environnement et les dépendances.

Cloner le projet :

```bash
git clone https://github.com/zaratan/TeensyRecorders_ProfilesEditor.git
cd TeensyRecorders_ProfilesEditor
```

Installer les dépendances (crée le `.venv` automatiquement) :

```bash
uv sync --dev
```

Lancer l'application :

```bash
uv run dev
```

Compiler l'application localement :

```bash
uv run pyinstaller TeensyProfilesEditor.spec
```

Le binaire produit se trouve dans `dist/` (`.app` sur macOS, `.exe` sur Windows). Pour produire une version signée + notarisée macOS, c'est le workflow CI qui s'en occupe automatiquement sur tag `v*`.

---

## 📜 Licence

Projet distribué sous licence MIT.
