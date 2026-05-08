from fastapi import APIRouter
from db.queries import read_raw_prices
import json
from pathlib import Path
from api.schemas import TickersResponse

router = APIRouter()

@router.get("/tickers", response_model=TickersResponse)
def get_tickers():
    """
    Returns the list of halal universe tickers with their names.
    Reads from halal_universe.json aka no DB query needed.
    """
    universe_path = Path(__file__).parent.parent.parent / "halal_universe.json"
    with open(universe_path) as f:
        data = json.load(f)

    return {
        "tickers": [
            {"ticker": s["ticker"], "name": s["name"]}
            for s in data["compliant"]
        ]
    }