"""
config.py
---------
Point unique de configuration du projet.

On regroupe ici tout ce qui peut changer (liste des villes, chemins, réglages
du beauty score, noms de buckets...) pour ne pas avoir de "valeurs magiques"
dispersées dans le reste du code.
"""

from pathlib import Path

# --- Chemins du projet -------------------------------------------------------
# On calcule les chemins à partir de l'emplacement de ce fichier, comme ça le
# projet fonctionne quel que soit le dossier depuis lequel on le lance.
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
FIGURES_DIR = BASE_DIR / "reports" / "figures"

# Fichiers de sortie
WEATHER_CSV = DATA_PROCESSED_DIR / "villes_meteo.csv"
HOTELS_CSV = DATA_PROCESSED_DIR / "df_top3_hotels.csv"


# --- Les 35 villes cibles (source : One Week In.com, via l'énoncé) ----------
VILLES = [
    "Mont Saint Michel", "St Malo", "Bayeux", "Le Havre", "Rouen",
    "Paris", "Amiens", "Lille", "Strasbourg", "Chateau du Haut Koenigsbourg",
    "Colmar", "Eguisheim", "Besancon", "Dijon", "Annecy", "Grenoble", "Lyon",
    "Gorges du Verdon", "Bormes les Mimosas", "Cassis", "Marseille",
    "Aix en Provence", "Avignon", "Uzes", "Nimes", "Aigues Mortes",
    "Saintes Maries de la mer", "Collioure", "Carcassonne", "Ariege",
    "Toulouse", "Montauban", "Biarritz", "Bayonne", "La Rochelle",
]


# --- Paramètres du Beauty Score ---------------------------------------------
# Chacun a sa propre définition du "beau temps" (cf. énoncé). On définit ici
# des valeurs "idéales" et des pénalités, faciles à ajuster.
TEMP_IDEALE = 20.0        # température parfaite en °C
HUMIDITE_IDEALE = 40.0    # humidité parfaite en %
PLUIE_IDEALE = 0.0        # pas de pluie = idéal

PENALITE_PAR_DEGRE = 3.0     # points perdus par °C d'écart avec 20°C
PENALITE_PAR_MM_PLUIE = 2.0  # points perdus par mm de pluie cumulée
PENALITE_PAR_PCT_HUM = 1.0   # points perdus par % d'humidité au-dessus de 40%


# --- APIs --------------------------------------------------------------------
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OWM_ONECALL_URL = "https://api.openweathermap.org/data/2.5/forecast"

# Adresse e-mail de contact exigée par la politique d'usage de Nominatim.
# À remplacer par la tienne avant exécution.
CONTACT_EMAIL = "geoffrey.madalinski@gmail.com"

# User-Agent custom (bonne pratique / politesse envers les serveurs)
USER_AGENT = "KayakTripPlanner/1.0"


# --- AWS S3 (data lake) ------------------------------------------------------
# À adapter à ton compte. La clé/secret sont lus depuis le .env, jamais ici.
S3_BUCKET = "bucket-geoffrey-dsfs-ft-38"
S3_PREFIX = "projets-certification-cdsd/projet-kayak_GM/"
S3_REGION = "eu-north-1"
