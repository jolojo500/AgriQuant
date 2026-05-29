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
        api.getRankings().then(data => setTopStocks(data.rankings.slice(0,3))).catch(() => {})
        api.getTickers().then(data => setTickerCount(data.tickers.length)).catch(() => {})
        api.getWeather().then(data => setRegionCount(data.regions.length)).catch(() => {})
        api.getLatestModel().then(data => setLatestModel(data.best_model)).catch(() => {})
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
        <div style={{ minHeight: '100vh', padding: '4rem 2rem', maxWidth: '1100px', margin: '0 auto' }}>

        {/* Hero */}
        <section style={{ marginBottom: '6rem' }}>
            <p style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.7rem',
                color: 'var(--green)',
                letterSpacing: '0.12em',
                marginBottom: '1.5rem',
            }}>
                Agricultural quantitative analysis
            </p>

            <h1 style={{
                fontFamily: 'var(--font-display)',
                fontWeight: 600,
                fontSize: 'clamp(1.8rem, 3.5vw, 3rem)',
                lineHeight: 1.2,
                color: 'var(--text-primary)',
                margin: '0 0 1.25rem',
            }}>
                Where weather moves markets.
            </h1>

            <p style={{
                fontFamily: 'var(--font-display)',
                fontWeight: 400,
                fontSize: '0.95rem',
                color: 'var(--text-secondary)', //#FFFFED this also kinda good ngl, might be better for eyes
                maxWidth: '480px',
                lineHeight: 1.75,
                margin: '0 0 2.5rem',
            }}>
                AgriQuant cross-references satellite weather data, global crop yields,
                and halal-screened agricultural equities to predict quarterly stock returns.
            </p>

            <div style={{ display: 'flex', gap: '1rem' }}>
                <button onClick={() => navigate('/globe')} style={{
                fontFamily: 'var(--font-display)',
                fontWeight: 600,
                fontSize: '0.85rem',
                padding: '0.65rem 1.5rem',
                background: 'var(--green)',
                color: 'var(--bg-primary)',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                }}>
                Explore Globe
                </button>
                <button onClick={() => navigate('/stocks')} style={{
                fontFamily: 'var(--font-display)',
                fontWeight: 600,
                fontSize: '0.85rem',
                padding: '0.65rem 1.5rem',
                background: 'transparent',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-bright)',
                borderRadius: '4px',
                cursor: 'pointer',
                }}>
                View Rankings
                </button>
            </div>
        </section>

        
        {/* Stat cards */}
        <section style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1px',
        background: 'var(--border)',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        overflow: 'hidden',
        marginBottom: '6rem',
        }}>
        {stats.map(({ label, value, mono }) => (
            <div key={label} style={{
            background: 'var(--bg-card)',
            padding: '1.75rem',
            }}>
            <p style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.65rem',
                color: 'var(--text-secondary)',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                margin: '0 0 0.75rem',
            }}>
                {label}
            </p>
            <p style={{
                fontFamily: mono ? 'var(--font-mono)' : 'var(--font-display)',
                fontSize: '1.6rem',
                fontWeight: 700,
                color: 'var(--text-primary)',
                margin: 0,
            }}>
                {value}
            </p>
            </div>
        ))}
        </section>


        {/* How it works */}
        <section style={{ marginBottom: '6rem' }}>
        <p style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.7rem',
            color: 'var(--green)',
            letterSpacing: '0.12em',
            marginBottom: '3rem',
        }}>
            How it works
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0px' }}>
            {steps.map(({ number, title, description }) => (
            <div key={number} style={{
                display: 'grid',
                gridTemplateColumns: '80px 1fr',
                gap: '2rem',
                padding: '2rem 0',
                borderTop: '1px solid var(--border)',
            }}>
                <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.75rem',
                color: 'var(--text-muted)',
                paddingTop: '0.2rem',
                }}>
                {number}
                </span>
                <div>
                <p style={{
                    fontFamily: 'var(--font-display)',
                    fontWeight: 600,
                    fontSize: '1rem',
                    color: 'var(--text-primary)',
                    margin: '0 0 0.5rem',
                }}>
                    {title}
                </p>
                <p style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: '0.9rem',
                    color: 'var(--text-secondary)',
                    lineHeight: 1.75,
                    margin: 0,
                    maxWidth: '560px',
                }}>
                    {description}
                </p>
                </div>
            </div>
            ))}
            <div style={{ borderTop: '1px solid var(--border)' }} />
        </div>
        </section>

        {/* Top stocks preview */}
        <section style={{ marginBottom: '6rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '1.5rem' }}>
            <p style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.7rem',
            color: 'var(--green)',
            letterSpacing: '0.12em',
            margin: 0,
            }}>
            Top predictions this quarter
            </p>
            <button onClick={() => navigate('/stocks')} style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.7rem',
            color: 'var(--text-secondary)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            letterSpacing: '0.08em',
            }}>
            View all →
            </button>
        </div>

        <div style={{ border: '1px solid var(--border)', borderRadius: '8px', overflow: 'hidden' }}>
            {/* Header */}
            <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr 1fr',
            padding: '0.75rem 1.5rem',
            borderBottom: '1px solid var(--border)',
            }}>
            {['Ticker', 'Quarter', 'Predicted Return'].map(h => (
                <span key={h} style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.65rem',
                color: 'var(--text-muted)',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                }}>
                {h}
                </span>
            ))}
            </div>

            {/* Rows */}
            {topStocks.length === 0
            ? <div style={{ padding: '2rem 1.5rem' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Loading...
                </span>
                </div>
                      
            : topStocks.map(r => (
                <div
                    key={r.ticker}
                    onClick={() => navigate(`/stocks/${r.ticker}`)}
                    style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 1fr',
                    padding: '1rem 1.5rem',
                    borderBottom: '1px solid var(--border)',
                    cursor: 'pointer',
                    transition: 'background 0.15s',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-card)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                    {r.ticker}
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                    {r.quarter}
                    </span>
                    <span style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.9rem',
                    color: r.predicted_return >= 0 ? 'var(--green)' : 'var(--red)',
                    }}>
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