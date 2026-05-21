# 📜 Changelog - TeensyRecorders Profiles Editor

Toutes les modifications notables du projet sont documentées ici.

## [Unreleased]

### Corrigé (bloquants post-review 3-agents)
- **`HeterodyneMode` / `Pre-HeterSelectiveFilter` exposés à 0..3** au lieu de 0/1. Le firmware (`Const.h:715-740` : `HAM_MAX=4`, `HSF_MAX=4`) accepte 4 modes pour chacun : Manuel / Auto / Toujours manuel / Toujours auto, et NoSel / Selective / AlwaysNoSel / AlwaysSel. Un profil hérité contenant 2 ou 3 était silencieusement coercé à 0 (« Manuel » / « Non ») au save. Combos étendus + libellés FR explicites.
- **Validation par-profil** : `save_profile` validait uniquement le profil courant, alors que `_collect_overrides` émet les **4 profils** depuis leur cache. Un utilisateur qui édite Profile_3 (avec une valeur invalide), switch sur Profile_2 et save écrivait Profile_3 sans avertissement. Validation et `_compute_enabled_map` désormais paramétrés par `pid`, erreurs collectées sur les 4 profils ; auto-switch vers le 1er profil en faute ; dialogue groupé par profil. Cohérent avec l'asymétrie write/read du firmware.
- **Validation cluster PRS-S Maître/Esclave** : un avertissement bloquant est levé si plusieurs profils ont `OpMode=Synchro` ET `MasterSlave=0`. Permet d'éviter la configuration cluster invalide (deux maîtres).
- **`out_name` réduit au nom de fichier seul** : `Path("dir") / "/absolu"` retourne `/absolu` (sémantique Path) — l'utilisateur pouvait saisir un chemin absolu ou `../escape` et écrire hors du dossier de sortie choisi. Le champ est désormais réduit à `Path(name).name` avec ajout automatique de l'extension `.ini`.
- **Encoding fallback à la lecture** : `load_lines` tentait UTF-8 strict, ce qui crashait l'app sur un fichier exporté depuis un outil Windows (CP1252/Latin-1, ou BOM Notepad). Tente désormais utf-8-sig → utf-8 → latin-1. `open_ini_file` enveloppe l'erreur de parsing dans un `QMessageBox.critical` lisible et restaure le fichier précédent — plus de crash silencieux.
- **Champs vides explicitement rejetés** : un `RelativeThreshold` vidé par l'utilisateur retournait `("18", None)` (default firmware) via le `try/except`, l'utilisateur perdait visibilité sur la valeur réellement écrite. `_validate_and_normalize` lève désormais « champ requis » sur empty string pour int/float et ProfileName/WavPrefix.

### Corrigé (UX bloquants)
- **Contraste AA en Light Mode** : les hex gris (`#a0a0a0`, `#9a9a9a`, `#8a8a8a`, `#5a5a5a`) étaient calibrés dark mode uniquement et tombaient à ~2.6:1 sur fond blanc — sous-titres, footer, path label et icônes d'aide illisibles. Ajout d'un helper `_theme_colors()` qui détecte `Qt.ColorScheme.Dark` via `QApplication.styleHints()` et expose des tokens `secondary_text/subtitle/tertiary_text/border` calibrés pour AA dans les deux modes.
- **Drift banner — bouton « Voir détails » contrast 2.56:1 → 5.2:1** : bordure `#6e8fb5` (fail AA composant UI) → `#9bb5d6` sur fond `#2b4d7a`.
- **Dismiss banner par signature** : le dismiss ne survivait pas à un rechargement de fichier (banner détruite à chaque `_refresh_drift_banner`). Persisté désormais sous forme de signature `(missing_keys, dropped_keys)` dans `self._dismissed_drift_signatures`. Réouvrir un fichier avec la même dérive ne ressuscite plus la banner ; une signature différente la fait réapparaître normalement. Tooltip mis à jour : « Masquer (cette session) ». Caractère `✕` → `×` (convention macOS).
- **Banner d'onboarding au premier lancement** : à la première ouverture (avant qu'un fichier ait jamais été chargé via « Ouvrir un fichier… »), une banner violette (`#5a3a7a`) explique que l'utilisateur édite actuellement le modèle de démonstration. Disparaît dès qu'un fichier est ouvert ou qu'un save réussit (`QSettings.has_opened_file=True`).
- **Bordure rouge live-clear** : la bordure rouge + tooltip d'erreur persistaient jusqu'au prochain save même après correction. Slot `_live_clear_error(key)` connecté sur tous les `textChanged`/`currentIndexChanged` : revalide en arrière-plan et efface l'erreur dès que la valeur passe valide. Early return si la clé n'est pas dans `field_errors` (zéro coût sur les keystrokes des champs non-fautifs).

