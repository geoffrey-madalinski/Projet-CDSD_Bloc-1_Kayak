"""
viz.py
------
Génération des cartes Plotly et sauvegarde dans reports/figures/.

Conformément au livrable demandé, on produit deux cartes :
  - Carte 1 : les 5 destinations incontournables (meilleur weather score)
  - Carte 2 : les 20 hôtels les plus populaires (meilleures notes)

Chaque figure est exportée en HTML (interactif) et en PNG (statique, pour
un rapport). Le PNG nécessite le paquet `kaleido`.
"""

import plotly.express as px
import plotly.graph_objects as go

from . import config


def _hotels_par_ville(df_hotels, ville):
    """Construit le petit texte 'Top 3 hôtels' affiché au survol d'une ville."""
    hotels = df_hotels[df_hotels["city"] == ville].sort_values("note", ascending=False)
    if hotels.empty:
        return "Aucun hôtel trouvé"
    texte = "<b>Top 3 hôtels :</b><br>"
    for i, (_, ligne) in enumerate(hotels.iterrows(), start=1):
        note = ligne["note"] if "note" in ligne else "?"
        texte += f"{i}. {ligne['hotel_name']} — {note}/10<br>"
    return texte


def carte_top_destinations(df_weather, df_hotels, n=35):
    """
    Carte des n meilleures destinations (par weather score).

    La taille et la couleur des points reflètent le weather score ; le survol
    affiche le top 3 des hôtels de la ville.
    """
    # On garde les n villes au meilleur score.
    top = df_weather.sort_values("weather_score", ascending=False).head(n).copy()
    top["hotels_text"] = top["city"].apply(lambda v: _hotels_par_ville(df_hotels, v))

    fig = px.scatter_map(
        top,
        lat="latitude",
        lon="longitude",
        hover_name="city",
        color="weather_score",
        size="weather_score",
        color_continuous_scale="RdYlGn",
        size_max=25,
        zoom=4.3,
        map_style="carto-positron",
        hover_data={"latitude": False, "longitude": False, "weather_score": False},
    )
    fig.update_traces(
        customdata=list(zip(top["weather_score"], top["hotels_text"])),
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Weather_score : <b>%{customdata[0]:.1f}</b><br>"
            "%{customdata[1]}<extra></extra>"
        ),
    )

    # Calque Top 5 : étoiles dorées avec label + numéro de rang
    top5 = top.head(5).copy().reset_index(drop=True)
    top5["rank_label"] = [f"#{i+1} {c}" for i, c in enumerate(top5["city"])]
    fig.add_trace(go.Scattermap(
        lat=top5["latitude"],
        lon=top5["longitude"],
        mode="markers+text",
        marker=dict(size=22, color="gold", symbol="star"),
        text=top5["rank_label"],
        textposition="top right",
        textfont=dict(size=11, color="#222", family="Arial Black"),
        customdata=list(zip(top5["weather_score"], top5["hotels_text"])),
        hovertemplate=(
            "<b>⭐ %{text}</b><br>"
            "Score : %{customdata[0]:.1f}<br>"
            "%{customdata[1]}<extra>Top 5</extra>"
        ),
        name="Top 5 weather score",
        showlegend=True,
    ))

    fig.update_layout(
        title="Prévision météorologique à 7 jours | Weather score (%)",
        height=650, width=600,
        margin=dict(l=0, r=0, b=0, t=50),
        coloraxis_colorbar=dict(title="Score"),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )
    return fig


def carte_top_hotels(df_weather, df_hotels, n=20):
    """
    Carte des n hôtels les mieux notés, toutes villes confondues.

    On récupère les coordonnées via la ville (jointure avec df_weather), ce
    qui évite un géocodage supplémentaire des hôtels.
    """
    # Jointure pour récupérer lat/lon de la ville de chaque hôtel.
    df = df_hotels.merge(
        df_weather[["city", "latitude", "longitude"]],
        on="city", how="left",
    )
    top = df.sort_values("note", ascending=False).head(n).copy()

    fig = px.scatter_map(
        top,
        lat="latitude",
        lon="longitude",
        hover_name="hotel_name",
        color="note",
        size="note",
        color_continuous_scale="Viridis",
        size_max=20,
        zoom=4.3,
        map_style="carto-positron",
        hover_data={"city": True, "latitude": False, "longitude": False},
    )
    fig.update_layout(
        title=f"Top {n} des hôtels les mieux notés (note Booking)",
        height=650, width=600,
        margin=dict(l=0, r=0, b=0, t=50),
        coloraxis_colorbar=dict(title="Note /10"),
    )
    return fig


def sauvegarder(fig, nom_fichier):
    """
    Sauvegarde une figure dans reports/figures/ en HTML et (si possible) PNG.

    Le PNG dépend de `kaleido` ; s'il n'est pas installé, on garde au moins
    le HTML interactif et on prévient l'utilisateur.
    """
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    chemin_html = config.FIGURES_DIR / f"{nom_fichier}.html"
    fig.write_html(str(chemin_html))
    print(f"  [OK] {chemin_html}")

    try:
        chemin_png = config.FIGURES_DIR / f"{nom_fichier}.png"
        fig.write_image(str(chemin_png), scale=2)
        print(f"  [OK] {chemin_png}")
    except Exception as erreur:
        print(f"  [i] PNG non généré ({erreur}). Installe 'kaleido' si besoin.")


def generer_toutes_figures(df_weather, df_hotels):
    """Génère et sauvegarde les deux cartes du livrable."""
    fig1 = carte_top_destinations(df_weather, df_hotels, n=5)
    sauvegarder(fig1, "carte_top5_destinations")

    fig2 = carte_top_hotels(df_weather, df_hotels, n=20)
    sauvegarder(fig2, "carte_top20_hotels")
