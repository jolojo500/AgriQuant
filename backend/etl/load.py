import os
from dotenv import load_dotenv
from supabase import create_client, Client
import json
import pandas as pd
from etl.extract_prices import PriceResponse
from etl.extract_weather import WeatherResponse, NasaResponse
from etl.extract_yields import YieldResponse


load_dotenv()

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

#L bit of the ETL pipeline only writes where it's later used so no fetch from db etc defined here

def load_raw_prices(prices: list[PriceResponse]) -> None:
    """
    Inserts daily price records for all halal universe tickers.
    Upserts on (ticker, date) so safe to re-run without duplicates.
    """
    rows = []
    for price_response in prices:
        for record in price_response.records:
            rows.append({
                "ticker": price_response.ticker,
                "date":   str(record.date),
                "close":  record.close,
                "volume": record.volume,
            })

    supabase.table("raw_prices").upsert(rows, on_conflict="ticker,date").execute()
    print(f"  raw_prices : {len(rows)} rows upserted")


def load_raw_weather(
    weather: WeatherResponse,
    nasa: NasaResponse,
) -> None:
    """
    Merges Open-Meteo and NASA POWER records for one region,
    then inserts into raw_weather.
    Upserts on (region, date).
    """
    nasa_by_date = {str(r.date): r for r in nasa.records}

    rows = []
    for w in weather.records:
        date_str = str(w.date)
        n = nasa_by_date.get(date_str)  # None if nasa has no record for that day

        rows.append({
            "region":          weather.region,
            "date":            date_str,
            "rainfall_mm":     w.rainfall_mm,
            "temp_max":        w.temp_max,
            "temp_min":        w.temp_min,
            "solar_radiation": n.solar_radiation if n else None,
            "humidity":        n.humidity        if n else None,
            "wind_speed":      n.wind_speed       if n else None,
        })

    supabase.table("raw_weather").upsert(rows, on_conflict="region,date").execute()
    print(f"  raw_weather [{weather.region}] : {len(rows)} rows upserted")


def load_raw_yields(yields: list[YieldResponse]) -> None:
    """
    Inserts annual crop yield records for all crop/country combinations.
    Upserts on (crop, country, year).
    """
    rows = []
    for yr in yields:
        for record in yr.records:
            rows.append({
                "crop":            record.crop,
                "country":         record.country,
                "year":            record.year,
                "yield_kg_ha":     record.yield_kg_ha,
                "yield_tonnes_ha": record.yield_tonnes_ha,
            })

    supabase.table("raw_yields").upsert(rows, on_conflict="crop,country,year").execute()
    print(f"  raw_yields : {len(rows)} rows upserted")


def load_ml_features(df_ml: pd.DataFrame) -> None:
    """
    Stores the final ML-ready DataFrame into ml_features.
    Each row = one (ticker, quarter) pair.
    All feature columns are packed into a single jsonb column.
    Target (stock_return_next_q) is stored separately for easy querying.
    Upserts on (ticker, quarter).
    """
    # Everything except ticker and target is a feature
    feature_cols = [
        c for c in df_ml.columns
        if c not in ("quarter","ticker", "stock_return_next_q")
    ]

    rows = []
    for date_idx, row in df_ml.iterrows():
        quarter = date_idx.to_period("Q").strftime("%YQ%q")

        rows.append({
            "ticker":  row["ticker"],
            "quarter": quarter,
            "features": json.dumps({
                col: (None if pd.isna(row[col]) else round(float(row[col]), 6))
                for col in feature_cols
            }),
            "target": (
                None if pd.isna(row["stock_return_next_q"])
                else round(float(row["stock_return_next_q"]), 6)
            ),
        })

    supabase.table("ml_features").upsert(rows, on_conflict="ticker,quarter").execute()
    print(f"  ml_features : {len(rows)} rows upserted")


if __name__ == "__main__":
    #Moved those here because all these arent needed for above funcs so only imports when this block runs
    from etl.extract_prices import fetch_all_prices
    from etl.extract_weather import (
        fetch_raw_weather, parse_weather,
        fetch_raw_nasa, parse_nasa,
    )
    from etl.extract_yields import download_faostat_bulk, fetch_all_yields
    from etl.transform import (
        build_weather_features, add_weather_lags,
        build_stock_features, add_stock_lags,
        build_yield_features, add_yield_lags,
        build_ml_dataset,
    )
    from etl.transform_config import WEATHER_REGIONS
    import time


    print("Step 1: Loading raw prices...")
    all_prices = fetch_all_prices()
    load_raw_prices(all_prices)

    print("\nStep 2 & 4a: Fetching weather...")
    for region in WEATHER_REGIONS:
        raw_weather = fetch_raw_weather(region["lat"], region["lon"])
        weather     = parse_weather(raw_weather, region["name"])
        raw_nasa    = fetch_raw_nasa(region["lat"], region["lon"])
        nasa        = parse_nasa(raw_nasa, region["name"])
        load_raw_weather(weather, nasa)  # raw insert
        time.sleep(2)  #Slow but makes so no rate limit in step 4          

    print("\nStep 3: Loading raw yields...")
    df_fao = download_faostat_bulk()
    all_yields = fetch_all_yields(df_fao)
    load_raw_yields(all_yields)

    print("\nStep 4: Building and loading ML features...")
    df_weather = add_weather_lags(build_weather_features())
    df_stocks  = add_stock_lags(build_stock_features())
    df_yields  = add_yield_lags(build_yield_features(df_fao))
    df_ml      = build_ml_dataset(df_weather, df_stocks, df_yields)
    load_ml_features(df_ml)

    print("\nDone,  all tables loaded.")