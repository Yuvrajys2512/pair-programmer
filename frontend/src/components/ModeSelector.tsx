import type { ReviewMode } from '../types'

interface Props {
  mode: ReviewMode
  onChange: (mode: ReviewMode) => void
  disabled?: boolean
}

const MODES: { value: ReviewMode; label: string; icon: string; rounds: number }[] = [
  { value: 'roast',    label: 'Roast',    icon: '🔥', rounds: 2 },
  { value: 'standard', label: 'Standard', icon: '⚡', rounds: 3 },
  { value: 'deep',     label: 'Deep',     icon: '🔬', rounds: 5 },
]

export default function ModeSelector({ mode, onChange, disabled }: Props) {
  return (
    <div className="mode-selector">
      {MODES.map((m) => (
        <button
          key={m.value}
          className={mode === m.value ? 'active' : ''}
          onClick={() => onChange(m.value)}
          disabled={disabled}
          title={`${m.rounds} rounds`}
        >
          {m.icon} {m.label}
        </button>
      ))}
    </div>
  )
}
