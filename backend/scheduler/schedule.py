from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import time
from datetime import date


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("agriquant.scheduler")

def _last_closed_quarter() -> str:
    """
    Returns the quarter that just closed, relative to today.
    Pipeline runs the day after a quarter closes (Jan 1, Apr 1, Jul 1, Oct 1),
    so "today" is already in the new quarter — we step back by one.
    """
    today = date.today()
    q = (today.month - 1) // 3 + 1
    year = today.year

    last_q = q - 1
    if last_q == 0:
        last_q = 4
        year -= 1

    return f"{year}Q{last_q}"

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


def run_daily_pipeline() -> None:
    """
    Runs every day at 2AM. Self-healing: fetches everything missing
    since the last recorded date per ticker/region, not just "today".
    If the server was down for days, this catches up automatically.
    """
    import time
    from datetime import date, timedelta
    from etl.transform_config import WEATHER_REGIONS, START_YEAR
    from etl.extract_prices import fetch_all_prices
    from etl.extract_weather import fetch_raw_weather, parse_weather, fetch_raw_nasa, parse_nasa
    from etl.load import load_raw_prices, load_raw_weather
    from db.queries import read_last_weather_date

    today = date.today()
    log.info(f"[DAILY] Self-healing fetch — target end date: {today}")
    # --- Prices: simple full refetch, upsert handles dedup ---
    log.info("[DAILY] Prices...")
    try:
        all_prices = fetch_all_prices()
        load_raw_prices(all_prices)
    except Exception as e:
        log.error(f"[DAILY] Prices failed: {e}")

    # --- Weather: incremental, rate limit matters here ---
    log.info("[DAILY] Weather...")
    for region in WEATHER_REGIONS:
        name = region["name"]
        last_date = read_last_weather_date(name)
        start = (last_date + timedelta(days=1)) if last_date else date(START_YEAR, 1, 1)

        if start > today:
            continue

        log.info(f"[DAILY] {name} weather: {start} → {today}")
        try:
            raw_weather = fetch_raw_weather(region["lat"], region["lon"], start_date=str(start), end_date=str(today))
            weather = parse_weather(raw_weather, name)
            raw_nasa = fetch_raw_nasa(region["lat"], region["lon"], start=start.strftime("%Y%m%d"), end=today.strftime("%Y%m%d"))
            nasa = parse_nasa(raw_nasa, name)
            load_raw_weather(weather, nasa)
        except Exception as e:
            log.error(f"[DAILY] {name} weather failed: {e}")
        time.sleep(2)

    log.info("[DAILY] Pipeline completed")

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
        df_ml      = _drop_incomplete_quarter(df_ml)
        load_ml_features(df_ml)

        # Retrain on fresh data
        log.info("[QUARTERLY] Step 3: Retraining model...")
        from ml.train import run_training  #made from __main__
        run_training()

        #upload new model
        from db.queries import upload_model
        upload_model()

        log.info("[QUARTERLY] Step 4: Generating predictions for all tickers...")
        from ml.predict import predict_all_tickers
        predict_all_tickers(_last_closed_quarter())

        log.info("[QUARTERLY] Step 5: Filling actual returns...")
        from db.queries import fill_actual_returns
        fill_actual_returns()

        log.info("[QUARTERLY] Pipeline completed")

    except Exception as e:
        log.error(f"[QUARTERLY] Failed: {e}")
        raise

def run_halal_check() -> None:
    """
    Weekly, re-checks Shariah compliance for all candidates.
    If the universe changed, re-runs the quarterly pipeline so
    the model no longer trains on non-compliant stocks.
    raw_prices is kept (historical data stays valid).
    """
    import json
    from pathlib import Path
    from etl.extract_halal_universe import build_halal_universe
    from db.queries import delete_ml_features_for_ticker

    log.info("[HALAL] Checking Shariah compliance...")

    universe_path = Path("halal_universe.json")
    with open(universe_path) as f:
        old_compliant = {s["ticker"] for s in json.load(f)["compliant"]}

    build_halal_universe()  # overwrites halal_universe.json

    with open(universe_path) as f:
        new_compliant = {s["ticker"] for s in json.load(f)["compliant"]}

    removed = old_compliant - new_compliant
    added   = new_compliant - old_compliant

    if not removed and not added:
        log.info("[HALAL] Universe unchanged")
        return

    if removed:
        log.info(f"[HALAL] Removed (non-compliant): {removed}")
        for ticker in removed:
            delete_ml_features_for_ticker(ticker)

    if added:
        log.info(f"[HALAL] Added (newly compliant): {added}")

    log.info("[HALAL] Universe changed — triggering quarterly pipeline...")
    run_quarterly_pipeline()


import pandas as pd
from datetime import date

def _drop_incomplete_quarter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drops the current in-progress quarter from the dataset.
    Only fully closed quarters should ever be used for training —
    a partial quarter has incomplete price/weather data and would
    look like a real data point when it isn't one yet.

    Also nulls the LAST CLOSED quarter's target: it is the return of the
    currently open quarter, which a mid-quarter run computes from partial
    prices (shift(-1) runs before this drop). Scheduled day-1 runs have no
    open-quarter prices yet, so there this is a no-op — but manual
    mid-quarter runs would otherwise write partial returns into training
    targets and into fill_actual_returns.
    """
    current_q = pd.Timestamp(date.today()).to_period("Q")
    df = df[df.index < current_q.start_time].copy()
    df.loc[df.index.to_period("Q") == current_q - 1, "stock_return_next_q"] = float("nan")
    return df

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        run_daily_pipeline,    #run_daily_fetch,
        CronTrigger(hour=2, minute=0),  # 2AM UTC every day
        id="daily_pipeline",    #id="daily_fetch",
    )

    scheduler.add_job(
        run_quarterly_pipeline,
        CronTrigger(month="1,4,7,10", day="1", hour="3", minute=0),  # 3AM after daily finishes
        id="quarterly_pipeline",
    )

    scheduler.add_job(
    run_halal_check,
    CronTrigger(day_of_week="sun", hour=1, minute=0),  # Every Sunday 1AM UTC
    id="halal_check",
    )

    log.info("Scheduler started")
    log.info("  Daily fetch    : 2AM UTC every day")
    log.info("  Quarterly pipeline : 3AM UTC — Jan 1, Apr 1, Jul 1, Oct 1")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        log.info("Scheduler stopped")