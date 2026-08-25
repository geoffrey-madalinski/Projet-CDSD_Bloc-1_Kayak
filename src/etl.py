"""
etl.py
------
Processus ETL : du data lake (S3) vers le data warehouse (Neon DB).

  - Extract   : on relit les CSV depuis S3
  - Transform : on nettoie et on valide (doublons, plages de valeurs, texte)
  - Load      : on insère dans PostgreSQL (Neon DB) par upsert sur clé naturelle,
                ce qui rend le pipeline rejouable sans créer de doublon

L'entrepôt SQL est ce que les analystes interrogeront ensuite : il doit
contenir des données propres et accessibles facilement.
"""

import os
import math

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from . import config, data_lake


# ---------------------------------------------------------------------------
# EXTRACT
# ---------------------------------------------------------------------------
def extract():
    """Relit les deux datasets depuis le data lake S3."""
    df_weather = data_lake.telecharger_csv("villes_meteo.csv")
    df_hotels = data_lake.telecharger_csv("df_top3_hotels.csv")
    print(f"  Extract : {len(df_weather)} villes, {len(df_hotels)} hôtels")
    return df_weather, df_hotels


# ---------------------------------------------------------------------------
# TRANSFORM
# ---------------------------------------------------------------------------
def transform(df_weather, df_hotels):
    """
    Nettoie et valide les données avant chargement.

    Étapes : suppression des doublons, contrôle des plages de valeurs
    (weather_score dans [0-100], note dans [0-10]), nettoyage du texte.
    """
    # 1) Doublons : une ville n'apparaît qu'une fois, un hôtel une fois par ville.
    df_weather = df_weather.drop_duplicates(subset=["city"]).copy()
    df_hotels = df_hotels.drop_duplicates(subset=["city", "hotel_name"]).copy()

    # 2) Plages de valeurs : on "clippe" ce qui dépasse plutôt que de jeter.
    df_weather["weather_score"] = df_weather["weather_score"].clip(0, 100)
    if "note" in df_hotels.columns:
        df_hotels["note"] = df_hotels["note"].clip(0, 10)

    # 3) Coordonnées GPS plausibles (France métropolitaine, large marge).
    df_weather = df_weather[
        df_weather["latitude"].between(40, 52)
        & df_weather["longitude"].between(-5, 10)
    ]

    # 4) Nettoyage du texte : on enlève les espaces superflus.
    df_hotels["hotel_name"] = df_hotels["hotel_name"].astype(str).str.strip()
    if "description" in df_hotels.columns:
        df_hotels["description"] = (
            df_hotels["description"].fillna("").astype(str).str.strip()
        )

    # 5) Garde-fou sur la clé naturelle : (city, hotel_name) est la clé primaire
    #    côté entrepôt, donc aucune des deux colonnes ne peut être vide.
    avant = len(df_hotels)
    df_hotels = df_hotels[
        df_hotels["hotel_name"].notna()
        & (df_hotels["hotel_name"].str.lower() != "nan")
        & (df_hotels["hotel_name"] != "")
        & df_hotels["city"].notna()
    ]
    if len(df_hotels) < avant:
        print(f"  [!] {avant - len(df_hotels)} hôtel(s) écarté(s) : clé incomplète")

    print(f"  Transform : {len(df_weather)} villes, {len(df_hotels)} hôtels après nettoyage")
    return df_weather, df_hotels


# ---------------------------------------------------------------------------
# LOAD
# ---------------------------------------------------------------------------
def _connexion():
    """Ouvre une connexion PostgreSQL vers Neon DB (paramètres dans le .env)."""
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        sslmode=os.getenv("PGSSLMODE", "require"),  # Neon impose le SSL
    )


def _nan_vers_none(valeur):
    """psycopg2 ne sait pas insérer NaN : on le convertit en None (NULL SQL)."""
    if valeur is None:
        return None
    try:
        if math.isnan(float(valeur)):
            return None
    except (TypeError, ValueError):
        pass
    return valeur


def reinitialiser_tables():
    """
    Supprime les tables. À n'appeler que si le schéma change.

    En usage courant on ne détruit rien : creer_tables() est non destructif et
    load() met à jour l'existant par upsert.
    """
    conn = _connexion()
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS hotels;")
    cur.execute("DROP TABLE IF EXISTS weather;")
    conn.commit()
    cur.close()
    conn.close()
    print("  [OK] Tables weather et hotels supprimées")


