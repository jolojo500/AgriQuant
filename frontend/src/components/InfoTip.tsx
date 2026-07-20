import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { motion } from 'framer-motion'

const OPEN_DELAY = 120
const CLOSE_GRACE = 300

// The two geometries the portal shape morphs between.
// bottom: -24 parks the shape exactly over the 16px button (which sits 24px below the wrapper origin).
const morph = {
  ball:  { width: 16,  height: 16,     borderRadius: 8, bottom: -24 },
  panel: { width: 256, height: 'auto', borderRadius: 6, bottom: 0 },
} as const

export default function InfoTip({ text }: { text: string }) {
  const anchor = useRef<HTMLSpanElement>(null)
  const openT = useRef<number>(undefined)
  const closeT = useRef<number>(undefined)
  const refillT = useRef<number>(undefined)
  const [primed, setPrimed] = useState(false)
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null)
  const [closing, setClosing] = useState(false)

  useEffect(() => () => {
    clearTimeout(openT.current); clearTimeout(closeT.current); clearTimeout(refillT.current)
  }, [])

  const enter = () => {
    clearTimeout(closeT.current); clearTimeout(refillT.current)
    setClosing(false)
    setPrimed(true)
    openT.current = window.setTimeout(() => {
      const r = anchor.current?.getBoundingClientRect()
      if (r) setPos({ x: r.left + r.width / 2, y: r.top })
    }, OPEN_DELAY)
  }

  const leave = () => {
    clearTimeout(openT.current)
    closeT.current = window.setTimeout(() => setClosing(true), CLOSE_GRACE)
  }

  // Runs after every morph completes; only acts when it was the closing one
  const finishClose = () => {
    if (!closing) return
    setPos(null)
    setClosing(false)
    refillT.current = window.setTimeout(() => setPrimed(false), 40)
  }

  return (
    <>
      {/* Resting ball + its socket. The flying shape lives in the portal. */}
      <span
        ref={anchor}
        onMouseEnter={enter}
        onMouseLeave={leave}
        className="relative inline-flex w-4 h-4 shrink-0 cursor-help"
      >
        {pos ? (
          <span className="absolute inset-0 rounded-full bg-black/40" />
        ) : (
          <span
            className={`flex items-center justify-center w-4 h-4 rounded-full border font-mono text-[0.65rem] font-bold leading-none select-none transition-colors duration-150 ${
              primed ? 'bg-surface border-accent text-transparent' : 'bg-accent border-accent text-canvas'
            }`}
          >
            ?
          </span>
        )}
      </span>

      {pos && createPortal(
        <span className="fixed z-[200] block w-0 h-0" style={{ left: pos.x, top: pos.y - 8 }}>
          <motion.span
            initial={morph.ball}
            animate={closing ? morph.ball : morph.panel}
            transition={{ duration: 0.25, ease: [0.3, 0.9, 0.4, 1] }}
            onAnimationComplete={finishClose}
            onMouseEnter={() => { clearTimeout(closeT.current); setClosing(false) }}
            onMouseLeave={leave}
            style={{ x: '-50%' }}
            className="absolute left-0 overflow-hidden bg-surface border border-accent/60 shadow-[0_8px_24px_rgba(0,0,0,0.55)] pointer-events-auto"
          >
            {/* Fixed-width inner so text doesn't reflow while the outer box grows over it */}
            <motion.span
              animate={{ opacity: closing ? 0 : 1 }}
              transition={closing ? { duration: 0.06 } : { duration: 0.15, delay: 0.15 }}
              className="block w-64 px-3 py-2 font-mono text-[0.65rem] leading-relaxed text-ink-muted text-left"
            >
              {text}
            </motion.span>
          </motion.span>
        </span>,
        document.body,
      )}
    </>
  )
}
