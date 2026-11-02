import os
import logging
import pandas as pd
import requests
from datetime import date, timedelta
from urllib.parse import quote
from typing import Optional, Any
import json
import duckdb
from analysis import print_analysis

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, 'data')
LOG_DIR = os.path.join(ROOT_DIR, 'logging')

BASE_URL = "https://api.erg.ic.ac.uk/AirQuality"

RAW_DIR = os.path.join(DATA_DIR, "raw", "daily")

START_DATE = date(2026, 10, 1)
END_DATE = date(2026, 11, 4)

REFRESH_RAW = False

URLS = {
    "sites": f"{BASE_URL}/Information/MonitoringSites/GroupName=London/Json",
    "daily": f"{BASE_URL}/Daily/MonitoringIndex/Latest/GroupName=London/Json"
}

DB_PATH = os.path.join(DATA_DIR, "air_quality.duckdb")

def fetch_data(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()

def get_daily_data(day):
    os.makedirs(RAW_DIR, exist_ok=True)

    filename = os.path.join(
        RAW_DIR,
        f"{day.isoformat()}.json"
    )

    # Reuse the original response if we already have it.
    if os.path.exists(filename) and not REFRESH_RAW:
        print(f"Loading backup: {day}")
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)

    date_string = quote(day.strftime("%d %b %Y"), safe="")

    url = (
        f"{BASE_URL}/Daily/MonitoringIndex/"
        f"GroupName=London/Date={date_string}/Json"
    )

    print(f"Downloading: {day}")

    data = fetch_data(url)

    # Save the original API response.
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return data

def collect_historical_data(start_date, end_date):
    all_readings = []

    current_date = start_date

    while current_date <= end_date:
        daily_json = get_daily_data(current_date)

        daily_readings = extract_daily_readings(daily_json)

        if not daily_readings.empty:
            all_readings.append(daily_readings)

        current_date += timedelta(days=1)

    if not all_readings:
        return pd.DataFrame()

    return pd.concat(all_readings, ignore_index=True)


def clean_keys(record):
    return {
        key.lstrip("@"): value
        for key, value in record.items()
    }


def extract_sites(data):
    sites = []

    def walk(obj):
        if isinstance(obj, dict):
            record = clean_keys(obj)

            if "SiteCode" in record:
                sites.append(record)

            for value in obj.values():
                walk(value)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return pd.DataFrame(sites).drop_duplicates("SiteCode")


def as_list(value):
    """Normalise an API object or array into a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def extract_daily_readings(data):
    readings = []

    daily = data.get("DailyAirQualityIndex", {})

    monitoring_date = daily.get("@MonitoringIndexDate")

    authorities = as_list(daily.get("LocalAuthority"))

    for authority in authorities:

        borough = authority.get("@LocalAuthorityName")
        authority_code = authority.get("@LocalAuthorityCode")

        sites = as_list(authority.get("Site"))

        for site in sites:

            site_code = site.get("@SiteCode")
            site_name = site.get("@SiteName")

            bulletin_date = site.get(
                "@BulletinDate", monitoring_date
            )

            latitude = site.get("@Latitude")
            longitude = site.get("@Longitude")

            species_list = as_list(site.get("Species"))

            for species in species_list:

                readings.append({
                    "site_code": site_code,
                    "site_name": site_name,
                    "borough": borough,
                    "authority_code": authority_code,
                    "latitude": latitude,
                    "longitude": longitude,
                    "pollutant": species.get("@SpeciesCode"),
                    "pollutant_name": species.get("@SpeciesDescription"),
                    "air_quality_index": species.get("@AirQualityIndex"),
                    "air_quality_band": species.get("@AirQualityBand"),
                    "index_source": species.get("@IndexSource"),
                    "recorded_at": bulletin_date
                })

    return pd.DataFrame(readings)



def run_pipeline():

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)

    # 1. Retrieve site metadata.
    sites_json = fetch_data(URLS["sites"])
    sites = extract_sites(sites_json)

    # 2. Collect historical daily readings.
    readings = collect_historical_data(
        START_DATE,
        END_DATE
    )

    if readings.empty:
        raise ValueError("No historical readings were retrieved.")

    # 3. Transform site metadata.
    sites = sites.rename(columns={
        "SiteCode": "site_code",
        "SiteName": "site_name",
        "LocalAuthorityName": "borough",
        "Latitude": "latitude",
        "Longitude": "longitude",
        "SiteType": "site_type"
    })

    site_columns = [
        "site_code",
        "site_name",
        "borough",
        "latitude",
        "longitude",
        "site_type"
    ]

    for column in site_columns:
        if column not in sites.columns:
            sites[column] = None

    sites = sites[site_columns].drop_duplicates("site_code")

    # 4. Transform readings.
    readings["air_quality_index"] = pd.to_numeric(
        readings["air_quality_index"],
        errors="coerce"
    )

    readings["latitude"] = pd.to_numeric(
        readings["latitude"],
        errors="coerce"
    )

    readings["longitude"] = pd.to_numeric(
        readings["longitude"],
        errors="coerce"
    )

    readings["recorded_at"] = pd.to_datetime(
        readings["recorded_at"],
        errors="coerce"
    )

    readings = readings.dropna(
        subset=["site_code", "air_quality_index", "recorded_at"]
    )

    readings = readings[
        readings["air_quality_index"].between(1, 10)
    ].copy()

    # Add site metadata to readings.
    readings = readings.merge(
        sites[["site_code", "site_type"]],
        on="site_code",
        how="left"
    )

    readings = readings.drop_duplicates(
        subset=["site_code", "pollutant", "recorded_at"]
    )

    # 5. Print dataset analysis.
    print_analysis(readings, sites)

    # 6. Persist data.
    with duckdb.connect(DB_PATH) as con:

        con.register("sites_df", sites)
        con.register("readings_df", readings)

        con.execute("""
            CREATE OR REPLACE TABLE monitoring_sites AS
            SELECT * FROM sites_df
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS daily_readings AS
            SELECT * FROM readings_df
            WHERE FALSE
        """)

        before = con.execute(
            "SELECT COUNT(*) FROM daily_readings"
        ).fetchone()

        before = before[0] if before else 0

        print(con.execute("DESCRIBE daily_readings").df())
        print("Incoming columns:", readings.columns.tolist())
        print("Incoming column count:", len(readings.columns))

        con.execute("""
        INSERT INTO daily_readings (
            site_code,
            site_name,
            borough,
            authority_code,
            latitude,
            longitude,
            pollutant,
            pollutant_name,
            air_quality_index,
            air_quality_band,
            index_source,
            recorded_at,
            site_type
        )
        SELECT
            incoming.site_code,
            incoming.site_name,
            incoming.borough,
            incoming.authority_code,
            incoming.latitude,
            incoming.longitude,
            incoming.pollutant,
            incoming.pollutant_name,
            incoming.air_quality_index,
            incoming.air_quality_band,
            incoming.index_source,
            incoming.recorded_at,
            incoming.site_type
        FROM readings_df incoming
        WHERE NOT EXISTS (
            SELECT 1
            FROM daily_readings existing
            WHERE existing.site_code = incoming.site_code
            AND existing.pollutant = incoming.pollutant
            AND existing.recorded_at = incoming.recorded_at
        )
        """)

        after = con.execute(
            "SELECT COUNT(*) FROM daily_readings"
        ).fetchone()

        after = after[0] if after else 0

        print(f"Records before: {before}")
        print(f"Records after: {after}")
        print(f"New records inserted: {after - before}")

