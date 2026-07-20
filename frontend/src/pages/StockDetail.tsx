import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Rectangle, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api } from '../api/client'
import StatTile from '../components/StatTile'
import InfoTip from '../components/InfoTip'
import type { PriceRecord, PredictionRecord } from '../types'

const RANGES = [
  { key: '1Y', years: 1 },
  { key: '3Y', years: 3 },
  { key: '5Y', years: 5 },
  { key: 'All', years: 99 },
] as const
type RangeKey = (typeof RANGES)[number]['key']

const AXIS_TICK = { fill: 'var(--color-ink-muted)', fontSize: 10, fontFamily: 'Space Mono' }

function fmtPct(v: number) {
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
}

/* --- custom tooltips (styled like the site's cards) --- */

function PriceTip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface border border-line-strong rounded-md px-3 py-2 font-mono text-[0.7rem]">
      <p className="m-0 text-ink-faint">{label}</p>
      <p className="m-0 text-ink">${Number(payload[0].value).toFixed(2)}</p>
    </div>
  )
}

function QuarterTip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  return (
    <div className="bg-surface border border-line-strong rounded-md px-3 py-2 font-mono text-[0.7rem] leading-relaxed">
      <p className="m-0 text-ink-faint">{label}</p>
      <p className="m-0 text-ink">
        Predicted <span className="text-cyan">{fmtPct(row.predicted)}</span>
      </p>
      {row.pending ? (
        <p className="m-0 text-ink-faint">Actual pending — quarter still open</p>
      ) : (
        <>
          <p className="m-0 text-ink">
            Actual <span className={row.actual >= 0 ? 'text-accent' : 'text-danger'}>{fmtPct(row.actual)}</span>
          </p>
          <p className={`m-0 ${row.hit ? 'text-accent' : 'text-danger'}`}>
            {row.hit ? '✓ direction hit' : '✗ direction miss'}
          </p>
        </>
      )}
    </div>
  )
}

/* --- bar shapes: 4px rounded data-end, square at the zero baseline --- */

const predShape = (p: any) => (
  <Rectangle
    {...p}
    radius={p.payload.predicted >= 0 ? [4, 4, 0, 0] : [0, 0, 4, 4]}
    fillOpacity={p.payload.pending ? 0.45 : 1}
  />
)
const actShape = (p: any) => (
  <Rectangle {...p} radius={(p.payload.actual ?? 0) >= 0 ? [4, 4, 0, 0] : [0, 0, 4, 4]} />
)

