from importlib.metadata import PackageNotFoundError, version as _pkg_version

# Build-time generated file (see TeensyProfilesEditor.spec) — exists in
# packaged builds, absent in dev. Dev installs read the package metadata.
try:
    from ._version import __version__ as BUILD_VERSION
except ImportError:
    try:
        BUILD_VERSION = _pkg_version("teensy-profiles-editor")
    except PackageNotFoundError:
        BUILD_VERSION = "0.0.0+unknown"


# --- Single source of truth for stable string identifiers --------------------
#
# These three classes consolidate the magic strings that used to live as
# literals scattered across ui_editor.py (OpMode names, device tokens,
# accent colours). Using class attributes — rather than enum or constants
# module — keeps lookups syntactically light (``OpMode.SYNCHRO``) and means
# they round-trip through ``FIELDS["OpMode"]["choices"]`` as plain strings.
#
# Renaming an OpMode (e.g. firmware bump renames "Heterodyne" to "HeterMode")
# now means touching ONE place; the test_schema_sync guard asserts that every
# OpMode.* and Device.* value is referenced by FIELDS so a typo here breaks
# the test instead of silently breaking a greying rule.


class OpMode:
    """Operating modes recognised by the firmware (``sOMValues[]`` in
    ``Const.h``). Values are the exact strings written to the INI file."""
    AUTO_RECORD = "Auto record"
    FIXED_PROTO = "Fixed P. Proto."
    RHINOLOGGER = "RhinoLogger"
    HETERODYNE = "Heterodyne"
    TIMED = "Timed recording"
    AUDIO_REC = "Audio Rec."
    SYNCHRO = "Synchro"


class Device:
    """Hardware variants exposed in the top-bar device selector. Mirrors the
    scope tokens in ``SCOPE_BADGES`` for the AR/PRS variants; ``PR`` is the
    baseline (no scope badge, all fields enabled by default)."""
    PR = "PR"
    AR = "AR"
    PRS = "PRS"
    PRS_S = "PRS-S"


class AppColors:
    """App-wide accent colours. Local hover/pressed shades and the dark-
    popup palette stay inline near their widget — these are the values
    that recurred in multiple stylesheets and benefit from a single name.

    The PRIMARY shade was darkened from #2b78ff (~4.0:1 on white, sub-AA
    for body text) to #1a5fd0 (~5.8:1, AA-passing) — the Save button text
    is at the AA limit on the prior shade, and we don't want the most
    important action in the UI to flunk accessibility.
    """
    PRIMARY = "#1a5fd0"                   # Save button bg, helper popup bg, combo selection, hover accent
    PRIMARY_HOVER = "#144aa0"             # Save button hover
    PRIMARY_PRESSED = "#0d3f8a"           # Save button pressed
    ERROR = "#e74c3c"                     # Validation error border + tooltip
    DRIFT_BANNER_BG = "#2b4d7a"           # Blue drift banner
    DRIFT_BANNER_BORDER = "#9bb5d6"       # Drift banner detail-button border (AA-passing)
    DRIFT_BANNER_HOVER = "#3a6094"        # Drift banner detail-button hover
    ONBOARDING_BANNER_BG = "#5a3a7a"      # Violet first-launch banner
    SCHEMA_MISMATCH_BG = "#a05a1a"        # Amber banner for firmware schema version mismatch (stronger signal than drift)


# Firmware schema version this build is aligned with. The embedded template
# at ``initial_profile/Profiles.ini`` carries the same version in its first
# comment line. Loaded user files that declare a different version trigger
# the schema-mismatch banner so the user knows the firmware on their device
# may not match what this editor expects.
FIRMWARE_SCHEMA_VERSION = "0.8"


# Scope badges shown next to fields specific to a hardware variant or a
# particular operating mode. Rendered as 16-px coloured chips by
# ui_editor.make_label_with_helper. Each field in FIELDS may carry an
# optional "scope" key (one of these tokens) — if absent, no badge.
SCOPE_BADGES = {
    "AR": {
        "color": "#1d8a8a",  # teal
        "label": "AR",
        "tooltip": "Champ utilisé uniquement par l'Active Recorder",
    },
    "PRS": {
        # Darker amber than the original #c08019 — contrast ratio with white
        # text bumped from ~3.4:1 (fails AA body text) to ~5.2:1 (passes AA).
        "color": "#8c5d12",
        "label": "PRS",
        "tooltip": "Champ utilisé sur Passive Recorder Stéréo (PRS et PRS-S)",
    },
    "PRS-S": {
        # Distinct from PRS: cluster-only features (Synchro Master role,
        # top synchro params, LED indicator). The badge advertises the
        # narrower constraint so a PRS-without-S user doesn't mistake
        # MasterSlave/TopAudioFreq for fields they can safely use.
        "color": "#a04a5a",  # darker rose, distinct from the PRS amber and the AR teal
        "label": "PRS-S",
        "tooltip": "Champ utilisé uniquement par le PRS-S en mode Synchro",
    },
    "RhinoLogger": {
        "color": "#7b3aa8",  # purple
        "label": "RL",
        "tooltip": "Champ utilisé uniquement en mode RhinoLogger",
    },
}


