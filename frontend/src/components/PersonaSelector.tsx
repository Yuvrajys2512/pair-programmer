import { useEffect, useState } from 'react'
import { listPersonas } from '../api'
import type { Persona } from '../types'

interface Props {
  value: string | null
  onChange: (slug: string | null) => void
  disabled?: boolean
}

export default function PersonaSelector({ value, onChange, disabled }: Props) {
  const [personas, setPersonas] = useState<Persona[] | null>(null)

  useEffect(() => {
    listPersonas().then(setPersonas).catch((e) => {
      console.error('Failed to load personas', e)
      setPersonas([])
    })
  }, [])

  const selected = personas?.find((p) => p.slug === value)
  return (
    <select
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value || null)}
      disabled={disabled || personas === null}
      className="btn-ghost"
      style={{ background: 'var(--panel-2)', minWidth: 160 }}
      title={selected ? selected.description : 'Persona overlay (optional)'}
    >
      <option value="">Persona: default</option>
      {personas?.map((p) => (
        <option key={p.slug} value={p.slug}>
          {p.name}
        </option>
      ))}
    </select>
  )
}