export default function StockDetail() {
  const { ticker = '' } = useParams()
  const T = ticker.toUpperCase()

  const [prices, setPrices] = useState<PriceRecord[] | null>(null)
  const [preds, setPreds] = useState<PredictionRecord[] | null>(null)
  const [name, setName] = useState('')
  const [notFound, setNotFound] = useState(false)
  const [range, setRange] = useState<RangeKey>('3Y')

  useEffect(() => {
    setPrices(null); setPreds(null); setNotFound(false)
    api.getPrices(T).then(d => setPrices(d.prices)).catch(() => setNotFound(true))
    api.getPredictions(T).then(d => setPreds(d.predictions)).catch(() => setPreds([]))
    api.getTickers()
      .then(d => setName(d.tickers.find(t => t.ticker === T)?.name ?? ''))
      .catch(() => {})
  }, [T])

  // Price series clipped to the selected range
  const visiblePrices = useMemo(() => {
    if (!prices) return []
    const years = RANGES.find(r => r.key === range)!.years
    const cutoff = new Date()
    cutoff.setFullYear(cutoff.getFullYear() - years)
    const c = cutoff.toISOString().slice(0, 10)
    return prices.filter(p => p.date >= c)
  }, [prices, range])

  // Track record rows + local stats — computed once from the predictions list
  const { rows, acc, hits, closedN, mae, current } = useMemo(() => {
    const list = [...(preds ?? [])].sort((a, b) => a.quarter.localeCompare(b.quarter))
    const rows = list.map(p => ({
      quarter: p.quarter,
      predicted: p.predicted_return,
      actual: p.actual_return,
      pending: p.actual_return == null,
      hit: p.actual_return != null && (p.predicted_return >= 0) === (p.actual_return >= 0),
    }))
    const closed = rows.filter(r => !r.pending)
    const hits = closed.filter(r => r.hit).length
    const acc = closed.length ? hits / closed.length : null
    const mae = closed.length
      ? closed.reduce((s, r) => s + Math.abs(r.predicted - (r.actual as number)), 0) / closed.length
      : null
    const current = [...rows].reverse().find(r => r.pending) ?? null
    return { rows, acc, hits, closedN: closed.length, mae, current }
  }, [preds])

  const loading = prices === null && !notFound

  if (notFound) {
    return (
      <div className="mx-auto max-w-[1000px] px-8 py-12">
        <p className="font-mono text-[0.8rem] text-ink-muted">
          No price data for “{T}” — it may not be in the halal universe.
        </p>
        <Link to="/stocks" className="font-mono text-[0.8rem] text-accent no-underline">← Back to rankings</Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-[1000px] px-8 py-12">

      {/* Header */}
      <Link to="/stocks" className="font-mono text-[0.7rem] text-ink-faint no-underline hover:text-ink-muted">
        ← Rankings
      </Link>
      <div className="flex flex-wrap items-end justify-between gap-4 mt-3">
        <div>
          <h2 className="font-display font-semibold text-[1.8rem] text-ink m-0">{T}</h2>
          {name && <p className="font-display text-[0.85rem] text-ink-muted m-0">{name}</p>}
        </div>
        <div className="flex gap-2">
          {current && (
            <span className={`font-mono text-[0.7rem] border rounded px-3 py-1 ${
              current.predicted >= 0 ? 'text-accent border-accent/40' : 'text-danger border-danger/40'
            }`}>
              {current.quarter}: {fmtPct(current.predicted)} predicted
            </span>
          )}
          {acc != null && (
            <span className="font-mono text-[0.7rem] text-ink-muted border border-line rounded px-3 py-1">
              {(acc * 100).toFixed(0)}% direction accuracy
            </span>
          )}
        </div>
      </div>

      <p className="font-display text-[0.8rem] text-ink-muted leading-relaxed mt-4 mb-0 max-w-[680px]">
        Model forecasts — not investment advice. Verify current Shariah compliance and any
        purification owed on non-compliant income before acting.
      </p>

      {/* Price history */}
      <section className="mt-10">
        <div className="flex items-center justify-between mb-4">
          <p className="font-mono text-[0.7rem] text-accent tracking-[0.12em] m-0 flex items-center gap-1.5">
            Price history
            <InfoTip text="Daily adjusted close from Yahoo Finance — the same series the model's quarterly return features are built from." />
          </p>
          <div className="flex gap-1">
            {RANGES.map(r => (
              <button
                key={r.key}
                onClick={() => setRange(r.key)}
                className={`font-mono text-[0.65rem] px-2.5 py-1 rounded border cursor-pointer transition-colors duration-150 ${
                  range === r.key
                    ? 'text-ink border-accent/60'
                    : 'text-ink-faint border-line hover:text-ink-muted'
                }`}
              >
                {r.key}
              </button>
            ))}
          </div>
        </div>

        <div className="border border-line rounded-lg bg-surface/40 p-4">
          {loading ? (
            <div className="h-[300px] animate-pulse bg-surface rounded" />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={visiblePrices} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--color-accent)" stopOpacity={0.14} />
                    <stop offset="100%" stopColor="var(--color-accent)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--color-line)" vertical={false} />
                <XAxis
                  dataKey="date" tick={AXIS_TICK} tickLine={false}
                  axisLine={{ stroke: 'var(--color-line)' }}
                  minTickGap={60}
                  tickFormatter={(d: string) => (range === '1Y' ? d.slice(0, 7) : d.slice(0, 4))}
                />
                <YAxis
                  tick={AXIS_TICK} tickLine={false} axisLine={false} width={56}
                  domain={['auto', 'auto']}
                  tickFormatter={(v: number) => `$${Math.round(v)}`}
                />
                <Tooltip content={<PriceTip />} cursor={{ stroke: 'var(--color-line-strong)' }} />
                <Area
                  type="monotone" dataKey="close"
                  stroke="var(--color-accent)" strokeWidth={2}
                  fill="url(#priceFill)" dot={false} isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>

      {/* Track record */}
      <section className="mt-10">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <p className="font-mono text-[0.7rem] text-accent tracking-[0.12em] m-0 flex items-center gap-1.5">
            Predicted vs actual, by quarter
            <InfoTip text="Every bar pair is a genuine out-of-sample walk-forward prediction — the model only ever saw quarters before the one it predicted. The faded bar is the still-open quarter." />
          </p>
          {/* legend — 2 series, so it's mandatory */}
          <div className="flex gap-4 font-mono text-[0.65rem] text-ink-muted">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-cyan inline-block" /> Predicted
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-ink inline-block" /> Actual
            </span>
          </div>
        </div>

        <div className="border border-line rounded-lg bg-surface/40 p-4">
          {preds === null ? (
            <div className="h-[280px] animate-pulse bg-surface rounded" />
          ) : rows.length === 0 ? (
            <p className="font-mono text-[0.75rem] text-ink-faint m-0 p-8 text-center">
              No track record for {T} yet — predictions appear after the next training run.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barGap={2}>
                <CartesianGrid stroke="var(--color-line)" vertical={false} />
                <XAxis dataKey="quarter" tick={AXIS_TICK} tickLine={false}
                  axisLine={{ stroke: 'var(--color-line)' }} />
                <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} width={48}
                  tickFormatter={(v: number) => `${v}%`} />
                <ReferenceLine y={0} stroke="var(--color-line-strong)" />
                <Tooltip content={<QuarterTip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                <Bar dataKey="predicted" fill="var(--color-cyan)" maxBarSize={24} shape={predShape} />
                <Bar dataKey="actual" fill="var(--color-ink)" maxBarSize={24} shape={actShape} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>

      {/* Stats */}
      {closedN > 0 && (
        <section className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-px bg-line border border-line rounded-lg overflow-hidden mt-10">
          <StatTile
            label="Direction accuracy"
            value={acc != null ? `${(acc * 100).toFixed(0)}%` : '—'}
            sub={`${hits} of ${closedN} closed quarters`}
            tip="Did the model at least call up vs down correctly? 50% ≈ coin flip. Small sample — one quarter swings this a lot."
          />
          <StatTile
            label="Avg magnitude error"
            value={mae != null ? `${mae.toFixed(1)} pp` : '—'}
            sub="mean |predicted − actual|"
            tip="How far off the prediction was on average, in percentage points — the per-stock cousin of the RMSE the model is trained to minimize."
          />
          <StatTile
            label="Current forecast"
            value={current ? fmtPct(current.predicted) : '—'}
            valueClass={current ? (current.predicted >= 0 ? 'text-accent' : 'text-danger') : 'text-ink'}
            sub={current ? `for ${current.quarter}` : 'quarter closed'}
          />
          <StatTile label="Quarters tracked" value={String(closedN)} sub="out-of-sample only" />
        </section>
      )}
    </div>
  )
}
