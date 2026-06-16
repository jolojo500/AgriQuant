import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { RankingRecord, ReliabilityRecord } from '../types'

type Tab = 'predicted' | 'reliability'

export default function Stocks() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('predicted')
  const [rankings, setRankings] = useState<RankingRecord[]>([])
  const [reliability, setReliability] = useState<ReliabilityRecord[]>([])

  useEffect(() => {
    api.getRankings()
      .then(data => setRankings(data.rankings))
      .catch(() => setRankings([
        { ticker: 'CTVA', quarter: '2025Q1', predicted_return: 8.24,  model_version: 'Random Forest' },
        { ticker: 'ADM',  quarter: '2025Q1', predicted_return: 5.11,  model_version: 'Random Forest' },
        { ticker: 'BG',   quarter: '2025Q1', predicted_return: 3.87,  model_version: 'Random Forest' },
        { ticker: 'INGR', quarter: '2025Q1', predicted_return: 1.22,  model_version: 'Random Forest' },
        { ticker: 'IPI',  quarter: '2025Q1', predicted_return: -2.05, model_version: 'Random Forest' },
      ]))

    api.getReliability()
      .then(data => setReliability(data.rankings))
      .catch(() => setReliability([
        { ticker: 'CTVA', direction_accuracy: 0.75, n_predictions: 8 },
        { ticker: 'ADM',  direction_accuracy: 0.67, n_predictions: 9 },
        { ticker: 'BG',   direction_accuracy: 0.62, n_predictions: 8 },
        { ticker: 'INGR', direction_accuracy: 0.55, n_predictions: 7 },
        { ticker: 'IPI',  direction_accuracy: 0.44, n_predictions: 9 },
      ]))
  }, [])

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '3rem 2rem' }}>

      {/* Header */}
      <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--green)', letterSpacing: '0.12em', marginBottom: '0.5rem' }}>
        Halal agricultural equities
      </p>
      <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: '1.8rem', color: 'var(--text-primary)', margin: '0 0 2.5rem' }}>
        Stock Rankings
      </h2>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0', marginBottom: '2rem', borderBottom: '1px solid var(--border)' }}>
        {([['predicted', 'Predicted Return'], ['reliability', 'Model Reliability']] as const).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 600,
              fontSize: '0.85rem',
              padding: '0.75rem 1.5rem',
              background: 'none',
              border: 'none',
              borderBottom: tab === key ? '2px solid var(--green)' : '2px solid transparent',
              color: tab === key ? 'var(--text-primary)' : 'var(--text-secondary)',
              cursor: 'pointer',
              marginBottom: '-1px',
              transition: 'color 0.2s',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div style={{ border: '1px solid var(--border)', borderRadius: '8px', overflow: 'hidden' }}>
        {tab === 'predicted' ? (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', padding: '0.75rem 1.5rem', borderBottom: '1px solid var(--border)' }}>
              {['Ticker', 'Quarter', 'Predicted Return', 'Model'].map(h => (
                <span key={h} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                  {h}
                </span>
              ))}
            </div>
            {rankings.map(r => (
              <div
                key={r.ticker}
                onClick={() => navigate(`/stocks/${r.ticker}`)}
                style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', padding: '1rem 1.5rem', borderBottom: '1px solid var(--border)', cursor: 'pointer', transition: 'background 0.15s' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-card)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: 'var(--text-primary)' }}>{r.ticker}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{r.quarter}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: r.predicted_return >= 0 ? 'var(--green)' : 'var(--red)' }}>
                  {r.predicted_return >= 0 ? '+' : ''}{r.predicted_return.toFixed(2)}%
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>{r.model_version}</span>
              </div>
            ))}
          </>
        ) : (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', padding: '0.75rem 1.5rem', borderBottom: '1px solid var(--border)' }}>
              {['Ticker', 'Direction Accuracy', 'Quarters Tracked'].map(h => (
                <span key={h} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                  {h}
                </span>
              ))}
            </div>
            {reliability.map(r => (
              <div
                key={r.ticker}
                onClick={() => navigate(`/stocks/${r.ticker}`)}
                style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', padding: '1rem 1.5rem', borderBottom: '1px solid var(--border)', cursor: 'pointer', transition: 'background 0.15s' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-card)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: 'var(--text-primary)' }}>{r.ticker}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: r.direction_accuracy >= 0.6 ? 'var(--green)' : r.direction_accuracy >= 0.5 ? 'var(--amber)' : 'var(--red)' }}>
                  {(r.direction_accuracy * 100).toFixed(0)}%
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{r.n_predictions}Q</span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  )
}