### Tests
- **`tests/smoke_test_v07.py`** (nouveau) : 8 checks end-to-end couvrant chaque bloquant post-review (C1/C2/C4/C5/C6/C7, 🔴-3, 🔴-4, B). Sandbox QSettings dans `tempdir`, mock des `QMessageBox.*` pour éviter le blocage modal en mode headless. Exécutable seul (`python tests/smoke_test_v07.py`).

---

## [0.7.0] - 2026-05-21

### Ajouté
- **Co-auteur Zaratan** dans le footer et la fenêtre « À propos ». Le projet est désormais signé « © Alexandre LANGLAIS & Zaratan — 2026 ».
- **Sélecteur « Type d'appareil »** (PR / AR / PRS / PRS-S) à côté du sélecteur de profil. Préférence **persistée entre sessions** via `QSettings` (donc indépendante du fichier ouvert). En PR, les champs AR et PRS sont grisés ; en AR, les PRS le sont ; en PRS / PRS-S, les AR le sont. Combiné avec les règles OpMode / SampFreqU / ThresholdType : un champ est grisé dès qu'**au moins une** règle l'inhibe.
- **Modes invalides du combo OpMode désactivés** selon le matériel sélectionné, miroir du firmware (`CModeGeneric.cpp:873`, `CModeParams.cpp:1071+`) : `Heterodyne` / `Audio Rec.` sont AR-only, `Synchro` est PRS-S-only. Si l'OpMode courant devient invalide après changement du type d'appareil, l'app rebascule automatiquement sur `Auto record` (comme le firmware le ferait à froid).
- **Badges de scope colorés** à côté du label de chaque champ spécifique à un matériel ou un mode : chip <span style="color:#1d8a8a">**AR**</span> (Active Recorder, 10 champs Hétérodyne), <span style="color:#c08019">**PRS**</span> (Passive Recorder Stéréo, 6 champs Stéréo/Synchro/Top), <span style="color:#7b3aa8">**RL**</span> (RhinoLogger, 1 champ). Tooltip natif sur le badge précise le scope.
- **Bouton « Sauvegarder » en action primaire** : fond bleu #2b78ff, texte blanc, padding 8×20, hover/pressed plus foncés. Le distingue clairement du bouton « Choisir dossier sortie » (secondaire).
- **Focus automatique sur le premier champ en faute** après un Save invalide, en plus du switch d'onglet et de la bordure rouge. L'utilisateur peut corriger immédiatement sans cliquer.
- **Tooltips réécrits depuis les guides chiroptérologiques officiels** (`GuideParametres-Alphabetique.md`, `GuideParametres-ParContexte.md`). Les 55 helpers fournissent désormais, pour chaque paramètre : domaine de valeurs, valeur par défaut firmware, et **repères terrain par contexte d'usage** (site venteux, site pauvre, recherche Rhinolophes, etc.). Format : prose en HTML léger, avec `<b>` sur les valeurs clés et `<br><br>` pour séparer les blocs. Largeur du popup d'aide élargie à **360 px** pour éviter le wrap trop agressif.
- **Grisage conditionnel des paramètres hors contexte** : un champ devient inactif quand son mode ne s'applique pas, sans disparaître. Règles : champs Hétérodyne, RhinoLogger, Synchro et Cadencé n'apparaissent vifs que dans leur mode respectif ; les fréquences US et le filtre passe-haut entier basculent automatiquement avec leurs équivalents audio quand la `Fréquence US` passe sous 192 kHz ; `RelativeThreshold` / `AbsoluteThreshold` s'activent selon le `Type de seuil`. Les valeurs des champs grisés sont conservées (pas de reset au switch de mode).
- **Grisage du protocole Vigie-Chiro Point Fixe** : en mode `Fixed P. Proto.`, les **13 paramètres imposés par le firmware** au début de la session (fréquence 384 kHz, bande 8-120 kHz, type de seuil relatif, seuil 16 dB, `NbDetect=1`, `MinDuration=2`/`MaxDuration=30`, filtres désactivés, gain 0 dB, expansion ×10) sont grisés pour refléter qu'ils sont en lecture seule côté appareil. Vérifié par lecture directe de `CModeRecorder.cpp:1367-1384`.
- **Grisage des sous-titres de section** : un sous-titre devient automatiquement gris dès que tous les champs qu'il regroupe sont eux-mêmes grisés. Réduction visible de la « pollution visuelle » dans les modes contraints (Vigie-Chiro, modes uniques type RhinoLogger).
- **Désactivation des onglets dont aucun champ n'est actif** dans le mode courant : l'onglet est grisé visuellement *et* non cliquable. Par exemple, « Hétérodyne » se désactive automatiquement en mode RhinoLogger / Auto record. Si l'utilisateur était sur un onglet qui vient d'être désactivé, Qt rebascule automatiquement sur le tab voisin actif (continuité visuelle).
- **Validation cross-field au moment du Save** : 4 règles bloquantes — `MinFreqUS < MaxFreqUS`, `MinFreqA < MaxFreqA`, `MinDuration ≤ MaxDuration`, et **Nyquist** (`MaxFreqUS / MaxFreqA ≤ Fréquence d'échantillonnage ÷ 2`). Les violations affichent une **bordure rouge** sur les widgets en faute, basculent l'onglet actif sur le premier champ invalide, et résument toutes les erreurs dans un seul `MessageBox` (au lieu d'un dialogue par erreur).
- **Bouton « Ouvrir un fichier… »** pour charger un `Profiles.ini` existant (auparavant l'app n'ouvrait que le template embarqué). Au chargement, le cache d'édition est vidé, la bannière d'info des dérives schéma est recalculée et le formulaire est reconstruit. Le chemin du fichier source est affiché sous l'en-tête.
- **Pipeline « template canonique »** pour la sauvegarde : au lieu de modifier le fichier `.ini` d'entrée ligne par ligne (silencieusement bloqué si la clé est absente), l'app régénère désormais le fichier de sortie à partir du `initial_profile/Profiles.ini` embarqué en y injectant les valeurs courantes. Effet : le fichier produit est toujours **complet** et **aligné firmware**, même quand l'entrée provient d'un firmware plus ancien.
- **Bannière d'information au chargement** : si le `.ini` chargé contient des clés inconnues du firmware actuel ou en manque, une bannière non bloquante apparaît sous le sélecteur de profil, avec un détail cliquable et un bouton pour la masquer pour la session. Plus de paramètre silencieusement perdu.
- **Migration automatique d'alias hérités** : un fichier contenant `HeterSelectiveFilter=N` est lu sous son nom canonique `Pre-HeterSelectiveFilter`, et ré-écrit ainsi à la sauvegarde (cf. bug firmware référencé en interne).
- **Domaine `Profile`** (`app/profile.py`) : nouveau dataclass minimal qui prépare l'introduction de la validation cross-field (Nyquist, `min < max`) en phase suivante.
- **6 paramètres valides** précédemment absents de l'UI alors que le firmware les lit/écrit : `MasterSlave` (rôle dans un cluster PRS-S), `TopAudioFreq` / `TopDuration` / `TopPeriod` (top synchro pour PRS-S Maître), `AffRLPerm` (verrou d'affichage RhinoLogger), `BatcorderMode` (nommage compatible Batcorder ecoObs — paramètre auparavant commenté dans `config.py`).
- **Libellés combos lisibles** : nouveau champ optionnel `choice_labels` dans `FIELDS` qui découple la valeur INI du libellé affiché. Appliqué à 14 combos `0/1` (présentés en **Non/Oui**), `ThresholdType` (**Relatif/Absolu**), `HeterodyneMode` (**Manuel/Auto**), `StereoMode` (**Stéréo/Mono droit/Mono gauche**), `LEDSynchro` (libellés FR explicites), suffixe « kHz » sur `SampFreqU`/`SampFreqA`, suffixe « dB » sur `NumericGain`, « éch. » sur `TopDuration`. La valeur écrite dans le `.ini` reste rigoureusement la même.

