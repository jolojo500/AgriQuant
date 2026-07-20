import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../api/client'
import StatTile from '../components/StatTile'
import type { RankingRecord, ReliabilityRecord } from '../types'
import InfoTip from '../components/InfoTip'

//one merged row = ranking ∪ reliability ∪ company name
type Row = {
  ticker: string
  name: string
  quarter: string
  predicted_return: number
  model_version: string
  direction_accuracy: number | null  //null when no closed quarters yet
  n_predictions: number
}

type SortKey = 'predicted' | 'accuracy'


const FALLBACK_RANKINGS: RankingRecord[] = [
  { ticker: 'CTVA', quarter: '2025Q2', predicted_return: 8.24,  model_version: 'Random Forest' },
  { ticker: 'LNN',  quarter: '2025Q2', predicted_return: 5.11,  model_version: 'Random Forest' },
  { ticker: 'CALM', quarter: '2025Q2', predicted_return: 3.87,  model_version: 'Random Forest' },
  { ticker: 'INGR', quarter: '2025Q2', predicted_return: 1.22,  model_version: 'Random Forest' },
  { ticker: 'IPI',  quarter: '2025Q2', predicted_return: -2.05, model_version: 'Random Forest' },
]
const FALLBACK_RELIABILITY: ReliabilityRecord[] = [
  { ticker: 'CTVA', direction_accuracy: 0.75, n_predictions: 8 },
  { ticker: 'LNN',  direction_accuracy: 0.67, n_predictions: 9 },
  { ticker: 'CALM', direction_accuracy: 0.62, n_predictions: 8 },
  { ticker: 'INGR', direction_accuracy: 0.55, n_predictions: 7 },
  { ticker: 'IPI',  direction_accuracy: 0.44, n_predictions: 9 },
]


function accClasses(acc: number | null): { fill: string; track: string; text: string } {
  if (acc === null)  return { fill: 'bg-line-strong', track: 'bg-line/40', text: 'text-ink-faint' }
  if (acc >= 0.6)    return { fill: 'bg-accent', track: 'bg-accent/20', text: 'text-accent' }
  if (acc >= 0.5)    return { fill: 'bg-warn',   track: 'bg-warn/20',   text: 'text-warn' }
  return               { fill: 'bg-danger', track: 'bg-danger/20', text: 'text-danger' }
}

