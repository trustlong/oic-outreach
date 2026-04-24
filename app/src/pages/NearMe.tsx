import { useEffect, useState, useCallback, useRef } from 'react'
import type { HomeownerRecord, ScoredRecord } from '../lib/types'
import { loadCSV } from '../lib/csv'
import { lastMonthRange, lastYearRange } from '../lib/periods'
import { scoreGPS, top10 } from '../lib/scoring'
import Toggle from '../components/Toggle'
import SectionLabel from '../components/SectionLabel'
import CardList from '../components/CardList'
import FollowUp from '../components/FollowUp'

const TOGGLE_OPTIONS = [
  { value: 'month', label: 'Last Month' },
  { value: 'year',  label: 'Past 12 Months' },
]

export default function NearMe() {
  const [records, setRecords]     = useState<HomeownerRecord[]>([])
  const [period, setPeriod]       = useState<'month' | 'year'>('month')
  const [items, setItems]         = useState<ScoredRecord[]>([])
  const [followUpV, setFollowUpV] = useState(0)
  const [status, setStatus]       = useState('')
  const [located, setLocated]     = useState(false)
  const coords = useRef<{ lat: number; lon: number } | null>(null)

  useEffect(() => {
    if (!coords.current || !records.length) return
    const range = period === 'month' ? lastMonthRange() : lastYearRange()
    const { lat, lon } = coords.current
    setItems(top10(records, range, r => scoreGPS(r, lat, lon)))
  }, [records, period])

  async function locate() {
    setStatus('Loading data…')
    const data = records.length ? records : await loadCSV('all_homeowners_20mi.csv')
    if (!records.length) setRecords(data)
    setStatus('Requesting location…')

    navigator.geolocation.getCurrentPosition(
      pos => {
        coords.current = { lat: pos.coords.latitude, lon: pos.coords.longitude }
        setStatus(`📍 Scoring ${data.length.toLocaleString()} households…`)
        const range = period === 'month' ? lastMonthRange() : lastYearRange()
        setItems(top10(data, range, r => scoreGPS(r, coords.current!.lat, coords.current!.lon)))
        setLocated(true)
        setStatus('')
      },
      err => setStatus(`⚠️ Location unavailable: ${err.message}`),
      { enableHighAccuracy: true, timeout: 10000 }
    )
  }

  function relocate() {
    if (!coords.current || !records.length) return
    const range = period === 'month' ? lastMonthRange() : lastYearRange()
    setItems(top10(records, range, r => scoreGPS(r, coords.current!.lat, coords.current!.lon)))
  }

  function onPeriodChange(v: string) {
    setPeriod(v as 'month' | 'year')
    if (coords.current && records.length) {
      const range = v === 'month' ? lastMonthRange() : lastYearRange()
      setItems(top10(records, range, r => scoreGPS(r, coords.current!.lat, coords.current!.lon)))
    }
  }

  const range = period === 'month' ? lastMonthRange() : lastYearRange()
  const label = items.length
    ? `Top ${items.length} near you · ${range.label}`
    : `No households found nearby (${range.label}) — try switching to Past 12 Months`

  const onFollowUpChange = useCallback(() => setFollowUpV(v => v + 1), [])

  return (
    <>
      <header style={{ background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)', color: 'white', padding: '20px 16px 16px', textAlign: 'center' }}>
        <h1 style={{ fontSize: '1.2em', fontWeight: 700 }}>📍 Near Me</h1>
        <p style={{ fontSize: '.78em', opacity: .65, marginTop: 4 }}>Top 10 households closest to your current location</p>
        <a href="index.html" style={{ display: 'inline-block', marginTop: 10, fontSize: '.8em', color: 'rgba(255,255,255,.6)', textDecoration: 'none' }}>← Back to OIC Outreach</a>
      </header>

      {!located && (
        <div style={{ textAlign: 'center', padding: '24px 16px' }}>
          <button
            onClick={locate}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '14px 28px', background: '#1a73e8', color: 'white', border: 'none', borderRadius: 12, fontSize: '1em', fontWeight: 600, cursor: 'pointer' }}
          >
            📍 Find households near me
          </button>
        </div>
      )}

      {status && <div style={{ textAlign: 'center', padding: '12px 16px', fontSize: '.85em', color: '#888' }}>{status}</div>}

      {located && (
        <>
          <FollowUp records={records} version={followUpV} />
          <Toggle view={period} options={TOGGLE_OPTIONS} onChange={onPeriodChange} />
          <SectionLabel label={label} onRefresh={relocate} />
          <CardList items={items} onFollowUpChange={onFollowUpChange} />
          <div style={{ padding: '0 16px 24px', fontSize: '.74em', color: '#aaa', lineHeight: 1.7 }}>
            <p>¹ Distance shown from your current location, not OIC church.</p>
            <p>² Ethnicity estimated from US Census surname data — not verified.</p>
            <p>³ Score (max 7): Chinese=+3, other Asian=+2, Hispanic/Black=+1 · out-of-state=+2, in-state/unknown=+1 · ≤0.5mi=+3, ≤1mi=+2, ≤2mi=+1.</p>
            <p><a href="disclaimer.html" style={{ color: '#bbb' }}>Disclaimer</a></p>
          </div>
        </>
      )}
    </>
  )
}
