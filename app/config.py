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


# FIELDS schema reference: firmware CModeGeneric.cpp ImportProfiles (~line 2349)
# and ExportProfiles (~line 1922). Every combo's "choices" must match the
# firmware enum strings verbatim; the "choice_labels" override (optional)
# decouples the INI value from the UI label so we can present "Non/Oui",
# "Relatif/Absolu", "kHz", "dB", etc. without changing what is written to
# the file. If "choice_labels" is absent, the raw choice value is shown.
FIELDS = {
    # ---- Profil ----
    "ProfileName": {"type": "text", "limit": 11, "tag": "Nom de profil", "helper":"Nom du profil tel qu’il apparaît dans le TeensyRecorder."},
    # Walkin. Protoc. (PROTPED) and Road Protocol (PROTROUT) are intentionally
    # NOT exposed here. The firmware coerces these modes back to RECAUTO/PHETER
    # at every cold boot (cf. CModeGeneric.cpp:864-873), so persisting them in
    # a profile is silently ineffective. Both Vigie-Chiro session protocols are
    # activated manually from the device menu, per recording session.
    "OpMode": {"type": "combo", "choices": [
        "Auto record",
        "Fixed P. Proto.","RhinoLogger","Heterodyne",
        "Timed recording","Audio Rec.","Synchro"
    ], "default": "Auto record", "tag":"Mode d'enregistrement", "helper":"Mode de fonctionnement principal du TeensyRecorder."},
    "MasterSlave": {"type": "int", "min": 0, "max": 9, "step": 1, "default": 0, "tag": "Maître/Esclave", "helper": "Rôle dans un cluster synchronisé (PRS-S) : 0 = Maître ; 1 à 9 = Esclave numéroté. Un seul Maître par cluster."},

    # ---- Horaires ----
    "StartTime": {"type": "text", "tag": "Heure de début","helper": "Heure de début (HH:MM). Ignorée si le calcul automatique lever/coucher est activé."},
    "EndTime": {"type": "text", "tag": "Heure de fin", "helper": "Heure de fin (HH:MM). Ignorée si le calcul automatique lever/coucher est activé."},
    "RecTime": {"type": "int", "min": 1, "max": 43200, "step": 10, "default": 60, "tag": "Durée d'enregistrement (s)", "helper": "Durée maximale d'un fichier d'enregistrement, en secondes."},
    "WaitTime": {"type": "int", "min": 1, "max": 86400, "step": 10, "default": 540, "tag": "Temps d'attente (s)", "helper": "Temps d'attente entre deux enregistrements consécutifs."},

    # ---- Dates (fenêtre de validité) ----
    "StartDate": {"type": "text", "limit": 5, "default": "--/--", "tag": "Date de début", "helper": "Date de début de validité du profil (JJ/MM). '--/--' pour aucune limite."},
    "EndDate": {"type": "text", "limit": 5, "default": "--/--", "tag": "Date de fin", "helper": "Date de fin de validité du profil (JJ/MM). '--/--' pour aucune limite."},

    # ---- Soleil / Auto Start-Stop (calcul lever/coucher) ----
    "AutoStartStop": {"type": "combo", "choices": ["0", "1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Calcul lever/coucher", "helper": "Active le calcul automatique des horaires selon le lever et le coucher du soleil."},
    "Latitude": {"type": "float", "min": -90.0, "max": 90.0, "step": 0.000001, "default": 48.857918, "tag": "Latitude (°)", "helper": "Latitude WGS84 utilisée pour le calcul astronomique (point décimal requis)."},
    "Longitude": {"type": "float", "min": -180.0, "max": 180.0, "step": 0.000001, "default": 2.348615,  "tag": "Longitude (°)", "helper": "Longitude WGS84 utilisée pour le calcul astronomique (point décimal requis)."},
    "TUOffset": {"type": "int", "min": -12, "max": 14, "step": 1, "default": 2, "tag": "Décalage UTC", "helper": "Décalage horaire entre l'heure locale et le temps universel (UTC)."},
    "StartStopOffset": {"type": "int", "min": -360, "max": 360, "step": 1, "default": 0, "tag": "Extension nocturne (min)", "helper": "Décale les horaires calculés à partir du soleil : la valeur est soustraite à l'heure du coucher du soleil et ajoutée à l'heure du lever du soleil."},

    # ---- Audio ----
    "SampFreqU": {"type": "combo", "choices": ["24","48","96","192","250","384","500"], "choice_labels": ["24 kHz","48 kHz","96 kHz","192 kHz","250 kHz","384 kHz","500 kHz"], "default": "384", "tag": "Fréquence US", "helper": "Fréquence d'échantillonnage pour les ultrasons."},
    "SampFreqA": {"type": "combo", "choices": ["24","48","96","192"], "choice_labels": ["24 kHz","48 kHz","96 kHz","192 kHz"], "default": "48", "tag": "Fréquence audio", "helper": "Fréquence d'échantillonnage pour l'audio audible."},
    "NumericGain": {"type": "combo", "choices": ["0","6","12","18","24"], "choice_labels": ["0 dB","+6 dB","+12 dB","+18 dB","+24 dB"], "default": "12", "tag": "Gain numérique", "helper": "Amplification numérique appliquée au signal."},
    "LowpassFilter": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Filtre passe-bas / linéaire", "helper": "Active ou désactive le filtre passe-bas (SampFreq < 192 kHz) ou le filtre de linéarisation du micro MEMS (SampFreq ≥ 192 kHz)."},
    "HighpassFilter": {"type": "int", "min": 0, "max": 25, "default": 0, "tag": "Filtre passe-haut (kHz)", "helper": "Valeur du filtre passe-haut en kHz, utilisé quand SampFreq ≥ 192 kHz."},
    "fHighpassFilter": {"type": "float", "min": 0.0, "max": 25.0, "step": 0.1, "default": 0.0, "tag": "Filtre passe-haut fin (kHz)", "helper": "Valeur du filtre passe-haut en kHz avec précision 0,1 kHz, utilisé quand SampFreq < 192 kHz."},
    "Exp10": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "1", "tag": "Expansion de temps ×10", "helper": "Modifie l'en-tête WAV pour annoncer une fréquence 10× plus basse — le signal n'est pas réellement ralenti, mais devient audible dans un lecteur basique."},
    "StereoMode": {"type": "combo", "choices": ["Stereo","MonoRight","MonoLeft"], "choice_labels": ["Stéréo", "Mono droit", "Mono gauche"], "default": "Stereo", "tag": "Canal d'enregistrement", "helper": "Sélection du canal audio utilisé (PRS uniquement)."},
    "MicrophoneType": {"type": "combo", "choices": ["SPU0410","ICS43730","FG23329"], "default": "ICS43730", "tag": "Modèle de microphone", "helper": "Modèle de microphone utilisé par le capteur."},
    "TopAudioFreq": {"type": "int", "min": 1, "max": 50, "step": 1, "default": 2, "tag": "Fréquence top synchro (kHz)", "helper": "Fréquence du top synchro émis par le Maître aux Esclaves, enregistré dans chaque WAV pour permettre la synchronisation temporelle en post-traitement (PRS-S Maître)."},
    "TopDuration": {"type": "combo", "choices": ["256","512","1024"], "choice_labels": ["256 éch.","512 éch.","1024 éch."], "default": "256", "tag": "Durée du top", "helper": "Durée du top audio en nombre d'échantillons (PRS-S Maître)."},
    "TopPeriod": {"type": "int", "min": 0, "max": 10, "step": 1, "default": 0, "tag": "Période du top", "helper": "0 = top émis une seule fois au début de l'enregistrement ; ≥ 1 = tops émis périodiquement (PRS-S Maître)."},

    # ---- Hétérodyne ----
    "HeterodyneMode": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Manuel", "Auto"], "default": "0", "tag": "Mode hétérodyne", "helper": "Manuel : la molette choisit la fréquence. Auto : l'appareil cale automatiquement la fréquence sur le pic d'énergie."},
    "AutoRecHeter": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Auto-enregistrement hétérodyne", "helper": "Déclenche automatiquement un enregistrement depuis le mode hétérodyne."},
    "RefreshGraphe": {"type": "float", "min": 0.2, "max": 2.0, "step": 0.2, "default": 1.0, "tag": "Rafraîchissement graphique (s)", "helper": "Intervalle de mise à jour du graphe hétérodyne, en secondes."},
    "HeterLevel": {"type": "float", "min": 0.1, "max": 0.9, "step": 0.1, "default": 0.1, "tag": "Seuil hétérodyne", "helper": "Seuil de déclenchement du signal hétérodyne."},
    "Pre-TriggerAuto": {"type": "int", "min": 0, "max": 10, "default": 1, "tag": "Pré-trigger auto (s)", "helper": "Durée pré-enregistrée avant le déclenchement automatique. Teensy 4.1 avec mémoire étendue uniquement."},
    "Pre-TriggerHeter": {"type": "int", "min": 0, "max": 10, "default": 3, "tag": "Pré-trigger hétérodyne (s)", "helper": "Durée pré-enregistrée avant le déclenchement manuel. Teensy 4.1 avec mémoire étendue uniquement."},
    # Firmware writes "HeterSelectiveFilter" but reads "Pre-HeterSelectiveFilter"
    # (firmware bug in CModeGeneric.cpp line 2464). We align on the read-side name
    # so the value actually round-trips through the device.
    "Pre-HeterSelectiveFilter": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Filtre sélectif hétérodyne", "helper": "Active un filtrage sélectif du signal hétérodyne."},
    "HeterAutoPlay": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Lecture automatique", "helper": "Rejoue automatiquement la séquence enregistrée en X10 sur le casque après chaque détection."},
    "HeterWithGraph": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "1", "tag": "Affichage graphique", "helper": "Affiche le niveau instantané du signal hétérodyne."},
    "HeterAGC": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "AGC hétérodyne", "helper": "Active le contrôle automatique de gain en mode hétérodyne."},

    # ---- Fichiers ----
    "WavPrefix": {"type": "text", "limit": 5, "tag": "Préfixe fichier", "helper": "Préfixe utilisé pour nommer les fichiers WAV (5 caractères max)."},
    "LEDSynchro": {"type": "combo", "choices": ["NO","REC","3 REC"], "choice_labels": ["Aucune", "À chaque enregistrement", "3 premiers enregistrements"], "default": "REC", "tag": "Affichage LED", "helper": "Comportement de la LED du Teensy lors des enregistrements (vérification visuelle de la synchro PRS-S)."},
    "BatcorderMode": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Nommage Batcorder", "helper": "Si Oui, change le nommage des fichiers pour ressembler à celui du Batcorder ecoObs et crée un LOGFILE.txt mémorisant la température."},
    "ZCFile": {"type": "combo", "choices": ["0", "1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Format Zero Crossing", "helper": "Enregistre en format Zero Crossing (AnaBat). Beaucoup plus petit mais incompatible avec les classificateurs modernes (Tadarida, SonoChiro, Kaleidoscope)."},

    # ---- Fréquences ----
    "MinFreqUS": {"type": "int", "min": 100, "max": 150000, "step": 100, "default": 10000, "tag": "Fréquence US min (Hz)", "helper": "Fréquence ultrasonore minimale détectée."},
    "MaxFreqUS": {"type": "int", "min": 100, "max": 150000, "step": 100, "default": 120000, "tag": "Fréquence US max (Hz)", "helper": "Fréquence ultrasonore maximale détectée."},
    "MinFreqA": {"type": "int", "min": 100, "max": 96000, "step": 100, "default": 100, "tag": "Fréquence audio min (Hz)", "helper": "Fréquence audio minimale détectée."},
    "MaxFreqA": {"type": "int", "min": 100, "max": 96000, "step": 100, "default": 48000, "tag": "Fréquence audio max (Hz)", "helper": "Fréquence audio maximale détectée."},
    "MinDuration": {"type": "int", "min": 1, "max": 99, "default": 1, "tag": "Durée min (s)", "helper": "Durée minimale d’un événement détecté, en secondes."},
    "MaxDuration": {"type": "int", "min": 1, "max": 999, "default": 10, "tag": "Durée max (s)", "helper": "Durée maximale d’un événement détecté, en secondes."},
    "ThresholdType": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Relatif", "Absolu"], "default": "0", "tag": "Type de seuil", "helper": "Relatif : seuil au-dessus du bruit ambiant mesuré (adaptatif). Absolu : niveau fixe référencé au plein bruit."},
    "RelativeThreshold": {"type": "int", "min": 5, "max": 99, "default": 18, "tag": "Seuil relatif (dB)", "helper": "Seuil de détection relatif au bruit ambiant, en dB. Recommandation chiroptérologique : 18 dB."},
    "AbsoluteThreshold": {"type": "int", "min": -110, "max": -30, "default": -80, "tag": "Seuil absolu (dB)", "helper": "Seuil de détection absolu en dB, indépendant du bruit ambiant."},
    "NbDetect": {"type": "int", "min": 1, "max": 8, "default": 3, "tag": "Nombre de détections", "helper": "Nombre minimal de détections d'énergie parmi les 8 dernières FFT pour déclencher (filtre les clics brefs)."},

    # ---- Capteurs ----
    "ContMesTemp": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Mesure T° continue", "helper": "Active la mesure continue de la température (y compris pendant la veille)."},
    "TemperaturePeriod": {"type": "int", "min": 10, "max": 3600, "step": 10, "default": 60, "tag": "Période température (s)", "helper": "Intervalle entre deux mesures de température/humidité, en secondes."},
    "SaveNoise": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Sauvegarde du bruit", "helper": "Sauve le bruit moyen mesuré par bande dans un fichier CSV. Utile pour caractériser la qualité acoustique d'un site."},

    # ---- RhinoLogger ----
    "AffRLPerm": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Affichage RhinoLogger permanent", "helper": "Garde les compteurs d'activité RhinoLogger affichés en permanence. Désactiver en pose longue durée (discrétion, économie OLED)."},

    # ---- Alimentation (Power bank keep-alive) ----
    # Firmware uses DecodeBool: only 0/1 are accepted; any other value falls back
    # to the default (false). Documented default is "Non" (0) per ManuelTR.
    "PowerBank": {"type": "combo", "choices": ["0","1"], "choice_labels": ["Non", "Oui"], "default": "0", "tag": "Mode PowerBank", "helper": "À activer uniquement avec une power bank USB qui se coupe en faible courant. Réduit l'autonomie."},
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

    ("Horaires", "StartDate"): "Fenêtre calendaire (optionnelle)",
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
    ("Fréquences", "MinDuration"): "Durée des événements",
    ("Fréquences", "ThresholdType"): "Seuils de détection",

    ("Autre", "TemperaturePeriod"): "Capteurs",
    ("Autre", "AffRLPerm"): "RhinoLogger",
    ("Autre", "PowerBank"): "Alimentation",
}

PROFILE_LABELS = {"Profile 2": "2", "Profile 3": "3", "Profile 4": "4", "Profile 5": "5"}
