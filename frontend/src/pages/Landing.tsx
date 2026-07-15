import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { RankingRecord } from '../types'

export default function Landing() {

    const navigate = useNavigate()
    const [topStocks, setTopStocks] = useState<RankingRecord []>([])
    const [tickerCount, setTickerCount] = useState<number>(0)
    const [regionCount, setRegionCount] = useState<number>(0)
    const [latestModel, setLatestModel] = useState<string>('—')


    useEffect(() => {


        api.getRankings()
            .then(data => setTopStocks(data.rankings.slice(0, 3)))
            .catch(() => setTopStocks([
            { ticker: 'CTVA', quarter: '2025Q1', predicted_return: 8.24, model_version: 'Random Forest' },
            { ticker: 'ADM',  quarter: '2025Q1', predicted_return: 5.11, model_version: 'Random Forest' },
            { ticker: 'BG',   quarter: '2025Q1', predicted_return: 3.87, model_version: 'Random Forest' },
            ]))

        api.getTickers()
            .then(data => setTickerCount(data.tickers.length))
            .catch(() => setTickerCount(10))

        api.getWeather()
            .then(data => setRegionCount(data.regions.length))
            .catch(() => setRegionCount(10))

        api.getLatestModel()
            .then(data => setLatestModel(data.best_model))
            .catch(() => setLatestModel('Random Forest'))

    }, [])



    const stats = [
        { label: 'Halal stocks tracked', value: tickerCount || '—', mono: false },
        { label: 'Weather regions',      value: regionCount || '—', mono: false },
        { label: 'Model features',       value: '233',              mono: true  }, //should change with quarterly retrain as data selected remains same. CHANGE IF I remove columns because like model perf
        { label: 'Current model',        value: latestModel, mono: true },
    ]

    const steps = [
    {
        number: '01',
        title: 'Collect',
        description: 'Daily harvest of satellite weather data from NASA POWER and Open-Meteo across 10 agricultural regions, global crop yields from FAOSTAT and halal-screened equity prices via yfinance.',
    },
    {
        number: '02',
        title: 'Model',
        description: 'Walk-forward cross-validation across OLS, Random Forest and XGBoost. Each quarter trains on all prior data, no look-ahead bias. Best model is selected automatically and retrained on the full dataset.',
    },
    {
        number: '03',
        title: 'Predict',
        description: 'Quarterly return forecasts for each halal stock. Predictions are stored alongside actual returns as quarters close, building a live track record of directional accuracy over time.',
    },
    ]

    return (
        <div className="min-h-screen px-8 py-16 max-w-[1100px] mx-auto">

        {/* Hero */}
        <section className="mb-24">
            <p className="font-mono text-[0.7rem] text-accent tracking-[0.12em] mb-6">
                Agricultural quantitative analysis
            </p>

            <h1 className="font-display font-semibold text-[clamp(1.8rem,3.5vw,3rem)] leading-[1.2] text-ink mt-0 mb-5">
                Where weather moves markets.
            </h1>

            <p className="font-display font-normal text-[0.95rem] text-ink-muted max-w-[480px] leading-[1.75] mt-0 mb-10">
                AgriQuant cross-references satellite weather data, global crop yields,
                and halal-screened agricultural equities to predict quarterly stock returns.
            </p>

            <div className="flex gap-4">
                <button onClick={() => navigate('/globe')} className="font-display font-semibold text-[0.85rem] px-6 py-[0.65rem] bg-accent text-canvas rounded cursor-pointer">
                Explore Globe
                </button>
                <button onClick={() => navigate('/stocks')} className="font-display font-semibold text-[0.85rem] px-6 py-[0.65rem] bg-transparent text-ink border border-line-strong rounded cursor-pointer">
                View Rankings
                </button>
            </div>
        </section>


        {/* Stat cards */}
        <section className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-px bg-line border border-line rounded-lg overflow-hidden mb-24">
        {stats.map(({ label, value, mono }) => (
            <div key={label} className="bg-surface p-7">
            <p className="font-mono text-[0.65rem] text-ink-muted tracking-[0.1em] uppercase mt-0 mb-3">
                {label}
            </p>
            <p className={`${mono ? 'font-mono' : 'font-display'} text-[1.6rem] font-bold text-ink m-0`}>
                {value}
            </p>
            </div>
        ))}
        </section>


        {/* How it works */}
        <section className="mb-24">
        <p className="font-mono text-[0.7rem] text-accent tracking-[0.12em] mb-12">
            How it works
        </p>

        <div className="flex flex-col gap-0">
            {steps.map(({ number, title, description }) => (
            <div key={number} className="grid grid-cols-[80px_1fr] gap-8 py-8 border-t border-line">
                <span className="font-mono text-[0.75rem] text-ink-faint pt-[0.2rem]">
                {number}
                </span>
                <div>
                <p className="font-display font-semibold text-base text-ink mt-0 mb-2">
                    {title}
                </p>
                <p className="font-display text-[0.9rem] text-ink-muted leading-[1.75] m-0 max-w-[560px]">
                    {description}
                </p>
                </div>
            </div>
            ))}
            <div className="border-t border-line" />
        </div>
        </section>

        {/* Top stocks preview */}
        <section className="mb-24">
        <div className="flex justify-between items-baseline mb-6">
            <p className="font-mono text-[0.7rem] text-accent tracking-[0.12em] m-0">
            Top predictions this quarter
            </p>
            <button onClick={() => navigate('/stocks')} className="font-mono text-[0.7rem] text-ink-muted bg-transparent cursor-pointer tracking-[0.08em]">
            View all →
            </button>
        </div>

        <div className="border border-line rounded-lg overflow-hidden">
            {/* Header */}
            <div className="grid grid-cols-3 px-6 py-3 border-b border-line">
            {['Ticker', 'Quarter', 'Predicted Return'].map(h => (
                <span key={h} className="font-mono text-[0.65rem] text-ink-faint tracking-[0.1em] uppercase">
                {h}
                </span>
            ))}
            </div>

            {/* Rows */}
            {topStocks.length === 0
            ? <div className="px-6 py-8">
                <span className="font-mono text-[0.8rem] text-ink-faint">
                    Loading...
                </span>
                </div>

            : topStocks.map(r => (
                <div
                    key={r.ticker}
                    onClick={() => navigate(`/stocks/${r.ticker}`)}
                    className="grid grid-cols-3 px-6 py-4 border-b border-line cursor-pointer transition-colors duration-150 hover:bg-surface"
                >
                    <span className="font-mono text-[0.9rem] text-ink">
                    {r.ticker}
                    </span>
                    <span className="font-mono text-[0.9rem] text-ink-muted">
                    {r.quarter}
                    </span>
                    <span className={`font-mono text-[0.9rem] ${r.predicted_return >= 0 ? 'text-accent' : 'text-danger'}`}>
                    {r.predicted_return >= 0 ? '+' : ''}{r.predicted_return.toFixed(2)}%
                    </span>
                </div>
                ))
            }
        </div>
        </section>


        </div>
    )
}
