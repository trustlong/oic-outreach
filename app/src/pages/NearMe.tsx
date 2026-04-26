import { useEffect, useState, useCallback, useRef } from 'react'
import type { HomeownerRecord, ScoredRecord } from '../lib/types'
import { loadCSV } from '../lib/csv'
import { getRange } from '../lib/periods'
import { scoreGPS, top10, matchesEthnicity } from '../lib/scoring'
import { ethLabel } from '../lib/format'
import Filters, { type Period, type Ethnicity } from '../components/Filters'
import SectionLabel from '../components/SectionLabel'
import CardList from '../components/CardList'
import FollowUp from '../components/FollowUp'
import MapView from '../components/MapView'

export default function NearMe() {
  const [records, setRecords]     = useState<HomeownerRecord[]>([])
  const [period, setPeriod]       = useState<Period>('month')
  const [ethnicity, setEthnicity] = useState<Ethnicity>('all')
  const [items, setItems]         = useState<ScoredRecord[]>([])
  const [followUpV, setFollowUpV] = useState(0)
  const [status, setStatus]       = useState('')
  const [located, setLocated]     = useState(false)
  const coords = useRef<{ lat: number; lon: number } | null>(null)

  function rank(data: HomeownerRecord[], p: Period, e: Ethnicity, lat: number, lon: number) {
    const filtered = e === 'all' ? data : data.filter(r => matchesEthnicity(r, e))
    return top10(filtered, getRange(p), r => scoreGPS(r, lat, lon))
  }

  useEffect(() => {
    if (!coords.current || !records.length) return
    const { lat, lon } = coords.current
    setItems(rank(records, period, ethnicity, lat, lon))
  }, [records, period, ethnicity])

  async function locate() {
    setStatus('Loading data…')
    const data = records.length ? records : await loadCSV('all_homeowners_20mi.csv')
    if (!records.length) setRecords(data)
    setStatus('Requesting location…')

    navigator.geolocation.getCurrentPosition(
      pos => {
        coords.current = { lat: pos.coords.latitude, lon: pos.coords.longitude }
        setStatus(`📍 Scoring ${data.length.toLocaleString()} households…`)
        setItems(rank(data, period, ethnicity, coords.current!.lat, coords.current!.lon))
        setLocated(true)
        setStatus('')
      },
      err => setStatus(`⚠️ Location unavailable: ${err.message}`),
      { enableHighAccuracy: true, timeout: 10000 }
    )
  }

  function relocate() {
    if (!coords.current || !records.length) return
    setItems(rank(records, period, ethnicity, coords.current.lat, coords.current.lon))
  }

  const range = getRange(period)
  const eth = ethLabel(ethnicity)
  const label = items.length
    ? `Top ${items.length} ${eth}within 3 mi · ${range.label}`
    : `No ${eth}households within 3 mi (${range.label}) — try a longer date range`

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
          <Filters period={period} onPeriodChange={setPeriod} ethnicity={ethnicity} onEthnicityChange={setEthnicity} />
          <SectionLabel label={label} onRefresh={relocate} />
          <MapView
            items={items}
            center={coords.current ? { lat: coords.current.lat, lon: coords.current.lon } : undefined}
            centerLabel="You are here"
          />
          <CardList items={items} onFollowUpChange={onFollowUpChange} />
          <div style={{ padding: '0 16px 24px', fontSize: '.74em', color: '#aaa', lineHeight: 1.7 }}>
            <p>¹ Distance shown from your current location, not OIC church.</p>
            <p>² Ethnicity estimated from US Census surname data — not verified.</p>
            <p>³ Score (max 5): Chinese=+2, all others=+1 (OIC welcomes everyone) · ≤0.5mi=+3, ≤1mi=+2, ≤2mi=+1.</p>
            <p><a href="disclaimer.html" style={{ color: '#bbb' }}>Disclaimer</a></p>
          </div>
        </>
      )}
    </>
  )
}
