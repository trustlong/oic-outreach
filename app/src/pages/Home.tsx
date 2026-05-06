import { useEffect, useState, useCallback } from 'react'
import type { HomeownerRecord, ScoredRecord } from '../lib/types'
import { loadCSV } from '../lib/csv'
import { getRange } from '../lib/periods'
import { scoreOIC, top10, matchesEthnicity } from '../lib/scoring'
import { ethLabel } from '../lib/format'
import { migrateVisitedTimestamps } from '../lib/storage'
import { buildWeeklyReport } from '../lib/report'
import Filters, { type Period, type Ethnicity } from '../components/Filters'
import SectionLabel from '../components/SectionLabel'
import CardList from '../components/CardList'
import FollowUp from '../components/FollowUp'
import MapView from '../components/MapView'

export default function Home() {
  const [records, setRecords] = useState<HomeownerRecord[]>([])
  const [view, setView]       = useState<Period>('month')
  const [ethnicity, setEthnicity] = useState<Ethnicity>('all')
  const [items, setItems]     = useState<ScoredRecord[]>([])
  const [followUpV, setFollowUpV] = useState(0)
  const [loading, setLoading] = useState(true)
  const [reportStatus, setReportStatus] = useState('')

  useEffect(() => {
    migrateVisitedTimestamps()
    loadCSV('all_homeowners_20mi.csv').then(data => {
      setRecords(data)
      setLoading(false)
    })
  }, [])

  async function copyWeeklyReport() {
    const text = buildWeeklyReport(records)
    try {
      await navigator.clipboard.writeText(text)
      setReportStatus('✓ Copied to clipboard')
    } catch {
      setReportStatus('⚠️ Copy failed — see console')
      console.log(text)
    }
    setTimeout(() => setReportStatus(''), 2000)
  }

  useEffect(() => {
    if (!records.length) return
    const filtered = ethnicity === 'all' ? records : records.filter(r => matchesEthnicity(r, ethnicity))
    setItems(top10(filtered, getRange(view), scoreOIC))
  }, [records, view, ethnicity])

  const range = getRange(view)
  const label = `${range.label} · Top ${items.length || 10} priority ${ethLabel(ethnicity)}households`

  const onFollowUpChange = useCallback(() => setFollowUpV(v => v + 1), [])

  return (
    <>
      <header style={{ background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)', color: 'white', padding: '20px 16px 16px', textAlign: 'center' }}>
        <h1 style={{ fontSize: '1.2em', fontWeight: 700, letterSpacing: '.3px' }}>⛪ OIC Outreach</h1>
        <p style={{ fontSize: '.78em', opacity: .65, marginTop: 4 }}>
          New homeowners within 20 miles · Updated {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
        </p>
        <a href="nearme.html" style={{ display: 'inline-block', marginTop: 10, fontSize: '.8em', color: 'rgba(255,255,255,.7)', textDecoration: 'none' }}>📍 Near me →</a>
      </header>

      <FollowUp records={records} version={followUpV} />

      <Filters period={view} onPeriodChange={setView} ethnicity={ethnicity} onEthnicityChange={setEthnicity} />

      {loading
        ? <div style={{ textAlign: 'center', color: '#bbb', padding: '40px 16px' }}>Loading…</div>
        : <>
            <SectionLabel label={label} />
            <MapView items={items} />
            <CardList items={items} onFollowUpChange={onFollowUpChange} />
          </>
      }

      <div style={{ padding: '0 16px 24px', fontSize: '.74em', color: '#aaa', lineHeight: 1.7 }}>
        <p>¹ Ethnicity estimated from US Census surname data (BISG model) — not verified.</p>
        <p>² Household size estimated from sqft where available (Lynchburg, Amherst), otherwise from sale price — treat as approximate.</p>
        <p>³ Likely rentals excluded: companies/LLCs, and homes whose tax mail still goes to a different address 90+ days after sale (absentee landlords, local or out-of-area).</p>
        <p>⁴ Priority score (max 5): Chinese=+2, all others=+1 (OIC welcomes everyone) · ≤2mi=+3, ≤5mi=+2, ≤10mi=+1.</p>
      </div>

      <footer style={{ textAlign: 'center', padding: 24, fontSize: '.75em', color: '#bbb', lineHeight: 2 }}>
        <div style={{ marginBottom: 14 }}>
          <button
            onClick={copyWeeklyReport}
            disabled={!records.length}
            style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #d0d8e8', background: 'white', color: '#1a73e8', fontSize: '.95em', fontWeight: 500, cursor: records.length ? 'pointer' : 'default', opacity: records.length ? 1 : 0.5 }}
          >
            📋 Copy weekly report
          </button>
          {reportStatus && <div style={{ marginTop: 6, color: '#888', fontSize: '.9em' }}>{reportStatus}</div>}
        </div>
        Data from Bedford, Lynchburg, Campbell, Amherst &amp; Appomattox County GIS &nbsp;·&nbsp;
        Ethnicity via surgeo BISG &nbsp;·&nbsp; Refreshed every Monday
        <br /><a href="disclaimer.html" style={{ color: '#bbb' }}>Disclaimer</a>
      </footer>
    </>
  )
}
