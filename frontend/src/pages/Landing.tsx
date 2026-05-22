import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { RankingRecord } from '../types'

export default function Landing() {
  const navigate = useNavigate()
  const [topStock, setTopStock] = useState<RankingRecord | null>(null)

  useEffect(() => {
    api.getRankings()
      .then(data => setTopStock(data.rankings[0] ?? null))
      .catch(() => {})
  }, [])

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

    </div>
  )
}