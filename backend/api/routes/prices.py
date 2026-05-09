from fastapi import APIRouter, HTTPException
from db.queries import read_raw_prices
from api.schemas import PricesResponse, PriceRecord

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

    df["date"] = df["date"].astype(str)
    return PricesResponse(
    ticker=ticker.upper(),
    prices=[
        PriceRecord(**record)
        for record in df[["date", "close", "volume"]].to_dict(orient="records")
        ]
    )