# Plan your trip with Kayak

> Mandatory project for **block 1** (Building and feeding a data management infrastructure) of the French **CDSD certification** | Concepteur Développeur en
> Science des Données | RNCP35288 | JEDHA

Building an end-to-end data infrastructure for Kayak's marketing team, which wants
to launch an app that **recommends holiday destinations and hotels** based on real
weather and hotel data.<br>
The pipeline orchestrates the full chain: **collection → data lake → ETL → data
warehouse → visualisation**.

## Problem statement

A user study revealed that 70% of travellers would like more information about their
destination, and that people are sceptical of content from brands they don't know.
The marketing team therefore wants a data-driven app that recommends the best
destinations and hotels at any time. The team starts with no data, so the task is to
**build the underlying data infrastructure from scratch**.

## Objectives

- Collect destination data for **35 pre-selected French cities** via the [Nominatim](https://nominatim.org) API
- Retrieve **weather forecasts** for each destination via the [OpenWeatherMap](https://openweathermap.org) API
- Collect **hotel information** for each destination by scraping [Booking.com](https://booking.com)
- Store all of the above as CSV files in a **data lake** on AWS S3
- Extract, transform and load (ETL) the cleaned data from the data lake into a **data warehouse** on NeonDB

## Technical stack

- **Collection**: Nominatim (geocoding), OpenWeatherMap One Call (7-day forecast), Selenium + Parsel (Booking.com scraping)
- **Data lake**: AWS S3 (boto3)
- **ETL**: Python — Pandas, psycopg2
- **Data warehouse**: Neon DB (serverless PostgreSQL)
- **Visualisation**: Plotly
- **Config & secrets**: python-dotenv

## Infrastructure overview

| Step | Tool | Role |
|---|---|---|
| Weather collection | Nominatim + OpenWeatherMap | GPS coordinates + 7-day forecast |
| Hotel collection | Selenium + Parsel | top 3 Booking hotels per city |
| Data lake | AWS S3 | raw, cheap, scalable storage |
| ETL | Python (pandas + psycopg2) | extract / transform / load |
| Data warehouse | Neon DB (serverless PostgreSQL) | clean, queryable data |
| Visualisation | Plotly | maps of destinations and hotels |

## Installation

```bash
git clone https://github.com/geoffrey-madalinski/Projet_Kayak.git
cd Projet_Kayak
pip install -r requirements.txt
```

Create a `.env` file at the project root with your secret keys (never versioned -
it lives in `.gitignore`):

```env
api_key=YOUR_OPENWEATHERMAP_KEY
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
DATABASE_URL=postgresql://...neon.tech/...
```

## Usage

```bash
jupyter notebook Projet_Kayak_GM.ipynb
```

The business logic lives in the `src/` package (one module per step). The notebook
simply calls each module in order, keeping it readable and the functions reusable
and testable elsewhere.

## Project structure

```
Projet_Kayak/
├── data/
│   └── processed/
│       ├── villes_meteo.csv          # collected weather data
│       └── df_top3_hotels.csv        # collected hotel data
├── docs/                             # project statement, logos
├── notebooks/
│   └── Projet_Kayak_GM.ipynb         # orchestration notebook
├── reports/
│   └── figures/                      # exported Plotly maps (HTML + PNG)
├── src/
│   ├── config.py                     # cities, paths, scoring settings
│   ├── weather.py                    # Nominatim + OpenWeatherMap collection
│   ├── hotels.py                     # Booking.com scraping
│   ├── data_lake.py                  # S3 upload/download
│   ├── etl.py                        # extract / transform / load
│   └── viz.py                        # Plotly maps
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

## Approach

1. **Imports & configuration** — make `src/` importable, load secret keys from `.env`
2. **Weather collection** — GPS via Nominatim, 7-day forecast via OpenWeatherMap, then a `weather_score` (0–100) summarising forecast quality
3. **Hotel collection** — scrape Booking.com (Selenium + Parsel) for the top 3 hotels per city (name, rating, description, link)
4. **Data lake** — save CSVs locally, then upload them to an S3 bucket
5. **ETL** — extract from S3, transform (deduplicate, validate value ranges and GPS coordinates, clean text), load into Neon DB; the pipeline is **replayable** (tables are cleared before reloading)
6. **Visualisation** — two Plotly maps: top 5 destinations by weather score, and the top 20 best-rated hotels
7. **Conclusion** — synthesis of the complete infrastructure

## The `weather_score`

Each city starts at 100 points; penalties are applied across three criteria and then averaged:

- **temperature** — points lost the further it is from 20 °C
- **humidity** — points lost beyond 40%
- **rain** — points lost per mm accumulated over the week

Ideal values and penalties are configurable in `src/config.py`.

## Notes & caveats

- **Hotel scraping is slow** (one browser session per city).
- Booking's CSS classes change regularly: if a city returns 0 hotels, update the selectors in `src/hotels.py`.
- **GDPR**: only *public* data about *establishments* is collected — no personal user data is processed.

## Author

**Geoffrey MADALINSKI** - Certification CDSD (RNCP35288) - JEDHA

---
