import type { HomeownerRecord, CardState } from './types'

export function cardKey(r: HomeownerRecord): string {
  const name = r.Owner1.replace(/[^a-z0-9]/gi, '').toLowerCase().slice(0, 12)
  const date = r.Sale1D.replace(/[^0-9]/g, '')
  const lat  = parseFloat(r.LAT || '0').toFixed(3)
  const lon  = parseFloat(r.LON || '0').toFixed(3)
  return `oic-${name}-${date}-${lat}-${lon}`
}

export function getState(r: HomeownerRecord): CardState {
  return JSON.parse(localStorage.getItem(cardKey(r)) ?? '{}')
}

export function setState(r: HomeownerRecord, patch: Partial<CardState>): void {
  const s = getState(r)
  localStorage.setItem(cardKey(r), JSON.stringify({ ...s, ...patch }))
}

export function lastSundayMidnight(now: Date = new Date()): number {
  const d = new Date(now)
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() - d.getDay())
  return d.getTime()
}

const MIGRATION_KEY = 'oic-migrated-visitedAt'

// One-time backfill: existing visited cards have no visitedAt. Stamp them
// with this Sunday's midnight so they show up in this week's report and
// naturally fall out next week.
export function migrateVisitedTimestamps(): void {
  if (localStorage.getItem(MIGRATION_KEY) === '1') return
  const ts = lastSundayMidnight()
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (!key?.startsWith('oic-') || key === MIGRATION_KEY) continue
    try {
      const state = JSON.parse(localStorage.getItem(key) ?? '{}') as CardState
      if (state.visited && state.visitedAt == null) {
        localStorage.setItem(key, JSON.stringify({ ...state, visitedAt: ts }))
      }
    } catch { /* skip non-JSON entries */ }
  }
  localStorage.setItem(MIGRATION_KEY, '1')
}
