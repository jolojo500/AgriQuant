import requests
from pydantic import BaseModel
from datetime import date


# Minas Gerais coord, big coffee regeion of Brazil
LAT = -19.9
LON = -43.9

#Pydantic models
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

class NasaRecord(BaseModel): # Highly archaic stuff, no null vlaues but -999.0 and LATE replies
    date: date
    solar_radiation: float  # W/m² solar energy received that day (MJ/m²/day = Watts per square meter)
    humidity: float         # %, relative humidity 
    wind_speed: float       # m/s

class NasaResponse(BaseModel):
    region: str
    lat: float
    lon: float
    records: list[NasaRecord]




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


def fetch_raw_nasa(lat: float, lon: float) -> dict:
    url="https://power.larc.nasa.gov/api/temporal/daily/point" #could do area but annoying
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN,RH2M,WS2M",
         #aka 'parameters': {'ALLSKY_SFC_SW_DWN': {'units': 'MJ/m^2/day', 'longname': 'All Sky Surface Shortwave Downward Irradiance'}, 'RH2M': {'units': '%', 'longname': 'Relative Humidity at 2 Meters'}, 'WS2M': {'units': 'm/s', 'longname': 'Wind Speed at 2 Meters'}}
        "community": "AG",          # Agriculture profile, optimised for crops
        "longitude": lon,
        "latitude": lat,
        "start": "20200101",        # NASA wants YYYYMMDD format with no dashes (-)
        "end": "20241231",
        "format": "JSON",
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def parse_nasa(raw: dict, region: str) -> NasaResponse:
    # NASA has diff structure from Open-Meteo
    # raw["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"] = {"20200101": 12.3, ...} aka each params gives you a date and their data
    params = raw["properties"]["parameter"]
    solar = params["ALLSKY_SFC_SW_DWN"]
    humidity = params["RH2M"]
    wind = params["WS2M"]

    records = [
        NasaRecord(
            date = date(int(d[:4]), int(d[4:6]), int(d[6:])), #convert format
            solar_radiation = solar[d] if solar[d] != -999.0 else 0.0,  # -999 = null in  this api apparently
            humidity = humidity[d] if humidity[d] != -999.0 else 0.0,
            wind_speed = wind[d] if wind[d] != -999.0 else 0.0,
        )
        for d in solar.keys()
    ]
    return NasaResponse(
        region=region,
        lat=raw["geometry"]["coordinates"][1],
        lon=raw["geometry"]["coordinates"][0],
        records=records,
    )

if __name__ == "__main__":
    choice = input("Test (1) Open-Meteo or (2) NASA POWER ? ")
    
    if choice == "1":

        raw = fetch_raw_weather(LAT, LON)
        weather = parse_weather(raw, region="minas_gerais")

        print(f"Region : {weather.region}")
        print(f"Days : {len(weather.records)}")
        print(f"First save : {weather.records[0]}")
        print(f"Last save : {weather.records[-1]}")
    elif choice == "2":
        raw = fetch_raw_nasa(LAT, LON)
        print(raw)
        result = parse_nasa(raw, region="minas_gerais")
        print(f"Region : {result.region}")
        print(f"Days : {len(result.records)}")
        print(f"First save : {result.records[0]}")
        print(f"Last save : {result.records[-1]}")