def creer_tables():
    """
    Crée les tables si elles n'existent pas. Opération non destructive.

    Choix de conception : la clé primaire est une clé NATURELLE (métier), et
    non un compteur technique.
      - weather : city
      - hotels  : (city, hotel_name)
    """
    conn = _connexion()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS weather (
            id                INTEGER,
            city              VARCHAR(100) NOT NULL,
            latitude          FLOAT,
            longitude         FLOAT,
            country           VARCHAR(100),
            fetch_date        DATE,
            forecast_end_date DATE,
            avg_temp_7j       FLOAT,
            avg_humidity_7j   FLOAT,
            total_rain_7j     FLOAT,
            avg_pop_7j        FLOAT,
            weather_score     FLOAT,
            CONSTRAINT weather_pk PRIMARY KEY (city)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hotels (
            id          INTEGER,
            city        VARCHAR(100) NOT NULL,
            hotel_name  VARCHAR(255) NOT NULL,
            note        FLOAT,
            description TEXT,
            lien        TEXT,
            CONSTRAINT hotels_pk PRIMARY KEY (city, hotel_name)
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("  [OK] Tables weather et hotels prêtes (clé naturelle)")


def load(df_weather, df_hotels):
    """
    Insère les DataFrames nettoyés dans Neon DB.
    """
    conn = _connexion()
    cur = conn.cursor()

    lignes_weather = [
        (
            int(r.id), r.city, r.latitude, r.longitude, r.country,
            r.fetch_date, r.forecast_end_date,
            r.avg_temp_7j, r.avg_humidity_7j, r.total_rain_7j,
            r.avg_pop_7j, r.weather_score,
        )
        for r in df_weather.itertuples()
    ]
    execute_values(cur, """
        INSERT INTO weather
            (id, city, latitude, longitude, country,
             fetch_date, forecast_end_date,
             avg_temp_7j, avg_humidity_7j, total_rain_7j, avg_pop_7j, weather_score)
        VALUES %s
        ON CONFLICT (city) DO UPDATE SET
            id                = EXCLUDED.id,
            latitude          = EXCLUDED.latitude,
            longitude         = EXCLUDED.longitude,
            country           = EXCLUDED.country,
            fetch_date        = EXCLUDED.fetch_date,
            forecast_end_date = EXCLUDED.forecast_end_date,
            avg_temp_7j       = EXCLUDED.avg_temp_7j,
            avg_humidity_7j   = EXCLUDED.avg_humidity_7j,
            total_rain_7j     = EXCLUDED.total_rain_7j,
            avg_pop_7j        = EXCLUDED.avg_pop_7j,
            weather_score     = EXCLUDED.weather_score;
    """, lignes_weather)

    lignes_hotels = [
        (
            int(r.id), r.city, r.hotel_name, _nan_vers_none(r.note),
            _nan_vers_none(getattr(r, "description", None)),
            _nan_vers_none(getattr(r, "lien", None)),
        )
        for r in df_hotels.itertuples()
    ]
    execute_values(cur, """
        INSERT INTO hotels (id, city, hotel_name, note, description, lien)
        VALUES %s
        ON CONFLICT (city, hotel_name) DO UPDATE SET
            id          = EXCLUDED.id,
            note        = EXCLUDED.note,
            description = EXCLUDED.description,
            lien        = EXCLUDED.lien;
    """, lignes_hotels)

    conn.commit()
    cur.close()
    conn.close()
    print(f"  [OK] Load : {len(lignes_weather)} villes, {len(lignes_hotels)} hôtels "
          f"insérés ou mis à jour")


def verifier():
    """Contrôle final : compte les lignes et affiche le top 5 destinations."""
    conn = _connexion()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM weather;")
    n_weather = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM hotels;")
    n_hotels = cur.fetchone()[0]

    cur.execute(
        "SELECT city, weather_score FROM weather "
        "ORDER BY weather_score DESC LIMIT 5;"
    )
    top5 = cur.fetchall()

    cur.close()
    conn.close()

    print(f"  weather : {n_weather} lignes  |  hotels : {n_hotels} lignes")
    print("  Top 5 destinations :")
    for ville, score in top5:
        print(f"    {ville:<30} {score:.1f}")


def run_etl(reinitialiser=False):
    """
    Enchaîne tout le pipeline ETL en une seule fonction.

    `reinitialiser=True` supprime les tables avant de les recréer : à réserver
    aux changements de schéma. En usage courant on laisse False, l'upsert de
    load() suffit à maintenir l'entrepôt à jour sans jamais le vider.
    """
    df_weather, df_hotels = extract()
    df_weather, df_hotels = transform(df_weather, df_hotels)
    if reinitialiser:
        reinitialiser_tables()
    creer_tables()
    load(df_weather, df_hotels)
    verifier()