# FIELDS schema reference: firmware CModeGeneric.cpp ImportProfiles (~line 2349)
# and ExportProfiles (~line 1922). Every combo's "choices" must match the
# firmware enum strings verbatim; the "choice_labels" override (optional)
# decouples the INI value from the UI label so we can present "Non/Oui",
# "Relatif/Absolu", "kHz", "dB", etc. without changing what is written to
# the file. If "choice_labels" is absent, the raw choice value is shown.
#
# Helper text is rich-text (HelperPopup uses Qt.RichText). Use <b>…</b> to
# highlight defaults and key values, <br><br> for paragraph breaks. Source
# of truth for field guidance: PassiveRecorder/GuideParametres-Alphabetique.md
# and GuideParametres-ParContexte.md upstream.
#
# Declarative-attribute boundary (read this before adding new attrs)
# ─────────────────────────────────────────────────────────────────
# Attributes on a FIELD are good when they describe a property local to
# that field — `type`, `min/max/step`, `choices/choice_labels`, `tag`,
# `helper`, `limit`, `scope`, `unit_factor`. Each one has a single,
# unambiguous interpretation that doesn't depend on other fields.
#
# Attributes that would describe *cross-field* behaviour (e.g. a
# hypothetical `visible_when` saying "only show this field when OpMode
# is X and SampFreqU >= Y") do NOT belong here. We considered such an
# attribute, and rejected it: encoding boolean expressions in a dict
# means inventing a mini-DSL, then writing its interpreter, then writing
# its linter / typechecker / test framework. That's the inner-platform
# anti-pattern.
#
# Cross-field visibility belongs in ``app/visibility.py`` as a list of
# (predicate, fields_to_disable) tuples — predicates being plain Python
# lambdas reading a context dict. That keeps the abstraction at the
# level the problem actually has (non-local Boolean logic), and the
# rules stay trivially testable from pure Python.
#
# Rule of thumb: if a new attribute would need an interpreter to read,
# move it to ``visibility.py`` (or another impl module) instead.
FIELDS = {
    # ---- Profil ----
    "ProfileName": {"type": "text", "limit": 11, "tag": "Nom de profil",
        "helper": "Nom du profil tel qu'il apparaît dans le menu du TeensyRecorder. <b>11 caractères max</b>, alphanumériques + <code>_</code> / <code>-</code> / espace."},
    # Walkin. Protoc. (PROTPED) and Road Protocol (PROTROUT) are intentionally
    # NOT exposed here. The firmware coerces these modes back to RECAUTO/PHETER
    # at every cold boot (cf. CModeGeneric.cpp:864-873), so persisting them in
    # a profile is silently ineffective. Both Vigie-Chiro session protocols are
    # activated manually from the device menu, per recording session.
    "OpMode": {"type": "combo", "choices": [
        OpMode.AUTO_RECORD,
        OpMode.FIXED_PROTO, OpMode.RHINOLOGGER, OpMode.HETERODYNE,
        OpMode.TIMED, OpMode.AUDIO_REC, OpMode.SYNCHRO,
    ], "default": OpMode.AUTO_RECORD, "tag": "Mode d'enregistrement",
        "helper": "Mode de fonctionnement principal au démarrage.<br><br>"
                  "• <b>Auto record</b> : enregistrement automatique sur détection acoustique.<br>"
                  "• <b>Fixed P. Proto.</b> : protocole Point Fixe Vigie-Chiro, paramètres imposés par le firmware.<br>"
                  "• <b>RhinoLogger</b> : suivi long terme par bandes (CSV journaliers, pas de WAV).<br>"
                  "• <b>Timed recording</b> : enregistrement périodique cadencé.<br>"
                  "• <b>Heterodyne</b> / <b>Audio Rec.</b> : réservés à l'Active Recorder.<br>"
                  "• <b>Synchro</b> : cluster PRS-S synchronisé LoRa."},
    "MasterSlave": {"type": "int", "min": 0, "max": 9, "step": 1, "default": 0, "tag": "Maître/Esclave", "scope": "PRS-S",
        "helper": "<b>PRS-S uniquement, mode Synchro.</b> Rôle dans un cluster synchronisé LoRa. <b>0</b> = Maître ; <b>1 à 9</b> = Esclave numéroté. Un seul Maître par cluster ; les Esclaves doivent avoir des numéros uniques."},

    # ---- Horaires ----
    "StartTime": {"type": "text", "tag": "Heure de début",
        "helper": "Heure de démarrage des enregistrements (HH:MM). Avant cette heure, l'appareil dort en veille profonde. <b>Défaut : 22:00.</b><br><br>Si Heure début = Heure fin, pas de veille (H24) — utile pour un test, désastreux pour la batterie en pose longue."},
    "EndTime": {"type": "text", "tag": "Heure de fin",
        "helper": "Heure de fin des enregistrements (HH:MM). Après cette heure, retour en veille profonde. <b>Défaut : 06:00.</b>"},
    "RecTime": {"type": "int", "min": 1, "max": 43200, "step": 10, "default": 60, "tag": "Durée d'enregistrement (s)",
        "helper": "<b>Mode Cadencé uniquement.</b> Durée d'un enregistrement WAV, en secondes. 1 s à 12 h. <b>Défaut : 60 s.</b>"},
    "WaitTime": {"type": "int", "min": 1, "max": 86400, "step": 10, "default": 540, "tag": "Temps d'attente (s)",
        "helper": "<b>Mode Cadencé uniquement.</b> Durée d'attente entre deux enregistrements, en secondes. 1 s à 24 h. <b>Défaut : 540 s</b> (9 min)."},

    # ---- Dates (fenêtre de validité) ----
    "StartDate": {"type": "text", "limit": 5, "default": "--/--", "tag": "Date de début",
        "helper": "Date de début de validité du profil (JJ/MM, sans année). Permet de programmer une pose plusieurs jours à l'avance — l'appareil dort en attendant. <b>Défaut : --/--</b> (pas de limite, commence tout de suite)."},
    "EndDate": {"type": "text", "limit": 5, "default": "--/--", "tag": "Date de fin",
        "helper": "Date de fin de validité du profil (JJ/MM, sans année). <b>Défaut : --/--</b> (pas de date de fin, jusqu'à arrêt manuel ou batterie vide)."},

    # ---- Soleil / Auto Start-Stop (calcul lever/coucher) ----
    "AutoStartStop": {"type": "combo", "choices": ["0", "1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Calcul lever/coucher",
        "helper": "Si <b>Oui</b>, l'appareil calcule automatiquement les heures de début/fin à partir des heures astronomiques de lever/coucher du soleil. Prérequis : <b>Latitude</b>, <b>Longitude</b>, <b>Fuseau UTC</b>. <b>Défaut : Non.</b>"},
    "Latitude": {"type": "float", "min": -90.0, "max": 90.0, "step": 0.000001, "default": 48.857918, "tag": "Latitude (°)",
        "helper": "Latitude WGS84 en degrés décimaux (positif = Nord, négatif = Sud). 2 décimales suffisent.<br><br>Astuce : <b>clic long sur Google Maps mobile</b> → coordonnées dans la barre de recherche."},
    "Longitude": {"type": "float", "min": -180.0, "max": 180.0, "step": 0.000001, "default": 2.348615, "tag": "Longitude (°)",
        "helper": "Longitude WGS84 en degrés décimaux (positif = Est, négatif = Ouest)."},
    # Firmware stores TUOffset in MINUTES (-720..720), not hours. This was a
    # silent bug in the app: a user setting "2" got 2 minutes of UTC offset
    # on the device, not UTC+2. We expose minutes verbatim with examples in
    # the helper.
    "TUOffset": {"type": "int", "min": -720, "max": 720, "step": 1, "default": 60, "tag": "Décalage UTC (min)",
        "helper": "Décalage horaire entre l'heure locale et l'UTC pour le calcul soleil, <b>en minutes</b>.<br><br>"
                  "• <b>60</b> : UTC+1 (France hiver).<br>"
                  "• <b>120</b> : UTC+2 (France été).<br>"
                  "• <b>330</b> : UTC+5:30 (Inde) — la résolution à la minute permet les fuseaux décimaux."},
    "StartStopOffset": {"type": "int", "min": -60, "max": 60, "step": 1, "default": 0, "tag": "Extension nocturne (min)",
        "helper": "Décale les horaires calculés à partir du soleil, en minutes. <b>Positif</b> élargit la fenêtre (commence avant coucher, finit après lever). <b>Négatif</b> la rétrécit. <b>Défaut : 0.</b> Bornes firmware : -60 à 60."},

    # ---- Audio ----
    "SampFreqU": {"type": "combo", "choices": ["24","48","96","192","250","384","500"], "choice_labels": ["24 kHz","48 kHz","96 kHz","192 kHz","250 kHz","384 kHz","500 kHz"], "default": "384", "tag": "Fréquence ultrason",
        "helper": "Fréquence d'échantillonnage ultrason. Détermine la fréquence max enregistrable = SampFreq / 2 (Nyquist).<br><br>"
                  "• <b>384 kHz</b> : standard chiroptéro (couvre toutes espèces françaises, Petit Rhinolophe inclus à 110 kHz).<br>"
                  "• <b>250 kHz</b> : RhinoLogger long terme (CPU 48 MHz, autonomie ×2).<br>"
                  "• <b>500 kHz</b> : marge espèces exotiques.<br>"
                  "• <b>≤ 192 kHz</b> : rate les Rhinolophes."},
    # SampFreqA caps at 96 kHz: the firmware silently coerces any value
    # ≥ 192 kHz to 48 kHz (CModeGeneric.cpp:826-827, `if uiFeA >= FE192KHZ →
    # FE48KHZ`). Exposing 192 kHz here would mean offering a value the
    # firmware refuses to honour — silently corrupting the user's profile.
    "SampFreqA": {"type": "combo", "choices": ["24","48","96"], "choice_labels": ["24 kHz","48 kHz","96 kHz"], "default": "48", "tag": "Fréquence audio",
        "helper": "Fréquence d'échantillonnage en mode <b>Audio Rec.</b> (oiseaux, batraciens, bioacoustique non-ultrasonore). <b>48 kHz</b> standard. 96 kHz pour signaux haute fréquence (max accepté par le firmware en audio)."},
    "NumericGain": {"type": "combo", "choices": ["0","6","12","18","24"], "choice_labels": ["0 dB","+6 dB","+12 dB","+18 dB","+24 dB"], "default": "12", "tag": "Gain numérique",
        "helper": "Multiplie le signal numérique <b>après détection</b>, avant écriture WAV (×1 / ×2 / ×4 / ×8 / ×16). Ne change pas la sensibilité de déclenchement.<br><br>"
                  "• <b>0 dB</b> : préserve la dynamique, recommandé pour Tadarida, SonoChiro.<br>"
                  "• <b>+6 / +12 dB</b> : confort visuel sur sites pauvres.<br>"
                  "• <b>+18 / +24 dB</b> : risque de saturation irréversible sur passage proche."},
    "LowpassFilter": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Filtrage automatique",
        "helper": "Comportement double selon <b>Fréquence ultrason</b> :<br>"
                  "• <b>≤ 192 kHz</b> : filtre passe-bas anti-repliement.<br>"
                  "• <b>250 / 384 kHz</b> : linéarisation expérimentale du micro MEMS.<br>"
                  "• <b>500 kHz</b> ou sur PRS : non appliqué (CPU insuffisant).<br><br>"
                  "<b>Défaut : Non.</b> Recommandation officielle : laisser à Non sauf raison précise — sinon amplitudes non comparables à d'autres enregistreurs."},
    "HighpassFilter": {"type": "int", "min": 0, "max": 25, "default": 0, "tag": "Filtre passe-haut (kHz)",
        "helper": "Filtre passe-haut numérique 1er ordre (pente douce ~3 dB/octave). Coupe le bruit basse fréquence (vent, voiture, pluie). <b>Agit aussi sur le signal enregistré.</b> Utilisé quand SampFreq ≥ 192 kHz.<br><br>"
                  "• <b>0 kHz</b> : désactivé.<br>"
                  "• <b>8–10 kHz</b> : site rural calme.<br>"
                  "• <b>15–20 kHz</b> : site venteux / bord de route.<br>"
                  "• <b>25 kHz</b> : recherche Rhinolophes (exclut Noctules)."},
    "fHighpassFilter": {"type": "float", "min": 0.0, "max": 25.0, "step": 0.1, "default": 0.1, "tag": "Filtre passe-haut fin (kHz)",
        "helper": "Filtre passe-haut numérique, en kHz avec précision <b>0,1 kHz</b>. Coupe le bruit basse fréquence avec pas fin. Utilisé quand SampFreq < 192 kHz (mode audio)."},
    "Exp10": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "1", "tag": "Expansion de temps ×10",
        "helper": "Active l'expansion de temps ×10. <b>Modifie uniquement l'en-tête WAV</b> pour annoncer une fréquence 10× plus basse — le signal n'est <b>pas réellement</b> ralenti. Au playback dans VLC/Windows Media, le fichier se lit 10× plus lentement, donc audible à l'oreille humaine.<br><br>Kaleidoscope, Tadarida, BatExplorer détectent l'astuce automatiquement. Un script qui lit l'en-tête brut verra « 38,4 kHz » au lieu de 384 kHz. <b>Défaut : Oui.</b>"},
    "StereoMode": {"type": "combo", "choices": ["Stereo","MonoRight","MonoLeft"], "choice_labels": ["Stéréo", "Mono droit", "Mono gauche"], "default": "Stereo", "tag": "Canal d'enregistrement", "scope": "PRS",
        "helper": "<b>PRS uniquement.</b> Sur Passive Recorder Stéréo (2 micros), choisit le mode d'enregistrement. En <b>Stéréo</b>, le suffixe du fichier indique quel canal a déclenché : <code>_0_</code> = micro gauche, <code>_1_</code> = micro droit."},
    "MicrophoneType": {"type": "combo", "choices": ["SPU0410","ICS43730","FG23329"], "default": "ICS43730", "tag": "Modèle de microphone",
        "helper": "Modèle de microphone installé. Le défaut <b>ICS43730</b> couvre la plupart des cas chiroptéro. <b>SPU0410</b> et <b>FG23329</b> selon le matériel monté."},
    "TopAudioFreq": {"type": "int", "min": 1, "max": 50, "step": 1, "default": 2, "tag": "Fréquence top synchro (kHz)", "scope": "PRS-S",
        "helper": "<b>PRS-S Maître uniquement.</b> Fréquence du « top synchro » émis par le Maître aux Esclaves, enregistré dans chaque WAV pour permettre la synchronisation temporelle en post-traitement. <b>Défaut : 2 kHz.</b>"},
    "TopDuration": {"type": "combo", "choices": ["256","512","1024"], "choice_labels": ["256 éch.","512 éch.","1024 éch."], "default": "256", "tag": "Durée du top", "scope": "PRS-S",
        "helper": "<b>PRS-S Maître uniquement.</b> Durée du top audio en nombre d'échantillons. 256, 512 ou 1024."},
    "TopPeriod": {"type": "int", "min": 0, "max": 10, "step": 1, "default": 0, "tag": "Période du top", "scope": "PRS-S",
        "helper": "<b>PRS-S Maître uniquement.</b> <b>0</b> = top envoyé une seule fois au début de l'enregistrement. <b>≥ 1</b> = tops émis périodiquement pendant l'enregistrement."},

    # ---- Hétérodyne ----
    # Firmware accepts 0..3 (HAM_MAX=4 in Const.h:719): Manual / Auto /
    # AlwaysManu / AlwaysAuto. Exposing 0/1 only silently mutated profiles
    # carrying 2 or 3 to "Manual" at save time.
    "HeterodyneMode": {"type": "combo", "choices": ["0","1","2","3"],
        "choice_labels": ["Manuel", "Auto", "Toujours manuel", "Toujours auto"],
        "default": "0", "tag": "Mode hétérodyne", "scope": "AR",
        "helper": "<b>Active Recorder uniquement.</b><br><br>"
                  "• <b>Manuel</b> : c'est vous qui tournez la molette pour chercher la fréquence d'une espèce.<br>"
                  "• <b>Auto</b> : l'appareil cale automatiquement la fréquence sur le pic d'énergie détecté ; la molette permet de jouer à ±10 kHz autour.<br>"
                  "• <b>Toujours manuel</b> / <b>Toujours auto</b> : verrouille le mode et empêche la bascule manuelle depuis le menu de l'appareil."},
    "AutoRecHeter": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Auto-enregistrement hétérodyne", "scope": "AR",
        "helper": "<b>AR uniquement, mode Hétérodyne.</b> Déclenche automatiquement un enregistrement WAV depuis le mode hétérodyne quand un signal est détecté."},
    "RefreshGraphe": {"type": "float", "min": 0.2, "max": 2.0, "step": 0.2, "default": 1.0, "tag": "Rafraîchissement graphique (s)", "scope": "AR",
        "helper": "<b>AR uniquement.</b> Vitesse de défilement du graphe d'activité fréquentielle, en secondes. 0,2 à 2,0. Cosmétique, à ajuster au confort."},
    "HeterLevel": {"type": "float", "min": 0.1, "max": 0.9, "step": 0.1, "default": 0.1, "tag": "Seuil hétérodyne", "scope": "AR",
        "helper": "<b>AR uniquement.</b> Niveau audio de sortie hétérodyne. 0,1 à 0,9. À ajuster au confort selon le bruit ambiant."},
    "Pre-TriggerAuto": {"type": "int", "min": 0, "max": 15, "default": 1, "tag": "Pré-trigger auto (s)", "scope": "AR",
        "helper": "<b>Teensy 4.1 avec mémoire étendue uniquement.</b> Durée de signal pré-enregistrée avant le déclenchement automatique, en secondes (0 à 15). Évite que le 1er cri du fichier soit tronqué (le temps que l'algorithme de détection se déclenche). <b>Défaut : 1 s.</b> 3 s largement suffisant, monter à 5 s en site très actif."},
    "Pre-TriggerHeter": {"type": "int", "min": 1, "max": 15, "default": 1, "tag": "Pré-trigger hétérodyne (s)", "scope": "AR",
        "helper": "<b>Teensy 4.1 avec mémoire étendue uniquement.</b> Durée pré-enregistrée avant le déclenchement manuel en mode hétérodyne, en secondes (1 à 15). <b>Défaut : 1 s.</b>"},
    # Firmware writes "HeterSelectiveFilter" but reads "Pre-HeterSelectiveFilter"
    # (firmware bug in CModeGeneric.cpp line 2464). We align on the read-side name
    # so the value actually round-trips through the device.
    # Firmware accepts 0..3 (HSF_MAX=4 in Const.h:740): NoSel / Selective /
    # AlwaysNoSel / AlwaysSel. Same silent-mutation bug as HeterodyneMode if
    # exposed as 0/1 only.
    "Pre-HeterSelectiveFilter": {"type": "combo", "choices": ["0","1","2","3"],
        "choice_labels": ["Non", "Oui", "Toujours non", "Toujours oui"],
        "default": "0", "tag": "Filtre sélectif hétérodyne", "scope": "AR",
        "helper": "<b>AR, Teensy 4.1 uniquement.</b> Active un filtrage sélectif du signal hétérodyne pour améliorer la lisibilité dans un environnement bruyant. À tester sur le terrain.<br><br>"
                  "• <b>Non</b> / <b>Oui</b> : choix initial, ajustable depuis le menu de l'appareil.<br>"
                  "• <b>Toujours non</b> / <b>Toujours oui</b> : verrouille le mode."},
    "HeterAutoPlay": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Lecture automatique", "scope": "AR",
        "helper": "<b>AR uniquement, mode Hétérodyne.</b> Après chaque enregistrement déclenché, rejoue automatiquement la séquence en X10 sur le casque. Pratique en prospection active pour valider à l'oreille."},
    "HeterWithGraph": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "1", "tag": "Affichage graphique", "scope": "AR",
        "helper": "<b>AR uniquement, mode Hétérodyne.</b> Affiche le graphe d'activité fréquentielle sous la barre d'échelle. <b>Non</b> = remplacé par la liste des 3 derniers fichiers WAV."},
    "HeterAGC": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "AGC hétérodyne", "scope": "AR",
        "helper": "<b>AR uniquement, mode Hétérodyne.</b> Contrôle Automatique de Gain — atténue le bruit de sortie casque en présence de signaux faibles, améliore le confort d'écoute.<br><br>Inconvénients : moins sensible aux signaux faibles, cris faibles/moyens un peu moins définis, effet de pompage possible en alternance signaux forts/faibles."},

    # ---- Fichiers ----
    "WavPrefix": {"type": "text", "limit": 5, "tag": "Préfixe fichier",
        "helper": "Préfixe des noms de fichiers WAV (<b>5 caractères max</b>). Complété ensuite par le firmware avec n° de série, date, heure. <b>Défaut : PaRec.</b><br><br>Astuce multi-sites : coder le site dans le préfixe (<code>SITE1</code>, <code>GROT2</code>) pour identifier la provenance sans ouvrir les métadonnées."},
    "LEDSynchro": {"type": "combo", "choices": ["NO","REC","3 REC"], "choice_labels": ["Aucune", "À chaque enregistrement", "3 premiers enregistrements"], "default": "REC", "tag": "Affichage LED", "scope": "PRS-S",
        "helper": "<b>PRS-S Maître uniquement.</b> Allume ou non la LED du Teensy à chaque enregistrement pour vérifier visuellement la synchronisation. <b>3 premiers</b> = test discret (uniquement les 3 premiers enregistrements)."},
    "BatcorderMode": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Nommage Batcorder",
        "helper": "Change le nommage des fichiers pour ressembler à celui du <b>Batcorder ecoObs</b> (<code>DDMMYY-HHMMSS-NAMENUMBER-00001.wav</code>) et crée un <code>LOGFILE.txt</code> mémorisant la température. Utile si vous avez déjà un pipeline d'analyse Batcorder (BCAdmin, BCAnalyze). <b>Défaut : Non.</b>"},
    "ZCFile": {"type": "combo", "choices": ["0", "1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Format Zero Crossing",
        "helper": "<b>Zero-Crossing</b> (style AnaBat) au lieu du format WAV. <b>10–100× plus petit</b>, mais ne mémorise que la fréquence dominante, pas l'amplitude.<br><br>Compatible AnaLook, <b>incompatible avec les classificateurs modernes</b> (Kaleidoscope, Tadarida, SonoChiro). Restez en WAV pour 99 % des usages."},

    # ---- Fréquences ----
    # The 4 Min/Max Freq fields are stored in Hz on disk (firmware contract,
    # cf. DecodeInt ranges in CModeGeneric.cpp:2456-2462) but exposed in kHz
    # in the UI — chiropterologists think in kHz, and 100-Hz precision over
    # a 100..150000 Hz range is needlessly cluttered. The "unit_factor"
    # attribute drives the conversion at the I/O boundary: cache values are
    # in UI units (kHz, float), and ``_ui_to_ini`` / ``_ini_to_ui`` translate
    # only when reading from / writing to the disk format.
    "MinFreqUS": {"type": "float", "min": 0.1, "max": 150.0, "step": 0.1, "default": 10.0,
        "unit_factor": 1000, "tag": "Fréquence ultrason min (kHz)",
        "helper": "Limite inférieure de la bande d'analyse ultrason, <b>en kHz</b> (précision 0,1 kHz). Sous cette fréquence, l'énergie est ignorée pour le déclenchement (mais le WAV reste large bande). <b>Défaut : 10 kHz.</b><br><br>"
                  "• <b>10–15 kHz</b> : standard chiroptéro tous taxons.<br>"
                  "• Plus haute → rate Molossidae bas et Noctules.<br>"
                  "• Plus basse → déclenchements parasites (vent, voiture)."},
    "MaxFreqUS": {"type": "float", "min": 0.1, "max": 150.0, "step": 0.1, "default": 120.0,
        "unit_factor": 1000, "tag": "Fréquence ultrason max (kHz)",
        "helper": "Limite supérieure de la bande d'analyse ultrason, <b>en kHz</b>. <b>Défaut : 120 kHz.</b><br><br>"
                  "• <b>120–150 kHz</b> : couvre toutes les espèces françaises (Petit Rhinolophe ~110 kHz).<br>"
                  "• Plus basse → rate les Rhinolophes."},
    "MinFreqA": {"type": "float", "min": 0.1, "max": 96.0, "step": 0.1, "default": 0.1,
        "unit_factor": 1000, "tag": "Fréquence audio min (kHz)",
        "helper": "Limite inférieure de la bande d'analyse audio, <b>en kHz</b>. Utilisée quand SampFreq < 192 kHz. <b>Défaut : 0,1 kHz</b> (= 100 Hz côté firmware)."},
    "MaxFreqA": {"type": "float", "min": 0.1, "max": 96.0, "step": 0.1, "default": 20.0,
        "unit_factor": 1000, "tag": "Fréquence audio max (kHz)",
        "helper": "Limite supérieure de la bande d'analyse audio, <b>en kHz</b>. <b>Défaut : 20 kHz</b> (limite haute audible humaine). 48 kHz pour capter les Molossidae bas."},
    "MinDuration": {"type": "int", "min": 1, "max": 99, "default": 1, "tag": "Durée min (s)",
        "helper": "Durée <b>minimale</b> d'un fichier WAV, en secondes. L'enregistrement dure au moins cette valeur, même si plus aucun cri n'est détecté. Si un nouveau cri arrive avant la fin, le compteur repart pour Durée min secondes additionnelles. <b>Défaut : 1 s.</b><br><br>"
                  "• <b>3 s</b> : pose passive standard.<br>"
                  "• <b>5–10 s</b> : site pauvre, pour récolter assez de signal exploitable."},
    "MaxDuration": {"type": "int", "min": 1, "max": 999, "default": 10, "tag": "Durée max (s)",
        "helper": "Durée <b>maximale</b> d'un fichier WAV, en secondes. Si l'activité continue au-delà, le fichier est coupé et un nouveau démarre immédiatement. <b>Défaut : 10 s.</b><br><br>"
                  "• <b>30 s</b> : standard chiroptéro.<br>"
                  "• <b>60–120 s</b> : sites très actifs (colonies, swarming), pour limiter le nombre de fichiers."},
    "ThresholdType": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Relatif", "Absolu"], "default": "0", "tag": "Type de seuil",
        "helper": "<b>Relatif</b> (défaut) : seuil au-dessus du <b>bruit ambiant mesuré</b> dans la bande (adaptatif). Sous une ligne haute tension, le seuil monte ; en forêt silencieuse, il descend.<br><br><b>Absolu</b> : niveau fixe référencé à -120 dB (plein bruit), indépendant du bruit ambiant. À utiliser pour les <b>études quantitatives comparatives</b> (même seuil reproductible entre nuits/sites)."},
    "RelativeThreshold": {"type": "int", "min": 5, "max": 99, "default": 18, "tag": "Seuil relatif (dB)",
        "helper": "Seuil de déclenchement en dB <b>au-dessus du bruit ambiant mesuré</b> (adaptatif). 5–99 dB. <b>Défaut : 18 dB</b> (recommandation officielle chiroptérologique).<br><br>"
                  "• <b>15 dB</b> : très sensible, parasites en site bruyant.<br>"
                  "• <b>20 dB</b> : un peu plus sélectif.<br>"
                  "• <b>25–30 dB</b> : seuil haut, cris proches/forts uniquement.<br>"
                  "• <b>&gt; 30 dB</b> : risque de rater les cris lointains."},
    "AbsoluteThreshold": {"type": "int", "min": -110, "max": -30, "default": -80, "tag": "Seuil absolu (dB)",
        "helper": "Niveau fixe en dB référencé à -120 dB (plein bruit). <b>Indépendant du bruit ambiant.</b> -110 à -30 dB. <b>Défaut : -80 dB.</b><br><br>Avantage : niveau parfaitement reproductible d'une nuit à l'autre, utile pour études quantitatives. <b>Inconvénient :</b> sur site bruyant, enregistre du bruit en boucle ; sur site silencieux, rate les cris faibles."},
    "NbDetect": {"type": "int", "min": 1, "max": 8, "default": 3, "tag": "Nombre de détections",
        "helper": "Détections d'énergie requises parmi les <b>8 dernières FFT</b> pour déclencher (filtre les clics brefs). 1–8. <b>Défaut : 3.</b><br><br>À 384 kHz : 1 détection ≈ 0,67 ms, 8 détections ≈ 5,33 ms.<br><br>"
                  "• <b>1–2</b> : FM courtes (Pipistrelles, Myotis, social calls — imposé à 1 en Point Fixe Vigie-Chiro).<br>"
                  "• <b>3</b> : bon compromis.<br>"
                  "• <b>5–8</b> : ne déclenche que sur QFC longs et FC de Rhinolophes."},

    # ---- Capteurs ----
    "ContMesTemp": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Mesure T° continue",
        "helper": "Si <b>Oui</b>, l'appareil continue de mesurer la T°/humidité <b>même en mode Veille</b>. À activer si vous avez besoin d'une courbe T° continue 24/24 sur la pose. <b>Défaut : Non</b> (économie batterie)."},
    "TemperaturePeriod": {"type": "int", "min": 10, "max": 3600, "step": 10, "default": 60, "tag": "Période température (s)",
        "helper": "Intervalle entre deux mesures de température / humidité, en secondes. Stockées dans <code>PaRecARxxxxxx_THLog.csv</code>. <b>Défaut : 60 s</b> (1 min).<br><br>⚠️ La sonde est <b>à l'intérieur du boîtier</b> : la T° est influencée par la chaleur du CPU. Bonne pour les tendances, pas pour les valeurs absolues."},
    "SaveNoise": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Sauvegarde du bruit",
        "helper": "Sauve le bruit moyen mesuré par bande dans un fichier CSV séparé. Utile pour <b>caractériser la qualité acoustique d'un site</b> avant pose réelle. <b>Défaut : Non.</b>"},

    # ---- RhinoLogger ----
    "AffRLPerm": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Affichage RhinoLogger permanent", "scope": "RhinoLogger",
        "helper": "<b>Mode RhinoLogger uniquement.</b> Garde l'affichage des compteurs d'activité en permanence à l'écran. <b>Oui</b> = utile pour la mise au point sur site (vérifier visuellement que ça déclenche bien). <b>Non (défaut)</b> = recommandé en pose longue durée (discrétion, économie OLED)."},

    # ---- Alimentation (Power bank keep-alive) ----
    # Firmware uses DecodeBool: only 0/1 are accepted; any other value falls back
    # to the default (false). Documented default is "Non" (0) per ManuelTR.
    "PowerBank": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Mode PowerBank",
        "helper": "Force une consommation en veille plus élevée pour empêcher une <b>power bank USB 5 V</b> de se mettre elle-même en veille (et de couper l'appareil). À activer <b>uniquement</b> avec une power bank USB connue pour se couper en faible courant.<br><br><b>Inconvénient : autonomie réduite</b> (consommation veille augmentée). <b>Défaut : Non.</b>"},
}

