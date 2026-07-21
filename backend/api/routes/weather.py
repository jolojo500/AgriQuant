import time

from fastapi import APIRouter
from db.queries import read_weather_latest_by_region
from etl.transform_config import WEATHER_REGIONS
from api.schemas import WeatherResponse, WeatherRegion

router = APIRouter()

# Free-tier network hiccups (httpx ReadError on the first Supabase call after
# idle) were 500-ing this route. Weather aggregates move daily, not per-request:
# cache the built response for 10 minutes and serve the stale copy if a rebuild
# fails, instead of erroring.
_CACHE_TTL_S = 600
_cache: dict = {"at": 0.0, "resp": None}


def _fetch_rows_with_retry(region_name: str, attempts: int = 2) -> list[dict]:
    """One retry absorbs the transient 'resource temporarily unavailable' reads."""
    for i in range(attempts):
        try:
            return read_weather_latest_by_region(region_name)
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(0.3)
    return []


def _build_regions() -> list[WeatherRegion]:
    results = []

    for region in WEATHER_REGIONS:
        name = region["name"]

        # Fetch the most recent rows for this region (default limit 90 ≈ a quarter)
        rows = _fetch_rows_with_retry(name)

        if not rows:
            continue

        # Aggregate to one number per metric for the overlay
        rainfall   = sum(r["rainfall_mm"]  or 0 for r in rows)
        temp_max   = sum(r["temp_max"]     or 0 for r in rows) / len(rows)
        humidity   = sum(r["humidity"]     or 0 for r in rows) / len(rows)
        solar      = sum(r["solar_radiation"] or 0 for r in rows) / len(rows)
        wind       = sum(r["wind_speed"]      or 0 for r in rows) / len(rows)
        # Same thresholds as transform_config's WEATHER_FEATURES — the globe shows what the model sees
        drought_days     = sum(1 for r in rows if (r["rainfall_mm"] or 0) < 2.0)
        heat_stress_days = sum(1 for r in rows if (r["temp_max"] or 0) > 35.0)

        results.append(
            WeatherRegion(
                region=name,
                lat=region["lat"],
                lon=region["lon"],
                rainfall_mm=round(rainfall, 1),
                temp_max=round(temp_max, 1),
                humidity=round(humidity, 1),
                solar_radiation=round(solar, 1),
                wind_speed=round(wind, 1),
                drought_days=drought_days,
                heat_stress_days=heat_stress_days,
            )
        )

    return results


@router.get("/weather/regions", response_model=WeatherResponse)
def get_weather_regions():
    """
    Returns the latest quarterly weather metrics for each region.
    Used by Deck.gl to draw overlays on globe.
    """
    if _cache["resp"] is not None and time.time() - _cache["at"] < _CACHE_TTL_S:
        return _cache["resp"]

    try:
        results = _build_regions()
    except Exception:
        if _cache["resp"] is not None:
            return _cache["resp"]  # stale beats a 500
        raise

    resp = WeatherResponse(regions=results)
    _cache["at"] = time.time()
    _cache["resp"] = resp
    return resp
