"""
weather.py
----------
Collecte des données météo pour les 35 villes.

Pour chaque ville :
  1. on récupère ses coordonnées GPS via Nominatim (OpenStreetMap)
  2. on récupère les prévisions sur 7 jours via OpenWeatherMap One Call 3.0
  3. on calcule un "weather score" résumant la qualité du temps

Le résultat est un DataFrame propre, prêt à être sauvegardé en CSV.
"""

import time
from datetime import date

import requests
import pandas as pd

from . import config


def geocoder_ville(ville):
    """
    Renvoie (latitude, longitude, pays) pour une ville, ou None si échec.
    On utilise Nominatim, gratuit et sans clé.
    """
    params = {
        "q": ville,
        "format": "json",
        "addressdetails": 1,
        "limit": 1,
        "email": config.CONTACT_EMAIL,  # exigé par la politique d'usage
    }
    reponse = requests.get(
        config.NOMINATIM_URL,
        params=params,
        headers={"User-Agent": config.USER_AGENT},
        timeout=20,
    )

    # Si la requête échoue ou ne renvoie rien d'exploitable, on abandonne.
    if reponse.status_code != 200 or not reponse.json():
        return None

    resultat = reponse.json()[0]
    latitude = float(resultat["lat"])
    longitude = float(resultat["lon"])
    pays = resultat.get("address", {}).get("country", "Inconnu")
    return latitude, longitude, pays


def recuperer_meteo(latitude, longitude, api_key, n_jours=config.NB_JOURS_PREVISION):
    """
    Renvoie la liste des prévisions journalières pour un point GPS,
    ou None en cas d'échec.
    Utilise l'API One Call 3.0 d'OpenWeatherMap, qui expose directement un
    tableau `daily` de 8 jours : on ne garde que les `n_jours` premiers.
    L'énoncé demande la fenêtre des 7 prochains jours.
    """
    params = {
        "lat": latitude,
        "lon": longitude,
        "appid": api_key,
        "units": "metric",
        # On ne demande que le journalier : le reste serait téléchargé pour rien.
        "exclude": "current,minutely,hourly,alerts",
    }
    reponse = requests.get(config.OWM_ONECALL_URL, params=params, timeout=20)

    if reponse.status_code != 200:
        return None

    daily = reponse.json().get("daily", [])
    if not daily:
        return None

    return daily[:n_jours]


def calculer_weather_score(temp_moy, humidite_moy, pluie_totale):
    """
    Calcule un score de 0 à 100 résumant la qualité du temps.
    Logique : on part de 100 et on retire des points selon 3 critères
    (température, humidité, pluie). Plus on s'éloigne de l'idéal, plus on perd.
    On fait ensuite la moyenne des trois sous-scores.
    """
    # Sous-score température : pénalité par degré d'écart avec 20°C.
    ecart_temp = abs(temp_moy - config.TEMP_IDEALE)
    score_temp = 100 - ecart_temp * config.PENALITE_PAR_DEGRE

    # Sous-score humidité : on ne pénalise que l'excès au-dessus de 40%.
    exces_hum = max(0, humidite_moy - config.HUMIDITE_IDEALE)
    score_hum = 100 - exces_hum * config.PENALITE_PAR_PCT_HUM

    # Sous-score pluie : pénalité par mm cumulé sur la semaine.
    score_pluie = 100 - pluie_totale * config.PENALITE_PAR_MM_PLUIE

    # Moyenne des trois, puis on borne le résultat entre 0 et 100.
    score = (score_temp + score_hum + score_pluie) / 3
    return max(0, min(100, score))


def collecter_meteo(api_key, villes=None, pause=1.0):
    """
    Boucle principale : construit le DataFrame météo des villes demandées.
    `pause` : temps d'attente entre deux villes pour respecter Nominatim.
    Renvoie un DataFrame avec une ligne par ville et un id unique.
    """
    if villes is None:
        villes = config.VILLES

    lignes = []

    # enumerate(..., start=1) donne directement un id unique par ville.
    for id_ville, ville in enumerate(villes, start=1):
        geo = geocoder_ville(ville)
        if geo is None:
            print(f"  [!] Géolocalisation échouée : {ville}")
            time.sleep(pause)
            continue
        latitude, longitude, pays = geo

        daily = recuperer_meteo(latitude, longitude, api_key)
        if not daily:
            print(f"  [!] Météo indisponible : {ville}")
            time.sleep(pause)
            continue

        # On agrège les 7 jours en quelques indicateurs simples.
        temp_moy = sum(j["temp"]["day"] for j in daily) / len(daily)
        humidite_moy = sum(j["humidity"] for j in daily) / len(daily)
        pluie_totale = sum(j.get("rain", 0) for j in daily)
        pop_moy = sum(j.get("pop", 0) for j in daily) / len(daily)

        weather = calculer_weather_score(temp_moy, humidite_moy, pluie_totale)

        lignes.append({
            "id": id_ville,
            "city": ville,
            "latitude": latitude,
            "longitude": longitude,
            "country": pays,
            "fetch_date": date.today().isoformat(),
            "forecast_end_date": date.fromtimestamp(daily[-1]["dt"]).isoformat(),
            "avg_temp_7j": round(temp_moy, 2),
            "avg_humidity_7j": round(humidite_moy, 2),
            "total_rain_7j": round(pluie_totale, 2),
            "avg_pop_7j": round(pop_moy, 2),
            "weather_score": round(weather, 2),
        })
        print(f"  [OK] {ville:<30} weather={weather:5.1f}")

        time.sleep(pause)  # politesse envers Nominatim

    return pd.DataFrame(lignes)