SECTION_TITLES = {

    # ────────── Profil ──────────
    "Profil": [
        "ProfileName", "OpMode",
        # Synchro (PRS-S)
        "MasterSlave",
    ],

    # ────────── Horaires ──────────
    "Horaires": [
        # Horaires fixes
        "StartTime", "EndTime", "RecTime", "WaitTime",
        # Fenêtre calendaire
        "StartDate", "EndDate",
        # Calcul automatique solaire
        "AutoStartStop", "Latitude", "Longitude", "TUOffset", "StartStopOffset",
    ],

    # ────────── Audio ──────────
    "Audio": [
        # Échantillonnage
        "SampFreqU", "SampFreqA",
        # Gain et dynamique
        "NumericGain", "Exp10",
        # Filtres fréquentiels
        "LowpassFilter", "HighpassFilter", "fHighpassFilter",
        # Configuration du signal
        "StereoMode", "MicrophoneType",
        # Top synchro (PRS-S)
        "TopAudioFreq", "TopDuration", "TopPeriod",
    ],

    # ────────── Hétérodyne ──────────
    "Hétérodyne": [
        # Activation / déclenchement
        "HeterodyneMode", "AutoRecHeter",
        # Visualisation
        "RefreshGraphe", "HeterLevel", "HeterWithGraph",
        # Pré-déclenchement
        "Pre-TriggerAuto", "Pre-TriggerHeter",
        # Traitement/lecture
        "Pre-HeterSelectiveFilter", "HeterAGC", "HeterAutoPlay",
    ],

    # ────────── Fréquences ──────────
    "Fréquences": [
        # Ultrasons
        "MinFreqUS", "MaxFreqUS",
        # Audio
        "MinFreqA", "MaxFreqA",
        # Durée des événements
        "MinDuration", "MaxDuration",
        # Seuils
        "ThresholdType", "RelativeThreshold", "AbsoluteThreshold",
        # Validation
        "NbDetect",
    ],

    # ────────── Fichiers ──────────
    "Fichiers": [
        # Nom/format
        "WavPrefix", "ZCFile", "BatcorderMode",
        # Indication LED
        "LEDSynchro",
    ],

    # ────────── Autre ──────────
    "Autre": [
        # Bruit ambiant
        "SaveNoise",
        # Capteurs
        "TemperaturePeriod", "ContMesTemp",
        # RhinoLogger
        "AffRLPerm",
        # Alimentation
        "PowerBank",
    ],
}

