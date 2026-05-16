import os
import json
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"],
)


def read_ml_features(
    ticker: str | None = None,
    quarter: str | None = None,
    ) -> pd.DataFrame:
    """
    Loads all rows from ml_features and reconstructs
    a DataFrame identical to the one built by transform.py.
    Each row = one (ticker, quarter) pair.
    """
    query = supabase.table("ml_features").select("*")

    if ticker:
        query = query.eq("ticker", ticker)
    if quarter:
        query = query.eq("quarter", quarter)
        
    response = query.order("quarter").execute()
    rows = response.data

    records = []
    for row in rows:
        # features is a jsonb dict so we unpack all feature columns flat
        record = {
            "ticker":               row["ticker"],
            "quarter":              row["quarter"],
            "stock_return_next_q":  row["target"],
            **json.loads(row["features"]),  # unpacks all 200+ feature columns
        }
        records.append(record)

    df = pd.DataFrame(records)
    #df = df.sort_values(["ticker", "quarter"]).reset_index(drop=True)
    return df


def read_raw_prices(ticker: str | None = None) -> pd.DataFrame:
    """
    Loads daily price records from raw_prices.
    If ticker is provided, filters to that ticker only.
    """
    query = supabase.table("raw_prices").select("*")

    if ticker:
        query = query.eq("ticker", ticker)

    response = query.order("date").execute()

    df = pd.DataFrame(response.data)
    df["date"] = pd.to_datetime(df["date"])
    return df



def save_prediction(
    ticker: str,
    quarter: str,
    predicted_return: float,
    model_version: str,
    actual_return: float | None = None,
) -> None:
    """
    Saves one model prediction to ml_predictions.
    actual_return is None at prediction time 
    it gets filled in later once the quarter closes.
    """
    supabase.table("ml_predictions").insert({
        "ticker":           ticker,
        "quarter":          quarter,
        "predicted_return": round(predicted_return, 6),
        "actual_return":    actual_return,
        "model_version":    model_version,
    }).execute()


def read_predictions(ticker: str | None = None) -> pd.DataFrame:
    """
    Loads prediction history from ml_predictions.
    Used by the API and for backtesting evaluation.
    """
    query = supabase.table("ml_predictions").select("*")

    if ticker:
        query = query.eq("ticker", ticker)

    response = query.order("created_at").execute()
    return pd.DataFrame(response.data)

def save_training_run(
    best_model:        str,
    rmse_ols:          float,
    rmse_rf:           float,
    rmse_xgb:          float,
    best_rmse:         float,
    n_features:        int,
    n_rows:            int,
    start_year:        int,
    train_quarters:    int,
    feature_importance: dict, 
    baseline_rmse: float,
) -> None:
    """Logs each training run with RMSE scores and feature importances."""
    supabase.table("ml_training_runs").insert({
        "best_model":          best_model,
        "rmse_ols":            round(rmse_ols,  4),
        "rmse_rf":             round(rmse_rf,   4),
        "rmse_xgb":            round(rmse_xgb,  4),
        "best_rmse":           round(best_rmse, 4),
        "n_features":          n_features,
        "n_rows":              n_rows,
        "start_year":          start_year,
        "train_quarters":      train_quarters,
        "feature_importance":  feature_importance,  #jsonb, Supabase auto does dict serialisation
        "baseline_rmse": round(baseline_rmse, 4), #baseline basically is lazy prediction which is "0% next quarter", this ends up meaning that rmse of the baseline is simply the standard deviation and if we beat it then the model actually learned relevant things and isnt just spouting out random noise
    }).execute()    
    print("  Training run logged to Supabase")

def read_weather_latest_by_region(region: str, days: int = 90) -> list[dict]:
    """
    Returns the most recent N days of weather data for one region.
    Used by the API to build globe overlays.
    """
    response = (
        supabase.table("raw_weather")
        .select("*")
        .eq("region", region)
        .order("date", desc=True)
        .limit(days) # 90 is about a quarter
        .execute()
    )
    return response.data


def read_raw_weather_df(region: str) -> pd.DataFrame:
    """Reads all weather data for one region from Supabase."""
    response = (
        supabase.table("raw_weather")
        .select("*")
        .eq("region", region)
        .order("date")
        .execute()
    )
    df = pd.DataFrame(response.data)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df


def read_raw_prices_df(ticker: str) -> pd.DataFrame:
    """Reads all price data for one ticker from Supabase."""
    response = (
        supabase.table("raw_prices")
        .select("*")
        .eq("ticker", ticker)
        .order("date")
        .execute()
    )
    df = pd.DataFrame(response.data)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df

def fill_actual_returns() -> None:
    """
    After each quarterly pipeline, fills actual_return in ml_predictions
    for quarters that have now closed.
    Reads actual returns from ml_features (target column).
    """
    # Get all predictions still missing actual_return
    response = (
        supabase.table("ml_predictions")
        .select("ticker, quarter")
        .is_("actual_return", "null")
        .execute()
    )

    if not response.data:
        print("  No predictions missing actual_return")
        return

    # Deduplicate ticker/quarter pairs
    pairs = {(r["ticker"], r["quarter"]) for r in response.data}

    filled = 0
    for ticker, quarter in pairs:
        # Look up actual return from ml_features (target column)
        result = (
            supabase.table("ml_features")
            .select("target")
            .eq("ticker", ticker)
            .eq("quarter", quarter)
            .execute()
        )

        if not result.data or result.data[0]["target"] is None:
            continue  # Quarter not closed yet or no data

        actual = result.data[0]["target"]

        # Update all predictions for this ticker/quarter
        supabase.table("ml_predictions").update(
            {"actual_return": round(float(actual), 6)}
        ).eq("ticker", ticker).eq("quarter", quarter).is_("actual_return", "null").execute()

        filled += 1

    print(f"  fill_actual_returns: {filled} ticker/quarter pairs updated")

def delete_ml_features_for_ticker(ticker: str) -> None:
    """Removes all ml_features rows for a delisted/non-compliant ticker."""
    supabase.table("ml_features").delete().eq("ticker", ticker).execute()
    print(f"  Deleted ml_features for {ticker}")