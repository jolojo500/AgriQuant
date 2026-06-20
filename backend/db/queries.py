import os
import json
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import date

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
    filters = {}
    if ticker:
        filters["ticker"] = ticker
    if quarter:
        filters["quarter"] = quarter

    rows = _paginated_select("ml_features", filters, order_col="quarter")

    records = [
        {
            "ticker":              row["ticker"],
            "quarter":             row["quarter"],
            "stock_return_next_q": row["target"],
            **json.loads(row["features"]), #unpacking the 200+ features
        }
        for row in rows
    ]
    return pd.DataFrame(records)


def read_raw_prices(ticker: str | None = None) -> pd.DataFrame:
    """
    Loads daily price records from raw_prices.
    If ticker is provided, filters to that ticker only.
    """
    filters = {"ticker": ticker} if ticker else {}
    rows = _paginated_select("raw_prices", filters, order_col="date")
    df = pd.DataFrame(rows)
    if not df.empty:
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
    supabase.table("ml_predictions").upsert({
        "ticker":           ticker,
        "quarter":          quarter,
        "predicted_return": round(predicted_return, 6),
        "actual_return":    actual_return,
        "model_version":    model_version,
    }, on_conflict="ticker,quarter").execute()


def read_predictions(ticker: str | None = None) -> pd.DataFrame:
    """
    Loads prediction history from ml_predictions.
    Used by the API and for backtesting evaluation.
    """
    filters = {"ticker": ticker} if ticker else {}
    rows = _paginated_select("ml_predictions", filters, order_col="created_at")
    
    return pd.DataFrame(rows)

def save_training_run(
    best_model:        str,
    rmse_ols:          float,
    rmse_rf:           float,
    rmse_xgb:          float,
    rmse_lgbm:         float,
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
        "rmse_lgbm":           round(rmse_lgbm, 4),
        "best_rmse":           round(best_rmse, 4),
        "n_features":          n_features,
        "n_rows":              n_rows,
        "start_year":          start_year,
        "train_quarters":      train_quarters,
        "feature_importance":  feature_importance,  #jsonb, Supabase auto does dict serialisation
        "baseline_rmse": round(baseline_rmse, 4), #baseline basically is lazy prediction which is "0% next quarter", this ends up meaning that rmse of the baseline is simply the standard deviation and if we beat it then the model actually learned relevant things and isnt just spouting out random noise
    }).execute()    
    print("  Training run logged to Supabase")

def read_latest_training_run() -> dict | None:
    response = (
        supabase.table("ml_training_runs")
        .select("*")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None

def read_training_history() -> list[dict]:
   # response = (
    #    supabase.table("ml_training_runs")
    #    .select("id, best_model, rmse_ols, rmse_rf, rmse_xgb, best_rmse, baseline_rmse, n_features, n_rows, start_year, train_quarters, created_at")
    #    .order("created_at")
    #    .execute()
    #)
    #return response.data
    columns = (
        "id, best_model, rmse_ols, rmse_rf, rmse_xgb, best_rmse, "
        "baseline_rmse, n_features, n_rows, start_year, train_quarters, created_at"
    )
    return _paginated_select("ml_training_runs", order_col="created_at", columns=columns)

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
    """Reads ALL weather data for one region, paginated past Supabase's 1000-row default cap."""
    rows = _paginated_select("raw_weather", {"region": region}, order_col="date")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")


def read_raw_prices_df(ticker: str) -> pd.DataFrame:
    """Reads ALL price data for one ticker, paginated past Supabase's 1000-row default cap."""
    rows = _paginated_select("raw_prices", {"ticker": ticker}, order_col="date")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")

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


def read_last_price_date(ticker: str) -> date | None:
    """Returns the most recent date we have prices for, or None if never fetched."""
    response = (
        supabase.table("raw_prices")
        .select("date")
        .eq("ticker", ticker)
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    return date.fromisoformat(response.data[0]["date"]) if response.data else None


def read_last_weather_date(region: str) -> date | None:
    """Returns the most recent date we have weather for, or None if never fetched."""
    response = (
        supabase.table("raw_weather")
        .select("date")
        .eq("region", region)
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    return date.fromisoformat(response.data[0]["date"]) if response.data else None

def download_model(local_path: str = "ml/model.pkl") -> bool:
    """Downloads model.pkl from Supabase Storage if not present locally."""
    from pathlib import Path
    if Path(local_path).exists():
        return True
    try:
        res = supabase.storage.from_("models").download("model.pkl")
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(res)
        print("  model.pkl downloaded from Supabase Storage")
        return True
    except Exception as e:
        print(f"  model.pkl not found in Storage: {e}")
        return False

def upload_model(local_path: str = "ml/model.pkl") -> None:
    """Uploads model.pkl to Supabase Storage after retraining."""
    with open(local_path, "rb") as f:
        supabase.storage.from_("models").upload(
            "model.pkl", f, {"upsert": "true"}
        )
    print("  model.pkl uploaded to Supabase Storage")

    
def _paginated_select(
    table: str,
    filters: dict | None = None,
    order_col: str = "date",
    desc: bool = False,
    columns: str = "*",
) -> list[dict]:
    """
    Generic paginated select — works around Supabase's 1000-row default cap.
    Loops with .range() until a page comes back shorter than page_size.
    """
    all_rows = []
    page_size = 1000
    start = 0

    while True:
        query = supabase.table(table).select(columns)
        if filters:
            for col, val in filters.items():
                query = query.eq(col, val)
        query = query.order(order_col, desc=desc).range(start, start + page_size - 1)

        response = query.execute()
        rows = response.data
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        start += page_size

    return all_rows