SUBTITLES = {
    # Sous-titre au début de l'onglet
    ("Profil", None): "Identification du profil",
    ("Horaires", None): "Horaires fixes d’enregistrement",
    ("Audio", None): "Échantillonnage",
    ("Hétérodyne", None): "Activation et déclenchement",
    ("Fichiers", None): "Nom et organisation des fichiers",
    ("Fréquences", None): "Spectre ultrasonore",
    ("Autre", None): "Bruit ambiant",

    # Sous-titres déclenchés avant une clé
    ("Profil", "OpMode"): "Mode de fonctionnement",
    ("Profil", "MasterSlave"): "Synchro multi-appareils (PRS-S)",

    ("Horaires", "StartDate"): "Fenêtre calendaire",
    ("Horaires", "AutoStartStop"): "Déclenchement automatique basé sur le soleil",

    ("Audio", "NumericGain"): "Gain et dynamique du signal",
    ("Audio", "LowpassFilter"): "Filtres fréquentiels",
    ("Audio", "StereoMode"): "Configuration du signal",
    ("Audio", "TopAudioFreq"): "Top synchro (PRS-S Maître)",

    ("Hétérodyne", "RefreshGraphe"): "Visualisation et niveau du signal",
    ("Hétérodyne", "Pre-TriggerAuto"): "Pré-déclenchement",
    ("Hétérodyne", "Pre-HeterSelectiveFilter"): "Traitement du signal",

    ("Fichiers", "LEDSynchro"): "Indication LED (synchro PRS-S)",

    ("Fréquences", "MinFreqA"): "Spectre audible",
    ("Fréquences", "MinDuration"): "Durée des enregistrements",
    ("Fréquences", "ThresholdType"): "Seuils de détection",

    ("Autre", "TemperaturePeriod"): "Capteurs",
    ("Autre", "AffRLPerm"): "RhinoLogger",
    ("Autre", "PowerBank"): "Alimentation",
}

PROFILE_LABELS = {"Profile 2": "2", "Profile 3": "3", "Profile 4": "4", "Profile 5": "5"}
