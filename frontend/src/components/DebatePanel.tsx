import { useEffect, useRef } from 'react'
import type { CriticReview, DebateTurn } from '../types'

interface Props {
  turns: DebateTurn[]
}

function InitialReview({ review }: { review: CriticReview }) {
  return (
    <div className="initial-review">
      <div className="initial-summary">{review.summary}</div>
      {review.items.map((it, i) => (
        <div key={i} className={`review-item ${it.severity}`}>
          <div className="review-item-head">
            <span className={`sev ${it.severity}`}>{it.severity}</span>
            <span>{it.category}</span>
            {it.line_number !== null && <span>line {it.line_number}</span>}
          </div>
          <div className="issue">{it.issue}</div>
          <div className="fix"><strong>Fix:</strong> {it.suggestion}</div>
        </div>
      ))}
    </div>
  )
}

export default function DebatePanel({ turns }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom as new chunks arrive
  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [turns])

  if (turns.length === 0) {
    return (
      <div className="empty">
        <h3>Waiting for the debate to begin…</h3>
        <p>Paste code on the left, pick a mode, hit Run.</p>
      </div>
    )
  }

  return (
    <div ref={scrollRef} className="debate-scroll">
      {turns.map((t, i) => (
        <div key={i} className={`turn ${t.agent.toLowerCase()}`}>
          <div className="turn-header">
            <span className="round-badge">Round {t.round}</span>
            <span>{t.agent}</span>
            {t.isInitial && <span className="round-badge">opening review</span>}
          </div>
          {t.isInitial && t.initialReview ? (
            <InitialReview review={t.initialReview} />
          ) : (
            <div className="turn-body">
              {t.content}
              {t.streaming && <span className="streaming-cursor" />}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
