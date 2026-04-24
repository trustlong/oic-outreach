interface Props {
  label: string
  onRefresh?: () => void
}

export default function SectionLabel({ label, onRefresh }: Props) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '0 16px 12px' }}>
      <p style={{ textAlign: 'center', fontSize: '.78em', color: '#888' }}>{label}</p>
      {onRefresh && (
        <button
          onClick={onRefresh}
          title="Re-sort from current location"
          style={{ background: 'none', border: 'none', color: '#bbb', fontSize: '.9em', cursor: 'pointer', padding: '2px 4px', lineHeight: 1 }}
        >
          ↺
        </button>
      )}
    </div>
  )
}
