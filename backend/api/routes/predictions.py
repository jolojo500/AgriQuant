from fastapi import APIRouter, HTTPException
from db.queries import read_predictions
from ml.predict import predict_next_quarter
from api.schemas import PredictionResponse, PredictionHistoryResponse, RankingsResponse

router = APIRouter()

@router.get("/predict/{ticker}/{quarter}", response_model=PredictionResponse)
def predict(ticker: str, quarter: str):
    """
    Runs a prediction for ticker at given quarter.
    ex: /predict/CTVA/2024Q3 → predicts 2024Q4 return
    """
    try:
        result = predict_next_quarter(ticker.upper(), quarter)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/predictions/{ticker}", response_model=PredictionHistoryResponse)
def get_prediction_history(ticker: str):
    """
    Returns prediction history vs actual returns for one ticker.
    Used for the machine's performance chart.
    """
    df = read_predictions(ticker=ticker.upper())

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No predictions for {ticker}")

    return {
        "ticker":      ticker.upper(),
        "predictions": df[[
            "quarter", "predicted_return", "actual_return", "model_version", "created_at"
        ]].to_dict(orient="records"),
    }


@router.get("/rankings", response_model=RankingsResponse)
def get_rankings():
    """
    Returns all tickers ranked by predicted return for the latest quarter.
    Used for the 'best stocks' leaderboard (stocks with best reliability of our predicitons).
    """
    df = read_predictions()

    if df.empty:
        return {"rankings": []}

    # Keep only the most recent prediction per ticker
    latest = (
        df.sort_values("created_at", ascending=False)
        .groupby("ticker")
        .first()
        .reset_index()
        .sort_values("predicted_return", ascending=False)
    )

    return {
        "rankings": latest[[
            "ticker", "predicted_return", "quarter", "model_version"
        ]].to_dict(orient="records")
    }