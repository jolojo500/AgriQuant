from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import time

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("agriquant.scheduler")


def run_daily_fetch() -> None:
    """
    Fetches fresh prices and weather every day.
    Lightweight, just raw data into Supabase, no transforms.
    """
    from etl.extract_prices import fetch_all_prices
    from etl.extract_weather import fetch_raw_weather, parse_weather, fetch_raw_nasa, parse_nasa
    from etl.transform_config import WEATHER_REGIONS
    from etl.load import load_raw_prices, load_raw_weather

    log.info("[DAILY] Starting daily fetch...")

    try:
        log.info("[DAILY] Step 1: Prices...")
        all_prices = fetch_all_prices()
        load_raw_prices(all_prices)

        log.info("[DAILY] Step 2: Weather...")
        for region in WEATHER_REGIONS:
            raw_weather = fetch_raw_weather(region["lat"], region["lon"])
            weather     = parse_weather(raw_weather, region["name"])
            raw_nasa    = fetch_raw_nasa(region["lat"], region["lon"])
            nasa        = parse_nasa(raw_nasa, region["name"])
            load_raw_weather(weather, nasa)
            time.sleep(4)  # Open meteo rate limit

        log.info("[DAILY] Fetch completed")

    except Exception as e:
        log.error(f"[DAILY] Failed: {e}")
        raise


def run_quarterly_pipeline() -> None:
    """
    Quarterly transform + retrain + predict.
    Reads from Supabase, zero external API calls so we dont get bothered by open meteo.
    Runs after each quarter closes: Jan 1, Apr 1, Jul 1, Oct 1.
    """
    from etl.extract_yields import download_faostat_bulk, fetch_all_yields
    from etl.transform import (
        build_weather_features_from_db, add_weather_lags,
        build_stock_features_from_db,  add_stock_lags,
        build_yield_features,          add_yield_lags,
        build_ml_dataset,
    )
    from etl.load import load_raw_yields, load_ml_features

    log.info("[QUARTERLY] Starting quarterly pipeline...")

    try:
        # Yields are annual — still fetch from FAO (lightweight, cached)
        log.info("[QUARTERLY] Step 1: Yields (FAO, cached)...")
        df_fao     = download_faostat_bulk()
        all_yields = fetch_all_yields(df_fao)
        load_raw_yields(all_yields)

        # Transform reads from DB, no API calls
        log.info("[QUARTERLY] Step 2: Building ML features from DB...")
        df_weather = add_weather_lags(build_weather_features_from_db())
        df_stocks  = add_stock_lags(build_stock_features_from_db())
        df_yields  = add_yield_lags(build_yield_features(df_fao))
        df_ml      = build_ml_dataset(df_weather, df_stocks, df_yields)
        load_ml_features(df_ml)

        # Retrain on fresh data
        log.info("[QUARTERLY] Step 3: Retraining model...")
        from ml.train import run_training  #made from __main__
        run_training()

        log.info("[QUARTERLY] Step 4: Filling actual returns...")
        from db.queries import fill_actual_returns
        fill_actual_returns()

        log.info("[QUARTERLY] Pipeline completed")

    except Exception as e:
        log.error(f"[QUARTERLY] Failed: {e}")
        raise


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        run_daily_fetch,
        CronTrigger(hour=2, minute=0),  # 2AM UTC every day
        id="daily_fetch",
    )

    scheduler.add_job(
        run_quarterly_pipeline,
        CronTrigger(month="1,4,7,10", day="1", hour="3", minute=0),  # 3AM after daily finishes
        id="quarterly_pipeline",
    )

    log.info("Scheduler started")
    log.info("  Daily fetch    : 2AM UTC every day")
    log.info("  Quarterly pipeline : 3AM UTC — Jan 1, Apr 1, Jul 1, Oct 1")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        log.info("Scheduler stopped")