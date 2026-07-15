from fastapi import APIRouter
from db.queries import read_weather_latest_by_region
from etl.transform_config import WEATHER_REGIONS
from api.schemas import WeatherResponse, WeatherRegion

router = APIRouter()

@router.get("/weather/regions", response_model=WeatherResponse)
def get_weather_regions():
    """
    Returns the latest quarterly weather metrics for each region.
    Used by Deck.gl to draw overlays on globe.
    """
    results = []

    for region in WEATHER_REGIONS:
        name = region["name"]

        # Fetch the most recent row for this region
        rows = read_weather_latest_by_region(name) #default limit param is at 90 so about a quarter

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

    return WeatherResponse(regions=results)