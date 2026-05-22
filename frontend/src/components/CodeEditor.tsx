import Editor from '@monaco-editor/react'

interface Props {
  code: string
  onChange: (next: string) => void
  language: string
  readOnly?: boolean
}

export default function CodeEditor({ code, onChange, language, readOnly }: Props) {
  return (
    <Editor
      height="100%"
      language={language}
      theme="vs-dark"
      value={code}
      onChange={(v) => onChange(v ?? '')}
      options={{
        readOnly: readOnly ?? false,
        fontSize: 13,
        fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        smoothScrolling: true,
        renderLineHighlight: 'gutter',
        padding: { top: 12, bottom: 12 },
      }}
    />
  )
}
