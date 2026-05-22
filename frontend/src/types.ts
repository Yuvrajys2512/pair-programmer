export type AgentName = 'CRITIC' | 'ADVOCATE'
export type ReviewMode = 'roast' | 'standard' | 'deep'
export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'

export interface ReviewItem {
  category: string
  severity: Severity
  line_number: number | null
  issue: string
  suggestion: string
}

export interface CriticReview {
  summary: string
  items: ReviewItem[]
}

export interface ActionItem {
  priority: Severity
  description: string
  affected_lines: number[]
}

export interface Verdict {
  summary: string
  score: number
  critic_wins: string[]
  advocate_wins: string[]
  strengths: string[]
  action_items: ActionItem[]
  winner: AgentName
  winner_reasoning: string
}

export interface ChangeEntry {
  action_item_index: number
  description: string
}

export interface FixResult {
  original_code: string
  fixed_code: string
  changes_made: boolean
  changelog: ChangeEntry[]
}

export interface DebateTurn {
  agent: AgentName
  round: number
  isInitial: boolean
  content: string
  initialReview?: CriticReview
  streaming: boolean
}

export interface ReviewSummary {
  id: string
  language: string | null
  mode: string
  rounds: number
  status: string
  score: number | null
  winner: string | null
  created_at: string
  completed_at: string | null
  code_preview: string
}

export interface ReviewDetail extends ReviewSummary {
  code: string
  messages: {
    agent: string
    round_number: number
    content: string
    is_initial_review: boolean
  }[]
  verdict: Verdict | null
  fix: FixResult | null
  error: string | null
}

export type SseEvent =
  | { type: 'start'; review_id: string; rounds: number; mode: string }
  | { type: 'turn_start'; agent: AgentName; round: number; is_initial: boolean }
  | { type: 'chunk'; text: string }
  | { type: 'turn_complete'; agent: AgentName; round: number; content: string; is_initial: boolean }
  | { type: 'verdict'; verdict: Verdict }
  | { type: 'fix'; original_code: string; fixed_code: string; changes_made: boolean; changelog: ChangeEntry[] }
  | { type: 'complete'; review_id: string }
  | { type: 'error'; message: string }