### Corrigé (suite — post-review)
- **`TUOffset` exprimé en minutes** : le firmware stocke `iTUOffset` en **minutes** dans la plage -720..720 (cf. `CModeGeneric.cpp:2472`). L'app le déclarait en heures (-12..14), ce qui faisait que toute valeur saisie était silencieusement réduite à quelques minutes côté appareil. Bornes UI alignées, label « Décalage UTC (min) », défaut 60 (= UTC+1 France hiver), template mis à jour de `TUOffset=2` à `TUOffset=60`.
- **`StartStopOffset` bornes corrigées** : firmware -60..60 minutes ; l'app autorisait -360..360.
- **`Pre-TriggerAuto` / `Pre-TriggerHeter` bornes corrigées** : firmware 0..15 / 1..15 (et `Pre-TriggerHeter` min = 1, pas 0). Defaults alignés sur firmware (1 s pour les deux).
- **`MaxFreqA` cohérence template/FIELDS** : le défaut FIELDS écrasait silencieusement la valeur du template au save. Aligné sur 20 000 Hz (limite haute audible humaine — cohérent avec le template).
- **`fHighpassFilter` défaut firmware** : 0.0 → 0.1 (cf. `CModeGeneric.cpp:2420`).
- **Récursion `_refresh_opmode_combo_items`** : `setCurrentIndex(fallback)` retriggerait `apply_conditional_visibility` à travers le signal `currentIndexChanged`. `QSignalBlocker` posé sur le combo OpMode pendant la coercion.
- **Champs grisés validés silencieusement avant écriture** : un champ caché par switch de mode contenant une valeur invalide était écrit tel quel dans le `.ini`. Désormais validé en arrière-plan et coercé au défaut firmware si hors bornes — l'utilisateur ne voit aucun message d'erreur (le champ n'étant pas pertinent dans le mode courant).
- **Coercion silencieuse de l'`OpMode`** au changement de type d'appareil → MessageBox d'information qui explique le repli vers Auto record. Plus de mutation silencieuse de la valeur du profil.
- **`LowpassFilter` label ambigu** : « Filtre passe-bas / linéaire » → **« Filtrage automatique »**. Le champ a un comportement double selon `Fréquence ultrason`, et Non/Oui ne décrivait pas correctement les deux modes.
- **Contraste AA des badges de scope** : amber PRS `#c08019` (3.4:1 sur blanc) → `#8c5d12` (~5.2:1, passe AA).
- **Bordure d'erreur 1 px → 2 px** + **tooltip par champ** avec le message d'erreur en cas de validation bloquée au save. L'utilisateur peut survoler la bordure rouge pour voir la règle violée sans ré-ouvrir le dialogue.
- **`color: gray` → `#a0a0a0`** sur les 3 labels gris (path source, dossier sortie, footer copyright) — `gray` (= `#808080`) ratait l'AA contrast sur fond macOS dark.
- **Path source affiché en chemin court (nom de fichier seul)** + tooltip plein chemin → plus de risque de débordement horizontal sur le path résolu.
- **Tab actif préservé au switch de profil** : l'utilisateur reste sur le même onglet d'un profil à l'autre (comparaison facilitée).
- **Commentaires obsolètes du template embarqué** : `"ICS40730"` (typo amont) → `"ICS43730"` (×5 sections) pour refléter la vraie valeur acceptée par `sMTValues[]`.

### Supprimé (suite)
- **`app/profile.py`** : dataclass stub jamais wiré. La validation cross-field qu'il devait centraliser a finalement atterri dans `ui_editor._validate_cross_field`. Conforme à la règle « pas de code mort après tentative non-aboutie ».
- **Import `QToolTip`** : inutilisé depuis le retrait du tooltip natif sur les icônes d'aide.

### Tests
- **`tests/test_schema_sync.py` refactor** : remplace le parsing regex de `app/config.py` par un import direct de `FIELDS`/`SCOPE_BADGES`. Ajoute deux nouvelles vérifications : typo guard sur les attributs FIELDS autorisés (`type, min, max, step, default, choices, choice_labels, tag, helper, limit, scope`), et cohérence `len(choices) == len(choice_labels)` quand les deux sont présents.
- **`tests/test_template_roundtrip.py`** (nouveau) : garde l'invariant clé de la pipeline « template canonique » — `parse_ini(template) → render_from_template(template, {}) == template`. Exerce aussi l'injection d'override (string avec quotes, int sans quote), la détection missing/dropped, et la migration de l'alias `HeterSelectiveFilter`.

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
- **Modes `Walkin. Protoc.` (Pédestre) et `Road Protocol` (Routier) retirés du combo OpMode** : le firmware les *coerce* à `Auto record` (PR) ou `Heterodyne` (AR) à chaque démarrage à froid (cf. `CModeGeneric.cpp:864-873`). Les inscrire dans un profil était silencieusement inutile. Ces deux protocoles Vigie-Chiro s'activent **manuellement depuis le menu de l'appareil**, par session, ils ne sont pas persistables.

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
