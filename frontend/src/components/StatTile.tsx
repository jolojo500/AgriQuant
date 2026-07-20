import InfoTip from './InfoTip'

type Props = {
  label: string
  value: string
  sub?: string
  valueClass?: string  // status color (could be null if no return)
  mono?: boolean
  tip?: string
}

export default function StatTile({ label, value, sub, valueClass = 'text-ink', mono = true, tip }: Props) {
  return (
    <div className="bg-surface p-7">
      <p className="font-mono text-[0.65rem] text-ink-muted tracking-[0.1em] uppercase mt-0 mb-3 flex items-center gap-1.5">
        {label} {tip && <InfoTip text={tip} />}
      </p>
      <p className={`${mono ? 'font-mono' : 'font-display'} text-[1.6rem] font-bold m-0 ${valueClass}`}>
        {value}
      </p>
      {sub && <p className="font-mono text-[0.7rem] text-ink-faint mt-1.5 mb-0">{sub}</p>}
    </div>
  )
}



