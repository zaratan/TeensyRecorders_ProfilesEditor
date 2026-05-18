from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    BUILD_VERSION = _pkg_version("teensy-profiles-editor")
except PackageNotFoundError:
    BUILD_VERSION = "0.0.0+unknown"


FIELDS = {
    # ---- Profil ----
    "ProfileName": {"type": "text", "limit": 11, "tag": "Nom de profil", "helper":"Nom du profil tel qu’il apparaît dans le TeensyRecorder."},
    "OpMode": {"type": "combo", "choices": [
        "Auto record","Walkin. Protoc.","Road Protocol",
        "Fixed P. Proto.","RhinoLogger","Heterodyne",
        "Timed recording","Audio Rec.","Synchro"
    ], "tag":"Mode d'enregistrement", "helper":"Mode de fonctionnement principal du TeensyRecorder."},

    # ---- Horaires ----
    "StartTime": {"type": "text", "tag": "Heure de début","helper": "Heure de début (HH:MM). Ignorée si le calcul automatique lever/coucher est activé."},
    "EndTime": {"type": "text", "tag": "Heure de fin", "helper": "Heure de fin (HH:MM). Ignorée si le calcul automatique lever/coucher est activé."},
    "RecTime": {"type": "int", "min": 1, "max": 3600, "step": 10, "default": 60, "tag": "Durée d'enregistrement (s)", "helper": "Durée maximale d'un fichier d'enregistrement, en secondes."},
    "WaitTime": {"type": "int", "min": 1, "max": 3600, "step": 10, "default": 540, "tag": "Temps d'attente (s)", "helper": "Temps d'attente entre deux enregistrements consécutifs."},

    # ---- Dates (fenêtre de validité) ----
    "StartDate": {"type": "text", "limit": 5, "default": "--/--", "tag": "Date de début", "helper": "Date de début de validité du profil (JJ/MM). '--/--' pour aucune limite."},
    "EndDate": {"type": "text", "limit": 5, "default": "--/--", "tag": "Date de fin", "helper": "Date de fin de validité du profil (JJ/MM). '--/--' pour aucune limite."},

    # ---- Soleil / Auto Start-Stop (calcul lever/coucher) ----
    "AutoStartStop": {"type": "combo", "choices": ["0", "1"], "default": "0", "tag": "Calcul lever/coucher", "helper": "Active le calcul automatique des horaires selon le lever et le coucher du soleil."},
    "Latitude": {"type": "float", "min": -90.0, "max": 90.0, "step": 0.000001, "default": 48.857918, "tag": "Latitude (°)", "helper": "Latitude WGS84 utilisée pour le calcul astronomique (point décimal requis)."},
    "Longitude": {"type": "float", "min": -180.0, "max": 180.0, "step": 0.000001, "default": 2.348615,  "tag": "Longitude (°)", "helper": "Longitude WGS84 utilisée pour le calcul astronomique (point décimal requis)."},
    "TUOffset": {"type": "int", "min": -12, "max": 14, "step": 1, "default": 2, "tag": "Décalage UTC", "helper": "Décalage horaire entre l'heure locale et le temps universel (UTC)."},
    "StartStopOffset": {"type": "int", "min": -360, "max": 360, "step": 1, "default": 0, "tag": "Extension nocturne (min)", "helper": "Décale les horaires calculés à partir du soleil : la valeur est soustraite à l'heure du coucher du soleil et ajoutée à l'heure du lever du soleil."},

    # ---- Audio ----
    "SampFreqU": {"type": "combo", "choices": ["24","48","96","192","250","384","500"], "tag": "Fréquence US (kHz)", "helper": "Fréquence d'échantillonnage pour les ultrasons."},
    "SampFreqA": {"type": "combo", "choices": ["24","48","96","192"], "tag": "Fréquence audio (kHz)", "helper": "Fréquence d'échantillonnage pour l'audio audible."},
    "NumericGain": {"type": "combo", "choices": ["0","6","12","18","24"], "tag": "Gain numérique (dB)", "helper": "Amplification numérique appliquée au signal."},
    "LowpassFilter": {"type": "combo", "choices": ["0","1"], "default": "0", "tag": "Filtre passe-bas", "helper": "Active ou désactive le filtre passe-bas."},
    "HighpassFilter": {"type": "int", "min": 0, "max": 25, "default": 0, "tag": "Filtre passe-haut", "helper": "Valeur du filtre passe-haut en kHz."},
    "fHighpassFilter": {"type": "float", "min": 0.0, "max": 25.0, "step": 0.1, "default": 0.0, "tag": "Filtre passe-haut (fin)", "helper": "Réglage fin du filtre passe-haut."},
    "Exp10": {"type": "combo", "choices": ["0","1"], "default": "0", "tag": "Expansion de temps", "helper": "Active la mise en expansion de temps automatique des enregistrements."},
    "StereoMode": {"type": "combo", "choices": ["Stereo","MonoRight","MonoLeft"], "tag": "Canal d'enregistrement", "helper": "Sélection du canal audio utilisé."},
    "MicrophoneType": {"type": "combo", "choices": ["SPU0410","ICS40730","FG23329"], "tag": "Modèle de microphone", "helper": "Modèle de microphone utilisé par le capteur."},

    # ---- Hétérodyne ----
    "HeterodyneMode": {"type": "combo", "choices": ["0","1"], "default": "0", "tag": "Mode hétérodyne", "helper": "Active le mode d'écoute hétérodyne en temps réel."},
    "AutoRecHeter": {"type": "combo", "choices": ["0","1"], "default": "0", "tag": "Auto-enregistrement hétérodyne", "helper": "Déclenche automatiquement un enregistrement depuis le mode hétérodyne."},
    "RefreshGraphe": {"type": "float", "min": 0.2, "max": 2.0, "step": 0.2, "default": 1.0, "tag": "Rafraîchissement graphique", "helper": "Intervalle de mise à jour du graphe hétérodyne."},
    "HeterLevel": {"type": "float", "min": 0.1, "max": 0.9, "step": 0.1, "default": 0.5, "tag": "Seuil hétérodyne", "helper": "Seuil de déclenchement du signal hétérodyne."},
    "Pre-TriggerAuto": {"type": "int", "min": 0, "max": 10, "default": 1, "tag": "Pré-trigger auto (s)", "helper": "Durée pré-enregistrée avant le déclenchement automatique."},
    "Pre-TriggerHeter": {"type": "int", "min": 0, "max": 10, "default": 3, "tag": "Pré-trigger hétérodyne (s)", "helper": "Durée pré-enregistrée avant le déclenchement manuel."},
    "HeterSelectiveFilter": {"type": "combo", "choices": ["0","1"], "default": "0", "tag": "Filtre sélectif hétérodyne", "helper": "Active un filtrage sélectif du signal hétérodyne."},
    "HeterAutoPlay": {"type": "combo", "choices": ["0","1"], "default": "0", "tag": "Lecture automatique", "helper": "Lecture automatique des signaux détectés en hétérodyne."},
    "HeterWithGraph": {"type": "combo", "choices": ["0","1"], "default": "1", "tag": "Affichage graphique", "helper": "Affiche le niveau instantané du signal hétérodyne."},
    "HeterAGC": {"type": "combo", "choices": ["0","1"], "default": "0", "tag": "AGC hétérodyne", "helper": "Active le contrôle automatique de gain en mode hétérodyne."},

    # ---- Fichiers ----
    "WavPrefix": {"type": "text", "limit": 5, "tag": "Préfixe fichier", "helper": "Préfixe utilisé pour nommer les fichiers WAV."},
    "LEDSynchro": {"type": "combo", "choices": ["NO","REC","3 REC"], "tag": "Affichage LED", "helper": "Comportement de la LED lors des enregistrements."},
    #"BatcorderMode": {"type": "combo", "choices": ["0","1"], "default": "0", "tag": "Mode Batcorder", "helper": "Active un comportement compatible Batcorder."},
    "MaxFileLength": {"type": "int", "min": 1, "max": 999, "default": 60, "tag": "Durée max fichier (s)", "helper": "Durée maximale d'un fichier audio."},
    "ZCFile": {"type": "combo", "choices": ["0", "1"], "default": "0", "tag": "Format Zero Crossing", "helper": "Enregistre en format Zero Crossing."},

    # ---- Fréquences ----
    "MinFreqUS": {"type": "int", "min": 100, "max": 150000, "step": 100, "tag": "Fréquence US min (Hz)", "helper": "Fréquence ultrasonore minimale détectée."},
    "MaxFreqUS": {"type": "int", "min": 100, "max": 150000, "step": 100, "tag": "Fréquence US max (Hz)", "helper": "Fréquence ultrasonore maximale détectée."},
    "MinFreqA": {"type": "int", "min": 100, "max": 96000, "step": 100, "tag": "Fréquence audio min (Hz)", "helper": "Fréquence audio minimale détectée."},
    "MaxFreqA": {"type": "int", "min": 100, "max": 96000, "step": 100, "tag": "Fréquence audio max (Hz)", "helper": "Fréquence audio maximale détectée."},
    "MinDuration": {"type": "int", "min": 1, "max": 99, "default": 1, "tag": "Durée min (ms)", "helper": "Durée minimale d’un événement détecté."},
    "MaxDuration": {"type": "int", "min": 1, "max": 999, "default": 10, "tag": "Durée max (ms)", "helper": "Durée maximale d’un événement détecté."},
    "ThresholdType": {"type": "combo", "choices": ["0","1"], "default": "0", "tag": "Type de seuil", "helper": "Type de seuil utilisé pour la détection."},
    "RelativeThreshold": {"type": "int", "min": 5, "max": 99, "default": 18, "tag": "Seuil relatif", "helper": "Seuil de détection relatif."},
    "AbsoluteThreshold": {"type": "int", "min": -110, "max": -30, "default": -90, "tag": "Seuil absolu (dB)", "helper": "Seuil de détection absolu en dB."},
    "NbDetect": {"type": "int", "min": 1, "max": 8, "default": 3, "tag": "Nombre de détections", "helper": "Nombre minimal de détections consécutives requises."},
    "MinLevel": {"type": "int", "min": 0, "max": 100, "default": 15, "tag": "Niveau minimum", "helper": "Niveau minimal du signal pour être pris en compte."},
    "PreTrigger": {"type": "int", "min": 0, "max": 10, "default": 5, "tag": "Pré-trigger (s)", "helper": "Durée enregistrée avant le déclenchement."},

    # ---- Capteurs ----
    "ContMesTemp": {"type": "combo", "choices": ["0","1"], "default": "0", "tag": "Mesure température continue", "helper": "Active la mesure continue de la température."},
    "TemperaturePeriod": {"type": "int", "min": 10, "max": 3600, "step": 10, "default": 600, "tag": "Période température (s)", "helper": "Intervalle de mesure de la température."},
    "THSensorEnable": {"type": "combo", "choices": ["0","1"], "default": "1", "tag": "Capteur T/H", "helper": "Active le capteur température et d'humidité."},
    "SaveNoise": {"type": "combo", "choices": ["0","1"], "default": "0", "tag": "Sauvegarde bruit", "helper": "Conserve le bruit de fond."},
    #"GPSenable": {"type": "combo", "choices": ["0","1"], "default": "0", "tag": "GPS", "helper": "Active l'utilisation du GPS."},

    # ---- Alimentation (Power bank keep-alive) ----
    "PowerBank": {"type": "int", "min": 0, "max": 255, "step": 1, "default": 255, "tag": "Mode PowerBank", "helper": "Augmente la consommation en veille pour éviter l'arrêt des batteries externes."},
}

