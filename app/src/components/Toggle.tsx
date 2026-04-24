interface Props {
  view: string
  options: { value: string; label: string }[]
  onChange: (value: string) => void
}

export default function Toggle({ view, options, onChange }: Props) {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '16px', gap: 0 }}>
      {options.map((opt, i) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          style={{
            flex: 1,
            maxWidth: 180,
            padding: '10px 0',
            fontSize: '.88em',
            fontWeight: 600,
            border: '2px solid #1a73e8',
            borderRight: i < options.length - 1 ? 'none' : undefined,
            borderRadius: i === 0 ? '8px 0 0 8px' : i === options.length - 1 ? '0 8px 8px 0' : 0,
            background: view === opt.value ? '#1a73e8' : 'white',
            color: view === opt.value ? 'white' : '#1a73e8',
            cursor: 'pointer',
            transition: 'all .2s',
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
