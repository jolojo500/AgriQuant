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