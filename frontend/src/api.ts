import type { ReviewDetail, ReviewMode, ReviewSummary, SseEvent } from './types'

export async function* streamReview(params: {
  code: string
  language: string | null
  mode: ReviewMode
  max_rounds?: number
  run_fixer?: boolean
  signal?: AbortSignal
}): AsyncIterable<SseEvent> {
  const res = await fetch('/api/reviews/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      code: params.code,
      language: params.language,
      mode: params.mode,
      max_rounds: params.max_rounds ?? null,
      run_fixer: params.run_fixer ?? true,
    }),
    signal: params.signal,
  })
  if (!res.ok || !res.body) {
    throw new Error(`Stream request failed: ${res.status} ${res.statusText}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE frames are separated by a blank line.
    let idx
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      const line = frame.split('\n').find((l) => l.startsWith('data:'))
      if (!line) continue
      const payload = line.slice(5).trim()
      if (!payload) continue
      try {
        yield JSON.parse(payload) as SseEvent
      } catch (e) {
        console.error('Bad SSE payload:', payload, e)
      }
    }
  }
}

export async function listReviews(): Promise<ReviewSummary[]> {
  const res = await fetch('/api/reviews')
  if (!res.ok) throw new Error(`List failed: ${res.status}`)
  return res.json()
}

export async function fetchReview(id: string): Promise<ReviewDetail> {
  const res = await fetch(`/api/reviews/${id}`)
  if (!res.ok) throw new Error(`Fetch failed: ${res.status}`)
  return res.json()
}
