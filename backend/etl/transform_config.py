# ============================================================
# TRANSFORM CONFIGURATION
# Defines what features to compute and which regions/crops
# to use for each transformation step.
# ============================================================

# --- Weather regions ---
# Each region has GPS coords and a label
# These must match yield regions
WEATHER_REGIONS = [
    # USA — Corn Belt (corn, soy, wheat)
    {"name": "iowa",            "lat": 42.0,  "lon": -93.6},
    # USA — Great Plains (wheat, coton, sunflower)  
    {"name": "kansas",          "lat": 38.7,  "lon": -98.4},

    # Brazil — Mato Grosso (soy, corn, coton — Biggest agricultural state in the world)
    {"name": "mato_grosso",     "lat": -12.6, "lon": -55.9},
    # Brazil — Paraná (soy, wheat)
    {"name": "parana",          "lat": -23.4, "lon": -51.9},

    # Argentina — Pampas (soy, wheat, corn, sunflower)
    {"name": "buenos_aires_ag", "lat": -36.6, "lon": -63.8},

    # Canada — Saskatchewan (wheat, canola)
    {"name": "saskatchewan",    "lat": 52.1,  "lon": -106.7},

    # China — Heilongjiang (corn, soy, rice)
    {"name": "heilongjiang",    "lat": 47.0,  "lon": 128.9},
    # China — Henan (wheat)
    {"name": "henan",           "lat": 34.0,  "lon": 113.7},

    # India — Punjab (wheat, rice)
    {"name": "punjab_india",    "lat": 30.9,  "lon": 75.9},
    # India — Maharashtra (coton, soy)
    {"name": "maharashtra",     "lat": 19.7,  "lon": 75.7},
]

# --- Quarterly weather features to compute ---
# For each region we aggregate daily data into these quarterly metrics
WEATHER_FEATURES = {
    # Open-Meteo features
    "rainfall_total_mm":    ("precipitation_sum", "sum"),    # total rain this quarter
    "temp_avg_c":           ("temperature_2m_max", "mean"),  # avg daily max temp
    "drought_days":         ("precipitation_sum", "drought"), # days with < 2mm rain
    "heat_stress_days":     ("temperature_2m_max", "heat"),  # days above 35°C

    # NASA POWER features
    "solar_radiation_avg":  ("solar_radiation", "mean"),     # avg W/m² this quarter
    "humidity_avg":         ("humidity", "mean"),             # avg relative humidity %
    "wind_speed_avg":       ("wind_speed", "mean"),          # avg wind speed m/s
}

# --- Crops to include in the dataset ---
# All crops for all stocks — let Random Forest decide which matter
CROPS = [
    "maize",
    "wheat",
    "soybeans",
    "rice",
    "cotton",
    "canola",
    "sunflower",
    "cassava",
    "potatoes",
]

# Countries for yield data
YIELD_COUNTRIES = [
    "usa",
    "brazil",
    "argentina",
    "canada",
    "china",
    "india",
]

# --- Lag features to create ---
# Format: (column_pattern, lag_in_quarters)
# Example: ("rainfall_total_mm", 1) → rainfall of previous quarter
LAG_FEATURES = [
    ("rainfall_total_mm",   1),  # hydric stress carries over one quarter
    ("temp_avg_c",          1),  # temperature trend
    ("solar_radiation_avg", 1),  # solar trend
    ("stock_return",        1),  # momentum effect
    ("yield_{crop}_{country}", 4),  # yield from same quarter last year (annual cycle)
]

# --- Target definition ---
# We predict the stock return of the NEXT quarter
# stock_return = (price_end_of_quarter - price_start_of_quarter) / price_start_of_quarter
TARGET = "stock_return_next_q"

# --- Date range ---
START_YEAR = 2019
END_YEAR   = 2025