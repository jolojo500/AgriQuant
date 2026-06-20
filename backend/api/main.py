import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from api.routes import health, tickers, prices, weather, predictions, model
from scheduler.schedule import run_daily_pipeline, run_halal_check, run_quarterly_pipeline
from db.queries import download_model

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("agriquant.api")

scheduler = BackgroundScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Download model if not present
    download_model()

    # --- Startup ---
    scheduler.add_job(
        run_daily_pipeline,
        CronTrigger(hour=2, minute=0),
        id="daily_pipeline",
    )
    scheduler.add_job(
        run_quarterly_pipeline,
        CronTrigger(month="1,4,7,10", day="1", hour="3", minute=0),
        id="quarterly_pipeline",
    )
    scheduler.add_job(
        run_halal_check,
        CronTrigger(day_of_week="sun", hour=1, minute=0),
        id="halal_check",
    )
    scheduler.start()
    log.info("Scheduler started")
    log.info("  Daily pipeline    : 2AM UTC every day")
    log.info("  Quarterly pipeline: 3AM UTC — Jan 1, Apr 1, Jul 1, Oct 1")
    log.info("  Halal check       : 1AM UTC every Sunday")

    yield  #app runs here, between startup and shutdown

    # --- Shutdown ---
    scheduler.shutdown()
    log.info("Scheduler stopped")



app = FastAPI(
    title="AgriQuant API",
    description="ML pipeline forecasting quarterly returns for halal-screened agricultural equities.",
    version="1.0.0",
    lifespan=lifespan
)

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
app.include_router(model.router)

@app.get("/")
def root():
    return {
        "name": "AgriQuant API",
        "status": "live",
        "docs": "/docs",
    }