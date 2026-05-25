import { useCallback, useRef, useState } from 'react'
import './App.css'

import { fetchReview, streamReview } from './api'
import CodeEditor from './components/CodeEditor'
import DebatePanel from './components/DebatePanel'
import DiffView from './components/DiffView'
import HistoryView from './components/HistoryView'
import ModeSelector from './components/ModeSelector'
import PersonaSelector from './components/PersonaSelector'
import VerdictCard from './components/VerdictCard'
import type {
  CriticReview, DebateTurn, FixResult, ReviewMode, Verdict,
} from './types'

const STARTER_CODE = `def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + str(user_id)
    return db.execute(query).fetchone()


def add_tag(item, tags=[]):
    tags.append(item)
    return tags


def average_score(scores):
    return sum(scores) / len(scores)


def load_config(path):
    try:
        with open(path) as f:
            return eval(f.read())
    except:
        return None
`

export default function App() {
  const [code, setCode] = useState(STARTER_CODE)
  const [language, setLanguage] = useState<string>('python')
  const [mode, setMode] = useState<ReviewMode>('standard')
  const [persona, setPersona] = useState<string | null>(null)

  const [turns, setTurns] = useState<DebateTurn[]>([])
  const [verdict, setVerdict] = useState<Verdict | null>(null)
  const [fix, setFix] = useState<FixResult | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showHistory, setShowHistory] = useState(false)

  const abortRef = useRef<AbortController | null>(null)
  const debateScrollRef = useRef<HTMLDivElement | null>(null)

  const scrollToBottom = () => {
    const el = debateScrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }

  const reset = () => {
    setTurns([])
    setVerdict(null)
    setFix(null)
    setError(null)
  }

  const run = useCallback(async () => {
    if (running) return
    reset()
    setRunning(true)
    const controller = new AbortController()
    abortRef.current = controller

    try {
      for await (const ev of streamReview({
        code, language, mode, persona, run_fixer: true, signal: controller.signal,
      })) {
        switch (ev.type) {
          case 'turn_start':
            setTurns((prev) => [
              ...prev,
              { agent: ev.agent, round: ev.round, isInitial: ev.is_initial, content: '', streaming: true },
            ])
            setTimeout(scrollToBottom, 50)
            break
          case 'chunk':
            setTurns((prev) => {
              if (prev.length === 0) return prev
              const next = [...prev]
              const last = next[next.length - 1]
              next[next.length - 1] = { ...last, content: last.content + ev.text }
              return next
            })
            scrollToBottom()
            break
          case 'turn_complete':
            setTurns((prev) => {
              if (prev.length === 0) return prev
              const next = [...prev]
              const last = next[next.length - 1]
              let initialReview: CriticReview | undefined = undefined
              if (ev.is_initial) {
                try { initialReview = JSON.parse(ev.content) as CriticReview } catch { /* ignore */ }
              }
              next[next.length - 1] = { ...last, content: ev.content, streaming: false, initialReview }
              return next
            })
            break
          case 'verdict':
            setVerdict(ev.verdict)
            setTimeout(scrollToBottom, 50)
            break
          case 'fix':
            setFix({
              original_code: ev.original_code,
              fixed_code: ev.fixed_code,
              changes_made: ev.changes_made,
              changelog: ev.changelog,
            })
            setTimeout(scrollToBottom, 50)
            break
          case 'error':
            setError(ev.message)
            break
          case 'complete':
            break
        }
      }
    } catch (e: unknown) {
      if ((e as Error).name !== 'AbortError') {
        setError(String((e as Error).message || e))
      }
    } finally {
      setRunning(false)
      abortRef.current = null
    }
  }, [code, language, mode, persona, running])

  const stop = () => abortRef.current?.abort()

  const loadHistory = async (id: string) => {
    setShowHistory(false)
    const detail = await fetchReview(id)
    setCode(detail.code)
    if (detail.language) setLanguage(detail.language)
    if (detail.mode === 'roast' || detail.mode === 'standard' || detail.mode === 'deep') setMode(detail.mode)
    setPersona(detail.persona)

    const replayed: DebateTurn[] = detail.messages.map((m) => {
      let initialReview: CriticReview | undefined = undefined
      if (m.is_initial_review) {
        try { initialReview = JSON.parse(m.content) as CriticReview } catch { /* ignore */ }
      }
      return {
        agent: m.agent as 'CRITIC' | 'ADVOCATE',
        round: m.round_number,
        isInitial: m.is_initial_review,
        content: m.content,
        streaming: false,
        initialReview,
      }
    })
    setTurns(replayed)
    setVerdict(detail.verdict)
    setFix(detail.fix ? { ...detail.fix, original_code: detail.fix.original_code ?? detail.code } : null)
    setError(detail.error)
  }

  return (
    <>
      {running && <div className="progress-bar" />}

      <div className="app">
        {/* ── Topbar ── */}
        <div className="topbar">
          <div className="brand">
            <div className="brand-icon">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M5 3L2 8L5 13" stroke="#a78bfa" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M11 3L14 8L11 13" stroke="#60a5fa" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M9.5 2L6.5 14" stroke="#818cf8" strokeWidth="1.3" strokeLinecap="round"/>
              </svg>
            </div>
            <span className="brand-text">Pair Programmer</span>
          </div>

          <div className="topbar-actions">
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              disabled={running}
              className="topbar-select"
            >
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
              <option value="go">Go</option>
              <option value="rust">Rust</option>
              <option value="java">Java</option>
              <option value="cpp">C++</option>
              <option value="ruby">Ruby</option>
            </select>

            <ModeSelector mode={mode} onChange={setMode} disabled={running} />
            <PersonaSelector value={persona} onChange={setPersona} disabled={running} />

            <button className="btn-ghost" onClick={() => setShowHistory(true)}>
              History
            </button>

            {running ? (
              <button className="btn stop" onClick={stop}>■ Stop</button>
            ) : (
              <button className="btn" onClick={run} disabled={!code.trim()}>
                ▶ Run Review
              </button>
            )}
          </div>
        </div>

        {/* ── Split panels ── */}
        <div className="split">
          {/* Left — code editor */}
          <div className="left">
            <div className="section-header">
              <span className="hd-label">
                <span className="hd-icon">{'</>'}</span>
                Code Editor
              </span>
              <span style={{ color: 'var(--text-3)', fontSize: 11 }}>
                {code.split('\n').length} lines
              </span>
            </div>
            <div className="editor-wrap">
              <CodeEditor code={code} onChange={setCode} language={language} readOnly={running} />
            </div>
          </div>

          {/* Right — debate */}
          <div className="right">
            <div className="section-header">
              <span className="hd-label">
                <span className="hd-icon">⚔</span>
                Debate Arena
              </span>
              {running && (
                <span className="live-indicator">
                  <span className="live-dot">
                    <span className="live-dot-ring" />
                    <span className="live-dot-core" />
                  </span>
                  LIVE
                </span>
              )}
            </div>

            <div className="debate-scroll" ref={debateScrollRef}>
              {error && <div className="error-banner">{error}</div>}
              <DebatePanel turns={turns} />
              {verdict && <VerdictCard verdict={verdict} />}
              {fix && <DiffView fix={fix} />}
            </div>
          </div>
        </div>
      </div>

      {showHistory && (
        <HistoryView onClose={() => setShowHistory(false)} onSelect={loadHistory} />
      )}
    </>
  )
}
