from fastapi import APIRouter, HTTPException
from db.queries import read_raw_prices
from api.schemas import PricesResponse

router = APIRouter()

@router.get("/prices/{ticker}", response_model=PricesResponse)
def get_prices(ticker: str):
    """
    Returns daily price history for one ticker.
    Used by Recharts for the price chart.
    """
    df = read_raw_prices(ticker=ticker.upper())

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No prices found for {ticker}")

    return {
        "ticker": ticker.upper(),
        "prices": df[["date", "close", "volume"]].to_dict(orient="records"),
    }