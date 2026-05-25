import { useEffect, useState } from 'react'
import type { Verdict } from '../types'

interface Props {
  verdict: Verdict
}

function scoreClass(score: number): string {
  if (score >= 7) return 'good'
  if (score >= 4) return 'ok'
  return 'bad'
}

export default function VerdictCard({ verdict }: Props) {
  const [displayScore, setDisplayScore] = useState(0)

  useEffect(() => {
    const target = verdict.score
    const duration = 1100
    const startTime = performance.now()

    const tick = (now: number) => {
      const t = Math.min((now - startTime) / duration, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      setDisplayScore(Math.round(eased * target * 10) / 10)
      if (t < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [verdict.score])

  const cls = scoreClass(verdict.score)

  return (
    <div className="verdict">
      <div className="verdict-head">
        <h2>
          <span className="judge-icon">⚖</span>
          The Judge's Verdict
        </h2>
        <div className="score-wrap">
          <div className={`score ${cls}`}>
            {displayScore.toFixed(displayScore % 1 === 0 ? 0 : 1)}<span style={{ fontSize: '0.4em', opacity: 0.6 }}>/10</span>
          </div>
          <span className="score-label">Code Quality</span>
        </div>
      </div>

      <div className="winner-line">
        Winner:
        <span className={`winner-badge ${verdict.winner}`}>{verdict.winner}</span>
        <span className="reason">— {verdict.winner_reasoning}</span>
      </div>

      <div className="verdict-summary">{verdict.summary}</div>

      <div className="verdict-grid">
        {verdict.critic_wins.length > 0 && (
          <div className="verdict-box critic">
            <h4>Critic was right about</h4>
            <ul>{verdict.critic_wins.map((w, i) => <li key={i}>{w}</li>)}</ul>
          </div>
        )}
        {verdict.advocate_wins.length > 0 && (
          <div className="verdict-box advocate">
            <h4>Advocate was right about</h4>
            <ul>{verdict.advocate_wins.map((w, i) => <li key={i}>{w}</li>)}</ul>
          </div>
        )}
        {verdict.strengths.length > 0 && (
          <div className="verdict-box strengths" style={{ gridColumn: verdict.critic_wins.length > 0 && verdict.advocate_wins.length > 0 ? '1 / -1' : undefined }}>
            <h4>Strengths</h4>
            <ul>{verdict.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
          </div>
        )}
      </div>

      {verdict.action_items.length > 0 && (
        <div className="action-items">
          <h4>Action Items</h4>
          {verdict.action_items.map((ai, i) => (
            <div key={i} className="action-item">
              <span className={`sev ${ai.priority}`}>{ai.priority}</span>
              <span className="lines">
                {ai.affected_lines.length ? `L${ai.affected_lines.join(', ')}` : '—'}
              </span>
              <span style={{ color: 'var(--text-2)' }}>{ai.description}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
