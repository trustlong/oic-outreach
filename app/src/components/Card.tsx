import { useState } from 'react'
import type { ScoredRecord } from '../lib/types'
import { getState, setState } from '../lib/storage'
import { fmtName, fmtOrigin, fmtAddr, ETH_COLOR } from '../lib/format'

interface Props {
  item: ScoredRecord
  rank: number
  onFollowUpChange: () => void
}

export default function Card({ item, rank, onFollowUpChange }: Props) {
  const { r, score, dist } = item
  const initial = getState(r)
  const [open, setOpen]           = useState(false)
  const [visited, setVisited]     = useState(initial.visited ?? false)
  const [interested, setInterested] = useState(initial.interested ?? false)
  const [note, setNote]           = useState(initial.note ?? '')
  const [noteSaved, setNoteSaved] = useState(false)

  const eth   = r.ESTIMATED_ETHNICITY || 'Unknown'
  const color = ETH_COLOR[eth] ?? '#95a5a6'
  const nav   = r.LAT && r.LON ? `https://maps.google.com/?q=${parseFloat(r.LAT)},${parseFloat(r.LON)}` : ''

  function toggleVisited() {
    const next = !visited
    setVisited(next)
    setState(r, { visited: next })
  }

  function toggleInterested() {
    const next = !interested
    setInterested(next)
    setState(r, { interested: next })
    onFollowUpChange()
  }

  function saveNote(val: string) {
    setNote(val)
    setState(r, { note: val })
    setNoteSaved(true)
    setTimeout(() => setNoteSaved(false), 1500)
  }

  return (
    <div style={{
      background: 'white', borderRadius: 12, marginBottom: 10,
      overflow: 'hidden', boxShadow: open ? '0 4px 16px rgba(0,0,0,.12)' : '0 1px 4px rgba(0,0,0,.08)',
      borderLeft: `4px solid ${color}`, opacity: !open && visited ? 0.45 : 1,
      transition: 'box-shadow .2s',
    }}>
      {/* Header */}
      <div onClick={() => setOpen(o => !o)} style={{ display: 'flex', alignItems: 'center', padding: '13px 14px', cursor: 'pointer', gap: 12 }}>
        <span style={{ fontSize: '1.1em', fontWeight: 800, color: '#bbb', minWidth: 22, textAlign: 'center' }}>{rank}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '.95em', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: '#1a1a2e' }}>
            {fmtName(r.Owner1)}
          </div>
          <div style={{ fontSize: '.78em', color: '#888', marginTop: 3, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <span>{dist.toFixed(1)} mi · {r.SOURCE}</span>
            <span style={{ color: '#aaa' }}>·</span>
            <span>{r.Sale1D}</span>
          </div>
        </div>
        <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 20, fontSize: '.72em', fontWeight: 700, color: 'white', background: color, whiteSpace: 'nowrap' }}>
          {eth}
        </span>
        <span style={{ fontSize: '.8em', color: '#ccc', transition: 'transform .25s', transform: open ? 'rotate(180deg)' : 'none', minWidth: 16 }}>▼</span>
      </div>

      {/* Detail */}
      {open && (
        <div style={{ padding: '12px 14px 14px 48px', fontSize: '.84em', color: '#555', borderTop: '1px solid #f0f0f0' }}>
          <DetailRow label="Address" value={`${fmtAddr(r.LocAddr)}, ${r.SOURCE}`} />
          <DetailRow label="Origin"  value={fmtOrigin(r.MOVE_ORIGIN)} />
          <DetailRow label="Household" value={`Est. ${r.EST_HOUSEHOLD_SIZE || '?'} people`} />

          {/* Score dots */}
          <div style={{ display: 'flex', gap: 4, marginTop: 10, paddingTop: 10, borderTop: '1px solid #f0f0f0' }}>
            {Array.from({ length: 7 }, (_, j) => (
              <div key={j} style={{ width: 10, height: 10, borderRadius: '50%', background: j < score ? '#1a73e8' : '#e0e0e0' }} />
            ))}
            <span style={{ fontSize: '.75em', color: '#aaa', marginLeft: 6, alignSelf: 'center' }}>Score {score}/7</span>
          </div>

          {nav && (
            <a href={nav} target="_blank" rel="noopener" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 12, padding: '7px 14px', color: '#1a73e8', border: '1px solid #d0d8e8', borderRadius: 8, fontSize: '.82em', fontWeight: 500, textDecoration: 'none' }}>
              📍 Navigate to address
            </a>
          )}

          {/* Actions */}
          <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
            <ActionBtn active={visited} activeClass="visited" onClick={toggleVisited}>
              {visited ? '✅ Visited' : '❓ Visited'}
            </ActionBtn>
            <ActionBtn active={interested} activeClass="interested" onClick={toggleInterested}>
              {interested ? '📌 Following Up' : '❓ Follow Up?'}
            </ActionBtn>
          </div>

          <textarea
            value={note}
            onChange={e => saveNote(e.target.value)}
            placeholder="Add a note..."
            style={{ width: '100%', marginTop: 10, padding: '8px 10px', border: '1px solid #e0e0e0', borderRadius: 8, fontSize: '.82em', fontFamily: 'inherit', color: '#333', resize: 'none', minHeight: 60 }}
          />
          {noteSaved && <div style={{ fontSize: '.78em', color: '#aaa', marginTop: 6 }}>✓ Saved</div>}
        </div>
      )}
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', gap: 8, marginBottom: 6, alignItems: 'flex-start' }}>
      <span style={{ color: '#aaa', minWidth: 64, fontSize: '.88em', paddingTop: 1 }}>{label}</span>
      <span style={{ color: '#333', fontWeight: 500 }}>{value}</span>
    </div>
  )
}

function ActionBtn({ active, activeClass, onClick, children }: { active: boolean; activeClass: string; onClick: () => void; children: React.ReactNode }) {
  const styles: Record<string, React.CSSProperties> = {
    visited:    { background: '#eafaf1', borderColor: '#27ae60', color: '#27ae60' },
    interested: { background: '#fef9e7', borderColor: '#f39c12', color: '#e67e22' },
  }
  return (
    <button
      onClick={e => { e.stopPropagation(); onClick() }}
      style={{
        flex: 1, minWidth: 80, padding: '8px 6px', borderRadius: 8,
        fontSize: '.78em', fontWeight: 600, border: '1px solid #e0e0e0',
        background: 'white', color: '#555', cursor: 'pointer', textAlign: 'center',
        transition: 'all .15s',
        ...(active ? styles[activeClass] : {}),
      }}
    >
      {children}
    </button>
  )
}