SECTION_TITLES = {

    # ────────── Profil ──────────
    "Profil": [
        "ProfileName", "OpMode",
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
        "HeterSelectiveFilter", "HeterAGC", "HeterAutoPlay",
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
        "NbDetect", "MinLevel", "PreTrigger",
    ],

    # ────────── Fichiers ──────────
    "Fichiers": [
        # Nom/format
        "WavPrefix", "ZCFile",
        # Contraintes fichier
        "MaxFileLength",
    ],

    # ────────── Autre ──────────
    "Autre": [
        # Indications/environnement
        "LEDSynchro", "SaveNoise",
        # Capteurs
        "THSensorEnable", "TemperaturePeriod", "ContMesTemp",
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
    ("Autre", None): "Indications & environnement",

    # Sous-titres déclenchés avant une clé
    ("Profil", "OpMode"): "Mode de fonctionnement",

    ("Horaires", "StartDate"): "Fenêtre calendaire (optionnelle)",
    ("Horaires", "AutoStartStop"): "Déclenchement automatique basé sur le soleil",

    ("Audio", "NumericGain"): "Gain et dynamique du signal",
    ("Audio", "LowpassFilter"): "Filtres fréquentiels",
    ("Audio", "StereoMode"): "Configuration du signal",

    ("Hétérodyne", "RefreshGraphe"): "Visualisation et niveau du signal",
    ("Hétérodyne", "Pre-TriggerAuto"): "Pré-déclenchement",
    ("Hétérodyne", "HeterSelectiveFilter"): "Traitement du signal",

    ("Fréquences", "MinFreqA"): "Spectre audible",
    ("Fréquences", "MinDuration"): "Durée des événements",
    ("Fréquences", "ThresholdType"): "Seuils de détection",

    ("Autre", "THSensorEnable"): "Capteurs",
    ("Autre", "PowerBank"): "Alimentation",
}

PROFILE_LABELS = {"Profile 2": "2", "Profile 3": "3", "Profile 4": "4", "Profile 5": "5"}
