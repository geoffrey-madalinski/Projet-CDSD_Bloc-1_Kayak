"""
hotels.py
---------
Scraping du top 3 des hôtels par ville sur Booking.com.

On utilise Selenium pour charger la page (Booking est dynamique, un simple
requests ne suffit pas) puis Parsel pour extraire proprement les informations.

Remarque importante : les noms de classes CSS de Booking changent souvent.
Si le scraping renvoie 0 hôtel, c'est presque toujours qu'il faut mettre à
jour les sélecteurs CSS ci-dessous en inspectant la page.
"""

import time

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from parsel import Selector
from urllib.parse import quote_plus

from . import config


def _creer_driver():
    """
    Crée un navigateur Chrome "headless" (sans interface graphique).

    Les options --no-sandbox / --disable-dev-shm-usage évitent les plantages
    fréquents quand on tourne dans un conteneur ou un environnement limité.
    """
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-agent={config.USER_AGENT}")
    return webdriver.Chrome(options=options)


def _construire_url(ville):
    """Construit l'URL de recherche Booking triée par note utilisateurs."""
    return (
        "https://www.booking.com/searchresults.html"
        f"?ss={quote_plus(ville)}&lang=fr&group_adults=2&no_rooms=1"
        "&group_children=0&order=review_score_and_count"
    )


def scraper_ville(ville, n_hotels=3):
    """
    Renvoie un DataFrame des `n_hotels` meilleurs hôtels d'une ville.

    On ouvre la page, on scrolle un peu pour déclencher le chargement
    dynamique, puis on parse le HTML obtenu.
    """
    driver = _creer_driver()
    try:
        driver.get(_construire_url(ville))
        time.sleep(3)  # laisser la page se charger

        # Booking charge les résultats au scroll : on descend 3 fois.
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        selector = Selector(text=driver.page_source)
    except Exception as erreur:
        print(f"  [!] Erreur Selenium ({ville}) : {erreur}")
        return pd.DataFrame()
    finally:
        # On ferme toujours le navigateur, même en cas d'erreur.
        driver.quit()

    # Chaque bloc correspond à une carte hôtel dans la liste de résultats.
    blocs = selector.css("div[data-testid='property-card']")

    lignes = []
    for bloc in blocs[:n_hotels]:
        nom = bloc.css("div[data-testid='title']::text").get()
        note = bloc.css("[data-testid='review-score'] div[aria-hidden='true']::text").get()
        desc_candidats = [
            t.strip() for t in bloc.css("div.fff1944c52:not(.f4008c3a61)::text").getall()
            if len(t.strip()) > 60
        ]
        description = desc_candidats[0] if desc_candidats else None
        lien = bloc.css("a[data-testid='title-link']::attr(href)").get()

        # On nettoie la note ("8,9" -> 8.9) si elle est présente.
        if note:
            note = note.replace(",", ".").strip()
            try:
                note = float(note)
            except ValueError:
                note = None

        lignes.append({
            "city": ville,
            "hotel_name": nom.strip() if nom else None,
            "note": note,
            "description": description.strip() if description else None,
            "lien": lien,
        })

    return pd.DataFrame(lignes)


def scraper_toutes_villes(villes=None, n_hotels=3):
    """
    Boucle sur toutes les villes et concatène les résultats.

    On ajoute un id unique global à la fin pour la cohérence avec la base.
    """
    if villes is None:
        villes = config.VILLES

    morceaux = []
    for ville in villes:
        print(f"  Scraping : {ville}")
        df_ville = scraper_ville(ville, n_hotels=n_hotels)
        if not df_ville.empty:
            morceaux.append(df_ville)
        time.sleep(1)  # on évite de marteler le serveur

    if not morceaux:
        return pd.DataFrame()

    df = pd.concat(morceaux, ignore_index=True)
    df.insert(0, "id", range(1, len(df) + 1))  # id unique par hôtel
    return df
