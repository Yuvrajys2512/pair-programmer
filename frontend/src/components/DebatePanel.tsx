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

const AVATARS: Record<string, string> = { CRITIC: 'C', ADVOCATE: 'A' }

export default function DebatePanel({ turns }: Props) {
  if (turns.length === 0) {
    return (
      <div className="empty">
        <div className="empty-graphic">⚔</div>
        <h3>Ready to review</h3>
        <p>
          Paste your code on the left, pick a mode, and hit{' '}
          <strong style={{ color: 'var(--accent-bright)' }}>Run Review</strong>.
        </p>
        <div className="empty-agents">
          <span className="empty-critic">Critic</span>
          <span className="vs">vs</span>
          <span className="empty-advocate">Advocate</span>
        </div>
      </div>
    )
  }

  return (
    <>
      {turns.map((t, i) => (
        <div key={i} className={`turn ${t.agent.toLowerCase()}`}>
          <div className="turn-header">
            <span className="turn-avatar">{AVATARS[t.agent]}</span>
            <span className="turn-agent-name">{t.agent}</span>
            <span className="round-badge">Round {t.round}</span>
            {t.isInitial && <span className="round-badge">Opening</span>}
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
    </>
  )
}
