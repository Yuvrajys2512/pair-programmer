import { useEffect, useState } from 'react'
import { listReviews } from '../api'
import type { ReviewSummary } from '../types'

interface Props {
  onClose: () => void
  onSelect: (id: string) => void
}

function relTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export default function HistoryView({ onClose, onSelect }: Props) {
  const [reviews, setReviews] = useState<ReviewSummary[] | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    listReviews().then(setReviews).catch((e) => setErr(String(e)))
  }, [])

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>Review History</h2>
          <button className="btn-ghost" onClick={onClose}>✕ Close</button>
        </div>

        {err && <div className="error-banner">{err}</div>}

        {reviews === null && !err && (
          <div className="empty" style={{ flex: 'none', padding: '32px 0' }}>
            <p>Loading…</p>
          </div>
        )}

        {reviews !== null && reviews.length === 0 && (
          <div className="empty" style={{ flex: 'none', padding: '32px 0' }}>
            <div className="empty-graphic">📋</div>
            <h3>No reviews yet</h3>
            <p>Run a review and it'll show up here.</p>
          </div>
        )}

        {reviews !== null && reviews.length > 0 && (
          <div className="history-list">
            {reviews.map((r) => (
              <div key={r.id} className="history-row" onClick={() => onSelect(r.id)}>
                <span className={`status-badge ${r.status}`}>{r.status}</span>
                <span className="lang-mode">
                  {r.language || '?'} · {r.mode}
                  {r.persona && (
                    <> · <span style={{ color: 'var(--accent-bright)' }}>{r.persona}</span></>
                  )}
                </span>
                <span className="preview">{r.code_preview || '(empty)'}</span>
                <span className="score-pill">
                  {r.score !== null ? `${r.score}/10` : '—'}
                </span>
                <span className="when">{relTime(r.created_at)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
