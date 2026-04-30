import requests
import pandas as pd


# Minas Gerais coord, big coffee regeion of Brazil
LAT = -19.9
LON = -43.9

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


if __name__ == "__main__":
    data = fetch_raw_weather(LAT, LON)
    print(data)