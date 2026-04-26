import { useState } from 'react'
import type { HomeownerRecord } from '../lib/types'
import { getState, setState, cardKey } from '../lib/storage'
import { fmtName, fmtAddr, ETH_COLOR } from '../lib/format'

interface Props {
  records: HomeownerRecord[]
  version: number  // bump to re-render
}

export default function FollowUp({ records, version: _ }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const interested = records.filter(r => getState(r).interested)

  if (!interested.length) return null

  return (
    <div style={{ display: 'block', margin: '0 12px 4px', background: '#fff8ee', border: '1px solid #f5d78e', borderRadius: 12, overflow: 'hidden' }}>
      <div
        onClick={() => setCollapsed(c => !c)}
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px 6px', fontSize: '.82em', fontWeight: 700, color: '#b7791f', cursor: 'pointer' }}
      >
        <span>📌 Following Up <span style={{ fontWeight: 400, color: '#c4933f', fontSize: '.9em' }}>({interested.length})</span></span>
        <span style={{ fontSize: '.8em', color: '#c4933f', transition: 'transform .25s', transform: collapsed ? 'rotate(180deg)' : 'none' }}>▲</span>
      </div>
      {!collapsed && (
        <div style={{ padding: '0 8px 8px' }}>
          {interested.map(r => <FollowUpCard key={cardKey(r)} r={r} />)}
        </div>
      )}
    </div>
  )
}

function FollowUpCard({ r }: { r: HomeownerRecord }) {
  const [open, setOpen] = useState(false)
  const [note, setNote] = useState(getState(r).note ?? '')
  const [saved, setSaved] = useState(false)

  const eth   = r.ESTIMATED_ETHNICITY || 'Unknown'
  const color = ETH_COLOR[eth] ?? '#95a5a6'
  const nav   = r.LAT && r.LON ? `https://maps.google.com/?q=${parseFloat(r.LAT)},${parseFloat(r.LON)}` : ''

  function saveNote(val: string) {
    setNote(val)
    setState(r, { note: val })
    setSaved(true)
    setTimeout(() => setSaved(false), 1500)
  }

  function remove() {
    setState(r, { interested: false })
    // Force re-render of parent by reloading page state — simplest approach
    window.location.reload()
  }

  return (
    <div style={{ background: 'white', borderRadius: 12, marginBottom: 6, overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,.08)', borderLeft: `4px solid ${color}` }}>
      <div onClick={() => setOpen(o => !o)} style={{ display: 'flex', alignItems: 'center', padding: '13px 14px', cursor: 'pointer', gap: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '.95em', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{fmtName(r.Owner1)}</div>
          <div style={{ fontSize: '.78em', color: '#888', marginTop: 3, display: 'flex', gap: 8 }}>
            <span>{r.SOURCE}</span><span style={{ color: '#aaa' }}>·</span><span>{r.Sale1D}</span>
          </div>
        </div>
        <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 20, fontSize: '.72em', fontWeight: 700, color: 'white', background: color }}>{eth}</span>
        <span style={{ fontSize: '.8em', color: '#ccc', transform: open ? 'rotate(180deg)' : 'none', transition: 'transform .25s', minWidth: 16 }}>▼</span>
      </div>
      {open && (
        <div style={{ padding: '12px 14px 14px 14px', fontSize: '.84em', color: '#555', borderTop: '1px solid #f0f0f0' }}>
          <div style={{ marginBottom: 6 }}><span style={{ color: '#aaa', marginRight: 8 }}>Address</span>{fmtAddr(r.LocAddr)}, {r.SOURCE}</div>
          <textarea
            value={note}
            onChange={e => saveNote(e.target.value)}
            placeholder="Add a note..."
            style={{ width: '100%', marginTop: 8, padding: '8px 10px', border: '1px solid #e0e0e0', borderRadius: 8, fontSize: '.82em', fontFamily: 'inherit', resize: 'none', minHeight: 60 }}
          />
          {saved && <div style={{ fontSize: '.78em', color: '#aaa', marginTop: 4 }}>✓ Saved</div>}
          {nav && <a href={nav} target="_blank" rel="noopener" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 10, padding: '7px 14px', color: '#1a73e8', border: '1px solid #d0d8e8', borderRadius: 8, fontSize: '.82em', textDecoration: 'none' }}>📍 Navigate</a>}
          <div style={{ marginTop: 10 }}>
            <button onClick={remove} style={{ fontSize: '.78em', color: '#c0392b', background: 'none', border: '1px solid #eaa', borderRadius: 6, padding: '5px 10px', cursor: 'pointer' }}>
              ✕ Remove from Following Up
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
