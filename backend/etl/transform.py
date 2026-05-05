import pandas as pd
import numpy as np
from datetime import date
from etl.transform_config import (
    WEATHER_REGIONS, WEATHER_FEATURES, CROPS,
    YIELD_COUNTRIES, LAG_FEATURES, START_YEAR, END_YEAR
)
from etl.extract_weather import fetch_raw_weather, parse_weather, fetch_raw_nasa, parse_nasa
from etl.extract_prices import fetch_prices, load_halal_universe
from etl.extract_yields import download_faostat_bulk, parse_yields, FAO_CROPS, FAO_COUNTRIES

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
    base = df_daily.resample("QS").agg({ 
        "rainfall_mm":      "sum",    # total rain this quarter
        "temp_max":         "mean",   # avg of daily max temps
        "temp_min":         "mean",   # avg of daily min temps
        "solar_radiation":  "mean",   # avg solar energy
        "humidity":         "mean",   # avg humidity
        "wind_speed":       "mean",   # avg wind speed
    })

    # Custom features, can't do these with simple agg
    drought_days = (
        df_daily["rainfall_mm"]
        .resample("QS")
        .apply(lambda x: (x < 2.0).sum())
        .rename("drought_days")
    )# we define custom things before affecting them to wahetevr (base["whatever"] = etc) because fragmentation

    heat_stress_days = (
        df_daily["temp_max"]
        .resample("QS")
        .apply(lambda x: (x > 35.0).sum())
        .rename("heat_stress_days")
    )

    quarter_labels = pd.Series(
        base.index.to_period("Q").astype(str),
        index=base.index,
        name="quarter",
    )

    # a single concat means no fragmentation so it is more efficient
    quarterly = pd.concat([base, drought_days, heat_stress_days, quarter_labels], axis=1)

    quarterly.columns = [
        f"{region_name}_{col}" if col != "quarter" else col
        for col in quarterly.columns
    ]

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

        """ old code had fragmentation warnings
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
        """

        
        prices = df["close"].resample("QS").agg(price_start="first", price_end="last")
        volume_avg = df["volume"].resample("QS").mean().rename("volume_avg")

        stock_return = (
            (prices["price_end"] - prices["price_start"])
            / prices["price_start"]
            * 100
        ).round(4).rename("stock_return")

        stock_return_next_q = stock_return.shift(-1).rename("stock_return_next_q")

        # Single concat for all 4 columns means no fragmentation
        quarterly = pd.concat(
            [prices, volume_avg, stock_return, stock_return_next_q],
            axis=1,
        )
        quarterly["ticker"] = ticker  #single assignement so its fine
        
        all_stocks.append(quarterly)

    df_all = pd.concat(all_stocks)
    df_all = df_all[
        (df_all.index.year >= START_YEAR) &
        (df_all.index.year <= END_YEAR)
    ]

    return df_all


def yield_response_to_df(crop: str, country: str, df_fao: pd.DataFrame) -> pd.DataFrame:
    """Converts a YieldResponse to a clean annual DataFrame."""
    result = parse_yields(df_fao, crop, country)
    df = pd.DataFrame([r.model_dump() for r in result.records])
    return df

def build_yield_features(df_fao: pd.DataFrame) -> pd.DataFrame:
    """
    Builds a quarterly yield feature DataFrame.
    Since yields are annual, we repeat each year's value
    across all 4 quarters of that year.
    Each row = one quarter, columns = all crop/country combinations.
    """
    # Start with a quarterly date range as the backbone
    quarters = pd.date_range(
        start=f"{START_YEAR}-01-01",
        end=f"{END_YEAR}-12-31",
        freq="QS"
    )
   
    #we do a dict to concat once instead of inserting many times
    columns: dict[str, pd.Series] = {}

    for crop in FAO_CROPS:
        for country in FAO_COUNTRIES:
            col_name = f"yield_{crop}_{country}_t_ha"
            try:
                df_yield = yield_response_to_df(crop, country, df_fao)
                if df_yield.empty:
                    continue
                columns[col_name] = pd.Series(
                    quarters.year.map(df_yield.set_index("year")["yield_tonnes_ha"]),
                    index=quarters,
                )
            except Exception:
                pass  # cassava/canada etc.

    # Dataframe made once from the full dict
    df_combined = pd.DataFrame(columns, index=quarters)

    return df_combined


def add_weather_lags(df_weather: pd.DataFrame) -> pd.DataFrame:
    new_cols = {}
    for col_pattern, lag in LAG_FEATURES:
        if "yield" in col_pattern or "stock" in col_pattern:
            continue
        for region in WEATHER_REGIONS:
            name = region["name"]
            matching = [
                c for c in df_weather.columns
                if name in c and col_pattern.split("_")[0] in c
                and "lag" not in c
            ]
            for col in matching:
                new_cols[f"{col}_lag{lag}q"] = df_weather[col].shift(lag)

    return pd.concat([df_weather, pd.DataFrame(new_cols, index=df_weather.index)], axis=1)


