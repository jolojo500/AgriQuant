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
    <div className="mx-auto max-w-[900px] px-8 py-12">

      {/* Header */}
      <p className="font-mono text-[0.7rem] text-accent tracking-[0.12em] mb-2">
        Halal agricultural equities
      </p>
      <h2 className="font-display font-semibold text-[1.8rem] text-ink mt-0 mb-10">
        Stock Rankings
      </h2>

      {/* Tabs */}
      <div className="flex gap-0 mb-8 border-b border-line">
        {([['predicted', 'Predicted Return'], ['reliability', 'Model Reliability']] as const).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`font-display font-semibold text-[0.85rem] px-6 py-3 bg-transparent -mb-px cursor-pointer transition-colors duration-200 border-b-2 ${
              tab === key ? 'text-ink border-accent' : 'text-ink-muted border-transparent'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="border border-line rounded-lg overflow-hidden">
        {tab === 'predicted' ? (
          <>
            <div className="grid grid-cols-[2fr_1fr_1fr_1fr] px-6 py-3 border-b border-line">
              {['Ticker', 'Quarter', 'Predicted Return', 'Model'].map(h => (
                <span key={h} className="font-mono text-[0.65rem] text-ink tracking-[0.1em] uppercase">
                  {h}
                </span>
              ))}
            </div>
            {rankings.map(r => (
              <div
                key={r.ticker}
                onClick={() => navigate(`/stocks/${r.ticker}`)}
                className="grid grid-cols-[2fr_1fr_1fr_1fr] px-6 py-4 border-b border-line cursor-pointer transition-colors duration-150 hover:bg-surface"
              >
                <span className="font-mono text-[0.9rem] text-ink">{r.ticker}</span>
                <span className="font-mono text-[0.9rem] text-ink-muted">{r.quarter}</span>
                <span className={`font-mono text-[0.9rem] ${r.predicted_return >= 0 ? 'text-accent' : 'text-danger'}`}>
                  {r.predicted_return >= 0 ? '+' : ''}{r.predicted_return.toFixed(2)}%
                </span>
                <span className="font-mono text-[0.75rem] text-ink">{r.model_version}</span>
              </div>
            ))}
          </>
        ) : (
          <>
            <div className="grid grid-cols-[2fr_1fr_1fr] px-6 py-3 border-b border-line">
              {['Ticker', 'Direction Accuracy', 'Quarters Tracked'].map(h => (
                <span key={h} className="font-mono text-[0.65rem] text-ink tracking-[0.1em] uppercase">
                  {h}
                </span>
              ))}
            </div>
            {reliability.map(r => (
              <div
                key={r.ticker}
                onClick={() => navigate(`/stocks/${r.ticker}`)}
                className="grid grid-cols-[2fr_1fr_1fr] px-6 py-4 border-b border-line cursor-pointer transition-colors duration-150 hover:bg-surface"
              >
                <span className="font-mono text-[0.9rem] text-ink">{r.ticker}</span>
                <span className={`font-mono text-[0.9rem] ${r.direction_accuracy >= 0.6 ? 'text-accent' : r.direction_accuracy >= 0.5 ? 'text-warn' : 'text-danger'}`}>
                  {(r.direction_accuracy * 100).toFixed(0)}%
                </span>
                <span className="font-mono text-[0.9rem] text-ink-muted">{r.n_predictions}Q</span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  )
}