export default function Stocks() {
  const navigate = useNavigate()
  const [rankings, setRankings] = useState<RankingRecord[] | null>(null)
  const [reliability, setReliability] = useState<ReliabilityRecord[] | null>(null)
  const [names, setNames] = useState<Record<string, string>>({})
  const [overallAcc, setOverallAcc] = useState<{ direction_accuracy: number | null; n_predictions: number } | null>(null)
  const [sortBy, setSortBy] = useState<SortKey>('predicted')
  const [offline, setOffline] = useState(false)

  useEffect(() => {
    api.getRankings()
      .then(d => setRankings(d.rankings))
      .catch(() => { setOffline(true); setRankings(FALLBACK_RANKINGS) })
    api.getReliability()
      .then(d => setReliability(d.rankings))
      .catch(() => setReliability(FALLBACK_RELIABILITY))
    api.getTickers()
      .then(d => setNames(Object.fromEntries(d.tickers.map(t => [t.ticker, t.name]))))
      .catch(() => setNames({}))
    api.getModelAccuracy()
      .then(setOverallAcc)
      .catch(() => setOverallAcc(null))
  }, [])

  const loading = rankings === null || reliability === null

  const rows: Row[] = useMemo(() => {
    if (!rankings) return []
    const rel = new Map((reliability ?? []).map(r => [r.ticker, r]))
    return rankings
      .map(r => ({
        ticker: r.ticker,
        name: names[r.ticker] ?? '',
        quarter: r.quarter,
        predicted_return: r.predicted_return,
        model_version: r.model_version,
        direction_accuracy: rel.get(r.ticker)?.direction_accuracy ?? null,
        n_predictions: rel.get(r.ticker)?.n_predictions ?? 0,
      }))
      .sort((a, b) =>
        sortBy === 'predicted'
          ? b.predicted_return - a.predicted_return
          : (b.direction_accuracy ?? -1) - (a.direction_accuracy ?? -1),
      )
  }, [rankings, reliability, names, sortBy])

  // Scale for the diverging bars: the largest |return| fills half the track
  const maxAbs = useMemo(
    () => Math.max(0.01, ...rows.map(r => Math.abs(r.predicted_return))),
    [rows],
  )

  const quarter = rows[0]?.quarter ?? '—'
  const topPick = rows.length
    ? rows.reduce((a, b) => (b.predicted_return > a.predicted_return ? b : a))
    : null
  const avgPredicted = rows.length
    ? rows.reduce((s, r) => s + r.predicted_return, 0) / rows.length
    : 0

  const fmtPct = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`

    const headerBtn = (key: SortKey, label: string) => (
    <button
      onClick={() => setSortBy(key)}
      className={`font-mono text-[0.65rem] tracking-[0.1em] uppercase text-left cursor-pointer bg-transparent p-0 transition-colors duration-200 ${
        sortBy === key ? 'text-ink' : 'text-ink-faint hover:text-ink-muted'
      }`}
    >
      {label} <span className={sortBy === key ? 'text-accent' : ''}>{sortBy === key ? '▾' : '↕'}</span>
    </button>
  )


  return (
    <div className="mx-auto max-w-[1000px] px-8 py-12">

      {/* Header */}
      <div className="flex items-baseline justify-between">
        <div>
          <p className="font-mono text-[0.7rem] text-accent tracking-[0.12em] mb-2">
            Halal agricultural equities
          </p>
          <h2 className="font-display font-semibold text-[1.8rem] text-ink mt-0 mb-0">
            Stock Rankings
          </h2>
        </div>
        <span className="font-mono text-[0.7rem] text-ink-muted border border-line rounded px-3 py-1">
          {quarter} forecast
        </span>
      </div>

      {offline && (
        <p className="font-mono text-[0.7rem] text-warn mt-3 mb-0">
          Live API unreachable — showing sample data
        </p>
      )}
      <p className="font-display text-[0.8rem] text-ink-muted leading-relaxed mt-4 mb-0 max-w-[680px]">
        Model forecasts, not investment advice. Compliance is screened via Zoya (AAOIFI)
        and re-checked weekly, but always verify each stock's current status and calculate
        any purification owed on non-compliant income before acting.
      </p>


      {/* KPI strip */}
      <section className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-px bg-line border border-line rounded-lg overflow-hidden mt-8 mb-10">
        <StatTile
          label="Top pick"
          value={topPick ? topPick.ticker : '—'}
          sub={topPick ? `${fmtPct(topPick.predicted_return)} predicted` : undefined}
        />
        <StatTile
          label="Avg predicted return"
          value={fmtPct(avgPredicted)}
          valueClass={avgPredicted >= 0 ? 'text-accent' : 'text-danger'}
          sub={`across ${rows.length} stocks`}
        />
        <StatTile
          label="Model direction accuracy"
          value={overallAcc?.direction_accuracy != null ? `${(overallAcc.direction_accuracy * 100).toFixed(0)}%` : '—'}
          sub={overallAcc ? `${overallAcc.n_predictions} closed predictions, all tickers` : undefined}
          tip="Pooled across every ticker and closed quarter, statistically sturdier than the per-ticker numbers which each rest on only ~8-17 quarters."
        />
        <StatTile
          label="Universe"
          value={String(rows.length)}
          sub="halal-screened stocks"
        />
      </section>

      {/* Leaderboard */}
      <div className="border border-line rounded-lg overflow-hidden">
        <div className="grid grid-cols-[2.5rem_1.4fr_1.3fr_1.2fr_0.7fr] gap-4 items-center px-6 py-3 border-b border-line">
          <span className="font-mono text-[0.65rem] text-ink-faint tracking-[0.1em] uppercase">#</span>
          <span className="font-mono text-[0.65rem] text-ink-faint tracking-[0.1em] uppercase">Stock</span>
            <span className="flex items-center gap-1.5">
              {headerBtn('predicted', 'Predicted return')}
              <InfoTip text="The model's forecast of next quarter's price return, made from this quarter's weather, yield and price features. A forecast, not advice." />
            </span>
            <span className="flex items-center gap-1.5">
              {headerBtn('accuracy', 'Direction accuracy')}
              <InfoTip text="Share of closed quarters where the model called the direction (up vs down) correctly. 50% ≈ coin flip. Per-ticker samples are small, treat gently." />
            </span>
          <span className="font-mono text-[0.65rem] text-ink-faint tracking-[0.1em] uppercase">Model</span>
        </div>

        {loading
          ? Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="grid grid-cols-[2.5rem_1.4fr_1.3fr_1.2fr_0.7fr] gap-4 items-center px-6 py-4 border-b border-line animate-pulse">
                {Array.from({ length: 5 }).map((_, j) => (
                  <div key={j} className="h-3 rounded bg-surface" />
                ))}
              </div>
            ))
          : rows.map((r, i) => {
              const acc = accClasses(r.direction_accuracy)
              const pos = r.predicted_return >= 0
              return (
                <motion.div
                  key={r.ticker}
                  layout
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25, delay: i * 0.03 }}
                  onClick={() => navigate(`/stocks/${r.ticker}`)}
                  className="grid grid-cols-[2.5rem_1.4fr_1.3fr_1.2fr_0.7fr] gap-4 items-center px-6 py-4 border-b border-line cursor-pointer transition-colors duration-150 hover:bg-surface"
                >
                  <span className="font-mono text-[0.75rem] text-ink-faint tabular-nums">
                    {String(i + 1).padStart(2, '0')}
                  </span>

                  <div className="min-w-0">
                    <span className="font-mono text-[0.9rem] text-ink">{r.ticker}</span>
                    {r.name && (
                      <p className="font-display text-[0.7rem] text-ink-muted m-0 truncate">{r.name}</p>
                    )}
                  </div>

                  {/* Diverging bar: zero-centered, rounded data-end, square baseline */}
                  <div className="flex items-center gap-3">
                    <span className={`font-mono text-[0.9rem] tabular-nums w-[4.5rem] ${pos ? 'text-accent' : 'text-danger'}`}>
                      {fmtPct(r.predicted_return)}
                    </span>
                    <div className="relative h-1.5 flex-1 max-w-[120px] bg-line/40 rounded-full">
                      <div className="absolute left-1/2 top-0 bottom-0 w-px bg-line-strong" />
                      <div
                        className={`absolute top-0 bottom-0 ${pos ? 'left-1/2 rounded-r-full bg-accent' : 'right-1/2 rounded-l-full bg-danger'}`}
                        style={{ width: `${(Math.abs(r.predicted_return) / maxAbs) * 50}%` }}
                      />
                    </div>
                  </div>

                  {/* Accuracy meter: same-ramp track, status thresholds */}
                  <div className="flex items-center gap-3">
                    <span className={`font-mono text-[0.9rem] tabular-nums w-[2.6rem] ${acc.text}`}>
                      {r.direction_accuracy != null ? `${(r.direction_accuracy * 100).toFixed(0)}%` : '—'}
                    </span>
                    <div className={`h-1.5 flex-1 max-w-[90px] rounded-full ${acc.track}`}>
                      <div
                        className={`h-full rounded-full ${acc.fill}`}
                        style={{ width: `${(r.direction_accuracy ?? 0) * 100}%` }}
                      />
                    </div>
                    <span className="font-mono text-[0.7rem] text-ink-faint">
                      {r.n_predictions > 0 ? `${r.n_predictions}Q` : ''}
                    </span>
                  </div>

                  <span className="font-mono text-[0.7rem] text-ink-faint truncate">{r.model_version}</span>
                </motion.div>
              )
            })}
      </div>

      <p className="font-mono text-[0.65rem] text-ink-faint mt-4">
        Click a row for price history and the model's full track record.
      </p>
    </div>
  )
}
