import requests
from pydantic import BaseModel
from datetime import date


# Minas Gerais coord, big coffee regeion of Brazil
LAT = -19.9
LON = -43.9

#Pydantic model
#defines valid weather records
class WeatherRecord(BaseModel):
    date: date
    rainfall_mm: float
    temp_max: float
    temp_min: float

class WeatherResponse(BaseModel):
    region: str
    lat: float
    lon: float
    records: list[WeatherRecord]



def fetch_raw_weather(lat: float, lon: float) -> dict:
    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2020-01-01",
        "end_date": "2024-12-31",
        "daily": [
            "precipitation_sum",
            "temperature_2m_max",
            "temperature_2m_min",
        ],
        "timezone": "America/Sao_Paulo",
    }

    response = requests.get(url, params=params)
    response.raise_for_status()  # proper crash if err
    return response.json()

def parse_weather(raw: dict, region: str) -> WeatherResponse:
    daily = raw["daily"]

    records = [
        WeatherRecord(
            date=d,
            rainfall_mm=rain if rain is not None else 0.0, #AKA pythonic ternary, literal sentence lmao
            temp_max=tmax if tmax is not None else 0.0,
            temp_min=tmin if tmin is not None else 0.0,
        ) #zip takes multiple lists and gives tuple by grouping by index. Ex: 
                #zip(["2020-01-01", "2020-01-02"], [0.9, 5.8], [29.1, 25.2])
                #returns: ("2020-01-01", 0.9, 29.1) puis ("2020-01-02", 5.8, 25.2)
        for d, rain, tmax, tmin in zip( #the vars are initialised here, weird but see below
            daily["time"],
            daily["precipitation_sum"],
            daily["temperature_2m_max"],
            daily["temperature_2m_min"],
        )
    ] #neat trick, basically does record=[] and then a for loop which does recors.append with every initated obj

    return WeatherResponse(
        region=region,
        lat=raw["latitude"],
        lon=raw["longitude"],
        records=records,
    )


if __name__ == "__main__":
    raw = fetch_raw_weather(LAT, LON)
    weather = parse_weather(raw, region="minas_gerais")

    print(f"Region : {weather.region}")
    print(f"Days : {len(weather.records)}")
    print(f"First save : {weather.records[0]}")
    print(f"Last save : {weather.records[-1]}")