def add_yield_lags(df_yields: pd.DataFrame) -> pd.DataFrame:
    new_cols = {}
    for col_pattern, lag in LAG_FEATURES:
        if "yield" not in col_pattern:
            continue
        for col in df_yields.columns:
            if "yield" in col and "lag" not in col:
                new_cols[f"{col}_lag1y"] = df_yields[col].shift(lag)

    return pd.concat([df_yields, pd.DataFrame(new_cols, index=df_yields.index)], axis=1)


def add_stock_lags(df_stocks: pd.DataFrame) -> pd.DataFrame:
    result = []
    for ticker in df_stocks["ticker"].unique():
        df_ticker = df_stocks[df_stocks["ticker"] == ticker].copy()
        new_cols = {}

        for col_pattern, lag in LAG_FEATURES:
            if "stock" not in col_pattern:
                continue
            matching = [
                c for c in df_ticker.columns
                if col_pattern.split("_")[0] in c
                and "lag" not in c
                and c != "ticker"
                and c != "stock_return_next_q"
            ]
            for col in matching:
                new_cols[f"{col}_lag{lag}q"] = df_ticker[col].shift(lag)

        df_ticker = pd.concat(
            [df_ticker, pd.DataFrame(new_cols, index=df_ticker.index)], axis=1
        )
        result.append(df_ticker)

    return pd.concat(result).sort_index()


def build_ml_dataset(
    df_weather: pd.DataFrame,
    df_stocks: pd.DataFrame,
    df_yields: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merges weather, stock, and yield features into one ML-ready DataFrame.
    Each row = one quarter x one stock ticker.
    
    Structure:
    - index: quarter start date
    - columns: all weather features + all yield features + stock features + target
    """
    all_rows = []

    tickers = df_stocks["ticker"].unique()

    for ticker in tickers:
        # Get stock data for this ticker
        df_ticker = df_stocks[df_stocks["ticker"] == ticker].copy()
        df_ticker = df_ticker.drop(columns=["ticker"])

        # Merge weather (same for all tickers — weather doesn't depend on stock)
        df_ticker = df_ticker.join(df_weather, how="left")

        # Merge yields (same for all tickers)
        df_ticker = df_ticker.join(df_yields, how="left")

        # Add ticker column back
        df_ticker["ticker"] = ticker

        all_rows.append(df_ticker)

    df_ml = pd.concat(all_rows)
    df_ml = df_ml.sort_index()

    return df_ml


if __name__ == "__main__":
    print("Step 1: Building weather features...")
    df_weather = build_weather_features()
    df_weather = add_weather_lags(df_weather)

    print(f"\nShape: {df_weather.shape}")
    print(f"Quarters: {df_weather.index[0]} → {df_weather.index[-1]}")
    print(f"\nColumns ({len(df_weather.columns)}):")
    for col in df_weather.columns:
        print(f"  {col}")
    print(f"\nFirst row:\n{df_weather.iloc[0]}")


    print("\nStep 2: Building stock features...")
    df_stocks = build_stock_features()
    df_stocks = add_stock_lags(df_stocks)

    print(f"\nShape: {df_stocks.shape}")
    print(df_stocks)
    print(f"\nSample (CTVA):")
    print(df_stocks[df_stocks["ticker"] == "CTVA"][
        ["price_start", "price_end", "stock_return", "stock_return_next_q"]
    ])
    print(f"\nSample (CTVA) FULL:")
    print(df_stocks[df_stocks["ticker"] == "CTVA"])


    print("\nStep 3: Building yield features...")
    df_fao = download_faostat_bulk()
    df_yields = build_yield_features(df_fao)
    df_yields = add_yield_lags(df_yields)

    print(f"\nShape: {df_yields.shape}")
    print(f"\nSample columns: {list(df_yields.columns[:5])}")
    print(f"\nFirst row:\n{df_yields.iloc[0]}")

     
    print("\nStep 4: Building ML dataset...")
    df_ml = build_ml_dataset(df_weather, df_stocks, df_yields)

    print(f"\nShape: {df_ml.shape}")
    print(f"Tickers: {df_ml['ticker'].unique()}")

    #print(f"\nColumns ({len(df_ml.columns)}):")
    #print(f"  Weather : {len([c for c in df_ml.columns if any(r['name'] in c for r in WEATHER_REGIONS)])}")
    #print(f"  Yields  : {len([c for c in df_ml.columns if 'yield' in c])}")
    #print(f"  Stock   : {len([c for c in df_ml.columns if c in ['price_start','price_end','volume_avg','stock_return','stock_return_next_q','ticker']])}")
    #print(f"\nSample row (CTVA, Q1 2020):")
    #sample = df_ml[(df_ml["ticker"] == "CTVA") & (df_ml.index.year == 2020) & (df_ml.index.quarter == 1)]
    #print(sample[["price_start", "price_end", "stock_return", "stock_return_next_q", "iowa_rainfall_mm", "yield_maize_usa_t_ha"]].to_string())