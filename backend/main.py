import os
import duckdb

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from functools import lru_cache

ERG_API = "https://api.erg.ic.ac.uk/AirQuality"

app = FastAPI(title="London Air Quality API")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT_DIR, "data", "air_quality.duckdb")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def query_db(sql, params=None):
    with duckdb.connect(DB_PATH, read_only=True) as con:
        return con.execute(sql, params or []).fetchdf().to_dict(
            orient="records"
        )


@app.get("/api/boroughs")
def get_boroughs():
    return query_db("""
        SELECT
            borough,
            AVG(air_quality_index) AS average_index,
            MAX(air_quality_index) AS maximum_index,
            COUNT(DISTINCT site_code) AS site_count,
            AVG(latitude) AS latitude,
            AVG(longitude) AS longitude
        FROM daily_readings
        WHERE borough IS NOT NULL
        GROUP BY borough
    """)


@app.get("/api/sites")
def get_sites():
    return query_db("""
        SELECT *
        FROM daily_readings
        ORDER BY borough, site_name
    """)


@app.get("/api/boroughs/{borough}/sites")
def get_borough_sites(borough: str):
    return query_db("""
        SELECT *
        FROM daily_readings
        WHERE LOWER(TRIM(borough)) = LOWER(TRIM(?))
        ORDER BY site_name, pollutant
    """, [borough])

@app.get("/api/health")
def health():
    return {"status": "running"}

@lru_cache(maxsize=10)
def fetch_health_advice(index: int):
    url = (
        f"{ERG_API}/Information/IndexHealthAdvice/"
        f"AirQualityIndex={index}/Json"
    )

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    return response.json()


@app.get("/api/health-advice/{index}")
def get_health_advice(index: int):
    if not 1 <= index <= 10:
        return {"error": "Index must be between 1 and 10"}

    return fetch_health_advice(index)