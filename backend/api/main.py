from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import health, tickers, prices, weather, predictions

app = FastAPI(title="AgriQuant API")

# Allows requests from the React frontend
# TODO in production, replace * with Firebase domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Firebase URL in production
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(tickers.router)
app.include_router(prices.router)
app.include_router(weather.router)
app.include_router(predictions.router)