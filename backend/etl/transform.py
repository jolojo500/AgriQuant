import pandas as pd
import numpy as np
from datetime import date
from etl.transform_config import (
    WEATHER_REGIONS, WEATHER_FEATURES, CROPS,
    YIELD_COUNTRIES, LAG_FEATURES, START_YEAR, END_YEAR
)
from etl.extract_weather import fetch_raw_weather, parse_weather, fetch_raw_nasa, parse_nasa
from etl.extract_prices import fetch_prices, load_halal_universe

def weather_response_to_df(region: dict) -> pd.DataFrame:
    """
    Fetches Open-Meteo + NASA POWER for a region and returns
    a single daily DataFrame with all weather columns.
    """
    print(f"  Fetching weather for {region['name']}...")

    # Open-Meteo
    raw_weather = fetch_raw_weather(region["lat"], region["lon"])
    weather = parse_weather(raw_weather, region["name"])

    df_weather = pd.DataFrame([r.model_dump() for r in weather.records])
    df_weather["date"] = pd.to_datetime(df_weather["date"])

    # NASA POWER
    raw_nasa = fetch_raw_nasa(region["lat"], region["lon"])
    nasa = parse_nasa(raw_nasa, region["name"])

    df_nasa = pd.DataFrame([r.model_dump() for r in nasa.records])
    df_nasa["date"] = pd.to_datetime(df_nasa["date"])

    # Merge on date — inner join, keep only dates both sources have
    df = pd.merge(df_weather, df_nasa, on="date", suffixes=("", "_nasa"))


    df = df.set_index("date")

    return df


def aggregate_weather_quarterly(df_daily: pd.DataFrame, region_name: str) -> pd.DataFrame:
    """
    Aggregates daily weather into quarterly features.
    Each row = one quarter.

    Custom aggregations:
    - drought_days: count of days with rainfall < 2mm
    - heat_stress_days: count of days with temp_max > 35°C
    """
    # Resample to quarters , QS = Quarter Start for example starts at 2020-01-01 until 2020-04-01
    quarterly = df_daily.resample("QS").agg({ 
        "rainfall_mm":      "sum",    # total rain this quarter
        "temp_max":         "mean",   # avg of daily max temps
        "temp_min":         "mean",   # avg of daily min temps
        "solar_radiation":  "mean",   # avg solar energy
        "humidity":         "mean",   # avg humidity
        "wind_speed":       "mean",   # avg wind speed
    })

    # Custom features, can't do these with simple agg
    quarterly["drought_days"] = (
        df_daily["rainfall_mm"]
        .resample("QS")
        .apply(lambda x: (x < 2.0).sum())  # count days with < 2mm rain
    )

    quarterly["heat_stress_days"] = (
        df_daily["temp_max"]
        .resample("QS")
        .apply(lambda x: (x > 35.0).sum())  # count days above 35°C
    )

    # Add region prefix to all columns so we know where data comes from
    # ex: "rainfall_mm" → "iowa_rainfall_mm"
    quarterly.columns = [f"{region_name}_{col}" for col in quarterly.columns]

    # Add quarter label column for readability
    quarterly["quarter"] = quarterly.index.to_period("Q").astype(str) #index is date, we already aggreagated (grouped) by quarter so it knowns wihch Q it is (2020Q1 etc)

    return quarterly


def build_weather_features() -> pd.DataFrame:
    """
    Runs weather extraction + aggregation for all regions.
    Merges all regions into one wide DataFrame.
    Each row = one quarter, columns = all regions x all features.
    """
    all_regions = []

    for region in WEATHER_REGIONS:
        df_daily = weather_response_to_df(region)
        df_quarterly = aggregate_weather_quarterly(df_daily, region["name"])
        all_regions.append(df_quarterly)

    # Merge all regions side by side on the date (whis is the index)
    df_combined = pd.concat(all_regions, axis=1)

    # Remove duplicate 'quarter' columns from concat, loc selects rows and cols : means all rows and the mask here is a filter so we keep only cols that arent duped
    df_combined = df_combined.loc[:, ~df_combined.columns.duplicated()] #~ is bool not btw since its an array or cols 

    # Filter to our date range
    df_combined = df_combined[
        (df_combined.index.year >= START_YEAR) &
        (df_combined.index.year <= END_YEAR)
    ]

    return df_combined


def price_response_to_df(ticker: str) -> pd.DataFrame:
    """Converts PriceResponse to a clean daily DataFrame."""
    result = fetch_prices(ticker)
    df = pd.DataFrame([r.model_dump() for r in result.records])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df


def build_stock_features() -> pd.DataFrame:
    """
    Aggregates daily stock prices to quarterly returns for all halal universe tickers.
    Each row = one quarter x one ticker.
    """
    universe = load_halal_universe()
    all_stocks = []

    for stock in universe:
        ticker = stock["ticker"]
        print(f"  Processing {ticker}...")

        df = price_response_to_df(ticker)

        quarterly = df["close"].resample("QS").agg( #must agg because resample q1 basically gives us a group of daily data per Q
            price_start="first", #column price_start takes the first value ("close" price) of the quarter
            price_end="last",
        )# notice how here df has ["close"] which means thatwe dont the the {} dict defining do what at column a b c
        quarterly["volume_avg"] = df["volume"].resample("QS").mean()
        quarterly["stock_return"] = (
            (quarterly["price_end"] - quarterly["price_start"])
            / quarterly["price_start"]
            * 100
        ).round(4)
        quarterly["stock_return_next_q"] = quarterly["stock_return"].shift(-1) #-1 means future (returns next q stock_return) +1 would be past, counter intuitive ngl
        # stock_return_next_q is our target (y), it isnt a lag feature so its fine to do here. 
        # a lag feature would be a remnant of the past useful, in our case will be stock_return of previous Q which could be a factor that influence current and next Q
        quarterly["ticker"] = ticker

        all_stocks.append(quarterly)

    df_all = pd.concat(all_stocks)
    df_all = df_all[
        (df_all.index.year >= START_YEAR) &
        (df_all.index.year <= END_YEAR)
    ]

    return df_all


if __name__ == "__main__":
    print("Step 1: Building weather features...")
    df_weather = build_weather_features()

    print(f"\nShape: {df_weather.shape}")
    print(f"Quarters: {df_weather.index[0]} → {df_weather.index[-1]}")
    print(f"\nColumns ({len(df_weather.columns)}):")
    for col in df_weather.columns:
        print(f"  {col}")
    print(f"\nFirst row:\n{df_weather.iloc[0]}")

    print("\nStep 2: Building stock features...")
    df_stocks = build_stock_features()

    print(f"\nShape: {df_stocks.shape}")
    print(f"\nSample (CTVA):")
    print(df_stocks[df_stocks["ticker"] == "CTVA"][
        ["price_start", "price_end", "stock_return", "stock_return_next_q"]
    ])