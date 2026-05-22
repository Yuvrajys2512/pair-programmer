import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued'
import type { FixResult } from '../types'

interface Props {
  fix: FixResult
}

export default function DiffView({ fix }: Props) {
  if (!fix.changes_made) {
    return (
      <div className="diff-wrap">
        <h3>The Fixer</h3>
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
          No changes needed — the code already addresses the action items.
        </p>
      </div>
    )
  }

  return (
    <div className="diff-wrap">
      <h3>The Fixer — proposed changes</h3>
      <ReactDiffViewer
        oldValue={fix.original_code}
        newValue={fix.fixed_code}
        splitView={true}
        useDarkTheme={true}
        compareMethod={DiffMethod.WORDS}
        styles={{
          variables: {
            dark: {
              codeFoldGutterBackground: '#0b0d13',
              codeFoldBackground: '#161922',
            },
          },
          contentText: { fontFamily: "'JetBrains Mono', Consolas, monospace", fontSize: 12 },
        }}
      />
      {fix.changelog.length > 0 && (
        <div className="changelog">
          <strong style={{ color: 'var(--text-dim)' }}>Changelog</strong>
          {fix.changelog.map((c, i) => (
            <div key={i} className="changelog-row">
              <span className="idx">#{c.action_item_index}</span>
              <span>{c.description}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
