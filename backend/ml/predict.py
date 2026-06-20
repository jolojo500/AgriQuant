import joblib
import numpy as np
import pandas as pd
from db.queries import read_ml_features, save_prediction

MODEL_PATH = "ml/model.pkl"


def load_model() -> dict:
    """Loads the saved model bundle from disk."""
    return joblib.load(MODEL_PATH)


def predict_next_quarter(ticker: str, quarter: str) -> dict:
    """
    Predicts the next quarter return for a given ticker and quarter.
    ticker  : ex "CTVA"
    quarter : ex "2024Q3" (the quarter we know, predicting Q4)

    Returns a dict with the prediction and metadata.
    """
    bundle = load_model()
    model       = bundle["model"]
    model_name  = bundle["model_name"]
    feature_cols = bundle["feature_cols"]

    # Load the row for this ticker/quarter from Supabase
    df = read_ml_features(ticker=ticker, quarter=quarter)

    if df.empty:
        raise ValueError(f"No data found for {ticker} / {quarter}")

    # One-hot encode ticker, must match exactly what train.py did
    df = pd.get_dummies(df, columns=["ticker"], prefix="ticker")

    # Align columns to training feature set
    # Adds missing columns (ex: ticker_NTR if only CTVA is passed) as 0
    # Removes extra columns not seen during training (aka if I ever add things without training first like regions)
    df = df.reindex(columns=feature_cols, fill_value=0)

    # Drop non-feature columns
    drop_cols = ["quarter", "stock_return_next_q"]
    X = df.drop(columns=[c for c in drop_cols if c in df.columns])

    # Impute NaNs with 0 (same fallback as train.py)
    X = X.fillna(0)

    predicted_return = float(model.predict(X)[0])

    # Save to ml_predictions in Supabase
    # quarter + 1 = the quarter we're predicting
    next_quarter = _next_quarter(quarter)
    save_prediction(
        ticker           = ticker,
        quarter          = next_quarter,
        predicted_return = predicted_return,
        model_version    = model_name,
    )

    return {
        "ticker":           ticker,
        "input_quarter":    quarter,
        "predicted_quarter": next_quarter,
        "predicted_return": round(predicted_return, 4),
        "model":            model_name,
    }


def _next_quarter(quarter: str) -> str:
    """
    Converts "2024Q3" → "2024Q4", handles year rollover.
    "2024Q4" → "2025Q1"
    """
    year = int(quarter[:4])
    q    = int(quarter[5])

    if q == 4:
        return f"{year + 1}Q1"
    return f"{year}Q{q + 1}"

def predict_all_tickers(quarter: str) -> None:
    """
    Runs predict_next_quarter for every ticker in the halal universe.
    Used by the quarterly pipeline, and reusable for manual seeding/backfilling.
    """
    import json
    from pathlib import Path

    universe_path = Path("halal_universe.json")
    with open(universe_path) as f:
        universe = json.load(f)["compliant"]

    for stock in universe:
        ticker = stock["ticker"]
        try:
            result = predict_next_quarter(ticker, quarter)
            print(f"  {ticker}: {result['predicted_return']}% for {result['predicted_quarter']}")
        except Exception as e:
            print(f"  {ticker} failed: {e}")

if __name__ == "__main__":
    ticker  = input("Ticker  : ").upper()
    quarter = input("Quarter : ")  # ex: 2024Q3

    result = predict_next_quarter(ticker, quarter)

    print(f"\nPrediction:")
    print(f"  Ticker    : {result['ticker']}")
    print(f"  Predicting: {result['predicted_quarter']}")
    print(f"  Return    : {result['predicted_return']}%")
    print(f"  Model     : {result['model']}")