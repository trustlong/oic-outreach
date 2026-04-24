import { useEffect, useState, useCallback } from 'react'
import type { HomeownerRecord, ScoredRecord } from '../lib/types'
import { loadCSV } from '../lib/csv'
import { lastMonthRange, lastYearRange } from '../lib/periods'
import { scoreOIC, top10 } from '../lib/scoring'
import Toggle from '../components/Toggle'
import SectionLabel from '../components/SectionLabel'
import CardList from '../components/CardList'
import FollowUp from '../components/FollowUp'

const TOGGLE_OPTIONS = [
  { value: 'month', label: 'Last Month' },
  { value: 'year',  label: 'Past 12 Months' },
]

export default function Home() {
  const [records, setRecords] = useState<HomeownerRecord[]>([])
  const [view, setView]       = useState<'month' | 'year'>('month')
  const [items, setItems]     = useState<ScoredRecord[]>([])
  const [followUpV, setFollowUpV] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadCSV('all_homeowners_20mi.csv').then(data => {
      setRecords(data)
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    if (!records.length) return
    const range = view === 'month' ? lastMonthRange() : lastYearRange()
    setItems(top10(records, range, scoreOIC))
  }, [records, view])

  const range = view === 'month' ? lastMonthRange() : lastYearRange()
  const label = view === 'month'
    ? `${range.label} · Top 10 priority households`
    : `${range.label} · Top 10 priority households`

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

      <Toggle view={view} options={TOGGLE_OPTIONS} onChange={v => setView(v as 'month' | 'year')} />

      {loading
        ? <div style={{ textAlign: 'center', color: '#bbb', padding: '40px 16px' }}>Loading…</div>
        : <>
            <SectionLabel label={label} />
            <CardList items={items} onFollowUpChange={onFollowUpChange} />
          </>
      }

      <div style={{ padding: '0 16px 24px', fontSize: '.74em', color: '#aaa', lineHeight: 1.7 }}>
        <p>¹ Ethnicity estimated from US Census surname data (BISG model) — not verified.</p>
        <p>² "Origin unknown" means the mailing address was already updated to the new home, or county has no mailing data (Campbell).</p>
        <p>³ Household size estimated from sqft where available (Lynchburg, Amherst), otherwise from sale price — treat as approximate.</p>
        <p>⁴ Companies, LLCs, and confirmed local movers are excluded.</p>
        <p>⁵ Priority score (max 7): ethnicity Chinese=+3, other Asian=+2, Hispanic/Black=+1 · origin out-of-state=+2, in-state/unknown=+1 · distance ≤5mi=+2, ≤10mi=+1.</p>
      </div>

      <footer style={{ textAlign: 'center', padding: 24, fontSize: '.75em', color: '#bbb', lineHeight: 2 }}>
        Data from Bedford, Lynchburg, Campbell, Amherst &amp; Appomattox County GIS &nbsp;·&nbsp;
        Ethnicity via surgeo BISG &nbsp;·&nbsp; Refreshed every Monday
        <br /><a href="disclaimer.html" style={{ color: '#bbb' }}>Disclaimer</a>
      </footer>
    </>
  )
}
