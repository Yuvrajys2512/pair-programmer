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
  return (
    <div className="verdict">
      <div className="verdict-head">
        <h2>The Judge's Verdict</h2>
        <div className={`score ${scoreClass(verdict.score)}`}>{verdict.score}/10</div>
      </div>

      <div className="winner-line">
        Winner: <span className={`agent ${verdict.winner}`}>{verdict.winner}</span> — {verdict.winner_reasoning}
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
          <div className="verdict-box strengths">
            <h4>Strengths</h4>
            <ul>{verdict.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
          </div>
        )}
      </div>

      {verdict.action_items.length > 0 && (
        <div className="action-items">
          <h4>Action items</h4>
          {verdict.action_items.map((ai, i) => (
            <div key={i} className="action-item">
              <span className={`sev ${ai.priority}`}>{ai.priority}</span>
              <span className="lines">
                {ai.affected_lines.length ? `L${ai.affected_lines.join(', ')}` : '—'}
              </span>
              <span>{ai.description}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
